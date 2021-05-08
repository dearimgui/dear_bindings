# Dear Bindings Version 0.02
# Generates C-language headers for Dear ImGui
# Developed by Ben Carter (ben@shironekolabs.com)

import os
import code_dom
import c_lexer
import modifiers.mod_remove_pragma_once
import modifiers.mod_flatten_namespaces
import modifiers.mod_attach_preceding_comments
import modifiers.mod_remove_function_bodies
import modifiers.mod_remove_operators
import modifiers.mod_remove_structs
import modifiers.mod_remove_functions
import modifiers.mod_add_prefix_to_loose_functions
import modifiers.mod_flatten_class_functions
import modifiers.mod_flatten_nested_classes
import modifiers.mod_flatten_templates
import modifiers.mod_disambiguate_functions
import modifiers.mod_convert_references_to_pointers
import modifiers.mod_remove_static_fields
import modifiers.mod_remove_nested_typedefs
import modifiers.mod_remove_all_functions_from_classes
import modifiers.mod_merge_blank_lines
import modifiers.mod_remove_blank_lines
import modifiers.mod_remove_empty_conditionals
import modifiers.mod_make_all_functions_use_imgui_api
import modifiers.mod_rename_defines
import modifiers.mod_forward_declare_structs
import modifiers.mod_mark_by_value_structs
import modifiers.mod_add_includes
import modifiers.mod_remove_includes
import generators.gen_struct_converters
import generators.gen_function_stubs


# Parse the C++ header found in src_file, and write a C header to dest_file_no_ext.h, with binding implementation in
# dest_file_no_ext.cpp. implementation_header should point to a file containing the header block for the implementation.
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
    else:
        context = code_dom.ParseContext()
        dom_root = code_dom.DOMHeaderFileSet()
        dom_root.add_child(code_dom.DOMHeaderFile.parse(context, stream))
        _, dom_root.filename = os.path.split(src_file)
        dom_root.validate_hierarchy()
        #  dom_root.dump()

        print("Storing unmodified DOM")

        dom_root.save_unmodified_clones()

        print("Applying modifiers")

        # Apply modifiers

        # Add headers we need and remove those we don't
        modifiers.mod_add_includes.apply(dom_root, ["<stdbool.h>"])  # We need stdbool.h to get bool defined
        modifiers.mod_remove_includes.apply(dom_root, ["<float.h>",
                                                       "<stdarg.h>",
                                                       "<stddef.h>",
                                                       "<string.h>"])

        modifiers.mod_attach_preceding_comments.apply(dom_root)
        modifiers.mod_remove_function_bodies.apply(dom_root)
        # Remove ImGuiOnceUponAFrame for now as it needs custom fiddling to make it usable from C
        # Remove ImNewDummy/ImNewWrapper as it's a helper for C++ new (and C dislikes empty structs)
        modifiers.mod_remove_structs.apply(dom_root, ["ImGuiOnceUponAFrame",
                                                      "ImNewDummy",  # ImGui <1.82
                                                      "ImNewWrapper"  # ImGui >=1.82
                                                      ])
        # Remove all functions from ImVector, as they're not really useful
        modifiers.mod_remove_all_functions_from_classes.apply(dom_root, ["ImVector"])
        modifiers.mod_add_prefix_to_loose_functions.apply(dom_root, "c")
        modifiers.mod_remove_operators.apply(dom_root)
        modifiers.mod_convert_references_to_pointers.apply(dom_root)
        # We remap the ImGui:: namespace to use ig as a prefix for brevity
        modifiers.mod_flatten_namespaces.apply(dom_root, {'ImGui': 'ImGui_'})
        modifiers.mod_flatten_nested_classes.apply(dom_root)
        # The custom type fudge here is a workaround for how template parameters are expanded
        modifiers.mod_flatten_templates.apply(dom_root, custom_type_fudges={'const ImFont**': 'ImFont* const*'})
        # We treat ImVec2 and ImVec4 as by-value types
        modifiers.mod_mark_by_value_structs.apply(dom_root, by_value_structs=['ImVec2', 'ImVec4', 'ImColor'])
        modifiers.mod_flatten_class_functions.apply(dom_root)
        modifiers.mod_remove_nested_typedefs.apply(dom_root)
        modifiers.mod_remove_static_fields.apply(dom_root)
        modifiers.mod_disambiguate_functions.apply(dom_root, name_suffix_remaps={
            # Some more user-friendly suffixes for certain types
            'const char*': 'Str',
            'char*': 'Str',
            'unsigned int': 'Uint'},
            # Functions that look like they have name clashes but actually don't
            # thanks to preprocessor conditionals
            functions_to_ignore=[
                "cImFileOpen",
                "cImFileClose",
                "cImFileGetSize",
                "cImFileRead",
                "cImFileWrite"])

        # Make all functions use CIMGUI_API
        modifiers.mod_make_all_functions_use_imgui_api.apply(dom_root)
        modifiers.mod_rename_defines.apply(dom_root, {'IMGUI_API': 'CIMGUI_API'})

        modifiers.mod_forward_declare_structs.apply(dom_root)
        modifiers.mod_remove_pragma_once.apply(dom_root)
        modifiers.mod_remove_empty_conditionals.apply(dom_root)
        modifiers.mod_merge_blank_lines.apply(dom_root)
        modifiers.mod_remove_blank_lines.apply(dom_root)

        dom_root.validate_hierarchy()

        # dom_root.dump()

        # Cases where the varargs list version of a function does not simply have a V added to the name and needs a
        # custom suffix instead
        custom_varargs_list_suffixes = {'appendf': 'v'}

        print("Writing output")

        with open(dest_file_no_ext + ".h", "w") as file:
            write_context = code_dom.WriteContext()
            write_context.for_c = True
            dom_root.write_to_c(file, context=write_context)

        # Generate implementations
        with open(dest_file_no_ext + ".cpp", "w") as file:
            with open(implementation_header, "r") as src_file:
                file.writelines(src_file.readlines())

            generators.gen_struct_converters.generate(dom_root, file, indent=0)

            generators.gen_function_stubs.generate(dom_root, file, indent=0,
                                                   custom_varargs_list_suffixes=custom_varargs_list_suffixes)


if __name__ == '__main__':
    # convert_header(r"TestCode\sdl2-cimgui-demo\externals\cimgui\imgui\imgui.h",
    #               r"TestCode\sdl2-cimgui-demo\generated\cimgui",
    #               r"templates/cimgui-header.cpp")

    convert_header(r"TestCode\sdl2-cimgui-demo\externals\cimgui\imgui\imgui_internal.h",
                   r"TestCode\sdl2-cimgui-demo\generated\cimgui_internal",
                   r"templates/cimgui_internal-header.cpp")
