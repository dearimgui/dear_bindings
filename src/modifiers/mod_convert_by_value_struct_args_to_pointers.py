from src import code_dom
from src import utils


# This modifier turns all instances of passing a struct by value as a function parameter into a pass-by-pointer instead
# (for the benefit of langauge bindings that don't want to deal with the complexities of C's struct-as-value rules)
def apply(dom_root):
    for type_element in dom_root.list_all_children_of_type(code_dom.DOMType):

        # Make a list of all structs we know about

        all_structs = {}

        for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
            all_structs[struct.name] = struct

        # Look for struct arguments

        is_argument = isinstance(type_element.parent, code_dom.DOMFunctionArgument)

        if is_argument and (not type_element.parent.is_array):
            if len(type_element.tokens) == 1:
                if type_element.tokens[0].value in all_structs:
                    # This is a struct argument, so insert a pointer token
                    pointer_token = utils.create_token('*')
                    pointer_token.type = 'ASTERISK'
                    pointer_token.nullable = False  # Because it started as a value type, it can't be null
                    type_element.tokens = [type_element.tokens[0], pointer_token]
