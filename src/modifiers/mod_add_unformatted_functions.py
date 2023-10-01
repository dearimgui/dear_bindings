from src import code_dom
from src import utils

def apply(dom_root, functions_to_ignore=[]):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        # Ignore based on exact name match
        if function.name in functions_to_ignore:
            continue

        if function.im_fmtargs is None:
            continue

        has_varargs = False

        for arg in function.arguments:
            if arg.is_varargs:
                has_varargs = True
                break

        if not has_varargs:
            continue  # Nothing to do

        new_function = function.clone()
        new_function.name += "Unformatted"
        new_function.im_fmtargs = None
        new_function.is_unformatted_helper = True

        # Assume the last argument is varargs, check if second-to-last argument is named 'fmt'
        fmt_arg = new_function.arguments[-2]
        if fmt_arg.name != "fmt":
            continue

        fmt_arg.stub_call_value = "\"%s\""
        fmt_arg.is_implicit_default = True

        unformatted_string_arg = code_dom.functionargument.DOMFunctionArgument()
        unformatted_string_arg.name = "text"
        unformatted_string_arg.parent = new_function
        unformatted_string_arg.arg_type = utils.create_type("const char*")
        unformatted_string_arg.arg_type.parent = unformatted_string_arg

        new_function.arguments.pop() # remove varargs
        new_function.arguments = new_function.arguments + [unformatted_string_arg]

        # Insert new function
        function.parent.insert_after_child(function, [new_function])
