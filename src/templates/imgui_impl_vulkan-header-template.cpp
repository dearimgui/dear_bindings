#include "%IMGUI_INCLUDE_DIR%imgui.h"
#include "%BACKEND_INCLUDE_DIR%imgui_impl_vulkan.h"

#include <stdio.h>

// Wrap this in a namespace to keep it separate from the C++ API
namespace cimgui
{
#include "%OUTPUT_HEADER_NAME%"
}

