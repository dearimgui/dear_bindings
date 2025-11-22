#
# Cross Platform Makefile
# Compatible with MSYS2/MINGW, Ubuntu 14.04.1 and Mac OS X
#
# You will need SDL3 (http://www.libsdl.org).

#CC = gcc
#CC = clang

EXE = example_sdl3_sdlgpu3
IMGUI_DIR=../../../imgui
GENERATED_DIR=../../generated

SOURCES=main.c
OBJS = $(addsuffix .o, $(basename $(notdir $(DCIMGUI_SOURCES))))

DCIMGUI_SOURCES = $(IMGUI_DIR)/imgui.cpp $(IMGUI_DIR)/imgui_demo.cpp $(IMGUI_DIR)/imgui_draw.cpp $(IMGUI_DIR)/imgui_tables.cpp $(IMGUI_DIR)/imgui_widgets.cpp
DCIMGUI_SOURCES += $(IMGUI_DIR)/backends/imgui_impl_sdl3.cpp $(IMGUI_DIR)/backends/imgui_impl_sdlgpu3.cpp
DCIMGUI_SOURCES += $(GENERATED_DIR)/dcimgui.cpp $(GENERATED_DIR)/backends/dcimgui_impl_sdl3.cpp $(GENERATED_DIR)/backends/dcimgui_impl_sdlgpu3.cpp
DCIMGUI_OBJS = $(addsuffix .o, $(basename $(notdir $(DCIMGUI_SOURCES))))
UNAME_S := $(shell uname -s)

CFLAGS = -I$(GENERATED_DIR) -I$(IMGUI_DIR) -I$(GENERATED_DIR)/backends -I$(IMGUI_DIR)/backends
CFLAGS += -g -Wall -Wformat
CXXFLAGS = -std=c++11
LIBS = -L. -ldcimgui -lm -lstdc++



##---------------------------------------------------------------------
## BUILD FLAGS PER PLATFORM
##---------------------------------------------------------------------

ifeq ($(UNAME_S), Linux) #LINUX
	ECHO_MESSAGE = "Linux"
	LIBS += -ldl `pkg-config sdl3 --libs`

	CFLAGS += `pkg-config sdl3 --cflags`
	CXXFLAGS += $(CFLAGS)
endif

ifeq ($(UNAME_S), Darwin) #APPLE
	ECHO_MESSAGE = "Mac OS X"
	LIBS += -framework Cocoa -framework IOKit -framework CoreVideo `pkg-config --libs sdl3`
	LIBS += -L/usr/local/lib -L/opt/local/lib

	CFLAGS += `pkg-config sdl3 --cflags`
	CFLAGS += -I/usr/local/include -I/opt/local/include
	CXXFLAGS += $(CFLAGS)
endif

ifeq ($(OS), Windows_NT)
	ECHO_MESSAGE = "MinGW"
	LIBS += -lgdi32 -limm32 `pkg-config --static --libs sdl3`

	CFLAGS += `pkg-config --cflags sdl3`
	CXXFLAGS += $(CFLAGS)
endif

##---------------------------------------------------------------------
## BUILD RULES
##---------------------------------------------------------------------

%.o:%.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o:$(IMGUI_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

%.o:$(IMGUI_DIR)/backends/%.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

%.o:$(GENERATED_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

%.o:$(GENERATED_DIR)/backends/%.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

all: $(EXE)
	@echo Build complete for $(ECHO_MESSAGE)

$(EXE): $(SOURCES) libdcimgui.a
	$(CC) -o $@ $(SOURCES) $(CFLAGS) $(LIBS)

libdcimgui.a: $(DCIMGUI_OBJS)
	ar rcs libdcimgui.a *.o

clean:
	rm -f $(EXE) $(OBJS) $(DCIMGUI_OBJS) libdcimgui.a
