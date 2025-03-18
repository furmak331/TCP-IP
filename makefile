CXX = g++
CXXFLAGS = -std=c++14 -Wall

SRCS = Device.cpp Connection.cpp EndDevice.cpp Hub.cpp Network.cpp main.cpp
OBJS = $(SRCS:.cpp=.o)
TARGET = network_simulator

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean