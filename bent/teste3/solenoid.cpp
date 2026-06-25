#include <fstream>
#include <iomanip>
#include <limits>
#include "epot_bicgstabsolver.hpp"
#include "meshvectorfield.hpp"
#include "gtkplotter.hpp"
#include "geomplotter.hpp"
#include "geometry.hpp"
#include "func_solid.hpp"
#include "epot_efield.hpp"
#include "error.hpp"
#include "ibsimu.hpp"
#include "trajectorydiagnostics.hpp"
#include "particledatabase.hpp"
#include "particlediagplotter.hpp"
#include "axisymmetricvectorfield.hpp"


using namespace std;


double q = 8.0;
double m = 40.0;
double E0 = q*10e3;
double Tt = 0.01;
double r0 = 25e-3;
double I = 100e-6;
double J = I/(r0*r0*M_PI);



void simu( int *argc, char ***argv )
{
    double h = 1e-3;
    Vec3D origo( -250e-3, 
		 0, 
		 0 );
    double sizereq[3] = { 500e-3,
                          50e-3, 
                          0 };
    Int3D meshsize( (int)floor(sizereq[0]/h)+1,
                    (int)floor(sizereq[1]/h)+1,
		    1);
    Geometry geom( MODE_CYL, meshsize, origo, h );

    geom.set_boundary( 1, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 2, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 3, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 4, Bound(BOUND_DIRICHLET, 0.0) ); // Beam pipe

    geom.build_mesh();

    EpotBiCGSTABSolver solver( geom );
    EpotField epot( geom );
    MeshScalarField scharge( geom );

    /*
    double bfield_h = 1e-3;
    int bfield_size = floor(500e-3/bfield_h)+1;
    double bfield_max = 0.7*450e-3;
    double bfield_w = 55e-3;
    vector<double> Bz;
    for( int a = 0; a < bfield_size; a++ ) {
	double x = origo[0]+bfield_h*a;
	Bz.push_back( bfield_max*exp(-x*x/(2*bfield_w*bfield_w)) );
    }
    AxisymmetricVectorField bfield( MODE_CYL, origo[0], bfield_h, Bz, 6 );
    */

    bool fout[3] = { true, true, false };
    MeshVectorField bfield( MODE_CYL, fout, 1.0e-3, 0.7, "sol.txt" );
    field_extrpl_e ex[6] = { FIELD_ZERO,
                             FIELD_ZERO,
                             FIELD_ZERO,
                             FIELD_ZERO,
                             FIELD_ZERO,
                             FIELD_ZERO };
    bfield.set_extrapolation( ex );

    EpotEfield efield( epot );
    field_extrpl_e efldextrpl[6] = { FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE, 
				     FIELD_SYMMETRIC_POTENTIAL, FIELD_EXTRAPOLATE,
                                     FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE };
    efield.set_extrapolation( efldextrpl );

    ParticleDataBaseCyl pdb( geom );
    bool pmirror[6] = { false, false, true, false, false, false };
    pdb.set_mirror( pmirror );

    for( size_t i = 0; i < 1; i++ ) {

	ibsimu.message(1) << "Major cycle " << i << "\n";
	ibsimu.message(1) << "-----------------------\n";

	solver.solve( epot, scharge );
	if( i > 0 && solver.get_iter() == 0 ) {
	    ibsimu.message(1) << "No iterations, breaking major cycle\n";
	    break;
	}
	efield.recalculate();

        pdb.clear(); 
	pdb.add_2d_beam_with_energy( 1000, J, q, m,
				     E0, 0, Tt,
				     geom.origo(0), 0,
				     geom.origo(0), r0 );
	
        pdb.iterate_trajectories( scharge, efield, bfield );

	TrajectoryDiagnosticData tdata;
        std::vector<trajectory_diagnostic_e> diagnostics;
        diagnostics.push_back( DIAG_R );
        diagnostics.push_back( DIAG_RP );
        diagnostics.push_back( DIAG_AP );
        diagnostics.push_back( DIAG_CURR );
        pdb.trajectories_at_plane( tdata, AXIS_X, geom.max(0)-geom.h(), diagnostics );
        EmittanceConv emit( 30, 30, tdata(0).data(), tdata(1).data(), tdata(2).data(), tdata(3).data(), 100 );

        // Output
        ofstream dout( "emit.txt", ios_base::app );
        dout << emit.alpha() << " "
             << emit.beta() << " "
             << emit.epsilon() << "\n";
        dout.close();

    }
    
    MeshScalarField tdens(geom);
    pdb.build_trajectory_density_field(tdens);

    GTKPlotter plotter( argc, argv );
    plotter.set_geometry( &geom );
    plotter.set_epot( &epot );
    plotter.set_bfield( &bfield );
    plotter.set_trajdens( &tdens );
    plotter.set_scharge( &scharge );
    plotter.set_particledatabase( &pdb );
    plotter.new_geometry_plot_window();
    plotter.run();
}


int main( int argc, char **argv )
{
    remove( "emit.txt" );

    try {
	//ibsimu.set_message_output( "ibsimu.txt" );
        ibsimu.set_message_threshold( MSG_VERBOSE, 1 );
	ibsimu.set_thread_count( 4 );
	simu( &argc, &argv );
    } catch( Error e ) {
	e.print_error_message( ibsimu.message( 0 ) );
        exit( 1 );
    }

    return( 0 );
}
