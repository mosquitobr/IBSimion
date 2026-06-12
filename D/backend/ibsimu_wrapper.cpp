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
#include "particlediagplotter.hpp"
#include "gtkwindow.hpp"

using namespace std;

// Configuration parsing helpers
std::map<std::string, std::string> read_config(const std::string &filename) {
    std::map<std::string, std::string> config;
    std::ifstream file(filename.c_str());
    if (!file.is_open()) {
        std::cerr << "Could not open config file: " << filename << std::endl;
        return config;
    }
    std::string line;
    while (std::getline(file, line)) {
        // remove comments
        size_t comment = line.find_first_of("#;");
        if (comment != std::string::npos) {
            line = line.substr(0, comment);
        }
        // trim spaces
        line.erase(std::remove_if(line.begin(), line.end(), ::isspace), line.end());
        if (line.empty()) continue;
        
        size_t eq = line.find('=');
        if (eq != std::string::npos) {
            std::string key = line.substr(0, eq);
            std::string val = line.substr(eq + 1);
            config[key] = val;
        }
    }
    return config;
}

double get_double(const std::map<std::string, std::string> &cfg, const std::string &key, double def) {
    auto it = cfg.find(key);
    if (it != cfg.end()) {
        return std::stod(it->second);
    }
    return def;
}

int get_int(const std::map<std::string, std::string> &cfg, const std::string &key, int def) {
    auto it = cfg.find(key);
    if (it != cfg.end()) {
        return std::stoi(it->second);
    }
    return def;
}

std::string get_str(const std::map<std::string, std::string> &cfg, const std::string &key, const std::string &def) {
    auto it = cfg.find(key);
    if (it != cfg.end()) {
        return it->second;
    }
    return def;
}

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
        ibsimu.set_thread_count( 4 );

        // Determine configuration file path
        std::string config_file = "sim_config.txt";
        if (argc > 1) {
            config_file = argv[1];
        }
        
        std::cout << "Loading configuration from: " << config_file << std::endl;
        auto cfg = read_config(config_file);

        // Parameters
        std::string mode = get_str(cfg, "mode", "CW"); // CW or PIC
        std::string import_mode = get_str(cfg, "import_mode", "DXF"); // DXF or STL
        
        double Vdeteletrons = get_double(cfg, "Vdeteletrons", 3700.0);
        double Vgradepositiva = get_double(cfg, "Vgradepositiva", 500.0);
        double Vgradenegativa = get_double(cfg, "Vgradenegativa", -500.0);
        double Vlente = get_double(cfg, "Vlente", -950.0);
        double Vdrift = get_double(cfg, "Vdrift", -2924.0);
        double Vdetions = get_double(cfg, "Vdetions", -4800.0);

        double E01 = get_double(cfg, "E01", 0.012);
        double E02 = get_double(cfg, "E02", 0.012);
        double E03 = get_double(cfg, "E03", 0.012);

        double Npart1 = get_double(cfg, "Npart1", 5e4);
        double Npart2 = get_double(cfg, "Npart2", 5e4);
        double Npart3 = get_double(cfg, "Npart3", 5e4);

        double q = get_double(cfg, "q", 1.0);
        double m1 = get_double(cfg, "m1", 136.2);
        double m2 = get_double(cfg, "m2", 137.2);
        double m3 = get_double(cfg, "m3", 138.2);

        double Tp = get_double(cfg, "Tp", 1e-3);
        double Tt = get_double(cfg, "Tt", 1e-4);

        double r0 = get_double(cfg, "r0", 5e-4);
        double h_param = get_double(cfg, "h", 5e-4); // mesh size (m)

        // Geometry boundaries
        double xmin = get_double(cfg, "xmin", -0.035);
        double xmax = get_double(cfg, "xmax", 0.035);
        double ymin = get_double(cfg, "ymin", -0.035);
        double ymax = get_double(cfg, "ymax", 0.035);
        double zmin = get_double(cfg, "zmin", 0.0);
        double zmax = get_double(cfg, "zmax", 0.36);

        // Alignment offset (translação)
        double dx = get_double(cfg, "dx", 0.0);
        double dy = get_double(cfg, "dy", 0.0);
        double dz = get_double(cfg, "dz", 0.0);
        
        int threads = get_int(cfg, "threads", 4);
        ibsimu.set_thread_count( threads );

        // Grid Node Calculations
        int nx = (int)std::round((xmax - xmin) / h_param) + 1;
        int ny = (int)std::round((ymax - ymin) / h_param) + 1;
        int nz = (int)std::round((zmax - zmin) / h_param) + 1;

        std::cout << "Mesh dimensions: " << nx << "x" << ny << "x" << nz 
                  << " with step h = " << h_param << " m" << std::endl;

        Geometry geom( MODE_3D, Int3D(nx, ny, nz), Vec3D(xmin, ymin, zmin), h_param );

        if (import_mode == "DXF") {
            std::string dxf_file = get_str(cfg, "dxf_filename", "tofl203d.dxf");
            std::cout << "Loading 2D DXF file: " << dxf_file << std::endl;
            
            MyDXFFile *dxffile = new MyDXFFile;
            dxffile->set_warning_level( 2 );
            dxffile->read( dxf_file );

            DXFSolid *s1 = new DXFSolid( dxffile, "deteletrons" );
            s1->scale( 1e-3 );
            s1->define_2x3_mapping( DXFSolid::rotz );
            s1->translate( Vec3D(dx, dy, dz) );
            geom.set_solid( 7, s1 );

            DXFSolid *s2 = new DXFSolid( dxffile, "gradepositiva" );
            s2->scale( 1e-3 );
            s2->define_2x3_mapping( DXFSolid::rotz );
            s2->translate( Vec3D(dx, dy, dz) );
            geom.set_solid( 8, s2 );

            DXFSolid *s3 = new DXFSolid( dxffile, "gradenegativa" );
            s3->scale( 1e-3 );
            s3->define_2x3_mapping( DXFSolid::rotz );
            s3->translate( Vec3D(dx, dy, dz) );
            geom.set_solid( 9, s3 );

            DXFSolid *s4 = new DXFSolid( dxffile, "lente" );
            s4->scale( 1e-3 );
            s4->define_2x3_mapping( DXFSolid::rotz );
            s4->translate( Vec3D(dx, dy, dz) );
            geom.set_solid( 10, s4 );

            DXFSolid *s5 = new DXFSolid( dxffile, "drift" );
            s5->scale( 1e-3 );
            s5->define_2x3_mapping( DXFSolid::rotz );
            s5->translate( Vec3D(dx, dy, dz) );
            geom.set_solid( 11, s5 );

            DXFSolid *s6 = new DXFSolid( dxffile, "detions" );
            s6->scale( 1e-3 );
            s6->define_2x3_mapping( DXFSolid::rotz );
            s6->translate( Vec3D(dx, dy, dz) );
            geom.set_solid( 12, s6 );
        } 
        else if (import_mode == "STL") {
            std::cout << "Loading 3D STL files..." << std::endl;
            double stl_scale = get_double(cfg, "stl_scale", 1e-3); // default is mm to meters
            
            std::string stl_det_el = get_str(cfg, "stl_deteletrons", "");
            std::string stl_grid_pos = get_str(cfg, "stl_gradepositiva", "");
            std::string stl_grid_neg = get_str(cfg, "stl_gradenegativa", "");
            std::string stl_len = get_str(cfg, "stl_lente", "");
            std::string stl_drft = get_str(cfg, "stl_drift", "");
            std::string stl_det_ion = get_str(cfg, "stl_detions", "");

            if (!stl_det_el.empty()) {
                STLSolid *s = new STLSolid( stl_det_el );
                s->scale( stl_scale );
                s->translate( Vec3D(dx, dy, dz) );
                geom.set_solid( 7, s );
            }
            if (!stl_grid_pos.empty()) {
                STLSolid *s = new STLSolid( stl_grid_pos );
                s->scale( stl_scale );
                s->translate( Vec3D(dx, dy, dz) );
                geom.set_solid( 8, s );
            }
            if (!stl_grid_neg.empty()) {
                STLSolid *s = new STLSolid( stl_grid_neg );
                s->scale( stl_scale );
                s->translate( Vec3D(dx, dy, dz) );
                geom.set_solid( 9, s );
            }
            if (!stl_len.empty()) {
                STLSolid *s = new STLSolid( stl_len );
                s->scale( stl_scale );
                s->translate( Vec3D(dx, dy, dz) );
                geom.set_solid( 10, s );
            }
            if (!stl_drft.empty()) {
                STLSolid *s = new STLSolid( stl_drft );
                s->scale( stl_scale );
                s->translate( Vec3D(dx, dy, dz) );
                geom.set_solid( 11, s );
            }
            if (!stl_det_ion.empty()) {
                STLSolid *s = new STLSolid( stl_det_ion );
                s->scale( stl_scale );
                s->translate( Vec3D(dx, dy, dz) );
                geom.set_solid( 12, s );
            }
        }

        // Set boundary conditions (X, Y, Z borders)
        geom.set_boundary( 1, Bound(BOUND_NEUMANN, 0.0) ); // xmin
        geom.set_boundary( 2, Bound(BOUND_NEUMANN, 0.0) ); // xmax
        geom.set_boundary( 3, Bound(BOUND_NEUMANN, 0.0) ); // ymin
        geom.set_boundary( 4, Bound(BOUND_NEUMANN, 0.0) ); // ymax

        // Solid boundaries (Dirichlet voltages)
        geom.set_boundary( 7, Bound(BOUND_DIRICHLET, Vdeteletrons) );
        geom.set_boundary( 8, Bound(BOUND_DIRICHLET, Vgradepositiva) );
        geom.set_boundary( 9, Bound(BOUND_DIRICHLET, Vgradenegativa) );
        geom.set_boundary( 10, Bound(BOUND_DIRICHLET, Vlente) );
        geom.set_boundary( 11, Bound(BOUND_DIRICHLET, Vdrift) );
        geom.set_boundary( 12, Bound(BOUND_DIRICHLET, Vdetions) );

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
        MeshVectorField bfield;
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

            // Beam currents calculation
            double h_overlap = 1e-3;
            double vq1 = 1.3884e4*sqrt(E01/m1);
            double vq2 = 1.3884e4*sqrt(E02/m2);
            double vq3 = 1.3884e4*sqrt(E03/m3);

            double vp1 = 1.3884e4*sqrt(Tp/m1);
            double vp2 = 1.3884e4*sqrt(Tp/m2);
            double vp3 = 1.3884e4*sqrt(Tp/m3);

            double vt1 = 1.3884e4*sqrt(Tt/m1);
            double vt2 = 1.3884e4*sqrt(Tt/m2);
            double vt3 = 1.3884e4*sqrt(Tt/m3);

            double I1 = (Npart1*vq1*1.602e-19)/h_overlap;
            double I2 = (Npart2*vq2*1.602e-19)/h_overlap;
            double I3 = (Npart3*vq3*1.602e-19)/h_overlap;

            double J1 = I1/(r0*r0*M_PI);
            double J2 = I2/(r0*r0*M_PI);
            double J3 = I3/(r0*r0*M_PI);

            for( size_t iter = 0; iter < 5; iter++ ) {
                solver.solve( epot, scharge );
                efield.recalculate();
                pdb.clear();
                
                pdb.add_cylindrical_beam_with_velocity( Npart1, J1, q, m1, vq1, vp1, vt1, Vec3D(0,0,0.081), Vec3D(1,0,0), Vec3D(0,1,0), r0 );
                pdb.add_cylindrical_beam_with_velocity( Npart2, J2, q, m2, vq2, vp2, vt2, Vec3D(0,0,0.081), Vec3D(1,0,0), Vec3D(0,1,0), r0 );
                pdb.add_cylindrical_beam_with_velocity( Npart3, J3, q, m3, vq3, vp3, vt3, Vec3D(0,0,0.081), Vec3D(1,0,0), Vec3D(0,1,0), r0 );
                
                // Add electron beam
                pdb.add_cylindrical_beam_with_velocity( 1e4, 3.8, -1, 1.0/1836, 1.88e6, 1.88e4, 5.949e4, Vec3D(0,0,0.081), -Vec3D(1,0,0), Vec3D(0,1,0), r0 );
                
                pdb.iterate_trajectories( scharge, efield, bfield );
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
            size_t i_part = 0;
            QRandom rng(3);
            double x[3];
            
            std::cout << "Adding particles for Species 1 (mass " << m1 << ", count " << Npart1 << ")" << std::endl;
            while( i_part < Npart1 ) {
                rng.get(x);
                x[0] = r0*(-1+2*x[0]);
                x[1] = r0*(-1+2*x[1]);
                x[2] = r0*(-1+2*x[2]);
                if( x[0]*x[0] + x[1]*x[1] + x[2]*x[2] > r0*r0 )
                    continue;
                pdb.add_particle( C, q, m1, ParticleP3D(0, x[0], 0, x[1], 0, x[2] + 0.081, 0) );
                i_part++;  
            }

            if (Npart2 > 0) {
                std::cout << "Adding particles for Species 2 (mass " << m2 << ", count " << Npart2 << ")" << std::endl;
                size_t i_part2 = 0;
                while( i_part2 < Npart2 ) {
                    rng.get(x);
                    x[0] = r0*(-1+2*x[0]);
                    x[1] = r0*(-1+2*x[1]);
                    x[2] = r0*(-1+2*x[2]);
                    if( x[0]*x[0] + x[1]*x[1] + x[2]*x[2] > r0*r0 )
                        continue;
                    pdb.add_particle( C, q, m2, ParticleP3D(0, x[0], 0, x[1], 0, x[2] + 0.081, 0) );
                    i_part2++;  
                }
            }

            if (Npart3 > 0) {
                std::cout << "Adding particles for Species 3 (mass " << m3 << ", count " << Npart3 << ")" << std::endl;
                size_t i_part3 = 0;
                while( i_part3 < Npart3 ) {
                    rng.get(x);
                    x[0] = r0*(-1+2*x[0]);
                    x[1] = r0*(-1+2*x[1]);
                    x[2] = r0*(-1+2*x[2]);
                    if( x[0]*x[0] + x[1]*x[1] + x[2]*x[2] > r0*r0 )
                        continue;
                    pdb.add_particle( C, q, m3, ParticleP3D(0, x[0], 0, x[1], 0, x[2] + 0.081, 0) );
                    i_part3++;  
                }
            }

            snapshot( pdb, "pout", 0.0 );
            ofstream of_field( "field.txt" );

            double dt = get_double(cfg, "dt", 0.5e-7);
            double T_final = get_double(cfg, "T_final", 5.1e-6);
            double t = 0.0;
            int step = 0;
            
            while( t < T_final ) {
                pdb.step_particles( scharge, efield, bfield, dt );
                solver.solve( epot, scharge );
                efield.recalculate();

                step++;
                t = step*dt;

                // snapshot at every step
                snapshot( pdb, "pout", t );
                of_field << t << " " << epot(Vec3D(0,0,0)) << "\n";
            }
            
            pdb.save("pdb.dat");
        }

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
            MeshScalarField tdens( geom );
            pdb.build_trajectory_density_field( tdens );
            GTKPlotter plotter( &argc, &argv );
            plotter.set_geometry( &geom );
            plotter.set_epot( &epot );
            plotter.set_bfield( &bfield );
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
