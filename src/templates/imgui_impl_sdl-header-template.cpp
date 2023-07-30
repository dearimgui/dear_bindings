#include "imgui.h"
#include "imgui_impl_sdl.h"

#include <stdio.h>
#include <stdarg.h>

// Wrap this in a namespace to keep it separate from the C++ API
namespace cimgui
{
#include "%OUTPUT_HEADER_NAME%"
}

