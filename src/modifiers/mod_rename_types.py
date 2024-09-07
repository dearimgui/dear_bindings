from src import code_dom
from src import utils


# This modifier renames types
# Takes a map mapping old names to new names
def apply(dom_root, name_map):
    for dom_type in dom_root.list_all_children_of_type(code_dom.DOMType):
        type_name = dom_type.get_fully_qualified_name()
        if type_name in name_map:
            dom_type.tokens = [utils.create_token(name_map[type_name])]
