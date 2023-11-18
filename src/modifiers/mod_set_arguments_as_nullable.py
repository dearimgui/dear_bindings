from src import code_dom
from src import utils


# This modifier sets the nullable flag on pointers in arguments with a given name
def apply(dom_root, argument_names, nullable):
    for arg in dom_root.list_all_children_of_type(code_dom.DOMFunctionArgument):
        if arg.name in argument_names:
            for tok in arg.arg_type.tokens:
                if tok.type == 'ASTERISK':
                    tok.nullable = nullable
