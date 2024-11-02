// dear imgui: "null" example application
// (compile and link imgui, create context, run headless with NO INPUTS, NO GRAPHICS OUTPUT)
// This is useful to test building, but you cannot interact with anything here!
#include <stdio.h>

#include "dcimgui.h"
#include "dcimgui_internal.h"

int main(int argc, char** argv)
{
    (void)argc;
    (void)argv;
    //IMGUI_CHECKVERSION();
    ImGui_CreateContext(NULL);
    ImGuiIO* io = ImGui_GetIO();

    // Build atlas
    unsigned char* tex_pixels = NULL;
    int tex_w, tex_h;
    ImFontAtlas_GetTexDataAsRGBA32(io->Fonts, &tex_pixels, &tex_w, &tex_h, NULL);

    for (int n = 0; n < 20; n++)
    {
        printf("NewFrame() %d\n", n);
        io->DisplaySize.x = 1920;
        io->DisplaySize.y = 1080;
        io->DeltaTime = 1.0f / 60.0f;
        ImGui_NewFrame();

        static float f = 0.0f;
        ImGui_Text("Hello, world!");
        #ifdef CIMGUI_NO_GENERATE_DEFAULT_ARG_FUNCTIONS
        ImGui_SliderFloat("float", &f, 0.0f, 1.0f, "%.3f", 0);
        #else
        ImGui_SliderFloat("float", &f, 0.0f, 1.0f);
        #endif
        ImGui_Text("Application average %.3f ms/frame (%.1f FPS)", 1000.0f / io->Framerate, io->Framerate);
        ImGui_ShowDemoWindow(NULL);
        ImGui_FocusItem();

        ImGui_DebugLog("%s", "Message from cimgui_internal.h!");
        #ifdef CIMGUI_WITH_GENERATE_UNFORMATTED_FUNCTIONS
        ImGui_DebugLogUnformatted("Message from cimgui_internal.h!");
        #endif

        ImGui_Render();
    }

    printf("DestroyContext()\n");
    ImGui_DestroyContext(NULL);
    return 0;
}
