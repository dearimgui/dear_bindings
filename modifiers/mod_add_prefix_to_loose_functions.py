import code_dom
import utils


# This modifier adds a name prefix to any "loose" functions (i.e. not a member of a class/struct/etc)
def apply(dom_root, prefix):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.get_parent_class() is None:
            function.name = prefix + function.name
