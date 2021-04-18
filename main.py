# Dear Bindings Version 0.02
# Generates C-language headers for Dear ImGui
# Developed by Ben Carter (ben@shironekolabs.com)

import code_dom
import c_lexer
import modifiers.mod_remove_pragma_once
import modifiers.mod_add_header
import modifiers.mod_flatten_namespaces
import modifiers.mod_attach_preceding_comments
import modifiers.mod_save_original_names
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
import modifiers.mod_merge_blank_lines
import modifiers.mod_remove_blank_lines
import modifiers.mod_remove_empty_conditionals
import generators.gen_function_stubs


def parse_header():

    print("Parsing")

    #with open(r"Test.h", "r") as f:
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

        print("Applying modifiers")

        # Apply modifiers

        modifiers.mod_save_original_names.apply(dom_root)
        modifiers.mod_add_header.apply(dom_root)
        modifiers.mod_attach_preceding_comments.apply(dom_root)
        modifiers.mod_remove_function_bodies.apply(dom_root)
        # Remove ImGuiOnceUponAFrame for now as it needs custom fiddling to make it usable from C
        # Remove ImNewDummy/ImNewWrapper as it's a helper for C++ new (and C dislikes empty structs)
        modifiers.mod_remove_structs.apply(dom_root, ["ImGuiOnceUponAFrame",
                                                      "ImNewDummy",  # ImGui <1.82
                                                      "ImNewWrapper"  # ImGui >=1.82
                                                      ])
        # Remove ImVector::contains()/etc because most of the things ImVector gets used with have no equality operator,
        # and thus they cannot compile correctly (on the C++ side)
        modifiers.mod_remove_functions.apply(dom_root, ["ImVector::contains",
                                                        "ImVector::find",
                                                        "ImVector::find_erase",
                                                        "ImVector::find_erase_unsorted"])
        modifiers.mod_remove_operators.apply(dom_root)
        modifiers.mod_convert_references_to_pointers.apply(dom_root)
        # We remap the ImGui:: namespace to use ig as a prefix for brevity
        modifiers.mod_flatten_namespaces.apply(dom_root, {'ImGui': 'ig'})
        modifiers.mod_flatten_nested_classes.apply(dom_root)
        # The custom type fudge here is a workaround for how template parameters are expanded
        modifiers.mod_flatten_templates.apply(dom_root, custom_type_fudges={'const ImFont**': 'ImFont* const*'})
        modifiers.mod_flatten_class_functions.apply(dom_root)
        modifiers.mod_remove_nested_typedefs.apply(dom_root)
        modifiers.mod_remove_static_fields.apply(dom_root)
        modifiers.mod_disambiguate_functions.apply(dom_root, {
            # Some more user-friendly suffixes for certain types
            'const char*': 'Str',
            'char*': 'Str',
            'unsigned int': 'Uint'})
        modifiers.mod_remove_pragma_once.apply(dom_root)
        modifiers.mod_remove_empty_conditionals.apply(dom_root)
        modifiers.mod_merge_blank_lines.apply(dom_root)
        modifiers.mod_remove_blank_lines.apply(dom_root)

        dom_root.validate_hierarchy()

        #dom_root.dump()

        # Cases where the varargs list version of a function does not simply have a V added to the name and needs a
        # custom suffix instead
        custom_varargs_list_suffixes = {'appendf': 'v'}

        # Make a list of known struct names, so that we know which things need struct prefixes when referenced
        known_structs = {}
        for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
            if struct.structure_type == 'STRUCT':
                known_structs[struct.name] = struct

        print("Writing output")

        with open(r"TestCode\sdl2-cimgui-demo\generated\cimgui.h", "w") as file:
            write_context = code_dom.WriteContext()
            write_context.for_c = True
            write_context.known_structs = known_structs.keys()
            dom_root.write_to_c(file, context=write_context)

        # Generate implementations
        with open(r"TestCode\sdl2-cimgui-demo\generated\cimgui.cpp", "w") as file:
            with open(r"templates/cimgui-header.cpp", "r") as src_file:
                file.writelines(src_file.readlines())
            generators.gen_function_stubs.generate(dom_root, file, indent=0,
                                                   custom_varargs_list_suffixes=custom_varargs_list_suffixes)


if __name__ == '__main__':
    parse_header()
