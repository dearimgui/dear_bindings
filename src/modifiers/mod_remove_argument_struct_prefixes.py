from src import code_dom


# This modifier removes any instances of struct type prefixes (i.e. "struct" and "class") in all function arguments
def apply(dom_root):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        for arg in function.arguments:
            if (arg.arg_type is not None) and isinstance(arg.arg_type, code_dom.DOMType):
                if arg.arg_type.has_structure_type_prefix():
                    arg.arg_type.remove_structure_type_prefix()
                    # print(f"Removed from {function.get_fully_qualified_name(return_fqn_even_for_member_functions=True)} arg {arg.name}")
