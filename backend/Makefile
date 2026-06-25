CC = g++
LDFLAGS = `pkg-config --libs ibsimu-1.0.6dev`
CXXFLAGS = -Wall -g `pkg-config --cflags ibsimu-1.0.6dev` -std=c++11

ibsimu_wrapper: ibsimu_wrapper.cpp
	$(CC) $(CXXFLAGS) ibsimu_wrapper.cpp -o ibsimu_wrapper $(LDFLAGS)

clean:
	rm -f ibsimu_wrapper *.o
