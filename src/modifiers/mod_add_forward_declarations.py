from src import code_dom
from src import utils


# This modifier adds additional forward declarations to the file
# declarations should be a set of C-style class/struct/union declaration statements
def apply(src_root, declarations):

    elements_to_append = []

    for declaration in declarations:
        type_element = utils.create_classstructunion(declaration)
        elements_to_append.append(type_element)

    if len(elements_to_append) == 0:
        return

    # We try and insert these before the first function

    insert_point = src_root.children[0]  # Default to adding at the top of the file if we can't find anywhere else

    for function in src_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.parent.get_prev_child(function) is not None:
            insert_point = function.parent.get_prev_child(function)
        break

    insert_point.parent.insert_before_child(insert_point, elements_to_append)
