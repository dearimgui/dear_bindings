#include "%IMGUI_INCLUDE_DIR%imgui.h"
#include "%IMGUI_INCLUDE_DIR%imgui_internal.h"

#include <stdio.h>

// Wrap this in a namespace to keep it separate from the C++ API
namespace cimgui
{
#include "%OUTPUT_HEADER_NAME%"
}

// Manual helpers
// These implement functionality that isn't in the original C++ API, but is useful to callers from other languages

CIMGUI_API void cimgui::ImVector_Construct(void* vector)
{
    // All ImVector classes are the same size, so it doesn't matter which we use for sizeof() here
    memset(vector, 0, sizeof(::ImVector<int>));
}

CIMGUI_API void cimgui::ImVector_Destruct(void* vector)
{
    // As with ImVector_construct(), it doesn't matter what the type parameter is here as we just want to get the
    // pointer and free it (without calling destructors or anything similar)
    ::ImVector<int>* real_vector = reinterpret_cast<::ImVector<int>*>(vector);
    if (real_vector->Data)
    {
        IM_FREE(real_vector->Data);
    }
}

#if defined(IMGUI_HAS_IMSTR)
#if IMGUI_HAS_IMSTR

// User-facing helper to convert char* to ImStr
CIMGUI_API cimgui::ImStr cimgui::ImStr_FromCharStr(const char* b)
{
    ImStr str;
    str.Begin = b;
    str.End = b ? b + strlen(b) : NULL;
    return str;
}

// Internal helper to convert char* directly to C++-style ImStr
static inline ::ImStr MarshalToCPP_ImStr_FromCharStr(const char* b)
{
    ::ImStr str;
    str.Begin = b;
    str.End = b ? b + strlen(b) : NULL;
    return str;
}
#endif // IMGUI_HAS_IMSTR
#endif // defined(IMGUI_HAS_IMSTR)

// Helpers for setting callbacks that return complex structures in PlatformIO
// These require a thunk in C++-land to work correctly, which is implemented here

#if defined(IMGUI_HAS_DOCK)

namespace
{
    // Data we use in the thunk to convert these from C++-style callbacks to C-style callbacks
    struct ImGui_DearBindingsThunkData
    {
        void(*PlatformIO_GetWindowPos_ThunkTarget)(cimgui::ImGuiViewport* vp, cimgui::ImVec2* result);
        void(*PlatformIO_GetWindowSize_ThunkTarget)(cimgui::ImGuiViewport* vp, cimgui::ImVec2* result);
        void(*PlatformIO_GetWindowFramebufferScale_ThunkTarget)(cimgui::ImGuiViewport* vp, cimgui::ImVec2* result);
        void(*PlatformIO_GetWindowWorkAreaInsets_ThunkTarget)(cimgui::ImGuiViewport* vp, cimgui::ImVec4* result);
    };

    // Get our thunk data for the current ImGui context, creating it if necessary
    ImGui_DearBindingsThunkData* ImGui_GetDearBindingsThunkData()
    {
        ImGuiIO& io = ImGui::GetIO();
        if (!io.BackendLanguageUserData)
        {
            io.BackendLanguageUserData = IM_NEW(ImGui_DearBindingsThunkData);
            memset(io.BackendLanguageUserData, 0, sizeof(ImGui_DearBindingsThunkData));
        }
        return reinterpret_cast<ImGui_DearBindingsThunkData*>(io.BackendLanguageUserData);
    }

    // Tidy up our thunk data, deleting it if all the target pointers are null (i.e. it is unused)
    void ImGui_TidyDearBindingsThunkData()
    {
        ImGuiIO& io = ImGui::GetIO();
        if (io.BackendLanguageUserData)
        {
            ImGui_DearBindingsThunkData* thunkData = reinterpret_cast<ImGui_DearBindingsThunkData*>(io.BackendLanguageUserData);
            if ((!thunkData->PlatformIO_GetWindowPos_ThunkTarget) &&
                (!thunkData->PlatformIO_GetWindowSize_ThunkTarget) &&
                (!thunkData->PlatformIO_GetWindowFramebufferScale_ThunkTarget) &&
                (!thunkData->PlatformIO_GetWindowWorkAreaInsets_ThunkTarget))
            {
                // Thunk data is unused and can be freed
                io.BackendLanguageUserData = nullptr;
                IM_DELETE(thunkData);
            }
        }
    }

    // Copies of the conversion stubs in order to deal with the fact that they are declared later in the file
    // Fixme: This is a little messy, but reordering things is also fiddly to do

    static inline ::ImVec2 ConvertToCPP_ImVec2_ForThunks(const cimgui::ImVec2& src)
    {
        ::ImVec2 dest;
        dest.x = src.x;
        dest.y = src.y;
        return dest;
    }

    static inline ::ImVec4 ConvertToCPP_ImVec4_ForThunks(const cimgui::ImVec4& src)
    {
        ::ImVec4 dest;
        dest.x = src.x;
        dest.y = src.y;
        dest.z = src.z;
        dest.w = src.w;
        return dest;
    }

    // Thunks for callbacks that need them

    ImVec2 ImGuiPlatformIO_GetWindowPos_Thunk(ImGuiViewport* vp)
    {
        ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
        cimgui::ImVec2 result;
        thunkData->PlatformIO_GetWindowPos_ThunkTarget(reinterpret_cast<cimgui::ImGuiViewport*>(vp), &result);
        return ConvertToCPP_ImVec2_ForThunks(result);
    }

    ImVec2 ImGuiPlatformIO_GetWindowSize_Thunk(ImGuiViewport* vp)
    {
        ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
        cimgui::ImVec2 result;
        thunkData->PlatformIO_GetWindowSize_ThunkTarget(reinterpret_cast<cimgui::ImGuiViewport*>(vp), &result);
        return ConvertToCPP_ImVec2_ForThunks(result);
    }

    ImVec2 ImGuiPlatformIO_GetWindowFramebufferScale_Thunk(ImGuiViewport* vp)
    {
        ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
        cimgui::ImVec2 result;
        thunkData->PlatformIO_GetWindowFramebufferScale_ThunkTarget(reinterpret_cast<cimgui::ImGuiViewport*>(vp), &result);
        return ConvertToCPP_ImVec2_ForThunks(result);
    }

    ImVec4 ImGuiPlatformIO_GetWindowWorkAreaInsets_Thunk(ImGuiViewport* vp)
    {
        ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
        cimgui::ImVec4 result;
        thunkData->PlatformIO_GetWindowWorkAreaInsets_ThunkTarget(reinterpret_cast<cimgui::ImGuiViewport*>(vp), &result);
        return ConvertToCPP_ImVec4_ForThunks(result);
    }
} // Anonymous namespace

CIMGUI_API void cimgui::ImGuiPlatformIO_SetPlatform_GetWindowPos(void(*func)(cimgui::ImGuiViewport* vp, cimgui::ImVec2* result))
{
    ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
    thunkData->PlatformIO_GetWindowPos_ThunkTarget = func;
    ::ImGui::GetPlatformIO().Platform_GetWindowPos = (func != nullptr) ? ImGuiPlatformIO_GetWindowPos_Thunk : nullptr;
    if (!func)
    {
        ImGui_TidyDearBindingsThunkData(); // Try to release thunk data if no longer required
    }
}

CIMGUI_API void cimgui::ImGuiPlatformIO_SetPlatform_GetWindowSize(void(*func)(cimgui::ImGuiViewport* vp, cimgui::ImVec2* result))
{
    ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
    thunkData->PlatformIO_GetWindowSize_ThunkTarget = func;
    ::ImGui::GetPlatformIO().Platform_GetWindowSize = (func != nullptr) ? ImGuiPlatformIO_GetWindowSize_Thunk : nullptr;
    if (!func)
    {
        ImGui_TidyDearBindingsThunkData(); // Try to release thunk data if no longer required
    }
}

CIMGUI_API void cimgui::ImGuiPlatformIO_SetPlatform_GetWindowFramebufferScale(void(*func)(cimgui::ImGuiViewport* vp, cimgui::ImVec2* result))
{
    ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
    thunkData->PlatformIO_GetWindowFramebufferScale_ThunkTarget = func;
    ::ImGui::GetPlatformIO().Platform_GetWindowFramebufferScale = (func != nullptr) ? ImGuiPlatformIO_GetWindowFramebufferScale_Thunk : nullptr;
    if (!func)
    {
        ImGui_TidyDearBindingsThunkData(); // Try to release thunk data if no longer required
    }
}

CIMGUI_API void cimgui::ImGuiPlatformIO_SetPlatform_GetWindowWorkAreaInsets(void(*func)(cimgui::ImGuiViewport* vp, cimgui::ImVec4* result))
{
    ImGui_DearBindingsThunkData* thunkData = ImGui_GetDearBindingsThunkData();
    thunkData->PlatformIO_GetWindowWorkAreaInsets_ThunkTarget = func;
    ::ImGui::GetPlatformIO().Platform_GetWindowWorkAreaInsets = (func != nullptr) ? ImGuiPlatformIO_GetWindowWorkAreaInsets_Thunk : nullptr;
    if (!func)
    {
        ImGui_TidyDearBindingsThunkData(); // Try to release thunk data if no longer required
    }
}

#endif // defined(IMGUI_HAS_DOCK)
