#include <fstream>
#include <iomanip>
#include <limits>
#include "epot_bicgstabsolver.hpp"
#include "meshvectorfield.hpp"
#include "gtkplotter.hpp"
#include "geomplotter.hpp"
#include "geometry.hpp"
#include "func_solid.hpp"
#include "stl_solid.hpp"
#include "epot_efield.hpp"
#include "error.hpp"
#include "ibsimu.hpp"
#include "trajectorydiagnostics.hpp"
#include "particledatabase.hpp"
#include "particlediagplotter.hpp"


using namespace std;


double Vpuller = -50e3;
double Vgnd = -40e3;

double Te = 5.0;
double Up = 5.0;
double E0 = 0.5*Te;

double q = 1.0;
double m = 1.0;
double Tt = 0.5;
double r0 = 8e-3;
double J = 300.0;

double sc_alpha = 0.9;
double h = 1.0e-3;
double nperh = 100;


void simu( int *argc, char ***argv )
{
    Vec3D origo( 0, 0, -5e-3 );
    double sizereq[3] = {  90e-3,
                           50e-3, 
                          125e-3 };
    Int3D meshsize( (int)floor(sizereq[0]/h)+1,
                    (int)floor(sizereq[1]/h)+1,
		    (int)floor(sizereq[2]/h)+1 );
    Geometry geom( MODE_3D, meshsize, origo, h );

    STLSolid *s1 = new STLSolid( "slit_assembly_plasma_1.stl" );
    s1->translate( Vec3D(-0.5*(0.225303+0.525303),-0.5*(0.156421+0.456421),0.233167) );
    geom.set_solid( 7, s1 );
    STLSolid *s2 = new STLSolid( "slit_assembly_puller_2.stl" );
    s2->translate( Vec3D(-0.5*(0.225303+0.525303),-0.5*(0.156421+0.456421),0.233167) );
    geom.set_solid( 8, s2 );
    STLSolid *s3 = new STLSolid( "slit_assembly_gnd_3.stl" );
    s3->translate( Vec3D(-0.5*(0.225303+0.525303),-0.5*(0.156421+0.456421),0.233167) );
    geom.set_solid( 9, s3 );

    geom.set_boundary( 1, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 2, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 3, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 4, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 5, Bound(BOUND_NEUMANN, 0.0) );
    geom.set_boundary( 6, Bound(BOUND_NEUMANN, 0.0) );

    geom.set_boundary( 7, Bound(BOUND_DIRICHLET, 0.0) );
    geom.set_boundary( 8, Bound(BOUND_DIRICHLET, Vpuller) );
    geom.set_boundary( 9, Bound(BOUND_DIRICHLET, Vgnd) );

    geom.build_mesh();
    geom.build_surface();

    EpotBiCGSTABSolver solver( geom );
    InitialPlasma init_plasma( AXIS_Z, 2e-4 );
    solver.set_initial_plasma( Up, &init_plasma );

    EpotField epot( geom );
    MeshScalarField scharge( geom );
    MeshScalarField scharge_ave( geom );
    MeshVectorField bfield;

    EpotEfield efield( epot );
    field_extrpl_e efldextrpl[6] = { FIELD_SYMMETRIC_POTENTIAL, FIELD_EXTRAPOLATE, 
				     FIELD_SYMMETRIC_POTENTIAL, FIELD_EXTRAPOLATE,
                                     FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE };
    efield.set_extrapolation( efldextrpl );

    ParticleDataBase3D pdb( geom );
    bool pmirror[6] = { true, false, true, false, false, false };
    pdb.set_mirror( pmirror );

    for( size_t a = 0; a < 5; a++ ) {

	ibsimu.message(1) << "Major cycle " << a << "\n";
	ibsimu.message(1) << "-----------------------\n";

	if( a == 1 ) {
	    double rhoe = pdb.get_rhosum();
	    solver.set_pexp_plasma( rhoe, Te, Up );
	}

	solver.solve( epot, scharge_ave );
	if( solver.get_iter() == 0 ) {
	    ibsimu.message(1) << "No iterations, breaking major cycle\n";
	    break;
	}
	efield.recalculate();

        pdb.clear(); 
	int Npart = floor(M_PI*r0*r0/(h*h)*nperh+0.5);
	pdb.add_rectangular_beam_with_energy( Npart, J, q, m,
					      E0, 0, Tt,
					      geom.origo(),
					      Vec3D(1,0,0),
					      Vec3D(0,1,0),
					      65e-3, 6e-3 );
	
        pdb.iterate_trajectories( scharge, efield, bfield );

	// 90 % space charge compensation at z>100 mm
	/*
	for( uint32_t k = 0; k < geom.size(2); k++ ) {
	    double z = geom.origo(2) + geom.h()*k;
	    if( z > 100e-3 ) {
	    for( uint32_t i = 0; i < geom.size(0); i++ ) {
		for( uint32_t j = 0; j < geom.size(1); j++ )
		    scharge(i,j,k) *= 0.1;
	    }
	}
	*/

	if( a == 0 ) {
	    scharge_ave = scharge;
	} else {
	    double sc_beta = 1.0-sc_alpha;
	    uint32_t nodecount = scharge.nodecount();
	    for( uint32_t b = 0; b < nodecount; b++ ) {
		scharge_ave(b) = sc_alpha*scharge(b) + sc_beta*scharge_ave(b);
	    }
	}

	TrajectoryDiagnosticData tdata;
        std::vector<trajectory_diagnostic_e> diagnostics;
        diagnostics.push_back( DIAG_Y );
        diagnostics.push_back( DIAG_YP );
        pdb.trajectories_at_plane( tdata, AXIS_Z, geom.max(2)-geom.h(), diagnostics );
        Emittance emit( tdata(0).data(), tdata(1).data() );

        // Output
        ofstream dout( "emit.txt", ios_base::app );
        dout << emit.alpha() << " "
             << emit.beta() << " "
             << emit.epsilon() << "\n";
        dout.close();

    }
    
    geom.save( "geom.dat" );
    epot.save( "epot.dat" );
    pdb.save( "pdb.dat" );

    if( false ) {
	MeshScalarField tdens(geom);
	pdb.build_trajectory_density_field(tdens);
	
	GTKPlotter plotter( argc, argv );
	plotter.set_geometry( &geom );
	plotter.set_epot( &epot );
	plotter.set_efield( &efield );
	plotter.set_bfield( &bfield );
	plotter.set_trajdens( &tdens );
	plotter.set_scharge( &scharge );
	plotter.set_particledatabase( &pdb );
	plotter.new_geometry_plot_window();
	plotter.run();
    }

    TrajectoryDiagnosticData tdata;
    std::vector<trajectory_diagnostic_e> diagnostics;
    diagnostics.push_back( DIAG_Y );
    diagnostics.push_back( DIAG_YP );
    pdb.trajectories_at_plane( tdata, AXIS_Z, geom.max(2)-geom.h(), diagnostics );
    Emittance emit( tdata(0).data(), tdata(1).data() );

    ofstream dout( "diag.txt", ios_base::app );
    dout << h << " " << emit.epsilon() << "\n";
}


int main( int argc, char **argv )
{
    remove( "emit.txt" );

    try {
	//ibsimu.set_message_output( "ibsimu.txt" );
        ibsimu.set_message_threshold( MSG_VERBOSE, 1 );
	ibsimu.set_thread_count( 8 );
	simu( &argc, &argv );
    } catch( Error e ) {
	e.print_error_message( ibsimu.message( 0 ) );
        exit( 1 );
    }

    return( 0 );
}
