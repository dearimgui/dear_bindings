from src import code_dom
from src import utils


# This modifier adds a marker to structs that should be treated as having a placement new style constructor, 
# which subsequent modifiers (and the code generator) can use
def apply(dom_root, has_placement_constructor_structs):
    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if struct.name in has_placement_constructor_structs:
            struct.has_placement_constructor = True
