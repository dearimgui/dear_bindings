# Dear Bindings Version v0.11 WIP
# Generates C-language headers for Dear ImGui
# Developed by Ben Carter (e-mail: ben AT shironekolabs.com, github: @ShironekoBen)

# Example command-line:
#   python dear_bindings.py --output dcimgui ../imgui/imgui.h
#   python dear_bindings.py --output dcimgui_internal --include ../imgui/imgui.h ../imgui/imgui_internal.h

# Example Input:
#   imgui.h     : a C++ header file (aiming to also support imgui_internal.h, implot.h etc.: support is not complete yet).

# Example output:
#   dcimgui.h    : a C header file for compilation by a modern C compiler, including full comments from original header file.
#   dcimgui.cpp  : a CPP implementation file which can to be linked into a C program.
#   dcimgui.json : full metadata to reconstruct bindings for other programming languages, including full comments.

import os
from pathlib import Path
from src import code_dom
from src import c_lexer
from src import utils
import argparse
import sys
import traceback
from src.modifiers import *
from src.generators import *
from src.type_comprehension import *


# Insert a single header template file, complaining if it does not exist
# Replaces any expansions in the expansions dictionary with the given result
def insert_single_template(dest_file, template_file, expansions):
    if not os.path.isfile(template_file):
        print("Template file " + template_file + " could not be found (note that template file names are "
                                                 "expected to match source file names, so if you have "
                                                 "renamed imgui.h you will need to rename the template as "
                                                 "well). The common template file is included regardless of source "
                                                 "file name.")
        sys.exit(2)

    with open(template_file, "r") as src_file:
        for line in src_file.readlines():
            for before, after in expansions.items():
                line = line.replace(before, after)
            dest_file.write(line)


# Insert the contents of the appropriate header template file(s)
def insert_header_templates(dest_file, template_dir, src_file_name, dest_file_ext, expansions):
    # Include the common template file
    insert_single_template(dest_file,
                           os.path.join(template_dir, "common-header-template" + dest_file_ext),
                           expansions)

    # Include the specific template for the file we are generating
    insert_single_template(dest_file,
                           os.path.join(template_dir, src_file_name + "-header-template" + dest_file_ext),
                           expansions)


def parse_single_header(src_file, context):
    print("Parsing " + src_file)

    with open(src_file, "r") as f:
        file_content = f.read()

    # Tokenize file and then convert into a DOM

    stream = c_lexer.tokenize(file_content)

    if False:  # Debug dump tokens
        while True:
            tok = stream.get_token()
            if not tok:
                break  # No more input
            print(tok)
        return

    return code_dom.DOMHeaderFile.parse(context, stream, os.path.split(src_file)[1])


# Parse the C++ header found in src_file, and write a C header to dest_file_no_ext.h, with binding implementation in
# dest_file_no_ext.cpp. Metadata will be written to dest_file_no_ext.json. implementation_header should point to a file
# containing the initial header block for the implementation (provided in the templates/ directory).
def convert_header(
        src_file,
        include_files,
        dest_file_no_ext,
        template_dir,
        no_struct_by_value_arguments,
        no_generate_default_arg_functions,
        generate_unformatted_functions,
        is_backend,
        imgui_include_dir,
        backend_include_dir,
        emit_combined_json_metadata,
        prefix_replacements
    ):

    # Set up context and DOM root
    context = code_dom.ParseContext()
    dom_root = code_dom.DOMHeaderFileSet()

    # Check if we'll do some special treatment for imgui_internal.h
    is_imgui_internal = os.path.basename(src_file) == "imgui_internal.h"

    # Parse any configuration include files and add them to the DOM
    for include_file in include_files:
        dom_root.add_child(parse_single_header(include_file, context))

    # Parse and add the main header
    main_src_root = parse_single_header(src_file, context)
    dom_root.add_child(main_src_root)

    # Assign a destination filename based on the output file
    dest_file_name_only = os.path.basename(dest_file_no_ext)
    _, main_src_root.dest_filename = os.path.split(dest_file_no_ext)
    main_src_root.dest_filename += ".h"  # Presume the primary output file is the .h

    dom_root.validate_hierarchy()
    #  dom_root.dump()

    print("Storing unmodified DOM")

    dom_root.save_unmodified_clones()

    print("Applying modifiers")

    # Apply modifiers

    # Add headers we need and remove those we don't
    if not is_backend:
        mod_add_includes.apply(dom_root, ["<stdbool.h>"])  # We need stdbool.h to get bool defined
        mod_add_includes.apply(dom_root, ["<stdint.h>"])  # We need stdint.h to get int32_t
        mod_remove_includes.apply(dom_root, ["<float.h>",
                                             "<string.h>"])

    if is_backend:
        # Backends need to reference dcimgui.h, not imgui.h
        mod_change_includes.apply(dom_root, {"\"imgui.h\"": "\"dcimgui.h\""})

        # Backends need a forward-declaration for ImDrawData so that the code generator understands
        # that it is an ImGui type and needs conversion
        mod_add_forward_declarations.apply(main_src_root, ["struct ImDrawData;"])

        # Look for "ImGui_ImplWin32_WndProcHandler" and rewrite the #if on it (this is a bit of a hack)
        mod_rewrite_containing_preprocessor_conditional.apply(dom_root, "ImGui_ImplWin32_WndProcHandler",
                                                              "0",
                                                              "IMGUI_BACKEND_HAS_WINDOWS_H",
                                                              True)

    mod_attach_preceding_comments.apply(dom_root)
    mod_remove_function_bodies.apply(dom_root)
    mod_assign_anonymous_type_names.apply(dom_root)
    # Remove ImGuiOnceUponAFrame for now as it needs custom fiddling to make it usable from C
    # Remove ImNewDummy/ImNewWrapper as it's a helper for C++ new (and C dislikes empty structs)
    mod_remove_structs.apply(dom_root, ["ImGuiOnceUponAFrame",
                                        "ImNewDummy",  # ImGui <1.82
                                        "ImNewWrapper",  # ImGui >=1.82
                                        # Templated stuff in imgui_internal.h
                                        "ImBitArray", # template with two parameters, not supported
                                        "ImSpanAllocator",
                                        ])
    # Remove all functions from certain types, as they're not really useful
    mod_remove_all_functions_from_classes.apply(dom_root, ["ImVector", "ImSpan", "ImChunkStream"])
    # Remove all functions from ImPool, since we can't handle nested template functions yet
    mod_remove_all_functions_from_classes.apply(dom_root, ["ImPool"])

    # Remove Value() functions which are dumb helpers over Text(), would need custom names otherwise
    mod_remove_functions.apply(dom_root, ["ImGui::Value"])
    # Remove ImQsort() functions as modifiers on function pointers seem to emit a "anachronism used: modifiers on data are ignored" warning.
    mod_remove_functions.apply(dom_root, ["ImQsort"])
    # FIXME: Remove incorrectly parsed constructor due to "explicit" keyword.
    mod_remove_functions.apply(dom_root, ["ImVec2ih::ImVec2ih"])
    # Remove ErrorLogCallbackToDebugLog() from imgui_internal.h as there isn't a ErrorLogCallbackToDebugLogV() version for the bindings to call right now
    mod_remove_functions.apply(dom_root, ["ImGui::ErrorLogCallbackToDebugLog"])
    # Remove some templated functions from imgui_internal.h that we don't want and cause trouble
    mod_remove_functions.apply(dom_root, ["ImGui::ScaleRatioFromValueT",
                                          "ImGui::ScaleValueFromRatioT",
                                          "ImGui::DragBehaviorT",
                                          "ImGui::SliderBehaviorT",
                                          "ImGui::RoundScalarWithFormatT",
                                          "ImGui::CheckboxFlagsT"])
    
    mod_remove_functions.apply(dom_root, ["ImGui::GetInputTextState",
                                          "ImGui::DebugNodeInputTextState"])
    

    mod_add_prefix_to_loose_functions.apply(dom_root, "c")

    if not is_backend:
        # Add helper functions to create/destroy ImVectors
        # Implementation code for these can be found in templates/imgui-header.cpp
        mod_add_manual_helper_functions.apply(dom_root,
                                              [
                                                  "void ImVector_Construct(void* vector); // Construct a "
                                                  "zero-size ImVector<> (of any type). This is primarily "
                                                  "useful when calling "
                                                  "ImFontGlyphRangesBuilder_BuildRanges()",

                                                  "void ImVector_Destruct(void* vector); // Destruct an "
                                                  "ImVector<> (of any type). Important: Frees the vector "
                                                  "memory but does not call destructors on contained objects "
                                                  "(if they have them)",
                                              ])
        # ImStr conversion helper, only enabled if IMGUI_HAS_IMSTR is on
        mod_add_manual_helper_functions.apply(dom_root,
                                              [
                                                  "ImStr ImStr_FromCharStr(const char* b); // Build an ImStr "
                                                  "from a regular const char* (no data is copied, so you need to make "
                                                  "sure the original char* isn't altered as long as you are using the "
                                                  "ImStr)."
                                              ],
                                              # This weirdness is because we want this to compile cleanly even if
                                              # IMGUI_HAS_IMSTR wasn't defined
                                              ["defined(IMGUI_HAS_IMSTR)", "IMGUI_HAS_IMSTR"])

    # Add a note to ImFontGlyphRangesBuilder_BuildRanges() pointing people at the helpers
    mod_add_function_comment.apply(dom_root,
                                   "ImFontGlyphRangesBuilder::BuildRanges",
                                   "(ImVector_Construct()/ImVector_Destruct() can be used to safely "
                                   "construct out_ranges)")

    mod_set_arguments_as_nullable.apply(dom_root, ["fmt"], False)  # All arguments called "fmt" are non-nullable
    mod_remove_operators.apply(dom_root)
    mod_remove_heap_constructors_and_destructors.apply(dom_root)
    mod_convert_references_to_pointers.apply(dom_root)
    if no_struct_by_value_arguments:
        mod_convert_by_value_struct_args_to_pointers.apply(dom_root)
    # Assume IM_VEC2_CLASS_EXTRA and IM_VEC4_CLASS_EXTRA are never defined as they are likely to just cause problems
    # if anyone tries to use it
    mod_flatten_conditionals.apply(dom_root, "IM_VEC2_CLASS_EXTRA", False)
    mod_flatten_conditionals.apply(dom_root, "IM_VEC4_CLASS_EXTRA", False)
    mod_flatten_namespaces.apply(dom_root, {'ImGui': 'ImGui_', 'ImStb': 'ImStb_'})
    mod_flatten_nested_classes.apply(dom_root)
    # The custom type fudge here is a workaround for how template parameters are expanded
    mod_flatten_templates.apply(dom_root, custom_type_fudges={'const ImFont**': 'ImFont* const*'})
    # Remove dangling unspecialized template that flattening didn't handle
    mod_remove_structs.apply(dom_root, ["ImVector_T"])
    # Mark all the ImVector_ instantiations as single-line definitions
    mod_mark_structs_as_single_line_definition.apply(dom_root, ["ImVector_"])

    # We treat certain types as by-value types
    mod_mark_by_value_structs.apply(dom_root, by_value_structs=[
        'ImVec1',
        'ImVec2',
        'ImVec2ih',
        'ImVec4',
        'ImColor',
        'ImStr',
        'ImRect',
        'ImGuiListClipperRange'
    ])
    mod_mark_internal_members.apply(dom_root)
    mod_flatten_class_functions.apply(dom_root)
    mod_flatten_inheritance.apply(dom_root)
    mod_remove_nested_typedefs.apply(dom_root)
    mod_remove_static_fields.apply(dom_root)
    mod_remove_extern_fields.apply(dom_root)
    mod_remove_constexpr.apply(dom_root)
    mod_generate_imstr_helpers.apply(dom_root)
    mod_remove_enum_forward_declarations.apply(dom_root)
    mod_calculate_enum_values.apply(dom_root)
    # Treat enum values ending with _ as internal, and _COUNT as being count values
    mod_mark_special_enum_values.apply(dom_root, internal_suffixes=["_"], count_suffixes=["_COUNT"])
    # Mark enums that end with Flags (or Flags_ for the internal ones) as being flag enums
    mod_mark_flags_enums.apply(dom_root, ["Flags", "Flags_"])

    # These two are special cases because there are now (deprecated) overloads that differ from the main functions
    # only in the type of the callback function. The normal disambiguation system can't handle that, so instead we
    # manually rename the older versions of those functions here.
    mod_rename_function_by_signature.apply(dom_root,
        'ImGui_Combo',  # Function name
        'old_callback',  # Argument to look for to identify this function
        'ImGui_ComboObsolete'  # New name
    )
    mod_rename_function_by_signature.apply(dom_root,
        'ImGui_ListBox',  # Function name
        'old_callback',  # Argument to look for to identify this function
        'ImGui_ListBoxObsolete'  # New name
    )

    # The DirectX backends declare some DirectX types that need to not have _t appended to their typedef names
    mod_mark_structs_as_using_unmodified_name_for_typedef.apply(dom_root,
                                                                ["ID3D11Device",
                                                                 "ID3D11DeviceContext",
                                                                 "ID3D12Device",
                                                                 "ID3D12DescriptorHeap",
                                                                 "ID3D12GraphicsCommandList",
                                                                 "D3D12_CPU_DESCRIPTOR_HANDLE",
                                                                 "D3D12_GPU_DESCRIPTOR_HANDLE",
                                                                 "IDirect3DDevice9",
                                                                 "GLFWwindow",
                                                                 "GLFWmonitor"
                                                                 ])

    # These DirectX types are awkward and we need to use a pointer-based cast when converting them
    mod_mark_types_for_pointer_cast.apply(dom_root, ["D3D12_CPU_DESCRIPTOR_HANDLE",
                                                     "D3D12_GPU_DESCRIPTOR_HANDLE"])

    # SDL backend forward-declared types
    mod_mark_structs_as_using_unmodified_name_for_typedef.apply(dom_root,
                                                                ["SDL_Window",
                                                                 "SDL_Renderer",
                                                                 "SDL_Gamepad",
                                                                 "_SDL_GameController"
                                                                 ])

    if is_imgui_internal:
        # Some functions in imgui_internal already have the Ex suffix,
        # which wreaks havok on disambiguation
        mod_rename_functions.apply(main_src_root, {
            'ImGui_BeginMenuEx': 'ImGui_BeginMenuWithIcon',
            'ImGui_MenuItemEx': 'ImGui_MenuItemWithIcon',
            'ImGui_BeginTableEx': 'ImGui_BeginTableWithID',
            'ImGui_ButtonEx': 'ImGui_ButtonWithFlags',
            'ImGui_ImageButtonEx': 'ImGui_ImageButtonWithFlags',
            'ImGui_InputTextEx': 'ImGui_InputTextWithHintAndSize',
            'ImGui_RenderTextClippedEx': 'ImGui_RenderTextClippedWithDrawList',
        })

    mod_disambiguate_functions.apply(dom_root,
                                     name_suffix_remaps={
                                         # Some more user-friendly suffixes for certain types
                                         'const char*': 'Str',
                                         'char*': 'Str',
                                         'unsigned int': 'Uint',
                                         'unsigned int*': 'UintPtr',
                                         'ImGuiID': 'ID',
                                         'const void*': 'Ptr',
                                         'void*': 'Ptr'},
                                     # Functions that look like they have name clashes but actually don't
                                     # thanks to preprocessor conditionals
                                     functions_to_ignore=[
                                         "cImFileOpen",
                                         "cImFileClose",
                                         "cImFileGetSize",
                                         "cImFileRead",
                                         "cImFileWrite"],
                                     functions_to_rename_everything=[
                                         "ImGui_CheckboxFlags"  # This makes more sense as IntPtr/UIntPtr variants
                                     ],
                                     type_priorities={
                                     })
    
    if not no_generate_default_arg_functions:
        mod_generate_default_argument_functions.apply(dom_root,
                                                      # We ignore functions that don't get called often because in those
                                                      # cases the default helper doesn't add much value but does clutter
                                                      # up the header file
                                                      functions_to_ignore=[
                                                          # Main
                                                          'ImGui_CreateContext',
                                                          'ImGui_DestroyContext',
                                                          # Demo, Debug, Information
                                                          'ImGui_ShowDemoWindow',
                                                          'ImGui_ShowMetricsWindow',
                                                          'ImGui_ShowDebugLogWindow',
                                                          'ImGui_ShowStackToolWindow',
                                                          'ImGui_ShowAboutWindow',
                                                          'ImGui_ShowStyleEditor',
                                                          # Styles
                                                          'ImGui_StyleColorsDark',
                                                          'ImGui_StyleColorsLight',
                                                          'ImGui_StyleColorsClassic',
                                                          # Windows
                                                          'ImGui_Begin',
                                                          'ImGui_BeginChild',
                                                          'ImGui_BeginChildID',
                                                          'ImGui_SetNextWindowSizeConstraints',
                                                          # Scrolling
                                                          'ImGui_SetScrollHereX',
                                                          'ImGui_SetScrollHereY',
                                                          'ImGui_SetScrollFromPosX',
                                                          'ImGui_SetScrollFromPosY',
                                                          # Parameters stacks
                                                          'ImGui_PushTextWrapPos',
                                                          # Widgets
                                                          'ImGui_ProgressBar',
                                                          'ImGui_ColorPicker4',
                                                          'ImGui_TreePushPtr', # Ensure why core lib has this default to NULL?
                                                          'ImGui_BeginListBox',
                                                          'ImGui_ListBox',
                                                          'ImGui_MenuItemBoolPtr',
                                                          'ImGui_BeginPopupModal',
                                                          'ImGui_OpenPopupOnItemClick',
                                                          'ImGui_TableGetColumnName',
                                                          'ImGui_TableGetColumnFlags',
                                                          'ImGui_TableSetBgColor',
                                                          'ImGui_GetColumnWidth',
                                                          'ImGui_GetColumnOffset',
                                                          'ImGui_BeginTabItem',
                                                          # Misc
                                                          'ImGui_LogToTTY',
                                                          'ImGui_LogToFile',
                                                          'ImGui_LogToClipboard',
                                                          'ImGui_BeginDisabled',
                                                          # Inputs
                                                          'ImGui_IsMousePosValid',
                                                          'ImGui_IsMouseDragging',
                                                          'ImGui_GetMouseDragDelta',
                                                          'ImGui_CaptureKeyboardFromApp',
                                                          'ImGui_CaptureMouseFromApp',
                                                          # Settings
                                                          'ImGui_LoadIniSettingsFromDisk',
                                                          'ImGui_LoadIniSettingsFromMemory',
                                                          'ImGui_SaveIniSettingsToMemory',
                                                          'ImGui_SaveIniSettingsToMemory',
                                                          # Memory Allcators
                                                          'ImGui_SetAllocatorFunctions',
                                                          # Other types
                                                          'ImGuiIO_SetKeyEventNativeDataEx',
                                                          'ImGuiTextFilter_Draw',
                                                          'ImGuiTextFilter_PassFilter',
                                                          'ImGuiTextBuffer_append',
                                                          'ImGuiInputTextCallbackData_InsertChars',
                                                          'ImColor_SetHSV',
                                                          'ImColor_HSV',
                                                          'ImGuiListClipper_Begin',
                                                          # ImDrawList
                                                          # - all 'int num_segments = 0' made explicit
                                                          'ImDrawList_AddCircleFilled',
                                                          'ImDrawList_AddBezierCubic',
                                                          'ImDrawList_AddBezierQuadratic',
                                                          'ImDrawList_PathStroke',
                                                          'ImDrawList_PathArcTo',
                                                          'ImDrawList_PathBezierCubicCurveTo',
                                                          'ImDrawList_PathBezierQuadraticCurveTo',
                                                          'ImDrawList_PathRect',
                                                          'ImDrawList_AddBezierCurve',
                                                          'ImDrawList_PathBezierCurveTo',
                                                          'ImDrawList_PushClipRect',
                                                          # ImFont, ImFontGlyphRangesBuilder
                                                          'ImFontGlyphRangesBuilder_AddText',
                                                          'ImFont_AddRemapChar',
                                                          'ImFont_RenderText',
                                                          # Obsolete functions
                                                          'ImGui_ImageButtonImTextureID',
                                                          'ImGui_ListBoxHeaderInt',
                                                          'ImGui_ListBoxHeader',
                                                          'ImGui_OpenPopupContextItem',
                                                      ],
                                                      function_prefixes_to_ignore=[
                                                          'ImGuiStorage_',
                                                          'ImFontAtlas_'
                                                      ],
                                                      trivial_argument_types=[
                                                          'ImGuiCond'
                                                      ],
                                                      trivial_argument_names=[
                                                          'flags',
                                                          'popup_flags'
                                                      ])

    # Do some special-case renaming of functions
    mod_rename_functions.apply(dom_root, {
        # We want the ImGuiCol version of GetColorU32 to be the primary one, but we can't use type_priorities on
        # mod_disambiguate_functions to achieve that because it also has more arguments and thus naturally gets passed
        # over. Rather than introducing yet another layer of knobs to try and control _that_, we just do some
        # after-the-fact renaming here.
        'ImGui_GetColorU32': 'ImGui_GetColorU32ImVec4',
        'ImGui_GetColorU32ImGuiCol': 'ImGui_GetColorU32',
        'ImGui_GetColorU32ImGuiColEx': 'ImGui_GetColorU32Ex',
        # ImGui_IsRectVisible is kinda inobvious as it stands, since the two overrides take the exact same type but
        # interpret it differently. Hence do some renaming to make it clearer.
        'ImGui_IsRectVisible': 'ImGui_IsRectVisibleBySize',
        'ImGui_IsRectVisibleImVec2': 'ImGui_IsRectVisible'
    })

    if generate_unformatted_functions:
        mod_add_unformatted_functions.apply(dom_root,
                                            functions_to_ignore=[
                                                'ImGui_Text',
                                                'ImGuiTextBuffer_appendf'
                                            ])
        
    if is_imgui_internal:
        mod_move_elements.apply(dom_root,
                                main_src_root,
                                [
                                    # This terribleness is because those few type definitions needs to appear
                                    # below the definitions of ImVector_ImGuiTable and ImVector_ImGuiTabBar
                                    (code_dom.DOMClassStructUnion, 'ImGuiTextIndex'),
                                    (code_dom.DOMClassStructUnion, 'ImPool_', True),
                                    #
                                    (code_dom.DOMClassStructUnion, 'ImVector_int'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_const_charPtr'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiColorMod'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiContextHook'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiDockNodeSettings'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiDockRequest'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiFocusScopeData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiGroupData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiID'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiInputEvent'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiItemFlags'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiKeyRoutingData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiListClipperData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiListClipperRange'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiNavTreeNodeData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiMultiSelectState'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiMultiSelectTempData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiOldColumnData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiOldColumns'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiPopupData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiPtrOrIndex'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiSettingsHandler'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiShrinkWidthItem'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiStackLevelInfo'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiStyleMod'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTabBar'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTabItem'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTable'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTableColumnSortSpecs'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTableHeaderData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTableInstanceData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTableTempData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiTreeNodeStackData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiViewportPPtr'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiWindowPtr'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_ImGuiWindowStackData'),
                                    (code_dom.DOMClassStructUnion, 'ImVector_unsigned_char'),
                                    #
                                    (code_dom.DOMClassStructUnion, 'ImChunkStream_ImGuiWindowSettings'),
                                    (code_dom.DOMClassStructUnion, 'ImChunkStream_ImGuiTableSettings'),
                                    # Fudge those typedefs to be at the top
                                    (code_dom.DOMTypedef, 'ImGuiTableColumnIdx', False, True),
                                ])
    else:
        mod_move_elements.apply(dom_root,
                                main_src_root,
                                [
                                    # This is currently defined after the point where the ImVector expansions appear,
                                    # so we need to move it up to avoid declaration issues. We move the #ifndef
                                    # rather than the typedef itself because we want the whole block.
                                    (code_dom.DOMPreprocessorIf, 'ImDrawIdx', False, True),
                                ])


    # Make all functions use CIMGUI_API/CIMGUI_IMPL_API
    mod_make_all_functions_use_imgui_api.apply(dom_root)
    # Rename the API defines
    mod_rename_defines.apply(dom_root, {'IMGUI_API': 'CIMGUI_API', 'IMGUI_IMPL_API': 'CIMGUI_IMPL_API'})
    # Remove these #defines as they don't make sense in C
    mod_remove_defines.apply(dom_root, ["IM_PLACEMENT_NEW(_PTR)", "IM_NEW(_TYPE)"])
    # Rewrite these defines to reference the new function names
    # This could be done more generically but there are only three at present and there's a limit to how generic
    # we can get (as there's all sorts of #define trickery that could break the general case), so for now we'll
    # just do it the easy way
    mod_rewrite_defines.apply(dom_root, [
        "IM_ALLOC(_SIZE)",
        "IM_FREE(_PTR)",
        "IMGUI_CHECKVERSION()"
    ], {"ImGui::": "ImGui_"})
    # Rename these to stop them generating compile warnings as they clash with those in imgui.h
    mod_rename_defines.apply(dom_root, {
        'IM_ALLOC(_SIZE)': 'CIM_ALLOC(_SIZE)',
        'IM_FREE(_PTR)': 'CIM_FREE(_PTR)',
        'IMGUI_CHECKVERSION()': 'CIMGUI_CHECKVERSION()'
    })

    mod_forward_declare_structs.apply(dom_root)
    mod_wrap_with_extern_c.apply(main_src_root)  # main_src_root here to avoid wrapping the config headers
    # For now we leave #pragma once intact on the assumption that modern compilers all support it, but if necessary
    # it can be replaced with a traditional #include guard by uncommenting the line below. If you find yourself needing
    # this functionality in a significant way please let me know!
    # mod_remove_pragma_once.apply(dom_root)
    mod_remove_empty_conditionals.apply(dom_root)
    mod_merge_blank_lines.apply(dom_root)
    mod_remove_blank_lines.apply(dom_root)
    mod_align_enum_values.apply(dom_root)
    mod_align_function_names.apply(dom_root)
    mod_align_structure_field_names.apply(dom_root)
    mod_align_comments.apply(dom_root)

    # Exclude some defines that aren't really useful from the metadata
    mod_exclude_defines_from_metadata.apply(dom_root, [
        "CIMGUI_IMPL_API",
        "IM_COL32_WHITE",
        "IM_COL32_BLACK",
        "IM_COL32_BLACK_TRANS",
        "ImDrawCallback_ResetRenderState"
    ])

    mod_replace_typedef_with_opaque_buffer.apply(dom_root, [
        ("ImBitArrayForNamedKeys", 20) # template with two parameters, not supported
    ])

    # Remove namespaced define
    mod_remove_typedefs.apply(dom_root, [
        "ImStbTexteditState"
    ])
    # Replace the stb_textedit type reference with an opaque pointer
    mod_change_class_field_type.apply(dom_root, "ImGuiInputTextState", "Stb", "void*")

    # If the user requested a custom prefix, then rename everything here

    if len(prefix_replacements) > 0:
        mod_rename_prefix.apply(dom_root, prefix_replacements)

    dom_root.validate_hierarchy()

    # Test code
    # dom_root.dump()

    # Cases where the varargs list version of a function does not simply have a V added to the name and needs a
    # custom suffix instead
    custom_varargs_list_suffixes = {'appendf': 'v'}

    # Get just the name portion of the source file, to use as the template name
    src_file_name_only = os.path.splitext(os.path.basename(src_file))[0]

    print("Writing output to " + dest_file_no_ext + "[.h/.cpp/.json]")

    # If our output name ends with _internal, then generate a version of it without that on the assumption that
    # this is probably imgui_internal.h and thus we need to know what imgui.h is (likely) called as well.
    if is_imgui_internal:
        dest_file_name_only_no_internal = dest_file_name_only[:-9]
    else:
        dest_file_name_only_no_internal = dest_file_name_only

    # Expansions to be used when processing templates, to insert variables as required
    expansions = {"%IMGUI_INCLUDE_DIR%": imgui_include_dir,
                  "%BACKEND_INCLUDE_DIR%": backend_include_dir,
                  "%OUTPUT_HEADER_NAME%": dest_file_name_only + ".h",
                  "%OUTPUT_HEADER_NAME_NO_INTERNAL%": dest_file_name_only_no_internal + ".h"}

    with open(dest_file_no_ext + ".h", "w") as file:
        insert_header_templates(file, template_dir, src_file_name_only, ".h", expansions)

        write_context = code_dom.WriteContext()
        write_context.for_c = True
        write_context.for_backend = is_backend
        main_src_root.write_to_c(file, context=write_context)

    # Generate implementations
    with open(dest_file_no_ext + ".cpp", "w") as file:
        insert_header_templates(file, template_dir, src_file_name_only, ".cpp", expansions)

        gen_struct_converters.generate(dom_root, file, indent=0)

        # Extract custom types from everything we parsed,
        # but generate only for the main header
        imgui_custom_types = utils.get_imgui_custom_types(dom_root)
        gen_function_stubs.generate(main_src_root, file, imgui_custom_types,
                                    indent=0,
                                    custom_varargs_list_suffixes=custom_varargs_list_suffixes,
                                    is_backend=is_backend)

    # Generate metadata
    if emit_combined_json_metadata:
        metadata_file_name = dest_file_no_ext + ".json"
        with open(metadata_file_name, "w") as file:
            # We intentionally generate JSON starting from the root here so that we emit metadata from all dependencies
            gen_metadata.generate(dom_root, file)
    else:
        # Emit separate metadata files for each header
        headers = dom_root.list_directly_contained_children_of_type(code_dom.DOMHeaderFile)
        for header in headers:
            if (header == main_src_root):
                metadata_file_name = dest_file_no_ext
            else:
                metadata_file_name = dest_file_no_ext + "_" + str(Path(header.source_filename).with_suffix(""))

            metadata_file_name = metadata_file_name + ".json"
            with open(metadata_file_name, "w") as file:
                gen_metadata.generate(header, file)


if __name__ == '__main__':
    # Parse the C++ header found in src_file, and write a C header to dest_file_no_ext.h, with binding implementation in
    # dest_file_no_ext.cpp. Metadata will be written to dest_file_no_ext.json. implementation_header should point to a
    # file containing the initial header block for the implementation (provided in the templates/ directory).

    print("Dear Bindings: parse Dear ImGui headers, convert to C and output metadata.")

    # Debug code
    #type_comprehender.get_type_description("void (*ImDrawCallback)(const ImDrawList* parent_list, const ImDrawCmd* cmd)").dump(0)

    default_template_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "src", "templates")

    parser = argparse.ArgumentParser(
                        add_help=True,
                        epilog='Result code 0 is returned on success, 1 on conversion failure and 2 on '
                               'parameter errors')
    parser.add_argument('src',
                        help='Path to source header file to process (generally imgui.h)')
    parser.add_argument('-o', '--output',
                        required=True,
                        help='Path to output files (generally dcimgui). This should have no extension, '
                             'as <output>.h, <output>.cpp and <output>.json will be written.')
    parser.add_argument('-t', '--templatedir',
                        default=default_template_dir,
                        help='Path to the implementation template directory (default: ./src/templates)')
    parser.add_argument('--nopassingstructsbyvalue',
                        action='store_true',
                        help='Convert any by-value struct arguments to pointers (for other language bindings)')
    parser.add_argument('--nogeneratedefaultargfunctions',
                        action='store_true',
                        help='Do not generate function variants with implied default values')
    parser.add_argument('--generateunformattedfunctions',
                        action='store_true',
                        help='Generate unformatted variants of format string supporting functions')
    parser.add_argument('--backend',
                        action='store_true',
                        help='Indicates that the header being processed is a backend header (experimental)')
    parser.add_argument('--imgui-include-dir',
                        default='',
                        help="Path to ImGui headers to use in emitted include files. Should include a trailing slash "
                             "(eg \"Imgui/\"). (default: blank)")
    parser.add_argument('--backend-include-dir',
                        default='',
                        help="Path to ImGui backend headers to use in emitted files. Should include a trailing slash "
                             "(eg \"Imgui/Backends/\"). (default: same as --imgui-include-dir)")
    parser.add_argument('--include',
                        help="Path to additional .h files to include (e.g. imgui.h if converting imgui_internal.h, "
                             "and/or the file you set IMGUI_USER_CONFIG to, if any)",
                        default=[],
                        action='append')
    parser.add_argument('--imconfig-path',
                        help="Path to imconfig.h. If not specified, imconfig.h will be assumed to be in the same "
                             "directory as the source file, or the directory immediately above it if --backend "
                             "is specified")
    parser.add_argument('--emit-combined-json-metadata',
                        action='store_true',
                        help="Emit a single combined metadata JSON file instead of emitting "
                             "separate metadata JSON files for each header",
                        default=False)
    parser.add_argument('--custom-namespace-prefix',
                        help="Specify a custom prefix to use on emitted functions/etc in place of the usual "
                             "namespace-derived ImGui_")
    parser.add_argument('--replace-prefix',
                        help="Specify a name prefix and something to replace it with as a pair of arguments of "
                             "the form <old prefix>=<new prefix>. For example, \"--replace-prefix ImFont_=if will\" "
                             "result in ImFont_FindGlyph() becoming ifFontGlyph() (and all other ImFont_ names "
                             "following suit)",
                        default=[],
                        action='append')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)

    args = parser.parse_args()

    include_files = []

    default_imconfig_path = os.path.dirname(os.path.realpath(args.src))

    # If --backend was specified, assume imconfig.h is in the directory above (as that is where it will be in the
    # standard layout
    if args.backend:
        default_imconfig_path = os.path.dirname(default_imconfig_path)

    # Add imconfig.h to the include list to get any #defines set in that
    imconfig_path = args.imconfig_path if args.imconfig_path is not None else (
        os.path.join(default_imconfig_path, "imconfig.h"))

    include_files.append(imconfig_path)

    # Build a map from all the requested prefix replacements
    prefix_replacements = {}
    for replacement_str in args.replace_prefix:
        if '=' not in replacement_str:
            print("--replace-prefix \"" + replacement_str + "\" is not of the form <old prefix>=<new prefix>")
            sys.exit(1)
        index = replacement_str.index('=')
        old_prefix = replacement_str[:index]
        new_prefix = replacement_str[(index+1):]
        prefix_replacements[old_prefix] = new_prefix

    # --custom-namespace-prefix is just handled as a handy short form for --replace-prefix ImGui_=<something>
    if args.custom_namespace_prefix is not None:
        prefix_replacements["ImGui_"] = args.custom_namespace_prefix

    # Add any user-supplied config file as well
    for include in args.include:
        include_files.append(os.path.realpath(include))

    # Perform conversion
    try:
        convert_header(
            os.path.realpath(args.src),
            include_files,
            args.output,
            args.templatedir,
            args.nopassingstructsbyvalue,
            args.nogeneratedefaultargfunctions,
            args.generateunformattedfunctions,
            args.backend,
            args.imgui_include_dir,
            args.backend_include_dir if args.backend_include_dir is not None else args.imgui_include_dir,
            args.emit_combined_json_metadata,
            prefix_replacements
        )
    except:  # noqa - suppress warning about broad exception clause as it's intentionally broad
        print("Exception during conversion:")
        traceback.print_exc()
        sys.exit(1)

    print("Done")
    sys.exit(0)
