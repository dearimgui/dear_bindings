# Dear Bindings Version 0.04 WIP
# Generates C-language headers for Dear ImGui
# Developed by Ben Carter (ben@shironekolabs.com)

import os
from src import code_dom
from src import c_lexer
import argparse
import sys
import traceback
from src.modifiers import *
from src.generators import *

# Parse the C++ header found in src_file, and write a C header to dest_file_no_ext.h, with binding implementation in
# dest_file_no_ext.cpp. Metadata will be written to dest_file_no_ext.json. implementation_header should point to a file
# containing the initial header block for the implementation (provided in the templates/ directory).
def convert_header(src_file, dest_file_no_ext, implementation_header):
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

    context = code_dom.ParseContext()
    dom_root = code_dom.DOMHeaderFileSet()
    dom_root.add_child(code_dom.DOMHeaderFile.parse(context, stream))

    # Assign a filename based on the output file
    _, dom_root.filename = os.path.split(dest_file_no_ext)
    dom_root.filename += ".h"  # Presume the primary output file is the .h

    dom_root.validate_hierarchy()
    #  dom_root.dump()

    print("Storing unmodified DOM")

    dom_root.save_unmodified_clones()

    print("Applying modifiers")

    # Apply modifiers

    # Add headers we need and remove those we don't
    mod_add_includes.apply(dom_root, ["<stdbool.h>"])  # We need stdbool.h to get bool defined
    mod_remove_includes.apply(dom_root, ["<float.h>",
                                         "<stdarg.h>",
                                         "<stddef.h>",
                                         "<string.h>"])

    mod_attach_preceding_comments.apply(dom_root)
    mod_remove_function_bodies.apply(dom_root)
    # Remove ImGuiOnceUponAFrame for now as it needs custom fiddling to make it usable from C
    # Remove ImNewDummy/ImNewWrapper as it's a helper for C++ new (and C dislikes empty structs)
    mod_remove_structs.apply(dom_root, ["ImGuiOnceUponAFrame",
                                        "ImNewDummy",  # ImGui <1.82
                                        "ImNewWrapper",  # ImGui >=1.82
                                        # Templated stuff in imgui_internal.h
                                        "ImBitArray",
                                        "ImBitVector",
                                        "ImSpan",
                                        "ImSpanAllocator",
                                        "ImPool",
                                        "ImChunkStream"])
    # Remove all functions from ImVector, as they're not really useful
    mod_remove_all_functions_from_classes.apply(dom_root, ["ImVector"])
    # Remove Value() functions which are dumb helpers over Text(), would need custom names otherwise
    mod_remove_functions.apply(dom_root, ["ImGui::Value"])
    # Remove some templated functions from imgui_internal.h that we don't want and cause trouble
    mod_remove_functions.apply(dom_root, ["ImGui::ScaleRatioFromValueT",
                                          "ImGui::ScaleValueFromRatioT",
                                          "ImGui::DragBehaviorT",
                                          "ImGui::SliderBehaviorT",
                                          "ImGui::RoundScalarWithFormatT",
                                          "ImGui::CheckboxFlagsT"])
    mod_add_prefix_to_loose_functions.apply(dom_root, "c")

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

    mod_remove_operators.apply(dom_root)
    mod_remove_heap_constructors_and_destructors.apply(dom_root)
    mod_convert_references_to_pointers.apply(dom_root)
    # Assume IM_VEC2_CLASS_EXTRA and IM_VEC4_CLASS_EXTRA are never defined as they are likely to just cause problems
    # if anyone tries to use it
    mod_flatten_conditionals.apply(dom_root, "IM_VEC2_CLASS_EXTRA", False)
    mod_flatten_conditionals.apply(dom_root, "IM_VEC4_CLASS_EXTRA", False)
    mod_flatten_namespaces.apply(dom_root, {'ImGui': 'ImGui_'})
    mod_flatten_nested_classes.apply(dom_root)
    # The custom type fudge here is a workaround for how template parameters are expanded
    mod_flatten_templates.apply(dom_root, custom_type_fudges={'const ImFont**': 'ImFont* const*'})
    # We treat ImVec2, ImVec4 and ImColor as by-value types
    mod_mark_by_value_structs.apply(dom_root, by_value_structs=['ImVec2', 'ImVec4', 'ImColor', 'ImStr'])
    mod_mark_internal_members.apply(dom_root)
    mod_flatten_class_functions.apply(dom_root)
    mod_remove_nested_typedefs.apply(dom_root)
    mod_remove_static_fields.apply(dom_root)
    mod_remove_constexpr.apply(dom_root)
    mod_generate_imstr_helpers.apply(dom_root)
    mod_disambiguate_functions.apply(dom_root,
                                     name_suffix_remaps={
                                         # Some more user-friendly suffixes for certain types
                                         'const char*': 'Str',
                                         'char*': 'Str',
                                         'unsigned int': 'Uint',
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
                                         "cImFileWrite"])
    mod_generate_default_argument_functions.apply(dom_root,
                                                  # We ignore functions that don't get called often because in those
                                                  # cases the default helper doesn't add much value but does clutter
                                                  # up the header file
                                                  functions_to_ignore=[
                                                      'ImGui_LoadIniSettingsFromDisk',
                                                      'ImGui_LoadIniSettingsFromMemory',
                                                      'ImGui_SaveIniSettingsToMemory',
                                                      'ImGui_SaveIniSettingsToMemory',
                                                      'ImGui_SetAllocatorFunctions',
                                                      'ImGui_CreateContext',
                                                      'ImGui_DestroyContext',
                                                      'ImGui_ShowDemoWindow',
                                                      'ImGui_ShowMetricsWindow',
                                                      'ImGui_ShowDebugLogWindow',
                                                      'ImGui_ShowStackToolWindow',
                                                      'ImGui_ShowAboutWindow',
                                                      'ImGui_ShowStyleEditor',
                                                      'ImGui_StyleColorsDark',
                                                      'ImGui_StyleColorsLight',
                                                      'ImGui_StyleColorsClassic',
                                                      'ImGui_Begin',
                                                      'ImGui_BeginChild',
                                                      'ImGui_BeginChildID',
                                                      'ImGui_SetNextWindowSizeConstraints',
                                                      'ImGui_SetScrollHereX',
                                                      'ImGui_SetScrollHereY',
                                                      'ImGui_SetScrollFromPosX',
                                                      'ImGui_SetScrollFromPosY',
                                                      'ImGui_PushTextWrapPos',
                                                      'ImGui_ProgressBar',
                                                      'ImGui_ColorPicker4',
                                                      'ImGui_TreePushPtr', # Ensure why core lib has this default to NULL?
                                                      'ImGui_BeginListBox',
                                                      'ImGui_ListBox',
                                                      'ImGui_MenuItemBoolPtr',
                                                      'ImGui_OpenPopupOnItemClick',
                                                      'ImGui_TableGetColumnName',
                                                      'ImGui_TableGetColumnFlags',
                                                      'ImGui_TableSetBgColor',
                                                      'ImGui_GetColumnWidth',
                                                      'ImGui_GetColumnOffset',
                                                      'ImGui_BeginTabItem',
                                                      'ImGui_LogToTTY',
                                                      'ImGui_LogToFile',
                                                      'ImGui_LogToClipboard',
                                                      'ImGui_BeginDisabled',
                                                      'ImGui_IsMousePosValid',
                                                      'ImGui_IsMouseDragging',
                                                      'ImGui_GetMouseDragDelta',
                                                      'ImGui_CaptureKeyboardFromApp',
                                                      'ImGui_CaptureMouseFromApp',
                                                      # Other types
                                                      'ImGuiIO_SetKeyEventNativeDataEx',
                                                      'ImGuiTextFilter_Draw',
                                                      'ImGuiTextFilter_PassFilter',
                                                      'ImGuiTextBuffer_append',
                                                      'ImGuiInputTextCallbackData_InsertChars',
                                                      'ImColor_SetHSV',
                                                      'ImColor_HSV',
                                                      'ImGuiListClipper_Begin',
                                                      # ImDrawList: all 'int num_segments = 0' made explicit
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
                                                  ])

    # Make all functions use CIMGUI_API
    mod_make_all_functions_use_imgui_api.apply(dom_root)
    mod_rename_defines.apply(dom_root, {'IMGUI_API': 'CIMGUI_API'})

    mod_forward_declare_structs.apply(dom_root)
    mod_wrap_with_extern_c.apply(dom_root)
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
        "IMGUI_IMPL_API",
        "IM_COL32_WHITE",
        "IM_COL32_BLACK",
        "IM_COL32_BLACK_TRANS",
        "ImDrawCallback_ResetRenderState",
    ])

    dom_root.validate_hierarchy()

    # dom_root.dump()

    # Cases where the varargs list version of a function does not simply have a V added to the name and needs a
    # custom suffix instead
    custom_varargs_list_suffixes = {'appendf': 'v'}

    print("Writing output to " + dest_file_no_ext + "[.h/.cpp/.json]")

    with open(dest_file_no_ext + ".h", "w") as file:
        write_context = code_dom.WriteContext()
        write_context.for_c = True
        dom_root.write_to_c(file, context=write_context)

    # Generate implementations
    with open(dest_file_no_ext + ".cpp", "w") as file:
        with open(implementation_header, "r") as src_file:
            file.writelines(src_file.readlines())

        gen_struct_converters.generate(dom_root, file, indent=0)

        gen_function_stubs.generate(dom_root, file, indent=0,
                                    custom_varargs_list_suffixes=custom_varargs_list_suffixes)

    # Generate metadata
    with open(dest_file_no_ext + ".json", "w") as file:
        gen_metadata.generate(dom_root, file)


if __name__ == '__main__':
    # Parse the C++ header found in src_file, and write a C header to dest_file_no_ext.h, with binding implementation in
    # dest_file_no_ext.cpp. Metadata will be written to dest_file_no_ext.json. implementation_header should point to a
    # file containing the initial header block for the implementation (provided in the templates/ directory).

    parser = argparse.ArgumentParser(description='Parse Dear ImGui headers, convert to C and output metadata',
                                     epilog='Result code 0 is returned on success, 1 on conversion failure and 2 on '
                                            'parameter errors')
    parser.add_argument('src',
                        help='Path to source header file to process (generally imgui.h)')
    parser.add_argument('--output', '-o',
                        required=True,
                        help='Path to output file(s). This should have no extension, as <output>.h, <output>.cpp and '
                             '<output>.json will be written.')
    parser.add_argument('--templatedir', '-t',
                        default="./src/templates",
                        help='Path to the implementation template directory (default: ./src/templates)')

    args = parser.parse_args()

    # Generate expected header template name from the source filename
    # Note that "header" in the name here means "file header" not "C header file", slightly confusingly
    template = os.path.join(args.templatedir, os.path.splitext(os.path.basename(args.src))[0] + "-header-template.cpp")

    if not os.path.isfile(template):
        print("Implementation template file " + template + " could not be found (note that template file names are "
                                                           "expected to match source file names, so if you have "
                                                           "renamed imgui.h you will need to rename the template as "
                                                           "well)")
        sys.exit(2)

    # Perform conversion
    try:
        convert_header(args.src, args.output, template)
    except:  # noqa - suppress warning about broad exception clause as it's intentionally broad
        print("Exception during conversion:")
        traceback.print_exc()
        sys.exit(1)

    print("Done")
    sys.exit(0)
