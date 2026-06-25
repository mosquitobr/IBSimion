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
           << p[6] << "\n"; // vz
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
        double h_param = get_double(cfg, "h", 1e-3); // mesh size (m)

        // Geometry boundaries
        double xmin = get_double(cfg, "xmin", -0.035);
        double xmax = get_double(cfg, "xmax", 0.035);
        double ymin = get_double(cfg, "ymin", -0.035);
        double ymax = get_double(cfg, "ymax", 0.035);
        double zmin = get_double(cfg, "zmin", 0.0);
        double zmax = get_double(cfg, "zmax", 0.36);
        
        int threads = get_int(cfg, "threads", 4);
        ibsimu.set_thread_count( threads );

        // Grid Node Calculations
        int nx = (int)std::round((xmax - xmin) / h_param) + 1;
        int ny = (int)std::round((ymax - ymin) / h_param) + 1;
        int nz = (int)std::round((zmax - zmin) / h_param) + 1;

        std::cout << "Mesh dimensions: " << nx << "x" << ny << "x" << nz 
                  << " with step h = " << h_param << " m" << std::endl;

        Geometry geom( MODE_3D, Int3D(nx, ny, nz), Vec3D(xmin, ymin, zmin), h_param );

        // Set boundary conditions (X, Y borders - Neumann by default, Dirichlet grounded if geometries is empty)
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
                        s->define_2x3_mapping(DXFSolid::rotz);
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
        field_extrpl_e efldextrpl[6] = { FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE,
                                         FIELD_SYMMETRIC_POTENTIAL, FIELD_EXTRAPOLATE,
                                         FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE };
        efield.set_extrapolation( efldextrpl );

        EpotBiCGSTABSolver solver( geom, 1.0e-4, 1000000, 1.0e-4, 10, true );
        ParticleDataBase3D pdb( geom );
        bool pmirror[6] = { false, false, false, false, false, false };
        pdb.set_mirror( pmirror );

        if (mode == "CW") {
            std::cout << "Starting Continuous Wave (CW) Steady-State Simulation..." << std::endl;
            pdb.set_surface_collision( false );

            int max_iterations = get_int(cfg, "iterations", 5);
            std::cout << "Running CW simulation with " << max_iterations << " iterations." << std::endl;
            for( size_t iter = 0; iter < max_iterations; iter++ ) {
                solver.solve( epot, scharge );
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
                        double J = current / (M_PI * radius * radius + 1e-20);
                        
                        double Tp = get_double(beam, "Tp", 0.02); // Parallel temperature dynamically loaded
                        double Tt = 1.0; // Transverse temperature
                        if (emittance > 0.0 && radius > 0.0) {
                            Tt = energy * (emittance * emittance) / (radius * radius);
                        }
                        
                        Vec3D bdir1(1.0, 0.0, 0.0);
                        Vec3D bdir2(0.0, 1.0, 0.0);
                        double bdir_y = get_double(beam, "dir_y", 0.0);
                        if (bdir_y < -0.5) {
                            bdir2 = Vec3D(0.0, 0.0, 1.0);
                        }

                        pdb.add_cylindrical_beam_with_energy(
                            n_part, J, charge, mass, energy, Tp, Tt, 
                            Vec3D(0.0, 0.0, z_start), bdir1, bdir2, radius
                        );
                    }
                }
                
                pdb.iterate_trajectories( scharge, efield, *bfield );
            }
            
            pdb.save("pdb.dat");

            std::cout << "Saving trajectories to trajectories.txt..." << std::endl;
            ofstream fileTraj( "trajectories.txt" );
            for( size_t k = 0; k < pdb.size(); k++ ) {
                const Particle3D &pp = pdb.particle( k );
                if ( pdb.size() > 500 && k % (pdb.size() / 500 + 1) != 0 ) continue;
                
                fileTraj << "TID " << k << " " << pp.m() << " " << pp.q() << " " << pp.IQ() << "\n";
                for ( size_t i = 0; i < pp.traj_size(); i++ ) {
                    const ParticleP3D &pt = pp.traj( i );
                    fileTraj << pt[0] << " " << pt[1] << " " << pt[3] << " " << pt[5] << "\n";
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
            pdb.trajectories_at_plane( tof, AXIS_Z, diag_plane_z, diagnostics );
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
            for( size_t k = 0; k < pdb.size(); k++ ) {
                Particle3D &pp = pdb.particle( k );
                fileOut << setw(12) << pp.IQ() << " " << setw(12) << pp.m() << " ";
                for( size_t j = 0; j < 7; j ++ )
                    fileOut << setw(12) << pp(j) << " ";
                fileOut << "\n";
            }
            fileOut.close();
        } 
        else if (mode == "PIC") {
            std::cout << "Starting Particle-in-Cell (PIC) Simulation..." << std::endl;
            pdb.set_save_trajectories( 1 );

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

                    double v_z_mean = 1.3884e4 * std::sqrt(energy / mass);
                    
                    double Tp = 1.0;
                    double Tt = 1.0;
                    if (emittance > 0.0 && radius > 0.0) {
                        Tt = energy * (emittance * emittance) / (radius * radius);
                    }

                    double dvp = 1.3884e4 * std::sqrt(Tp / mass);
                    double dvt = 1.3884e4 * std::sqrt(Tt / mass);

                    std::cout << "Adding particles for beam '" << nome << "': " 
                              << n_part << " particles, mass=" << mass << " u" << std::endl;

                    uint32_t i_part = 0;
                    while (i_part < n_part) {
                        double pt_x = 0.0, pt_y = 0.0, pt_z = z_start;
                        if (dist_type == "Gaussian") {
                            double u1 = dist_uni(gen);
                            double u2 = dist_uni(gen);
                            double r = radius * 0.5 * std::sqrt(-2.0 * std::log(u1 + 1e-20));
                            double theta = 2.0 * M_PI * u2;
                            pt_x = r * std::cos(theta);
                            pt_y = r * std::sin(theta);
                        } else {
                            double u1 = dist_uni(gen);
                            double u2 = dist_uni(gen);
                            double r = radius * std::sqrt(u1);
                            double theta = 2.0 * M_PI * u2;
                            pt_x = r * std::cos(theta);
                            pt_y = r * std::sin(theta);
                        }

                        double v_x = dist_norm(gen) * dvt;
                        double v_y = dist_norm(gen) * dvt;
                        double v_z = v_z_mean + dist_norm(gen) * dvp;

                        pdb.add_particle(C, charge, mass, ParticleP3D(0.0, pt_x, v_x, pt_y, v_y, pt_z, v_z));
                        i_part++;
                    }
                }
            }

            snapshot( pdb, "pout", 0.0 );
            ofstream of_field( "field.txt" );

            double dt = get_double(cfg, "dt", 0.5e-7);
            double T_final = get_double(cfg, "T_final", 5.1e-6);
            double t = 0.0;
            int step = 0;
            
            while( t < T_final ) {
                scharge.clear();

                MeshScalarField dummy_scharge( geom );
                ParticleStepper<ParticleP3D> ps_sub( dt / 1000.0, 1, pmirror, &dummy_scharge, 
                                                    &efield, bfield, &geom );
                ParticleStepper<ParticleP3D> ps_last( dt / 1000.0, 1, pmirror, &scharge, 
                                                     &efield, bfield, &geom );
                ParticleStepper<ParticleP3D> ps( dt, 1, pmirror, &scharge, 
                                                 &efield, bfield, &geom );

                for( uint32_t a = 0; a < pdb.size(); a++ ) {
                    Particle3D &p = pdb.particle( a );
                    if( p.get_status() != PARTICLE_OK )
                        continue;

                    double m = p.m();
                    if( m < 0.1 ) { // Electron sub-stepping
                        if( p[0] == 0 )
                            ps_sub.initialize( &p, a );
                        
                        bool alive = true;
                        for( int sub = 0; sub < 999; ++sub ) {
                            ps_sub.step( &p, a );
                            if( p.get_status() != PARTICLE_OK ) {
                                alive = false;
                                break;
                            }
                        }
                        if( alive ) {
                            ps_last.step( &p, a );
                        }
                    } else { // Heavy ion normal stepping
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

                snapshot( pdb, "pout", t );
                of_field << t << " " << epot(Vec3D(0,0,0)) << "\n";
            }
            
            pdb.save("pdb.dat");
        }

        // Export 3D fields including Potential, Electric Field, and Charge Density (optimized to Y ≈ 0 slice)
        std::cout << "-> Exporting 2D Central Slice of Potential and Electric Field..." << std::endl;
        std::ofstream pot_file("potential_field.dat");
        std::ofstream rho_file("charge_density.dat");
        if (pot_file.is_open() && rho_file.is_open()) {
            pot_file << "# X, Y, Z, V, Ex, Ey, Ez\n";
            rho_file << "# X, Y, Z, rho\n";
            for (int z_idx = 0; z_idx < nz; ++z_idx) {
                double z_pos = zmin + z_idx * h_param;
                for (int y_idx = 0; y_idx < ny; ++y_idx) {
                    if (y_idx != ny / 2) continue; // Central slice optimization
                    double y_pos = ymin + y_idx * h_param;
                    for (int x_idx = 0; x_idx < nx; ++x_idx) {
                        double x_pos = xmin + x_idx * h_param;
                        
                        double V = epot(x_idx, y_idx, z_idx);
                        double rho = scharge(x_idx, y_idx, z_idx);
                        
                        Vec3D E(0.0, 0.0, 0.0);
                        try {
                            if (x_idx > 0 && x_idx < nx-1 && y_idx > 0 && y_idx < ny-1 && z_idx > 0 && z_idx < nz-1) {
                                E = efield(Vec3D(x_pos, y_pos, z_pos));
                            }
                        } catch(...) {}
                        
                        pot_file << x_pos << " " << y_pos << " " << z_pos << " " << V << " " 
                                 << E[0] << " " << E[1] << " " << E[2] << "\n";
                        rho_file << x_pos << " " << y_pos << " " << z_pos << " " << rho << "\n";
                    }
                }
            }
            pot_file.close();
            rho_file.close();
        }

        // Export Trajectory Density (optimized to Y ≈ 0 slice)
        std::cout << "-> Exporting 2D Central Slice of Trajectory Density..." << std::endl;
        MeshScalarField tdens( geom );
        pdb.build_trajectory_density_field( tdens );
        std::ofstream tdens_file("trajectory_density.dat");
        if (tdens_file.is_open()) {
            tdens_file << "# X, Y, Z, tdens\n";
            for (int z_idx = 0; z_idx < nz; ++z_idx) {
                double z_pos = zmin + z_idx * h_param;
                for (int y_idx = 0; y_idx < ny; ++y_idx) {
                    if (y_idx != ny / 2) continue; // Central slice optimization
                    double y_pos = ymin + y_idx * h_param;
                    for (int x_idx = 0; x_idx < nx; ++x_idx) {
                        double x_pos = xmin + x_idx * h_param;
                        double val = tdens(x_idx, y_idx, z_idx);
                        tdens_file << x_pos << " " << y_pos << " " << z_pos << " " << val << "\n";
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
    } 
    catch ( Error e ) {
        e.print_error_message( ibsimu.message( 0 ) );
        exit( 1 );
    }

    std::cout << "Simulation completed successfully." << std::endl;
    return ( 0 );
}
