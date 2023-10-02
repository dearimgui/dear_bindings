from src import code_dom
from src import utils


def apply(dom_root, destination_header, type_names):
    for type in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        # Ignore based on exact name match
        if type.name not in type_names:
            continue

        new_type = type.clone()
        type.parent.remove_child(type)

        # Default to adding at the top of the file if we can't find anywhere else
        insert_point = destination_header.children[0]

        # Look for the right section to add these to - if we can, we want to put them in the same place as
        # forward declarations
        for comment in destination_header.list_all_children_of_type(code_dom.DOMComment):
            if "[SECTION] Forward declarations" in comment.comment_text:
                insert_point = comment
                # No early-out here because we actually want the /last/ instance of this comment

        insert_point.parent.insert_before_child(insert_point, [new_type])
