from src import code_dom
from src import utils

def apply(dom_root, varargs_count_limit):
    any_modifications_applied = False
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        has_varargs = False

        for arg in function.arguments:
            if arg.is_varargs:
                has_varargs = True
                break

        if not has_varargs:
            continue  # Nothing to do

        any_modifications_applied = True;
        for vararg_arg_count in reversed(range(1, varargs_count_limit + 1)):
            new_function = function.clone()

            new_function.name += "VA_" + str(vararg_arg_count)
            new_function.exploded_varargs_count = vararg_arg_count

            # varargs are always the last argument, we replace them by N explicit arguments
            new_function.arguments.pop()
            new_function.im_fmtargs = None

            for vararg_index in range (1, vararg_arg_count + 1):
                varargs_arg = code_dom.functionargument.DOMFunctionArgument()
                varargs_arg.name = "arg" + str(vararg_index)
                varargs_arg.parent = new_function
                varargs_arg.arg_type = utils.create_type("ImGuiPrintableVarArg")
                varargs_arg.arg_type.parent = varargs_arg

                new_function.arguments = new_function.arguments + [varargs_arg]

            # Insert new function

            function.parent.insert_after_child(function, [new_function])
    
    if any_modifications_applied:
        vararg_wrapper_type_insert_point = dom_root.children[0]  # Default to adding at the top of the file if we can't find anywhere else

        # Look for the right section to add these to - if we can, we want to put them in the same place as other custom types
        for comment in dom_root.list_all_children_of_type(code_dom.DOMComment):
            if "[SECTION] Forward declarations" in comment.comment_text:
                vararg_wrapper_type_insert_point = comment
                # No early-out here because we actually want the /last/ instance of this comment

        vararg_wrapper_type = utils.create_classstructunion("""
                                                            union ImGuiPrintableVarArg
                                                            {
                                                                int32_t val_int32;
                                                                int64_t val_int64;
                                                                float val_float;
                                                                double val_double;
                                                                void* val_ptr;
                                                            };
                                                            """)
    
        vararg_wrapper_type.attached_comment = code_dom.comment.DOMComment()
        vararg_wrapper_type.attached_comment.comment_text = "// Wrapper for printable arguments passed to format string supporting functions with explicit arguments"
        vararg_wrapper_type.attached_comment.is_attached_comment = True
        vararg_wrapper_type.attached_comment.parent = vararg_wrapper_type

        vararg_wrapper_type_insert_point.parent.insert_before_child(
            vararg_wrapper_type_insert_point,
            [
                vararg_wrapper_type, 
                code_dom.blanklines.DOMBlankLines(2)
            ]
        )