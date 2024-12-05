CXX := g++
# Compiler flags                                                                                                                                     
CXXFLAGS := -Wall -Wno-deprecated $(shell root-config --cflags) -I$(shell root-config --incdir) $(shell root-config --glibs) -L$(HIPO)/lib -llz4 -lhipo4 -I$(HIPO)/include

RICH-ana-tree: RICH-track-matching-tree.cpp 
	$(CXX) -o RICH-track-matching-tree RICH-track-matching-tree.cpp $(CXXFLAGS)

# Rule to clean the project                                                                                                                          
clean:
	rm -f $(OBJS) $(TARGET)
