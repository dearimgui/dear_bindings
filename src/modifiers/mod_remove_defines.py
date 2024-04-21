from src import code_dom
from src import utils


# This modifier removes the listed #defines
# define_names should be a list of define names
def apply(dom_root, define_names):
    for define in dom_root.list_all_children_of_type(code_dom.DOMDefine):
        if define.name in define_names:
            define.parent.remove_child(define)
