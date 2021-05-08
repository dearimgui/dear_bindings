# Dear Bindings Version 0.02
# Generates C-language headers for Dear ImGui
# Developed by Ben Carter (ben@shironekolabs.com)

import code_dom
import c_lexer
import modifiers.mod_remove_pragma_once
import modifiers.mod_flatten_namespaces
import modifiers.mod_attach_preceding_comments
import modifiers.mod_remove_function_bodies
import modifiers.mod_remove_operators
import modifiers.mod_remove_structs
import modifiers.mod_remove_functions
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


def parse_header():
    print("Parsing")

    # with open(r"Test.h", "r") as f:
    #    file_content = f.read()
    with open(r"TestCode\sdl2-cimgui-demo\externals\cimgui\imgui\imgui.h", "r") as f:
        file_content = f.read()

    # Tokenize file and then convert into a DOM

    stream = c_lexer.tokenize(file_content)

    if False:  # Debug dump tokens
        while True:
            tok = lexer.token()
            if not tok:
                break  # No more input
            print(tok)
    else:
        context = code_dom.ParseContext()
        dom_root = code_dom.DOMHeaderFile.parse(context, stream)
        dom_root.filename = "imgui.h"
        dom_root.validate_hierarchy()

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
        modifiers.mod_remove_operators.apply(dom_root)
        modifiers.mod_convert_references_to_pointers.apply(dom_root)
        # We remap the ImGui:: namespace to use ig as a prefix for brevity
        modifiers.mod_flatten_namespaces.apply(dom_root, {'ImGui': 'ig'})
        modifiers.mod_flatten_nested_classes.apply(dom_root)
        # The custom type fudge here is a workaround for how template parameters are expanded
        modifiers.mod_flatten_templates.apply(dom_root, custom_type_fudges={'const ImFont**': 'ImFont* const*'})
        # We treat ImVec2 and ImVec4 as by-value types
        modifiers.mod_mark_by_value_structs.apply(dom_root, by_value_structs=['ImVec2', 'ImVec4', 'ImColor'])
        modifiers.mod_flatten_class_functions.apply(dom_root)
        modifiers.mod_remove_nested_typedefs.apply(dom_root)
        modifiers.mod_remove_static_fields.apply(dom_root)
        modifiers.mod_disambiguate_functions.apply(dom_root, {
            # Some more user-friendly suffixes for certain types
            'const char*': 'Str',
            'char*': 'Str',
            'unsigned int': 'Uint'})

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

        with open(r"TestCode\sdl2-cimgui-demo\generated\cimgui.h", "w") as file:
            write_context = code_dom.WriteContext()
            write_context.for_c = True
            dom_root.write_to_c(file, context=write_context)

        # Generate implementations
        with open(r"TestCode\sdl2-cimgui-demo\generated\cimgui.cpp", "w") as file:
            with open(r"templates/cimgui-header.cpp", "r") as src_file:
                file.writelines(src_file.readlines())

            generators.gen_struct_converters.generate(dom_root, file, indent=0)

            generators.gen_function_stubs.generate(dom_root, file, indent=0,
                                                   custom_varargs_list_suffixes=custom_varargs_list_suffixes)


if __name__ == '__main__':
    parse_header()
