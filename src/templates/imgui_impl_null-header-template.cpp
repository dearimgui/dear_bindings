#include "%IMGUI_INCLUDE_DIR%imgui.h"
#include "%BACKEND_INCLUDE_DIR%imgui_impl_null.h"

#include <stdio.h>

// Wrap this in a namespace to keep it separate from the C++ API
// This define prevents #defines in the header getting defined again (as they are already in the normal header above),
// and thus generating redefinition warnings
#define DEAR_BINDINGS_INTERNAL_GLUE_CODE
namespace cimgui
{
#include "%OUTPUT_HEADER_NAME%"
}
#undef DEAR_BINDINGS_INTERNAL_GLUE_CODE

