from src import code_dom
from src import utils

# Moves elements to a specified header. 
# Last elements in the list will be first in the generated code
# elements_to_move: each tuple is (DOM type, name, (optional) insert_near_forward_declarations)
def apply(dom_root, destination_header, elements_to_move):
    for type_to_move in elements_to_move:
        element_type = type_to_move[0]
        element_name = type_to_move[1]
        insert_near_forward_declarations = False
        if (len(type_to_move) >= 3):
            insert_near_forward_declarations = type_to_move[2]

        for type in dom_root.list_all_children_of_type(element_type):
            # Ignore based on exact name match
            if type.name != element_name:
                continue

            new_type = type.clone()
            type.parent.remove_child(type)

            # Default to adding at the top of the file if we can't find anywhere else
            insert_point = destination_header.children[0]

            # Look for the right section to add these to
            for comment in destination_header.list_all_children_of_type(code_dom.DOMComment):
                if insert_near_forward_declarations:
                    if ("[SECTION] Forward declarations" in comment.comment_text):
                        insert_point = comment
                        # No early-out here because we actually want the /last/ instance of this comment
                elif ("[SECTION] Helpers" in comment.comment_text or # Found in imgui.h
                        "[SECTION] Widgets support: flags, enums, data structures" in comment.comment_text): # Found in imgui_internal.h
                    insert_point = comment
                    # No early-out here because we actually want the /last/ instance of this comment

            insert_point.parent.insert_after_child(insert_point, [new_type])
