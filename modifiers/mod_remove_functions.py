import code_dom


# This modifier removes functions with the (fully-qualified) names specified
def apply(dom_root, function_names):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.get_fully_qualified_name(return_fqn_even_for_member_functions=True) in function_names:
            function.parent.remove_child(function)
