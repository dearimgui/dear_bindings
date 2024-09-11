from src import code_dom
from src import utils


# This modifier removes all the fields from the classes specified
def apply(dom_root, class_names, add_dummy_field):
    for class_element in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if class_element.get_fully_qualified_name() not in class_names:
            continue

        fields = class_element.list_directly_contained_children_of_type(code_dom.DOMFieldDeclaration)

        if len(fields) == 0:
            continue

        for field in fields:
            field.parent.remove_child(field)

        # Create a comment to note what we did
        comment = code_dom.DOMComment()
        comment.comment_text = "// " + str(len(fields)) + " fields were removed"

        added_elements = [
            code_dom.DOMBlankLines(1),
            comment,
            code_dom.DOMBlankLines(1)
        ]

        if add_dummy_field:
            # Create a dummy field because C requires at least one
            dummy_field = code_dom.DOMFieldDeclaration()
            dummy_field.names = ["__dummy_do_not_use"]
            dummy_field.is_array = [False]
            dummy_field.width_specifiers = [None]
            dummy_field.accessibility = "private"
            dummy_field.field_type = utils.create_type("int")
            dummy_field.field_type.parent = dummy_field

            added_elements.append(dummy_field)
            added_elements.append(code_dom.DOMBlankLines(1))

        class_element.insert_before_child(class_element.children[0], added_elements)

        if add_dummy_field:
            dummy_field.parent = class_element
