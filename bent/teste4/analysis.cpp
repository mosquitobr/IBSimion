#include <fstream>
#include <iomanip>
#include <limits>
#include "meshvectorfield.hpp"
#include "dxf_solid.hpp"
#include "mydxffile.hpp"
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



using namespace std;



void simu( int argc, char **argv )
{
    std::ifstream is_geom( argv[1] );
    if( !is_geom.good() )
	throw( Error( ERROR_LOCATION, (string)"couldn\'t open file \'" + argv[1] + "\'" ) );
    Geometry geom( is_geom );
    is_geom.close();
    geom.build_surface();

    std::ifstream is_epot( argv[2] );
    if( !is_epot.good() )
	throw( Error( ERROR_LOCATION, (string)"couldn\'t open file \'" + argv[2] + "\'" ) );
    EpotField epot( is_epot, geom );
    is_epot.close();

    EpotEfield efield( epot );
    field_extrpl_e efldextrpl[6] = { FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE, 
				     FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE, 
				     FIELD_EXTRAPOLATE, FIELD_EXTRAPOLATE };
    efield.set_extrapolation( efldextrpl );

    std::ifstream is_pdb( argv[3] );
    if( !is_pdb.good() )
	throw( Error( ERROR_LOCATION, (string)"couldn\'t open file \'" + argv[3] + "\'" ) );
    ParticleDataBase3D pdb( is_pdb, geom );
    is_pdb.close();

    MeshScalarField tdens( geom );
    pdb.build_trajectory_density_field( tdens );

    GTKPlotter plotter( &argc, &argv );
    plotter.set_geometry( &geom );
    plotter.set_epot( &epot );
    plotter.set_efield( &efield );
    plotter.set_trajdens( &tdens );
    plotter.set_particledatabase( &pdb );
    plotter.new_geometry_plot_window();
    plotter.run();
}


int main( int argc, char **argv )
{
    if( argc <= 3 ) {
	cerr << "Usage: analysis geom epot pdb\n";
	exit( 1 );
    }

    try {
	ibsimu.set_message_threshold( MSG_VERBOSE, 1 );
	ibsimu.set_thread_count( 8 );
	simu( argc, argv );
    } catch( Error e ) {
	e.print_error_message( ibsimu.message( 0 ) );
        exit( 1 );
    }

    return( 0 );
}
