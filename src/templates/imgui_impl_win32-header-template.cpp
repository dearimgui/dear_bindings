#include "%IMGUI_INCLUDE_DIR%imgui.h"
#include "%BACKEND_INCLUDE_DIR%imgui_impl_win32.h"

#include <stdio.h>

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

// This define indicates that we have windows.h included
#define IMGUI_BACKEND_HAS_WINDOWS_H

// We need to manually declare this
extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

// Wrap this in a namespace to keep it separate from the C++ API
// This define prevents #defines in the header getting defined again (as they are already in the normal header above),
// and thus generating redefinition warnings
#define DEAR_BINDINGS_INTERNAL_GLUE_CODE
namespace cimgui
{
#include "%OUTPUT_HEADER_NAME%"
}
#undef DEAR_BINDINGS_INTERNAL_GLUE_CODE

