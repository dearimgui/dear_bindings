# Simple makefile for examples

# Directories
IMGUIDIR=../../../imgui
BACKENDSDIR=../../../imgui/backends
GENERATEDDIR=../../generated
GENERATEDBACKENDSDIR=../../generated/backends
OBJDIR=obj

# Settings for SDL
SDLCFLAGS=`sdl2-config --cflags`
SDLLINKFLAGS=`sdl2-config --cflags --libs`

CC=gcc
UNAME_S := $(shell uname -s)

CPPFLAGS=-I$(GENERATEDDIR) -I$(IMGUIDIR) -I$(GENERATEDBACKENDSDIR) -I$(BACKENDSDIR) $(SDLCFLAGS) -std=c++20
CFLAGS=-I$(GENERATEDDIR) -I$(IMGUIDIR) -I$(GENERATEDBACKENDSDIR) -I$(BACKENDSDIR) $(SDLCFLAGS)
LIBS=$(SDLLINKFLAGS)

# OSX and Linux need different mechanisms to link OpenGL

ifeq ($(UNAME_S), Linux)
	LIBS += -lGL
endif

ifeq ($(UNAME_S), Darwin)
	LIBS += -framework OpenGL
endif

all: directories example_sdl2_opengl2

$(OBJDIR)/main.o: main.c
	$(CC) $(CFLAGS) -c -o $@ $<
	
$(OBJDIR)/%.o: $(IMGUIDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<

$(OBJDIR)/%.o: $(BACKENDSDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<

$(OBJDIR)/%.o: $(GENERATEDDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<

$(OBJDIR)/%.o: $(GENERATEDBACKENDSDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<

directories:
	@mkdir -p $(OBJDIR)

example_sdl2_opengl2: $(OBJDIR)/main.o $(OBJDIR)/imgui_impl_opengl2.o $(OBJDIR)/imgui_impl_sdl2.o $(OBJDIR)/imgui.o $(OBJDIR)/imgui_demo.o $(OBJDIR)/imgui_draw.o $(OBJDIR)/imgui_tables.o $(OBJDIR)/imgui_widgets.o $(OBJDIR)/dcimgui.o $(OBJDIR)/dcimgui_impl_sdl2.o $(OBJDIR)/dcimgui_impl_opengl2.o
	$(CC) -o example_sdl_opengl2 $(OBJDIR)/main.o $(OBJDIR)/imgui_impl_opengl2.o $(OBJDIR)/imgui_impl_sdl2.o $(OBJDIR)/imgui.o $(OBJDIR)/imgui_demo.o $(OBJDIR)/imgui_draw.o $(OBJDIR)/imgui_tables.o $(OBJDIR)/imgui_widgets.o $(OBJDIR)/dcimgui.o $(OBJDIR)/dcimgui_impl_sdl2.o $(OBJDIR)/dcimgui_impl_opengl2.o -lstdc++ -lm $(LIBS)

clean:
	rm -rf $(OBJDIR)
	rm example_sdl_opengl2
