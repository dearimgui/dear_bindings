import code_dom


# This modifier generates variants of any function which has default arguments that takes only the required ones
# (for ease of programming, since C doesn't support default arguments)
def apply(dom_root):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        num_args = len(function.arguments)
        num_args_with_defaults = 0

        for arg in function.arguments:
            if arg.default_value_tokens is not None:
                num_args_with_defaults += 1

        if (num_args == 0) or (num_args_with_defaults == 0):
            continue  # Nothing useful to do

        # Clone the function and set the defaulted arguments

        new_function = function.clone()

        function.name += "Ex"  # Alter the name of the non-defaulted function

        for i in range(num_args - num_args_with_defaults, num_args):
            new_function.arguments[i].is_implicit_default = True
        new_function.is_default_argument_helper = True

        # Generate a comment noting the defaulted arguments

        comment_text = "// Implied "

        first = True
        for i in range(num_args - num_args_with_defaults, num_args):
            if not first:
                comment_text += ", "
            arg = function.arguments[i]
            if arg.name:
                comment_text += arg.name + " = "
            comment_text += code_dom.collapse_tokens_to_string(arg.default_value_tokens)
            first = False

        # Attach that comment and remove any others

        new_function.pre_comments = []

        comment = code_dom.DOMComment.from_string(comment_text)
        comment.is_attached_comment = True
        comment.parent = new_function

        new_function.attached_comment = comment

        # Insert new function

        function.parent.insert_after_child(function, [new_function])
