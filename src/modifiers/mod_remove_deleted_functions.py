from src import code_dom
from src import utils


# This modifier removes functions that have been explicited deleted in C++ (with "= delete")
def apply(dom_root):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.is_deleted:
            if isinstance(function.parent, code_dom.DOMTemplate):
                # If the function is templated, remove the template too
                template = function.parent
                template.parent.remove_child(template)
            else:
                function.parent.remove_child(function)
