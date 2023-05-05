from src import code_dom
from src import utils


# This modifier removes functions with the (fully-qualified) names specified
# Optionally removal can be limited to only functions within a specified preprocessor conditional expression
def apply(dom_root, function_names, preprocessor_conditional_expression=None):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.get_fully_qualified_name(return_fqn_even_for_member_functions=True) in function_names:
            if preprocessor_conditional_expression is not None:
                do_not_remove = True
                for conditional in utils.get_preprocessor_conditionals(function):
                    in_else = utils.is_in_else_clause(function, conditional)
                    if (conditional.get_expression() == preprocessor_conditional_expression) and \
                            not (conditional.is_negated ^ in_else):
                        do_not_remove = False
                        break
                if do_not_remove:
                    continue

            if isinstance(function.parent, code_dom.DOMTemplate):
                # If the function is templated, remove the template too
                template = function.parent
                template.parent.remove_child(template)
            else:
                function.parent.remove_child(function)
