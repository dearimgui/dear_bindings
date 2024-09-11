from src import code_dom
from src import utils


# This modifier changes the type of a class field
def apply(dom_root, class_name, field_name, new_field_type):
    for class_element in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if class_element.get_fully_qualified_name() != class_name:
            continue

        fields = class_element.list_directly_contained_children_of_type(code_dom.DOMFieldDeclaration)

        for field in fields:
            if field_name not in field.names:
                continue

            field.field_type = utils.create_type(new_field_type)
            field.field_type.parent = field
