/* 
 * IBSimion C++ Wrapper for IBSimu
 * Combines CW (Steady-state) and PIC (Particle-in-Cell) simulation modes.
 * Parses parameters from a configuration file.
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <nlohmann/json.hpp>

// Access the IBSimu library
#include "epot_bicgstabsolver.hpp"
#include "meshvectorfield.hpp"
#include "mydxffile.hpp"
#include "gtkplotter.hpp"
#include "geomplotter.hpp"
#include "geometry.hpp"
#include "func_solid.hpp"
#include "dxf_solid.hpp"
#include "stl_solid.hpp"
#include "epot_efield.hpp"
#include "random.hpp"
#include "error.hpp"
#include "ibsimu.hpp"
#include "trajectorydiagnostics.hpp"
#include "particledatabase.hpp"
#include "particlestepper.hpp"
#include "scharge.hpp"
#include "particlediagplotter.hpp"
#include "gtkwindow.hpp"

using namespace std;

/// Configuration parsing helpers
using json = nlohmann::json;

double get_double(const json &cfg, const std::string &key, double def) {
    if (cfg.contains(key)) {
        try {
            if (cfg[key].is_number()) {
                return cfg[key].get<double>();
            } else if (cfg[key].is_string()) {
                return std::stod(cfg[key].get<std::string>());
            }
        } catch (...) {}
    }
    return def;
}

int get_int(const json &cfg, const std::string &key, int def) {
    if (cfg.contains(key)) {
        try {
            if (cfg[key].is_number()) {
                return cfg[key].get<int>();
            } else if (cfg[key].is_string()) {
                return std::stoi(cfg[key].get<std::string>());
            }
        } catch (...) {}
    }
    return def;
}

std::string get_str(const json &cfg, const std::string &key, const std::string &def) {
    if (cfg.contains(key)) {
        try {
            if (cfg[key].is_string()) {
                return cfg[key].get<std::string>();
            } else if (cfg[key].is_number()) {
                return std::to_string(cfg[key].get<double>());
            }
        } catch (...) {}
    }
    return def;
}

#include <random>

class SolenoidMagneticField : public VectorField {
private:
    std::vector<double> _z_coords;
    std::vector<double> _r_coords;
    std::vector<std::vector<double>> _Bz;
    std::vector<std::vector<double>> _Br;
    bool _valid;

public:
    SolenoidMagneticField(const std::string &filename, double scale) : _valid(false) {
        std::ifstream file(filename.c_str());
        if (!file.is_open()) {
            std::cerr << "Warning: Could not open magnetic field file " << filename << std::endl;
            return;
        }

        double z_val, r_val, bz_val, br_val;
        std::vector<double> raw_z, raw_r, raw_bz, raw_br;
        while (file >> z_val >> r_val >> bz_val >> br_val) {
            raw_z.push_back(z_val * 1e-3); // mm to m
            raw_r.push_back(r_val * 1e-3); // mm to m
            raw_bz.push_back(bz_val * scale);
            raw_br.push_back(br_val * scale);
        }
        file.close();

        if (raw_z.empty()) {
            std::cerr << "Warning: Magnetic field file " << filename << " is empty." << std::endl;
            return;
        }

        // Extract unique sorted Z and R coordinates
        for (double z : raw_z) {
            if (std::find_if(_z_coords.begin(), _z_coords.end(), [z](double val) { return std::abs(val - z) < 1e-7; }) == _z_coords.end()) {
                _z_coords.push_back(z);
            }
        }
        for (double r : raw_r) {
            if (std::find_if(_r_coords.begin(), _r_coords.end(), [r](double val) { return std::abs(val - r) < 1e-7; }) == _r_coords.end()) {
                _r_coords.push_back(r);
            }
        }

        std::sort(_z_coords.begin(), _z_coords.end());
        std::sort(_r_coords.begin(), _r_coords.end());

        size_t Nz = _z_coords.size();
        size_t Nr = _r_coords.size();

        _Bz.assign(Nz, std::vector<double>(Nr, 0.0));
        _Br.assign(Nz, std::vector<double>(Nr, 0.0));

        // Populate grids
        for (size_t i = 0; i < raw_z.size(); ++i) {
            auto it_z = std::lower_bound(_z_coords.begin(), _z_coords.end(), raw_z[i] - 1e-7);
            auto it_r = std::lower_bound(_r_coords.begin(), _r_coords.end(), raw_r[i] - 1e-7);
            size_t idx_z = std::distance(_z_coords.begin(), it_z);
            size_t idx_r = std::distance(_r_coords.begin(), it_r);
            if (idx_z < Nz && idx_r < Nr) {
                _Bz[idx_z][idx_r] = raw_bz[i];
                _Br[idx_z][idx_r] = raw_br[i];
            }
        }

        _valid = true;
        std::cout << "Loaded Solenoid Magnetic Field: " << filename 
                  << " (Grid: Nz=" << Nz << ", Nr=" << Nr << ")" << std::endl;
    }

    virtual const Vec3D operator()(const Vec3D &x) const {
        if (!_valid || _z_coords.empty() || _r_coords.empty()) {
            return Vec3D(0.0, 0.0, 0.0);
        }

        // x is Vec3D(x_pos, y_pos, z_pos).
        // Since we are mapping (Z, R, Bz, Br) in a 2D cylindrical format:
        // In 3D: z is longitudinal, r = sqrt(x_pos^2 + y_pos^2) is radial.
        // The magnetic field components: B_z is longitudinal, B_r is radial.
        // We project B_r along x_pos and y_pos:
        // B_x = B_r * (x_pos / r)
        // B_y = B_r * (y_pos / r)
        double z_pos = x[2];
        double x_pos = x[0];
        double y_pos = x[1];
        double r_pos = std::sqrt(x_pos * x_pos + y_pos * y_pos);

        // Find nearest coordinate indices
        auto it_z = std::lower_bound(_z_coords.begin(), _z_coords.end(), z_pos);
        auto it_r = std::lower_bound(_r_coords.begin(), _r_coords.end(), r_pos);

        size_t idx_z = std::distance(_z_coords.begin(), it_z);
        size_t idx_r = std::distance(_r_coords.begin(), it_r);

        size_t z0 = (idx_z == 0) ? 0 : idx_z - 1;
        size_t z1 = (idx_z >= _z_coords.size()) ? _z_coords.size() - 1 : idx_z;
        size_t r0 = (idx_r == 0) ? 0 : idx_r - 1;
        size_t r1 = (idx_r >= _r_coords.size()) ? _r_coords.size() - 1 : idx_r;

        double z_frac = 0.0;
        if (z1 != z0) {
            z_frac = (z_pos - _z_coords[z0]) / (_z_coords[z1] - _z_coords[z0]);
        }
        if (z_frac < 0.0) z_frac = 0.0;
        if (z_frac > 1.0) z_frac = 1.0;

        double r_frac = 0.0;
        if (r1 != r0) {
            r_frac = (r_pos - _r_coords[r0]) / (_r_coords[r1] - _r_coords[r0]);
        }
        if (r_frac < 0.0) r_frac = 0.0;
        if (r_frac > 1.0) r_frac = 1.0;

        // Bilinear interpolation for Bz
        double bz_00 = _Bz[z0][r0];
        double bz_10 = _Bz[z1][r0];
        double bz_01 = _Bz[z0][r1];
        double bz_11 = _Bz[z1][r1];

        double bz_val = (1.0 - z_frac) * (1.0 - r_frac) * bz_00 +
                       z_frac * (1.0 - r_frac) * bz_10 +
                       (1.0 - z_frac) * r_frac * bz_01 +
                       z_frac * r_frac * bz_11;

        // Bilinear interpolation for Br
        double br_00 = _Br[z0][r0];
        double br_10 = _Br[z1][r0];
        double br_01 = _Br[z0][r1];
        double br_11 = _Br[z1][r1];

        double br_val = (1.0 - z_frac) * (1.0 - r_frac) * br_00 +
                       z_frac * (1.0 - r_frac) * br_10 +
                       (1.0 - z_frac) * r_frac * br_01 +
                       z_frac * r_frac * br_11;

        double bx_val = 0.0;
        double by_val = 0.0;
        if (r_pos > 1e-9) {
            bx_val = br_val * (x_pos / r_pos);
            by_val = br_val * (y_pos / r_pos);
        }

        return Vec3D(bx_val, by_val, bz_val);
    }
};

// Function to generate snapshots in PIC mode
void snapshot( ParticleDataBase3D &pdb, string fn, double t )
{
    ibsimu.message(1) << "Snapshot at t = " << t << "\n";
    std::ostringstream ss;
    ss << fn << "_" << std::scientific << std::setprecision(8) << t << ".txt";
    string fn2 = ss.str();
    ofstream of( fn2.c_str() );
    for( size_t i = 0; i < pdb.size(); i++ ) {
        Particle3D p = pdb.particle(i);
        if( p.get_status() != PARTICLE_OK )
            continue;
        of << p[0] << " " // t
           << p[1] << " " // x
           << p[2] << " " // vx
           << p[3] << " " // y
           << p[4] << " " // vy
           << p[5] << " " // z
           << p[6] << " " // vz
           << p.m() << " " // mass
           << p.q() << "\n"; // charge
    }
}

int main( int argc, char **argv )
{
    try {
        ibsimu.set_message_threshold( MSG_VERBOSE, 1 );

        // Determine configuration file path
        std::string config_file = "config_scenario.json";
        if (argc > 1) {
            config_file = argv[1];
        }
        
        std::cout << "Loading configuration from: " << config_file << std::endl;
        std::ifstream file(config_file.c_str());
        if (!file.is_open()) {
            std::cerr << "Could not open config file: " << config_file << std::endl;
            return 1;
        }
        json cfg;
        try {
            file >> cfg;
        } catch (const std::exception &e) {
            std::cerr << "JSON Parse error: " << e.what() << std::endl;
            file.close();
            return 1;
        }
        file.close();

        // Parameters
        std::string mode = get_str(cfg, "mode", "CW"); // CW or PIC
        std::string domain_type = get_str(cfg, "domain_type", "3D");
        double h_param = get_double(cfg, "h", 1e-3); // mesh size (m)

        // Geometry boundaries
        double xmin = get_double(cfg, "xmin", -0.035);
        double xmax = get_double(cfg, "xmax", 0.035);
        double ymin = get_double(cfg, "ymin", -0.035);
        double ymax = get_double(cfg, "ymax", 0.035);
        double zmin = get_double(cfg, "zmin", 0.0);
        double zmax = get_double(cfg, "zmax", 0.36);
        double rmax = get_double(cfg, "rmax", 0.035);
        
        int threads = get_int(cfg, "threads", 4);
        ibsimu.set_thread_count( threads );

        // Grid Node Calculations and Geometry Construction
        Geometry *geom_ptr = NULL;
        if (domain_type == "2D_CYL") {
            int nz = (int)std::round((zmax - zmin) / h_param) + 1;
            int nr = (int)std::round(rmax / h_param) + 1;
            std::cout << "Mesh dimensions (2D Cilíndrico): " << nz << "x" << nr << "x1"
                      << " with step h = " << h_param << " m" << std::endl;
            geom_ptr = new Geometry( MODE_CYL, Int3D(nz, nr, 1), Vec3D(zmin, 0.0, 0.0), h_param );
        } else if (domain_type == "2D") {
            int nz = (int)std::round((zmax - zmin) / h_param) + 1;
            int ny = (int)std::round((ymax - ymin) / h_param) + 1;
            std::cout << "Mesh dimensions (2D Cartesiano): " << nz << "x" << ny << "x1"
                      << " with step h = " << h_param << " m" << std::endl;
            geom_ptr = new Geometry( MODE_2D, Int3D(nz, ny, 1), Vec3D(zmin, ymin, 0.0), h_param );
        } else if (domain_type == "2DCYL") {
            int nz = (int)std::round((zmax - zmin) / h_param) + 1;
            int nr = (int)std::round(rmax / h_param) + 1;
            std::cout << "Mesh dimensions (2D Cilíndrico Especial 2DCYL): " << nz << "x" << nr << "x1"
                      << " with step h = " << h_param << " m" << std::endl;
            geom_ptr = new Geometry( MODE_CYL, Int3D(nz, nr, 1), Vec3D(zmin, 0.0, 0.0), h_param );
        } else {
            int nx = (int)std::round((xmax - xmin) / h_param) + 1;
            int ny = (int)std::round((ymax - ymin) / h_param) + 1;
            int nz = (int)std::round((zmax - zmin) / h_param) + 1;
            std::cout << "Mesh dimensions (3D Cartesiano): " << nx << "x" << ny << "x" << nz 
                      << " with step h = " << h_param << " m" << std::endl;
            geom_ptr = new Geometry( MODE_3D, Int3D(nx, ny, nz), Vec3D(xmin, ymin, zmin), h_param );
        }
        Geometry &geom = *geom_ptr;

        bool pmirror[6] = { false, false, false, false, false, false };
        if (cfg.contains("mirror") && cfg["mirror"].is_array() && cfg["mirror"].size() >= 6) {
            for(int i = 0; i < 6; ++i) {
                try {
                    pmirror[i] = cfg["mirror"][i].get<bool>();
                } catch(...) {}
            }
        }

        // Set external boundary conditions (6 faces: 1=xmin, 2=xmax, 3=ymin, 4=ymax, 5=zmin, 6=zmax)
        if (cfg.contains("boundaries") && cfg["boundaries"].is_array() && cfg["boundaries"].size() >= 6) {
            std::cout << "Configuring custom external boundary conditions..." << std::endl;
            for (int i = 0; i < 6; ++i) {
                try {
                    std::string b_str = cfg["boundaries"][i].get<std::string>();
                    bound_e b_type = BOUND_DIRICHLET;
                    if (b_str == "Neumann") {
                        b_type = BOUND_NEUMANN;
                    }
                    geom.set_boundary( i + 1, Bound(b_type, 0.0) );
                } catch(...) {}
            }
        } else {
            if (cfg.contains("geometries") && cfg["geometries"].is_array() && !cfg["geometries"].empty()) {
                geom.set_boundary( 1, Bound(BOUND_NEUMANN, 0.0) ); // xmin
                geom.set_boundary( 2, Bound(BOUND_NEUMANN, 0.0) ); // xmax
                geom.set_boundary( 3, Bound(BOUND_NEUMANN, 0.0) ); // ymin
                geom.set_boundary( 4, Bound(BOUND_NEUMANN, 0.0) ); // ymax
            } else {
                geom.set_boundary( 1, Bound(BOUND_DIRICHLET, 0.0) ); // xmin grounded
                geom.set_boundary( 2, Bound(BOUND_DIRICHLET, 0.0) ); // xmax grounded
                geom.set_boundary( 3, Bound(BOUND_DIRICHLET, 0.0) ); // ymin grounded
                geom.set_boundary( 4, Bound(BOUND_DIRICHLET, 0.0) ); // ymax grounded
            }
        }

        // Dynamic solids and boundary IDs
        uint32_t boundary_id = 7;
        
        if (cfg.contains("geometries") && cfg["geometries"].is_array()) {
            for (const auto& item : cfg["geometries"]) {
                std::string name = get_str(item, "name", "Eletrodo");
                std::string file_path = get_str(item, "file_path", "");
                double voltage = get_double(item, "voltage", 0.0);
                std::string btype_str = get_str(item, "type", "Dirichlet");
                
                bound_e btype = BOUND_DIRICHLET;
                if (btype_str == "Neumann") {
                    btype = BOUND_NEUMANN;
                }
                
                double tx = 0.0, ty = 0.0, tz = 0.0;
                if (item.contains("translation") && item["translation"].is_array() && item["translation"].size() >= 3) {
                    try {
                        tx = item["translation"][0].get<double>();
                        ty = item["translation"][1].get<double>();
                        tz = item["translation"][2].get<double>();
                    } catch(...) {}
                }
                
                double local_scale = get_double(item, "scale", 1e-3);

                if (file_path.empty()) {
                    continue;
                }
                
                size_t dot_idx = file_path.find_last_of(".");
                if (dot_idx == std::string::npos) continue;
                std::string ext = file_path.substr(dot_idx + 1);
                std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
                
                if (ext == "stl") {
                    std::cout << "Loading STL Geometry: " << name << " (" << file_path << ") at ID " << boundary_id << std::endl;
                    try {
                        STLSolid *s = new STLSolid(file_path);
                        s->scale(local_scale);
                        s->translate(Vec3D(tx, ty, tz));
                        geom.set_solid(boundary_id, s);
                        geom.set_boundary(boundary_id, Bound(btype, voltage));
                        boundary_id++;
                    } catch (const std::exception &e) {
                        std::cerr << "Error loading STL file " << file_path << ": " << e.what() << std::endl;
                    }
                } else if (ext == "dxf") {
                    std::cout << "Loading DXF Geometry: " << name << " (" << file_path << ") at ID " << boundary_id << std::endl;
                    try {
                        MyDXFFile *dxffile = new MyDXFFile;
                        dxffile->set_warning_level(2);
                        dxffile->read(file_path);
                        
                        std::string layer_name = get_str(item, "layer", "");
                        if (layer_name.empty()) {
                            layer_name = name;
                        }
                        
                        DXFSolid *s = new DXFSolid(dxffile, layer_name);
                        s->scale(local_scale);
                        if (domain_type == "3D" || domain_type == "3D_CART") {
                            std::string mapping_str = get_str(item, "mapping", "rotz");
                            if (mapping_str == "rotx") {
                                s->define_2x3_mapping(DXFSolid::rotx);
                            } else if (mapping_str == "unity") {
                                s->define_2x3_mapping(DXFSolid::unity);
                            } else {
                                s->define_2x3_mapping(DXFSolid::rotz);
                            }
                        }
                        s->translate(Vec3D(tx, ty, tz));
                        geom.set_solid(boundary_id, s);
                        geom.set_boundary(boundary_id, Bound(btype, voltage));
                        boundary_id++;
                    } catch (const std::exception &e) {
                        std::cerr << "Error loading DXF file " << file_path << ": " << e.what() << std::endl;
                    }
                }
            }
        }

        geom.build_mesh();
        geom.build_surface();
        geom.save( "tofgeom.dat" );

        std::cout << "Saving surface mesh to geometry.obj..." << std::endl;
        ofstream fileObj( "geometry.obj" );
        for( uint32_t a = 0; a < geom.surface_vertexc(); a++ ) {
            const Vec3D &v = geom.surface_vertex(a);
            fileObj << "v " << v[0] << " " << v[1] << " " << v[2] << "\n";
        }
        for( uint32_t a = 0; a < geom.surface_trianglec(); a++ ) {
            const VTriangle &t = geom.surface_triangle(a);
            fileObj << "f " << (t[0]+1) << " " << (t[1]+1) << " " << (t[2]+1) << "\n";
        }
        fileObj.close();

        // Construct the fields
        EpotField epot( geom );
        MeshScalarField scharge( geom );
        MeshScalarField scharge_ave( geom );
        
        // Dynamic Magnetic Field
        VectorField *bfield = NULL;
        std::string bfield_file = get_str(cfg, "magnetic_field_file", "");
        if (!bfield_file.empty()) {
            double bfield_scale = get_double(cfg, "magnetic_field_scale", 1.0);
            bfield = new SolenoidMagneticField( bfield_file, bfield_scale );
        } else {
            bfield = new MeshVectorField();
        }

        EpotEfield efield( epot );
        field_extrpl_e efldextrpl[6];
        for (int i = 0; i < 6; ++i) {
            efldextrpl[i] = pmirror[i] ? FIELD_SYMMETRIC_POTENTIAL : FIELD_EXTRAPOLATE;
        }
        efield.set_extrapolation( efldextrpl );

        EpotBiCGSTABSolver solver( geom );
        double solver_eps = get_double(cfg, "solver_eps", 1e-4);
        int solver_imax = get_int(cfg, "solver_imax", 1000000);
        solver.set_eps( solver_eps );
        solver.set_imax( solver_imax );

        InitialPlasma *init_plasma = NULL;
        if (cfg.contains("plasma_voltage")) {
            double plasma_voltage = get_double(cfg, "plasma_voltage", 0.0);
            double debye = get_double(cfg, "plasma_debye", 2e-4);
            std::string p_axis_str = get_str(cfg, "plasma_axis", "Z");
            
            decltype(AXIS_Z) p_axis = AXIS_Z;
            if (p_axis_str == "X") p_axis = AXIS_X;
            else if (p_axis_str == "Y") p_axis = AXIS_Y;
            
            init_plasma = new InitialPlasma( p_axis, debye );
            solver.set_initial_plasma( plasma_voltage, init_plasma );
            std::cout << "Configured Initial Plasma at axis " << p_axis_str 
                      << " with voltage " << plasma_voltage 
                      << " V and Debye-like transition " << debye << " m." << std::endl;
        }        ParticleDataBase *pdb_ptr = NULL;
        if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
            pdb_ptr = new ParticleDataBaseCyl( geom );
        } else if (domain_type == "2D") {
            pdb_ptr = new ParticleDataBase2D( geom );
        } else {
            pdb_ptr = new ParticleDataBase3D( geom );
        }
        ParticleDataBase &pdb = *pdb_ptr;
        pdb.set_mirror( pmirror );

        if (mode == "CW") {
            std::cout << "Starting Continuous Wave (CW) Steady-State Simulation..." << std::endl;
            pdb.set_surface_collision( false );

            int max_iterations = get_int(cfg, "iterations", 5);
            std::cout << "Running CW simulation with " << max_iterations << " iterations." << std::endl;
            for( size_t iter = 0; iter < max_iterations; iter++ ) {
                if (iter == 1 && cfg.contains("plasma_voltage")) {
                    double rhoe = pdb.get_rhosum();
                    double Te = get_double(cfg, "plasma_Te", 5.0);
                    double Up = get_double(cfg, "plasma_voltage", 0.0);
                    solver.set_pexp_plasma( rhoe, Te, Up );
                    std::cout << "Configured positive ion plasma (PEXP) with rhoe = " << rhoe 
                              << ", Te = " << Te << " eV, Up = " << Up << " V." << std::endl;
                }
                
                if( iter == 0 ) {
                    scharge_ave = scharge;
                } else {
                    double sc_alpha = get_double(cfg, "sc_alpha", 1.0);
                    double sc_beta = 1.0 - sc_alpha;
                    uint32_t nodecount = scharge.nodecount();
                    for( uint32_t b = 0; b < nodecount; b++ ) {
                        scharge_ave(b) = sc_alpha*scharge(b) + sc_beta*scharge_ave(b);
                    }
                }

                solver.solve( epot, scharge_ave );
                efield.recalculate();
                pdb.clear();
                
                // Add beams dynamically
                if (cfg.contains("beams") && cfg["beams"].is_array()) {
                    for (const auto& beam : cfg["beams"]) {
                        std::string nome = get_str(beam, "nome", "Feixe");
                        double mass = get_double(beam, "massa", 136.2);
                        double charge = get_double(beam, "carga", 1.0);
                        uint32_t n_part = get_int(beam, "particulas", 5000);
                        double energy = get_double(beam, "energy", 1000.0);
                        double current_ma = get_double(beam, "corrente", 1.0);
                        double radius = get_double(beam, "radius", 5e-4);
                        double emittance = get_double(beam, "emittance", 0.0);
                        double z_start = get_double(beam, "z_start", 0.081);
                        
                        double current = current_ma * 1e-3; // Convert mA to A
                        
                        double Tp = get_double(beam, "Tp", 0.02); 
                        double Tt = get_double(beam, "Tt", 0.0);
                        
                        std::string dist_type = get_str(beam, "distribution", "Uniform");
                        std::string shape = get_str(beam, "shape", "cylindrical");
                        bool is_rect = (dist_type == "Retangular" || dist_type == "rectangular" || dist_type == "Rectangular" || shape == "rectangular");
                        
                        double tam_x = get_double(beam, "tam_x", get_double(beam, "size1", get_double(beam, "radius", 5e-4)));
                        double tam_y = get_double(beam, "tam_y", get_double(beam, "size2", 5e-4));
                        
                        // Conversão de velocidade precisa baseada no benchmark de TOF
                        double energy_val = energy;
                        std::string input_type = get_str(beam, "beam_input_type", "energia");
                        if (input_type == "velocidade") {
                            double velocity = get_double(beam, "velocity", 0.0);
                            energy_val = mass * std::pow(velocity / 1.3884e4, 2.0);
                            std::cout << "Converting input velocity " << velocity << " m/s to energy " << energy_val << " eV" << std::endl;
                        }
                        
                        if (Tt <= 0.0) {
                            double scale_dim = is_rect ? tam_x : radius;
                            if (emittance > 0.0 && scale_dim > 0.0) {
                                Tt = energy_val * (emittance * emittance) / (scale_dim * scale_dim);
                            } else {
                                Tt = 0.1; 
                            }
                        }
                        
                        double orig_x = get_double(beam, "orig_x", 0.0);
                        double orig_y = get_double(beam, "orig_y", 0.0);
                        double orig_z = get_double(beam, "orig_z", z_start);
                        Vec3D origo(orig_x, orig_y, orig_z);
                        
                        Vec3D bdir1(1.0, 0.0, 0.0);
                        Vec3D bdir2(0.0, 1.0, 0.0);
                        double bdir_y = get_double(beam, "dir_y", 0.0);
                        if (bdir_y < -0.5) {
                            bdir2 = Vec3D(0.0, 0.0, 1.0);
                        }

                        if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                            ParticleDataBaseCyl *pdb_cyl = static_cast<ParticleDataBaseCyl*>(pdb_ptr);
                            Vec3D origo_2d(orig_z, 0.0, 0.0);
                            Vec3D bdir_2d(1.0, 0.0, 0.0);
                            double J = current / (M_PI * radius * radius + 1e-20);
                            if (beam.contains("current_density")) {
                                J = get_double(beam, "current_density", J);
                            }
                            std::cout << "Injecting 2D Cylindrical beam: " << nome << ", particles: " << n_part
                                      << ", J: " << J << ", energy: " << energy_val << " eV, radius: " << radius << std::endl;
                            pdb_cyl->add_2d_beam_with_energy(
                                n_part, J, charge, mass, energy_val, Tp, Tt,
                                orig_z, 0.0, 0.0, radius
                            );
                        } else if (domain_type == "2D") {
                            ParticleDataBase2D *pdb_2d = static_cast<ParticleDataBase2D*>(pdb_ptr);
                            double J = current / (2.0 * radius + 1e-20);
                            if (beam.contains("current_density")) {
                                J = get_double(beam, "current_density", J);
                            }
                            std::cout << "Injecting 2D Planar beam: " << nome << ", particles: " << n_part
                                      << ", J: " << J << ", energy: " << energy_val << " eV, radius: " << radius << std::endl;
                            pdb_2d->add_2d_beam_with_energy(
                                n_part, J, charge, mass, energy_val, Tp, Tt,
                                orig_z, orig_y, 0.0, radius
                            );
                        } else {
                            ParticleDataBase3D *pdb_3d = static_cast<ParticleDataBase3D*>(pdb_ptr);
                            if (is_rect) {
                                // Correção de J_rect física nominal sem fator multiplicador 4 fixo
                                double J_rect = current / (tam_x * tam_y + 1e-20);
                                if (beam.contains("current_density")) {
                                    J_rect = get_double(beam, "current_density", J_rect);
                                }
                                std::cout << "Injecting 3D Rectangular beam: " << nome << ", particles: " << n_part
                                          << ", J: " << J_rect << ", energy: " << energy_val << " eV" << std::endl;
                                pdb_3d->add_rectangular_beam_with_energy(
                                    n_part, J_rect, charge, mass, energy_val, Tp, Tt,
                                    origo, bdir1, bdir2, tam_x, tam_y
                                );
                            } else {
                                double J = current / (M_PI * radius * radius + 1e-20);
                                if (beam.contains("current_density")) {
                                    J = get_double(beam, "current_density", J);
                                }
                                std::cout << "Injecting 3D Cylindrical beam: " << nome << ", particles: " << n_part
                                          << ", J: " << J << ", energy: " << energy_val << " eV" << std::endl;
                                pdb_3d->add_cylindrical_beam_with_energy(
                                    n_part, J, charge, mass, energy_val, Tp, Tt, 
                                    origo, bdir1, bdir2, radius
                                );
                            }
                        }
                    }
                }
                
                pdb.iterate_trajectories( scharge, efield, *bfield );
            }
            
            pdb.save("pdb.dat");

            std::cout << "Saving trajectories to trajectories.txt..." << std::endl;
            ofstream fileTraj( "trajectories.txt" );
            if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                ParticleDataBaseCyl *pdb_cyl = static_cast<ParticleDataBaseCyl*>(pdb_ptr);
                for( size_t k = 0; k < pdb_cyl->size(); k++ ) {
                    const ParticleCyl &pp = pdb_cyl->particle( k );
                    if ( pdb_cyl->size() > 500 && k % (pdb_cyl->size() / 500 + 1) != 0 ) continue;
                    
                    fileTraj << "TID " << k << " " << pp.m() << " " << pp.q() << " " << pp.IQ() << "\n";
                    for ( size_t i = 0; i < pp.traj_size(); i++ ) {
                        const ParticlePCyl &pt = pp.traj( i );
                        fileTraj << pt[1] << " " << 0.0 << " " << pt[0] << " " << pt[3] << "\n";
                    }
                }
            } else if (domain_type == "2D") {
                ParticleDataBase2D *pdb_2d = static_cast<ParticleDataBase2D*>(pdb_ptr);
                for( size_t k = 0; k < pdb_2d->size(); k++ ) {
                    const Particle2D &pp = pdb_2d->particle( k );
                    if ( pdb_2d->size() > 500 && k % (pdb_2d->size() / 500 + 1) != 0 ) continue;
                    
                    fileTraj << "TID " << k << " " << pp.m() << " " << pp.q() << " " << pp.IQ() << "\n";
                    for ( size_t i = 0; i < pp.traj_size(); i++ ) {
                        const ParticleP2D &pt = pp.traj( i );
                        fileTraj << 0.0 << " " << pt[1] << " " << pt[0] << " " << pt[3] << "\n";
                    }
                }
            } else {
                ParticleDataBase3D *pdb_3d = static_cast<ParticleDataBase3D*>(pdb_ptr);
                for( size_t k = 0; k < pdb_3d->size(); k++ ) {
                    const Particle3D &pp = pdb_3d->particle( k );
                    if ( pdb_3d->size() > 500 && k % (pdb_3d->size() / 500 + 1) != 0 ) continue;
                    
                    fileTraj << "TID " << k << " " << pp.m() << " " << pp.q() << " " << pp.IQ() << "\n";
                    for ( size_t i = 0; i < pp.traj_size(); i++ ) {
                        const ParticleP3D &pt = pp.traj( i );
                        fileTraj << pt[0] << " " << pt[1] << " " << pt[3] << " " << pt[5] << "\n";
                    }
                }
            }
            fileTraj.close();

            // Diagnostics plane
            double diag_plane_z = get_double(cfg, "diag_plane_z", 0.3549);
            std::vector<trajectory_diagnostic_e> diagnostics;
            diagnostics.push_back( DIAG_T );
            diagnostics.push_back( DIAG_X );
            diagnostics.push_back( DIAG_VX );
            diagnostics.push_back( DIAG_Y );
            diagnostics.push_back( DIAG_VY );
            diagnostics.push_back( DIAG_Z );
            diagnostics.push_back( DIAG_VZ );
            diagnostics.push_back( DIAG_MASS );
            diagnostics.push_back( DIAG_QM );
            diagnostics.push_back( DIAG_CURR );

            TrajectoryDiagnosticData tof;
            if (domain_type == "2D_CYL" || domain_type == "2DCYL" || domain_type == "2D") {
                pdb.trajectories_at_plane( tof, AXIS_X, diag_plane_z, diagnostics );
            } else {
                pdb.trajectories_at_plane( tof, AXIS_Z, diag_plane_z, diagnostics );
            }
            tof.export_data( "tof.txt" );

            // Histogram
            if (tof.diag_size() > 0 && tof.traj_size() > 0) {
                const TrajectoryDiagnosticColumn &time = tof(0);
                Histogram1D tof_histo( 150, time.data() );
                ofstream of_histo("tof_histo.txt" );
                for( uint32_t i = 0; i < tof_histo.n(); i++ ) {
                    of_histo << tof_histo.coord(i) << " " << tof_histo(i) << "\n";
                }
            }

            // Export raw coordinates
            ofstream fileOut( "tof_out.txt" );
            if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                ParticleDataBaseCyl *pdb_cyl = static_cast<ParticleDataBaseCyl*>(pdb_ptr);
                for( size_t k = 0; k < pdb_cyl->size(); k++ ) {
                    const ParticleCyl &pp = pdb_cyl->particle( k );
                    fileOut << setw(12) << pp.IQ() << " " << setw(12) << pp.m() << " ";
                    for( size_t j = 0; j < 5; j ++ )
                        fileOut << setw(12) << pp(j) << " ";
                    fileOut << "\n";
                }
            } else if (domain_type == "2D") {
                ParticleDataBase2D *pdb_2d = static_cast<ParticleDataBase2D*>(pdb_ptr);
                for( size_t k = 0; k < pdb_2d->size(); k++ ) {
                    const Particle2D &pp = pdb_2d->particle( k );
                    fileOut << setw(12) << pp.IQ() << " " << setw(12) << pp.m() << " ";
                    for( size_t j = 0; j < 5; j ++ )
                        fileOut << setw(12) << pp(j) << " ";
                    fileOut << "\n";
                }
            } else {
                ParticleDataBase3D *pdb_3d = static_cast<ParticleDataBase3D*>(pdb_ptr);
                for( size_t k = 0; k < pdb_3d->size(); k++ ) {
                    const Particle3D &pp = pdb_3d->particle( k );
                    fileOut << setw(12) << pp.IQ() << " " << setw(12) << pp.m() << " ";
                    for( size_t j = 0; j < 7; j ++ )
                        fileOut << setw(12) << pp(j) << " ";
                    fileOut << "\n";
                }
            }
            fileOut.close();
        } 
        else if (mode == "PIC") {
            std::cout << "Starting Particle-in-Cell (PIC) Simulation..." << std::endl;
            ParticleDataBase3D &pdb_3d = *static_cast<ParticleDataBase3D*>(pdb_ptr);
            pdb_3d.set_save_trajectories( 1 );

            double C = CHARGE_E;
            std::random_device rd;
            std::mt19937 gen(rd());
            std::uniform_real_distribution<double> dist_uni(0.0, 1.0);
            std::normal_distribution<double> dist_norm(0.0, 1.0);

            if (cfg.contains("beams") && cfg["beams"].is_array()) {
                for (const auto& beam : cfg["beams"]) {
                    std::string nome = get_str(beam, "nome", "Feixe");
                    double mass = get_double(beam, "massa", 136.2);
                    double charge = get_double(beam, "carga", 1.0);
                    uint32_t n_part = get_int(beam, "particulas", 3000);
                    double energy = get_double(beam, "energy", 1000.0);
                    double radius = get_double(beam, "radius", 5e-4);
                    double emittance = get_double(beam, "emittance", 0.0);
                    double z_start = get_double(beam, "z_start", 0.081);
                    
                    std::string dist_type = get_str(beam, "distribution", "Uniform");
                    std::string shape = get_str(beam, "shape", "cylindrical");
                    bool is_rect = (dist_type == "Retangular" || dist_type == "rectangular" || dist_type == "Rectangular" || shape == "rectangular");
                    
                    double tam_x = get_double(beam, "tam_x", get_double(beam, "size1", get_double(beam, "radius", 5e-4)));
                    double tam_y = get_double(beam, "tam_y", get_double(beam, "size2", 5e-4));
                    
                    // Conversão de velocidade precisa baseada no benchmark de TOF
                    double energy_val = energy;
                    std::string input_type = get_str(beam, "beam_input_type", "energia");
                    if (input_type == "velocidade") {
                        double velocity = get_double(beam, "velocity", 0.0);
                        energy_val = mass * std::pow(velocity / 1.3884e4, 2.0);
                    }
                    
                    double v_z_mean = 1.3884e4 * std::sqrt(energy_val / mass);
                    
                    double Tp = get_double(beam, "Tp", 0.02);
                    double Tt = get_double(beam, "Tt", 0.0);
                    if (Tt <= 0.0) {
                        double scale_dim = is_rect ? tam_x : radius;
                        if (emittance > 0.0 && scale_dim > 0.0) {
                            Tt = energy_val * (emittance * emittance) / (scale_dim * scale_dim);
                        } else {
                            Tt = 0.1;
                        }
                    }

                    double dvp = 1.3884e4 * std::sqrt(Tp / mass);
                    double dvt = 1.3884e4 * std::sqrt(Tt / mass);

                    std::cout << "Adding particles for beam '" << nome << "' (is_rect=" << is_rect << "): " 
                              << n_part << " particles, mass=" << mass << " u" << std::endl;

                    // Ler origem customizada
                    double orig_x = get_double(beam, "orig_x", 0.0);
                    double orig_y = get_double(beam, "orig_y", 0.0);
                    double orig_z = get_double(beam, "orig_z", z_start);
                    Vec3D origo(orig_x, orig_y, orig_z);

                    // Ler direção customizada e formar base ortonormal 3D
                    double dir_x = 0.0;
                    double dir_z = 1.0;
                    if (beam.contains("dir_x") && beam.contains("dir_z")) {
                        dir_x = get_double(beam, "dir_x", 0.0);
                        dir_z = get_double(beam, "dir_z", 1.0);
                    }
                    
                    double dir_len = std::sqrt(dir_x*dir_x + dir_z*dir_z);
                    double d_x = 0.0, d_z = 1.0;
                    if (dir_len > 1e-9) {
                        d_x = dir_x / dir_len;
                        d_z = dir_z / dir_len;
                    }
                    Vec3D dir_vec(d_x, 0.0, d_z);
                    
                    double u_x = -d_z;
                    double u_z = d_x;
                    double u_len = std::sqrt(u_x*u_x + u_z*u_z);
                    if (u_len > 1e-9) {
                        u_x /= u_len;
                        u_z /= u_len;
                    } else {
                        u_x = 1.0;
                        u_z = 0.0;
                    }
                    Vec3D u_vec(u_x, 0.0, u_z);

                    // Produto vetorial manual de dir_vec e u_vec
                    Vec3D v_vec(
                        dir_vec[1]*u_vec[2] - dir_vec[2]*u_vec[1],
                        dir_vec[2]*u_vec[0] - dir_vec[0]*u_vec[2],
                        dir_vec[0]*u_vec[1] - dir_vec[1]*u_vec[0]
                    );

                    uint32_t i_part = 0;
                    while (i_part < n_part) {
                        double x_loc = 0.0;
                        double y_loc = 0.0;
                        if (is_rect) {
                            if (dist_type == "Gaussian") {
                                x_loc = dist_norm(gen) * tam_x * 0.5;
                                y_loc = dist_norm(gen) * tam_y * 0.5;
                            } else {
                                x_loc = (dist_uni(gen) - 0.5) * 2.0 * tam_x;
                                y_loc = (dist_uni(gen) - 0.5) * 2.0 * tam_y;
                            }
                        } else {
                            if (dist_type == "Gaussian") {
                                double u1 = dist_uni(gen);
                                double u2 = dist_uni(gen);
                                double r = radius * 0.5 * std::sqrt(-2.0 * std::log(u1 + 1e-20));
                                double theta = 2.0 * M_PI * u2;
                                x_loc = r * std::cos(theta);
                                y_loc = r * std::sin(theta);
                            } else {
                                double u1 = dist_uni(gen);
                                double u2 = dist_uni(gen);
                                double r = radius * std::sqrt(u1);
                                double theta = 2.0 * M_PI * u2;
                                x_loc = r * std::cos(theta);
                                y_loc = r * std::sin(theta);
                            }
                        }

                        // Cálculo posicional com projeção manual na base ortonormal
                        double pos_x = origo[0] + x_loc * u_vec[0] + y_loc * v_vec[0];
                        double pos_y = origo[1] + x_loc * u_vec[1] + y_loc * v_vec[1];
                        double pos_z = origo[2] + x_loc * u_vec[2] + y_loc * v_vec[2];

                        double v_loc_x = dist_norm(gen) * dvt;
                        double v_loc_y = dist_norm(gen) * dvt;
                        double v_loc_z = v_z_mean + dist_norm(gen) * dvp;

                        // Cálculo de velocidade com projeção manual na base ortonormal
                        double vel_x = v_loc_x * u_vec[0] + v_loc_y * v_vec[0] + v_loc_z * dir_vec[0];
                        double vel_y = v_loc_x * u_vec[1] + v_loc_y * v_vec[1] + v_loc_z * dir_vec[1];
                        double vel_z = v_loc_x * u_vec[2] + v_loc_y * v_vec[2] + v_loc_z * dir_vec[2];

                        pdb_3d.add_particle(C, charge, mass, ParticleP3D(0.0, pos_x, vel_x, pos_y, vel_y, pos_z, vel_z));
                        i_part++;
                    }
                }
            }

            std::vector<double> unique_masses;
            if (cfg.contains("beams") && cfg["beams"].is_array()) {
                for (const auto& beam : cfg["beams"]) {
                    double mass = get_double(beam, "massa", 136.2) * 1.66053906660e-27;
                    bool found = false;
                    for (double m_val : unique_masses) {
                        if (std::abs(mass - m_val) / m_val < 1e-3) {
                            found = true;
                            break;
                        }
                    }
                    if (!found) {
                        unique_masses.push_back(mass);
                    }
                }
            }

            double fast_species_mass = -1.0;
            bool optimize_pic_for_ions = false;
            if (unique_masses.size() > 1) {
                std::sort(unique_masses.begin(), unique_masses.end());
                double ratio = unique_masses[1] / unique_masses[0];
                if (ratio >= 100.0) {
                    fast_species_mass = unique_masses[0];
                    optimize_pic_for_ions = true;
                    std::cout << "Dynamic PIC Species Analysis: Light species detected (mass = " 
                              << fast_species_mass << " kg). Mass ratio = " << ratio 
                              << ". Treating light species as static background charge." << std::endl;
                }
            }

            snapshot( pdb_3d, "pout", 0.0 );
            ofstream of_field( "field.txt" );

            double dt = get_double(cfg, "dt", 0.5e-7);
            double T_final = get_double(cfg, "T_final", 5.1e-6);
            double t = 0.0;
            int step = 0;
            
            while( t < T_final ) {
                scharge.clear();

                ParticleStepper<ParticleP3D> ps( dt, 1, pmirror, &scharge, 
                                                 &efield, bfield, &geom );
                ParticleStepper<ParticleP3D> ps_static( 0.0, 1, pmirror, &scharge, 
                                                       &efield, bfield, &geom );

                for( uint32_t a = 0; a < pdb_3d.size(); a++ ) {
                    Particle3D &p = pdb_3d.particle( a );
                    if( p.get_status() != PARTICLE_OK )
                        continue;

                    double pm = p.m();
                    bool is_fast = (optimize_pic_for_ions && std::abs(pm - fast_species_mass) / fast_species_mass < 1e-3);

                    if( is_fast ) {
                        if( p[0] == 0 )
                            ps_static.initialize( &p, a );
                        ps_static.step( &p, a );
                        p[0] += dt;
                    } else {
                        if( p[0] == 0 )
                            ps.initialize( &p, a );
                        ps.step( &p, a );
                    }
                }

                scharge_finalize_step_pic( scharge );

                solver.solve( epot, scharge );
                efield.recalculate();

                step++;
                t = step*dt;

                snapshot( pdb_3d, "pout", t );
                of_field << t << " " << epot(Vec3D(0,0,0)) << "\n";
            }
            
            pdb_3d.save("pdb.dat");

            std::cout << "Saving PIC trajectories to trajectories.txt..." << std::endl;
            ofstream fileTraj( "trajectories.txt" );
            for( size_t k = 0; k < pdb_3d.size(); k++ ) {
                const Particle3D &pp = pdb_3d.particle( k );
                if ( pdb_3d.size() > 500 && k % (pdb_3d.size() / 500 + 1) != 0 ) continue;
                
                fileTraj << "TID " << k << " " << pp.m() << " " << pp.q() << " " << pp.IQ() << "\n";
                for ( size_t i = 0; i < pp.traj_size(); i++ ) {
                    const ParticleP3D &pt = pp.traj( i );
                    fileTraj << pt[0] << " " << pt[1] << " " << pt[3] << " " << pt[5] << "\n";
                }
            }
            fileTraj.close();
        }

        // Export 3D/2D fields including Potential, Electric Field, and Charge Density
        std::cout << "-> Exporting Potential and Electric Field..." << std::endl;
        std::ofstream pot_file("potential_field.dat");
        std::ofstream rho_file("charge_density.dat");
        if (pot_file.is_open() && rho_file.is_open()) {
            pot_file << "# X, Y, Z, V, Ex, Ey, Ez\n";
            rho_file << "# X, Y, Z, rho\n";
            if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                int nr_val = (int)std::round(rmax / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int r_idx = 0; r_idx < nr_val; ++r_idx) {
                        double r_pos = r_idx * h_param;
                        double V = epot(z_idx, r_idx, 0);
                        double rho = scharge(z_idx, r_idx, 0);
                        Vec3D E(0.0, 0.0, 0.0);
                        try {
                            if (z_idx > 0 && z_idx < nz_val-1 && r_idx > 0 && r_idx < nr_val-1) {
                                E = efield(Vec3D(z_pos, r_pos, 0.0));
                            }
                        } catch(...) {}
                        pot_file << r_pos << " " << 0.0 << " " << z_pos << " " << V << " " 
                                 << E[1] << " " << 0.0 << " " << E[0] << "\n";
                        rho_file << r_pos << " " << 0.0 << " " << z_pos << " " << rho << "\n";
                    }
                }
            } else if (domain_type == "2D") {
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                int ny_val = (int)std::round((ymax - ymin) / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int y_idx = 0; y_idx < ny_val; ++y_idx) {
                        double y_pos = ymin + y_idx * h_param;
                        double V = epot(z_idx, y_idx, 0);
                        double rho = scharge(z_idx, y_idx, 0);
                        Vec3D E(0.0, 0.0, 0.0);
                        try {
                            if (z_idx > 0 && z_idx < nz_val-1 && y_idx > 0 && y_idx < ny_val-1) {
                                E = efield(Vec3D(z_pos, y_pos, 0.0));
                            }
                        } catch(...) {}
                        pot_file << 0.0 << " " << y_pos << " " << z_pos << " " << V << " " 
                                 << 0.0 << " " << E[1] << " " << E[0] << "\n";
                        rho_file << 0.0 << " " << y_pos << " " << z_pos << " " << rho << "\n";
                    }
                }
            } else {
                int nx_val = (int)std::round((xmax - xmin) / h_param) + 1;
                int ny_val = (int)std::round((ymax - ymin) / h_param) + 1;
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int y_idx = 0; y_idx < ny_val; ++y_idx) {
                        if (y_idx != ny_val / 2) continue; // Central slice optimization
                        double y_pos = ymin + y_idx * h_param;
                        for (int x_idx = 0; x_idx < nx_val; ++x_idx) {
                            double x_pos = xmin + x_idx * h_param;
                            double V = epot(x_idx, y_idx, z_idx);
                            double rho = scharge(x_idx, y_idx, z_idx);
                            Vec3D E(0.0, 0.0, 0.0);
                            try {
                                if (x_idx > 0 && x_idx < nx_val-1 && y_idx > 0 && y_idx < ny_val-1 && z_idx > 0 && z_idx < nz_val-1) {
                                    E = efield(Vec3D(x_pos, y_pos, z_pos));
                                }
                            } catch(...) {}
                            pot_file << x_pos << " " << y_pos << " " << z_pos << " " << V << " " 
                                     << E[0] << " " << E[1] << " " << E[2] << "\n";
                            rho_file << x_pos << " " << y_pos << " " << z_pos << " " << rho << "\n";
                        }
                    }
                }
            }
            pot_file.close();
            rho_file.close();
        }

        // Export Current Density Vector Field J manually from trajectories
        std::cout << "-> Exporting Current Density Vector Field J..." << std::endl;
        std::ofstream j_file("current_density.dat");
        if (j_file.is_open()) {
            j_file << "# X, Y, Z, Jx, Jy, Jz\n";
            int nx = (domain_type == "2D_CYL" || domain_type == "2DCYL" || domain_type == "2D") ? 1 : (int)std::round((xmax - xmin) / h_param) + 1;
            int ny = (domain_type == "2D_CYL" || domain_type == "2DCYL") ? 1 : (int)std::round((ymax - ymin) / h_param) + 1;
            int nz = (int)std::round((zmax - zmin) / h_param) + 1;

            std::vector<std::vector<std::vector<Vec3D>>> J_grid(
                nx, std::vector<std::vector<Vec3D>>(
                    ny, std::vector<Vec3D>(nz, Vec3D(0.0, 0.0, 0.0))
                )
            );

            if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                ParticleDataBaseCyl *pdb_cyl = static_cast<ParticleDataBaseCyl*>(pdb_ptr);
                for( size_t k = 0; k < pdb_cyl->size(); k++ ) {
                    const ParticleCyl &pp = pdb_cyl->particle( k );
                    double IQ = pp.IQ();
                    for ( size_t i = 0; i + 1 < pp.traj_size(); i++ ) {
                        const ParticlePCyl &pt1 = pp.traj( i );
                        const ParticlePCyl &pt2 = pp.traj( i+1 );
                        double z1 = pt1[0], r1 = pt1[1];
                        double z2 = pt2[0], r2 = pt2[1];
                        
                        double z_mid = (z1 + z2) / 2.0;
                        double r_mid = (r1 + r2) / 2.0;
                        
                        int z_idx = (int)std::round((z_mid - zmin) / h_param);
                        int r_idx = (int)std::round(r_mid / h_param);
                        
                        if (z_idx >= 0 && z_idx < nz && r_idx >= 0 && r_idx < ny) {
                            double dz = z2 - z1;
                            double dr = r2 - r1;
                            double vol = h_param * h_param * h_param;
                            J_grid[0][r_idx][z_idx][0] += IQ * dr / vol; // r-component
                            J_grid[0][r_idx][z_idx][2] += IQ * dz / vol; // z-component
                        }
                    }
                }
            } else if (domain_type == "2D") {
                ParticleDataBase2D *pdb_2d = static_cast<ParticleDataBase2D*>(pdb_ptr);
                for( size_t k = 0; k < pdb_2d->size(); k++ ) {
                    const Particle2D &pp = pdb_2d->particle( k );
                    double IQ = pp.IQ();
                    for ( size_t i = 0; i + 1 < pp.traj_size(); i++ ) {
                        const ParticleP2D &pt1 = pp.traj( i );
                        const ParticleP2D &pt2 = pp.traj( i+1 );
                        double z1 = pt1[0], y1 = pt1[1];
                        double z2 = pt2[0], y2 = pt2[1];
                        
                        double z_mid = (z1 + z2) / 2.0;
                        double y_mid = (y1 + y2) / 2.0;
                        
                        int z_idx = (int)std::round((z_mid - zmin) / h_param);
                        int y_idx = (int)std::round((y_mid - ymin) / h_param);
                        
                        if (z_idx >= 0 && z_idx < nz && y_idx >= 0 && y_idx < ny) {
                            double dz = z2 - z1;
                            double dy = y2 - y1;
                            double vol = h_param * h_param * h_param;
                            J_grid[0][y_idx][z_idx][1] += IQ * dy / vol; // y-component
                            J_grid[0][y_idx][z_idx][2] += IQ * dz / vol; // z-component
                        }
                    }
                }
            } else {
                ParticleDataBase3D *pdb_3d = static_cast<ParticleDataBase3D*>(pdb_ptr);
                for( size_t k = 0; k < pdb_3d->size(); k++ ) {
                    const Particle3D &pp = pdb_3d->particle( k );
                    double IQ = pp.IQ();
                    for ( size_t i = 0; i + 1 < pp.traj_size(); i++ ) {
                        const ParticleP3D &pt1 = pp.traj( i );
                        const ParticleP3D &pt2 = pp.traj( i+1 );
                        double x1 = pt1[1], y1 = pt1[3], z1 = pt1[5];
                        double x2 = pt2[1], y2 = pt2[3], z2 = pt2[5];
                        
                        double x_mid = (x1 + x2) / 2.0;
                        double y_mid = (y1 + y2) / 2.0;
                        double z_mid = (z1 + z2) / 2.0;
                        
                        int x_idx = (int)std::round((x_mid - xmin) / h_param);
                        int y_idx = (int)std::round((y_mid - ymin) / h_param);
                        int z_idx = (int)std::round((z_mid - zmin) / h_param);
                        
                        if (x_idx >= 0 && x_idx < nx && y_idx >= 0 && y_idx < ny && z_idx >= 0 && z_idx < nz) {
                            double dx = x2 - x1;
                            double dy = y2 - y1;
                            double dz = z2 - z1;
                            double vol = h_param * h_param * h_param;
                            J_grid[x_idx][y_idx][z_idx][0] += IQ * dx / vol; // x-component
                            J_grid[x_idx][y_idx][z_idx][1] += IQ * dy / vol; // y-component
                            J_grid[x_idx][y_idx][z_idx][2] += IQ * dz / vol; // z-component
                        }
                    }
                }
            }

            if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                int nr_val = (int)std::round(rmax / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int r_idx = 0; r_idx < nr_val; ++r_idx) {
                        double r_pos = r_idx * h_param;
                        Vec3D J = J_grid[0][r_idx][z_idx];
                        j_file << r_pos << " " << 0.0 << " " << z_pos << " " 
                               << J[0] << " " << J[1] << " " << J[2] << "\n";
                    }
                }
            } else if (domain_type == "2D") {
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                int ny_val = (int)std::round((ymax - ymin) / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int y_idx = 0; y_idx < ny_val; ++y_idx) {
                        double y_pos = ymin + y_idx * h_param;
                        Vec3D J = J_grid[0][y_idx][z_idx];
                        j_file << 0.0 << " " << y_pos << " " << z_pos << " " 
                               << J[0] << " " << J[1] << " " << J[2] << "\n";
                    }
                }
            } else {
                int nx_val = (int)std::round((xmax - xmin) / h_param) + 1;
                int ny_val = (int)std::round((ymax - ymin) / h_param) + 1;
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int y_idx = 0; y_idx < ny_val; ++y_idx) {
                        if (y_idx != ny_val / 2) continue; // Central slice optimization
                        double y_pos = ymin + y_idx * h_param;
                        for (int x_idx = 0; x_idx < nx_val; ++x_idx) {
                            double x_pos = xmin + x_idx * h_param;
                            Vec3D J = J_grid[x_idx][y_idx][z_idx];
                            j_file << x_pos << " " << y_pos << " " << z_pos << " " 
                                   << J[0] << " " << J[1] << " " << J[2] << "\n";
                        }
                    }
                }
            }
            j_file.close();
        }

        // Export Trajectory Density
        std::cout << "-> Exporting Trajectory Density..." << std::endl;
        MeshScalarField tdens( geom );
        pdb.build_trajectory_density_field( tdens );
        std::ofstream tdens_file("trajectory_density.dat");
        if (tdens_file.is_open()) {
            tdens_file << "# X, Y, Z, tdens\n";
            if (domain_type == "2D_CYL" || domain_type == "2DCYL") {
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                int nr_val = (int)std::round(rmax / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int r_idx = 0; r_idx < nr_val; ++r_idx) {
                        double r_pos = r_idx * h_param;
                        double val = tdens(z_idx, r_idx, 0);
                        tdens_file << r_pos << " " << 0.0 << " " << z_pos << " " << val << "\n";
                    }
                }
            } else if (domain_type == "2D") {
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                int ny_val = (int)std::round((ymax - ymin) / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int y_idx = 0; y_idx < ny_val; ++y_idx) {
                        double y_pos = ymin + y_idx * h_param;
                        double val = tdens(z_idx, y_idx, 0);
                        tdens_file << 0.0 << " " << y_pos << " " << z_pos << " " << val << "\n";
                    }
                }
            } else {
                int nx_val = (int)std::round((xmax - xmin) / h_param) + 1;
                int ny_val = (int)std::round((ymax - ymin) / h_param) + 1;
                int nz_val = (int)std::round((zmax - zmin) / h_param) + 1;
                for (int z_idx = 0; z_idx < nz_val; ++z_idx) {
                    double z_pos = zmin + z_idx * h_param;
                    for (int y_idx = 0; y_idx < ny_val; ++y_idx) {
                        if (y_idx != ny_val / 2) continue; // Central slice optimization
                        double y_pos = ymin + y_idx * h_param;
                        for (int x_idx = 0; x_idx < nx_val; ++x_idx) {
                            double x_pos = xmin + x_idx * h_param;
                            double val = tdens(x_idx, y_idx, z_idx);
                            tdens_file << x_pos << " " << y_pos << " " << z_pos << " " << val << "\n";
                        }
                    }
                }
            }
            tdens_file.close();
        }

        delete bfield;

        // Plot output images natively if requested (non-GUI option)
        int generate_jpg = get_int(cfg, "generate_jpg", 1);
        if (generate_jpg) {
            GeomPlotter geomplotter( geom );
            geomplotter.set_size( 1200, 1200 );
            geomplotter.set_epot( &epot );
            geomplotter.set_particle_database( &pdb );
            geomplotter.set_view( VIEW_ZY, 70 );
            geomplotter.plot_png( "tofplot_zy.jpg" );
            geomplotter.set_view( VIEW_ZX, 70 );
            geomplotter.plot_png( "tofplot_zx.jpg" );
            geomplotter.set_view( VIEW_XY, 709.8 );
            geomplotter.plot_png( "tofplot_xy.jpg" );
        }

        // Interactive GUI Plotter (GTKPlotter)
        int interactive = get_int(cfg, "interactive_plot", 0);
        if (interactive) {
            std::cout << "Launching GTKPlotter..." << std::endl;
            GTKPlotter plotter( &argc, &argv );
            plotter.set_geometry( &geom );
            plotter.set_epot( &epot );
            plotter.set_bfield( bfield );
            plotter.set_efield( &efield );
            plotter.set_scharge( &scharge_ave );
            plotter.set_trajdens( &tdens );
            plotter.set_particledatabase( &pdb );
            plotter.new_geometry_plot_window();
            plotter.run();
        }

        if (init_plasma) {
            delete init_plasma;
        }
    } 
    catch ( Error e ) {
        e.print_error_message( ibsimu.message( 0 ) );
        exit( 1 );
    }

    std::cout << "Simulation completed successfully." << std::endl;
    return ( 0 );
}
