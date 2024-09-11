#include "%IMGUI_INCLUDE_DIR%imgui.h"
#include "%IMGUI_INCLUDE_DIR%imgui_internal.h"

// API for exported functions
#ifndef CIMGUI_API
#define CIMGUI_API extern "C"
#endif

#include <stdio.h>

// Wrap this in a namespace to keep it separate from the C++ API
namespace cimgui
{
extern "C"
{
#include "%OUTPUT_HEADER_NAME_NO_INTERNAL%"
#include "%OUTPUT_HEADER_NAME%"
}
}
