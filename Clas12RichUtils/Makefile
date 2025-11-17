CXX         := g++
ROOT_CFLAGS := $(shell root-config --cflags | sed 's|-std=[^ ]*||g')
ROOT_LIBS   := $(shell root-config --libs)
HIPO_LIBS   := -L$(HIPO)/lib -lhipo4 -llz4
HIPO_INCL   := -I$(HIPO)/include
JSON_INCL      := -I/usr/local/include

CXXFLAGS := -std=c++14 \
            -I/usr/local/include \
	    $(JSON_INCL) \
            $(ROOT_CFLAGS) \
            $(HIPO_INCL) \
            -Wall -Wno-deprecated

LDFLAGS  := $(ROOT_LIBS) $(HIPO_LIBS)

SRCS := \
    RICH-hipo-to-tree.cpp \
    HIPO-chunk-skim.cpp \
    RICH-skim-dst-modular-onetop.cpp \

OBJS := $(SRCS:.cpp=.o)
EXES := $(SRCS:.cpp=)

.PHONY: all clean

all: $(EXES)

# Link rule (must be indented by a TAB!)
%: %.o
	$(CXX) -o $@ $< $(LDFLAGS)

# Compile rule (must be indented by a TAB!)
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(EXES)
