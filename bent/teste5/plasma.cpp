#include <fstream>
#include <iostream>
#include <ibsimu.hpp>
#include <error.hpp>
#include <geometry.hpp>
#include <dxf_solid.hpp>
#include <mydxffile.hpp>
#include <epot_field.hpp>
#include <epot_efield.hpp>
#include <meshvectorfield.hpp>
#include <epot_bicgstabsolver.hpp>
#include <gtkplotter.hpp>
#include <trajectorydiagnostics.hpp>



using namespace std;


double Vpuller = -40e3;
double h = 1e-3;
double nperh = 100;
double r0 = 10e-3;
double Npart = r0/h*nperh;
double J = 600.0;
double Te = 5.0;
double E0 = 0.5*Te;
double Tt = 0.1;
double Up = 5.0;



void simu( int *argc, char ***argv )
{
  Vec3D origin( -2e-3, 0, 0 );
  Vec3D sizereq( 80e-3, 50e-3, 0 );
  Int3D size( floor(sizereq[0]/h)+1,
	      floor(sizereq[1]/h)+1,
	      1 );
  Geometry geom( MODE_2D, size, origin, h );

  MyDXFFile *dxffile = new MyDXFFile;
  dxffile->set_warning_level( 1 );
  dxffile->read( "plasma.dxf" );

  DXFSolid *s1 = new DXFSolid( dxffile, "plasma" );
  s1->scale( 1e-3 );
  geom.set_solid( 7, s1 );
  DXFSolid *s2 = new DXFSolid( dxffile, "puller" );
  s2->scale( 1e-3 );
  geom.set_solid( 8, s2 );

  geom.set_boundary( 1, Bound(BOUND_NEUMANN, 0.0) ); // xmin
  geom.set_boundary( 2, Bound(BOUND_NEUMANN, 0.0) ); // xmax
  geom.set_boundary( 3, Bound(BOUND_NEUMANN, 0.0) ); // rmin
  geom.set_boundary( 4, Bound(BOUND_NEUMANN, 0.0) ); // rmax

  geom.set_boundary( 7, Bound(BOUND_DIRICHLET, 0.0) );
  geom.set_boundary( 8, Bound(BOUND_DIRICHLET, Vpuller) );

  geom.build_mesh();

  EpotField epot( geom );
  MeshScalarField scharge( geom );
  MeshVectorField bfield;
  EpotEfield efield( epot );
  field_extrpl_e extrapl[6] = { FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE,
			        FIELD_SYMMETRIC_POTENTIAL, FIELD_EXTRAPOLATE,
			        FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE };
  efield.set_extrapolation( extrapl );
  
  EpotBiCGSTABSolver solver( geom );
  InitialPlasma init_plasma( AXIS_X, 1e-3 );
  solver.set_initial_plasma( Up, &init_plasma );

  ParticleDataBase2D pdb( geom );
  bool pmirror[6] = {false, false,
		     true, false,
		     false, false};
  pdb.set_mirror( pmirror );

  for( int a = 0; a < 15; a++ ) {

    ibsimu.message(1) << "Major cycle " << a << "\n";
    ibsimu.message(1) << "-----------------------\n";

    if( a == 1 ) {
	double rhoe = pdb.get_rhosum();
	solver.set_pexp_plasma( rhoe, Te, Up );
    }

    solver.solve( epot, scharge );
    if( solver.get_iter() == 0 ) {
      ibsimu.message(1) << "No iterations, breaking major cycle\n";
      break;
    }
      
    efield.recalculate();

    pdb.clear();
    pdb.add_2d_beam_with_energy( Npart, J, 1, 1, E0, 0, Tt, 
				 geom.origo(0), 0,
				 geom.origo(0), r0 );
    pdb.iterate_trajectories( scharge, efield, bfield );

    
    TrajectoryDiagnosticData tdata;
    vector<trajectory_diagnostic_e> diag;
    diag.push_back( DIAG_Y );
    diag.push_back( DIAG_YP );
    pdb.trajectories_at_plane( tdata, AXIS_X, geom.max(0), diag );
    Emittance emit( tdata(0).data(), tdata(1).data() );

    ofstream dataout( "emit.txt", ios_base::app );
    dataout << emit.alpha() << " "
	    << emit.beta() << " "
	    << emit.epsilon() << "\n";
    dataout.close();
  }

  GTKPlotter plotter( argc, argv );
  plotter.set_geometry( &geom );
  plotter.set_epot( &epot );
  plotter.set_particledatabase( &pdb );
  plotter.set_efield( &efield );
  plotter.set_bfield( &bfield );
  plotter.set_scharge( &scharge );
  plotter.new_geometry_plot_window();
  plotter.run();
}


int main( int argc, char **argv )
{
  remove( "emit.txt" );

  try {
    ibsimu.set_message_threshold( MSG_VERBOSE, 1 );
    ibsimu.set_thread_count( 2 );
    simu( &argc, &argv );
  } catch( Error e ) {
    e.print_error_message( ibsimu.message(0) );
  }

  return( 0 );
}
