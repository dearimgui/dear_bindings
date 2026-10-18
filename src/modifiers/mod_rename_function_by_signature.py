from src import code_dom


# This modifier renames a function that has an argument with a specific name
# If only_if_multiple is set, then the rule is only applied if there are multiple instances of functions that
# match the conditions given (and in that case it is applied only to the first instance found)
# This is something of a last-ditch mechanism to resolve name clashes
def apply(dom_root, old_name, argument_name, new_name, only_if_multiple = False):
    if only_if_multiple:
        match_count = 0
        for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
            if function.name == old_name:
                for arg in function.arguments:
                    if arg.name == argument_name:
                        match_count += 1
                        break
        if match_count < 2:
            return  # Only apply if there are multiple matching functions

    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.name == old_name:
            for arg in function.arguments:
                if arg.name == argument_name:
                    function.name = new_name
                    return  # Stop processing once we've found one instance
