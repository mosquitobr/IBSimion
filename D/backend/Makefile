CC = g++
LDFLAGS = `pkg-config --libs ibsimu-1.0.6dev`
CXXFLAGS = -Wall -g `pkg-config --cflags ibsimu-1.0.6dev`

ibsimu_wrapper: ibsimu_wrapper.o
	$(CC) -o ibsimu_wrapper ibsimu_wrapper.o $(LDFLAGS)
ibsimu_wrapper.o: ibsimu_wrapper.cpp

clean:
	$(RM) *.o ibsimu_wrapper
