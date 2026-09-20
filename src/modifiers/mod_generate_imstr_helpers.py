from src import code_dom
from src import utils


# This modifier generates variants of any function that takes ImStr which instead takes a regular char* argument
# In some cases variants already exist in the header, so we use functions_to_ignore to skip those
def apply(dom_root, functions_to_ignore):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.name in functions_to_ignore:
            continue

        num_args = len(function.arguments)
        has_imstr_args = False

        for arg in function.arguments:
            if (not arg.is_varargs) and (arg.arg_type.to_c_string() == 'ImStrv'):
                has_imstr_args = True
                break

        if not has_imstr_args:
            continue  # Nothing to do

        # Clone the function and convert the arguments to const char*

        new_function = function.clone()

        function.name += "ImStrv"  # Alter the name of the original function
        function.has_imstr_helper = True  # ...and note that we generated a helper for it

        for i in range(0, num_args):
            if new_function.arguments[i].is_varargs:
                continue
            if new_function.arguments[i].arg_type.to_c_string() == 'ImStrv':
                new_function.arguments[i].arg_type.tokens = utils.create_tokens_for_type('const char*')
        new_function.is_imstr_helper = True
        new_function.pre_comments = []

        # Insert new function

        function.parent.insert_after_child(function, [new_function])
