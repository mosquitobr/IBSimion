CC = g++
LDFLAGS = `pkg-config --libs ibsimu-1.0.6dev`
CXXFLAGS = -Wall -g `pkg-config --cflags ibsimu-1.0.6dev`

solenoid: solenoid.o
	$(CC) -o solenoid solenoid.o $(LDFLAGS)
solenoid.o: solenoid.cpp

clean:
	$(RM) *.o solenoid 

