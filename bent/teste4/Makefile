CC = g++
LDFLAGS = `pkg-config --libs ibsimu-1.0.6dev`
CXXFLAGS = -Wall -g `pkg-config --cflags ibsimu-1.0.6dev`

slit3d: slit3d.o
	$(CC) -o slit3d slit3d.o $(LDFLAGS)
slit3d.o: slit3d.cpp

analysis: analysis.o
	$(CC) -o analysis analysis.o $(LDFLAGS)
analysis.o: analysis.cpp

clean:
	$(RM) *.o slit3d analysis *~

