// NOTE: This example prioritizes simplicity over correctness, and should be
// used for reference purposes only. For simplicity, it avoids boilerplate that
// an actual application should certainly have like return value/error checking
// and releasing COM objects.

#define COBJMACROS
#define INITGUID
#define OEMRESOURCE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

// Requirements:
// - OS: Windows 10, Version 1507 (Original Release)
//     - DirectX 11.3
//     - DXGI 1.4
// - Graphics Card: Feature Level 11_0
#include <d3d11_3.h>
#include <dxgi1_4.h>
#pragma comment(lib, "d3d11")
#pragma comment(lib, "dxgi")

#define IMGUI_BACKEND_HAS_WINDOWS_H
#include <cimgui.h>
#include <cimgui_impl_dx11.h>
#include <cimgui_impl_win32.h>
// NOTE: You need to build this static library from the generated Dear Bindings
// files. See https://github.com/dearimgui/dear_bindings#usage.
#pragma comment(lib, "cimgui_win32_dx11")

#include <stdbool.h>
#include <stdint.h>

#define APP_NAME u"Dear ImGui C Example [Win32 | DX11]"

LRESULT CALLBACK
window_proc(HWND hwnd, UINT msg, WPARAM w_param, LPARAM l_param)
{
    if (cImGui_ImplWin32_WndProcHandler(hwnd, msg, w_param, l_param))
    {
        return true;
    }

    LRESULT r = 0;

    switch (msg)
    {
        case WM_MENUCHAR:
        {
            r = MAKELRESULT(0, MNC_CLOSE);
            break;
        }
        case WM_CLOSE:
        {
            DestroyWindow(hwnd);
            break;
        }
        case WM_DESTROY:
        {
            PostQuitMessage(0);
            break;
        }
        default:
        {
            r = DefWindowProcW(hwnd, msg, w_param, l_param);
            break;
        }
    }

    return r;
}

int32_t WINAPI
wWinMain(HINSTANCE inst,
         HINSTANCE prev_inst,
         WCHAR* cmd_args,
         int32_t show_code)
{
    (void)prev_inst;
    (void)cmd_args;
    (void)show_code;

    // Adjust to accommodate Windows scaling.
    SetProcessDPIAware();

    HWND wnd = 0;
    {
        WCHAR* class_name = u"Window Class";
        WNDCLASSW wc
            = {.style = CS_OWNDC,
               .lpfnWndProc = window_proc,
               .hInstance = inst,
               .hCursor = (HCURSOR)LoadImageW(0,
                                              MAKEINTRESOURCEW(OCR_NORMAL),
                                              IMAGE_CURSOR,
                                              0,
                                              0,
                                              LR_SHARED),
               .lpszClassName = class_name};
        RegisterClassW(&wc);
        wnd = CreateWindowW(class_name,
                            APP_NAME,
                            WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU
                                | WS_MINIMIZEBOX,
                            CW_USEDEFAULT,
                            CW_USEDEFAULT,
                            CW_USEDEFAULT,
                            CW_USEDEFAULT,
                            0,
                            0,
                            inst,
                            0);
        ShowWindow(wnd, SW_SHOWNORMAL);
    }

    ImGuiContext* ctx = ImGui_CreateContext(0);
    cImGui_ImplWin32_Init(wnd);

    // Initialize D3D11.
    ID3D11Device3* d;
    ID3D11DeviceContext3* dc;
    IDXGISwapChain3* sc;
    ID3D11RenderTargetView* rtv;
    {
        // Create device and device context.
        D3D_FEATURE_LEVEL feat_lvls[] = {D3D_FEATURE_LEVEL_11_0};
        ID3D11Device* base_d;
        ID3D11DeviceContext* base_dc;
        D3D11CreateDevice(0,
                          D3D_DRIVER_TYPE_HARDWARE,
                          0,
                          0,
                          feat_lvls,
                          1,
                          D3D11_SDK_VERSION,
                          &base_d,
                          0,
                          &base_dc);
        ID3D11Device_QueryInterface(base_d, &IID_ID3D11Device3, (void**)&d);
        ID3D11Device_Release(base_d);
        ID3D11DeviceContext_QueryInterface(base_dc,
                                           &IID_ID3D11DeviceContext3,
                                           (void**)&dc);
        ID3D11DeviceContext_Release(base_dc);

        // Create swap chain.
        IDXGIFactory4* f;
        CreateDXGIFactory2(0, &IID_IDXGIFactory4, (void**)&f);
        DXGI_SWAP_CHAIN_DESC1 scd
            = {.Format = DXGI_FORMAT_R8G8B8A8_UNORM,
               .SampleDesc = {.Count = 1},
               .BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT,
               .BufferCount = 2,
               .Scaling = DXGI_SCALING_STRETCH,
               .SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD};
        IDXGISwapChain1* base_sc;
        IDXGIFactory4_CreateSwapChainForHwnd(f,
                                             (IUnknown*)d,
                                             wnd,
                                             &scd,
                                             0,
                                             0,
                                             &base_sc);
        IDXGIFactory4_Release(f);
        IDXGISwapChain1_QueryInterface(base_sc,
                                       &IID_IDXGISwapChain3,
                                       (void**)&sc);
        IDXGISwapChain1_Release(base_sc);

        // Disable default DirectX [Alt + Enter] behavior.
        IDXGISwapChain3_GetParent(sc, &IID_IDXGIFactory4, (void**)&f);
        IDXGIFactory4_MakeWindowAssociation(f, wnd, DXGI_MWA_NO_ALT_ENTER);
        IDXGIFactory4_Release(f);

        // Create render target view.
        ID3D11Texture2D* back_buffer;
        IDXGISwapChain3_GetBuffer(sc,
                                  0,
                                  &IID_ID3D11Texture2D,
                                  (void**)&back_buffer);
        D3D11_RENDER_TARGET_VIEW_DESC rtvd
            = {.Format = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,
               .ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D};
        ID3D11Device3_CreateRenderTargetView(d,
                                             (ID3D11Resource*)back_buffer,
                                             &rtvd,
                                             &rtv);
        ID3D11Texture2D_Release(back_buffer);
    }

    cImGui_ImplDX11_Init((ID3D11Device*)d, (ID3D11DeviceContext*)dc);

    bool show_demo = true;

    MSG msg = {0};
    while (msg.message != WM_QUIT)
    {
        if (PeekMessageW(&msg, 0, 0, 0, PM_REMOVE))
        {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
            continue;
        }

        cImGui_ImplDX11_NewFrame();
        cImGui_ImplWin32_NewFrame();
        ImGui_NewFrame();

        ImGui_ShowDemoWindow(&show_demo);

        ImGui_Render();

        // Update D3D11.
        {
            ID3D11DeviceContext3_OMSetRenderTargets(dc, 1, &rtv, 0);
            float clear_color[] = {0.0f, 0.0f, 0.0f, 1.0f}; // black
            ID3D11DeviceContext3_ClearRenderTargetView(dc, rtv, clear_color);
        }

        cImGui_ImplDX11_RenderDrawData(ImGui_GetDrawData());

        IDXGISwapChain3_Present(sc, 1, 0);
    }

    cImGui_ImplDX11_Shutdown();
    cImGui_ImplWin32_Shutdown();
    ImGui_DestroyContext(ctx);

    return 0;
}
