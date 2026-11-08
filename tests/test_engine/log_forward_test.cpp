#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <iostream>
#include <vector>

#include "imgui.h"
#include "imgui_internal.h"

#define DEAR_BINDINGS_INTERNAL_GLUE_CODE
namespace cimgui
{
extern "C"
{
#include "dcimgui.h"
#include "dcimgui_internal.h"
}
}
#undef DEAR_BINDINGS_INTERNAL_GLUE_CODE

using cimgui::cImGuiTestEngineHook_Log;

// Define the four hooks app-side (imgui only declares them)
void ImGuiTestEngineHook_ItemAdd(ImGuiContext* ctx, ImGuiID id, const ImRect& bb, const ImGuiLastItemData* item_data)
{
    (void)ctx; (void)id; (void)bb; (void)item_data;
}

void ImGuiTestEngineHook_ItemInfo(ImGuiContext* ctx, ImGuiID id, const char* label, ImGuiItemStatusFlags flags)
{
    (void)ctx; (void)id; (void)label; (void)flags;
}

const char* ImGuiTestEngine_FindItemDebugLabel(ImGuiContext* ctx, ImGuiID id)
{
    (void)ctx; (void)id;
    return "";
}

static std::string g_captured_log;
static ImGuiContext* g_captured_ctx = nullptr;

void ImGuiTestEngineHook_Log(ImGuiContext* ctx, const char* fmt, ...)
{
    g_captured_ctx = ctx;
    va_list args;
    va_start(args, fmt);
    va_list args_copy;
    va_copy(args_copy, args);
    int len = vsnprintf(nullptr, 0, fmt, args_copy);
    va_end(args_copy);
    if (len >= 0)
    {
        std::vector<char> buf(len + 1);
        vsnprintf(buf.data(), buf.size(), fmt, args);
        g_captured_log.assign(buf.data(), len);
    }
    else
    {
        g_captured_log.clear();
    }
    va_end(args);
}

int main()
{
    // Test (a): format specifiers (%d, %s)
    {
        ImGuiContext* dummy_ctx = reinterpret_cast<ImGuiContext*>(0x1234);
        int num = 42;
        const char* str = "test_engine_logging";

        char expected[256];
        snprintf(expected, sizeof(expected), "Format check: int=%d, str=%s", num, str);

        g_captured_log.clear();
        g_captured_ctx = nullptr;
        cImGuiTestEngineHook_Log(reinterpret_cast<cimgui::ImGuiContext*>(dummy_ctx), "Format check: int=%d, str=%s", num, str);

        if (g_captured_ctx != dummy_ctx)
        {
            std::cerr << "FAIL: Context pointer mismatch in test (a)!" << std::endl;
            return 1;
        }
        if (g_captured_log != expected)
        {
            std::cerr << "FAIL: Log content mismatch in test (a)!" << std::endl;
            std::cerr << "  Expected: " << expected << std::endl;
            std::cerr << "  Got:      " << g_captured_log << std::endl;
            return 1;
        }
    }

    // Test (b): string longer than 9000 chars (also exercising %d and %s)
    {
        ImGuiContext* dummy_ctx = reinterpret_cast<ImGuiContext*>(0x5678);
        const int payload_len = 9500;
        std::string payload(payload_len, 'x');
        for (int i = 0; i < payload_len; ++i)
        {
            payload[i] = static_cast<char>('a' + (i % 26));
        }

        int code = 999;
        const char* prefix = "LONG_PAYLOAD";

        int expected_len = snprintf(nullptr, 0, "Prefix=%s Code=%d Payload=%s", prefix, code, payload.c_str());
        std::vector<char> expected_buf(expected_len + 1);
        snprintf(expected_buf.data(), expected_buf.size(), "Prefix=%s Code=%d Payload=%s", prefix, code, payload.c_str());
        std::string expected(expected_buf.data(), expected_len);

        g_captured_log.clear();
        g_captured_ctx = nullptr;
        cImGuiTestEngineHook_Log(reinterpret_cast<cimgui::ImGuiContext*>(dummy_ctx), "Prefix=%s Code=%d Payload=%s", prefix, code, payload.c_str());

        if (g_captured_ctx != dummy_ctx)
        {
            std::cerr << "FAIL: Context pointer mismatch in test (b)!" << std::endl;
            return 1;
        }
        if (g_captured_log.size() != expected.size() || g_captured_log != expected)
        {
            std::cerr << "FAIL: Log content mismatch in test (b)!" << std::endl;
            std::cerr << "  Expected length: " << expected.size() << std::endl;
            std::cerr << "  Got length:      " << g_captured_log.size() << std::endl;
            return 1;
        }
    }

    std::cout << "All log forwarding tests passed!" << std::endl;
    return 0;
}
