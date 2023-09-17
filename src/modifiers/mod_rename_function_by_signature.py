from src import code_dom


# This modifier renames a function that has an argument with a specific name
# This is something of a last-ditch mechanism to resolve name clashes
def apply(dom_root, old_name, argument_name, new_name):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.name == old_name:
            for arg in function.arguments:
                if arg.name == argument_name:
                    function.name = new_name
