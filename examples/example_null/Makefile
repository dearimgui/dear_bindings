# Simple makefile for examples

# Directories
IMGUIDIR=../../../imgui
GENERATEDDIR=../../generated
OBJDIR=obj

CC=gcc
CPPFLAGS=-I$(GENERATEDDIR) -I$(IMGUIDIR) -std=c++20
CFLAGS=-I$(GENERATEDDIR) -I$(IMGUIDIR)

all: directories example_null

$(OBJDIR)/main.o: main.c
	$(CC) $(CFLAGS) -c -o $@ $<

$(OBJDIR)/%.o: $(IMGUIDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<
	
$(OBJDIR)/%.o: $(GENERATEDDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<
	
directories:
	@mkdir -p $(OBJDIR)

example_null: $(OBJDIR)/main.o $(OBJDIR)/imgui.o $(OBJDIR)/imgui_demo.o $(OBJDIR)/imgui_draw.o $(OBJDIR)/imgui_tables.o $(OBJDIR)/imgui_widgets.o $(OBJDIR)/dcimgui.o
	$(CC) -o example_null $(OBJDIR)/main.o $(OBJDIR)/imgui.o $(OBJDIR)/imgui_demo.o $(OBJDIR)/imgui_draw.o $(OBJDIR)/imgui_tables.o $(OBJDIR)/imgui_widgets.o $(OBJDIR)/dcimgui.o -lstdc++ -lm 

clean:
	rm -rf $(OBJDIR)
	rm example_null
