#include "%IMGUI_INCLUDE_DIR%imgui.h"
#include "%IMGUI_INCLUDE_DIR%imgui_internal.h"

// API for exported functions
#ifndef CIMGUI_API
#define CIMGUI_API extern "C"
#endif

#include <stdio.h>

// Wrap this in a namespace to keep it separate from the C++ API
// This define prevents #defines in the header getting defined again (as they are already in the normal header above),
// and thus generating redefinition warnings
#define DEAR_BINDINGS_INTERNAL_GLUE_CODE
namespace cimgui
{
extern "C"
{
#include "%OUTPUT_HEADER_NAME_NO_INTERNAL%"
#include "%OUTPUT_HEADER_NAME%"
}
}
#undef DEAR_BINDINGS_INTERNAL_GLUE_CODE

#if defined(IMGUI_HAS_IMSTR)

// Internal helper to convert char* directly to C++-style ImStrv
static inline ::ImStrv MarshalToCPP_ImStrv_FromCharStr(const char* b)
{
    ::ImStrv str;
    str.Begin = b;
    str.End = b ? b + strlen(b) : NULL;
    return str;
}

#endif // defined(IMGUI_HAS_IMSTR)
