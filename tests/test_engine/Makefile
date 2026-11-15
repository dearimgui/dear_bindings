# Simple makefile for tests

# Directories
DEARBINDINGSROOT=../..
IMGUIDIR=../../../imgui
OBJDIR=obj
GENERATEDDIR=generated

CC=gcc
UNAME_S := $(shell uname -s)

CPPFLAGS=-I$(GENERATEDDIR) -I$(IMGUIDIR) -std=c++20
CFLAGS=-I$(GENERATEDDIR) -I$(IMGUIDIR)
LIBS=$(SDLLINKFLAGS)

all: directories bindings log_forward_test

$(GENERATEDDIR)/dcimgui.h: $(IMGUIDIR)/imgui.h
	python3 "$(DEARBINDINGSROOT)/dear_bindings.py" -o "$(GENERATEDDIR)/dcimgui" "$(IMGUIDIR)/imgui.h"

$(GENERATEDDIR)/dcimgui_internal.h: $(IMGUIDIR)/imgui_internal.h $(IMGUIDIR)/imgui.h
	python3 "$(DEARBINDINGSROOT)/dear_bindings.py" -o "$(GENERATEDDIR)/dcimgui_internal" "$(IMGUIDIR)/imgui_internal.h" --include "$(IMGUIDIR)/imgui.h" --imconfig-path "imgui_internal_test.h"

$(OBJDIR)/%.o: $(IMGUIDIR)/%.cpp
	$(CC) $(CPPFLAGS) -c -o $@ $<

$(OBJDIR)/log_forward_test.o: log_forward_test.cpp
	$(CC) $(CPPFLAGS) -DIMGUI_ENABLE_TEST_ENGINE -c -o $@ $<

$(OBJDIR)/dcimgui.o: $(GENERATEDDIR)/dcimgui.cpp
	$(CC) $(CPPFLAGS) -DIMGUI_ENABLE_TEST_ENGINE -c -o $@ $<

$(OBJDIR)/dcimgui_internal.o: $(GENERATEDDIR)/dcimgui_internal.cpp
	$(CC) $(CPPFLAGS) -DIMGUI_ENABLE_TEST_ENGINE -c -o $@ $<

directories:
	@mkdir -p $(OBJDIR)
	@mkdir -p $(GENERATEDDIR)

bindings: $(GENERATEDDIR)/dcimgui.h $(GENERATEDDIR)/dcimgui_internal.h

log_forward_test: $(OBJDIR)/log_forward_test.o $(OBJDIR)/dcimgui.o $(OBJDIR)/dcimgui_internal.o $(OBJDIR)/imgui.o $(OBJDIR)/imgui_demo.o $(OBJDIR)/imgui_draw.o $(OBJDIR)/imgui_tables.o $(OBJDIR)/imgui_widgets.o
	$(CC) -o log_forward_test $(OBJDIR)/log_forward_test.o $(OBJDIR)/dcimgui.o $(OBJDIR)/dcimgui_internal.o $(OBJDIR)/imgui.o $(OBJDIR)/imgui_demo.o $(OBJDIR)/imgui_draw.o $(OBJDIR)/imgui_tables.o $(OBJDIR)/imgui_widgets.o -lstdc++ -lm $(LIBS)

clean:
	rm -rf $(OBJDIR)
	rm -rf $(GENERATEDDIR)
	rm log_forward_test

run: directories bindings log_forward_test
	./log_forward_test
