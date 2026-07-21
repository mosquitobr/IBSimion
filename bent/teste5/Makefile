CC = g++
LDFLAGS = `pkg-config --libs ibsimu-1.0.6dev`
CXXFLAGS = -Wall -g `pkg-config --cflags ibsimu-1.0.6dev`

plasma: plasma.o
	$(CC) -o plasma plasma.o $(LDFLAGS)
plasma.o: plasma.cpp

clean:
	$(RM) *.o plasma 

