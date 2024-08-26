from src import code_dom
from src import utils


# This modifier looks for a function with a specific name, and then rewrites the containing preprocessor conditional
# with a specific pattern
def apply(dom_root, function_name, old_condition, new_condition, force_to_ifdef):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.name == function_name:
            for conditional in utils.get_preprocessor_conditionals(function):
                if conditional.get_expression() == old_condition:
                    conditional.expression_tokens = [ utils.create_token(new_condition) ]
                    if force_to_ifdef:
                        conditional.is_ifdef = True
                        conditional.is_negated = False
                        conditional.is_elif = False
