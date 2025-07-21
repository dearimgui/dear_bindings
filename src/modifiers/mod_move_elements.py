from src import code_dom
from src import utils

# Moves elements to a specified header. 
# Last elements in the list will be first in the generated code
# elements_to_move: each tuple is (DOM type, name, (optional) treat_name_as_prefix, (optional) insert_near_forward_declarations)
# If insert_near_forward_declarations is false then the elements
# will be added in the "Helpers" or "Widgets support" section instead
def apply(dom_root, destination_header, elements_to_move):
    for type_to_move in elements_to_move:
        element_type = type_to_move[0]
        element_name = type_to_move[1]
        treat_name_as_prefix = False
        insert_near_forward_declarations = False
        if (len(type_to_move) >= 3):
            treat_name_as_prefix = type_to_move[2]

        if (len(type_to_move) >= 4):
            insert_near_forward_declarations = type_to_move[3]

        for type in dom_root.list_all_children_of_type(element_type):
            if element_type is code_dom.DOMPreprocessorIf:
                # Special case to allow us to find #ifdefs by their expression
                effective_name = type.get_expression()
            else:
                effective_name = type.name

            if treat_name_as_prefix:
                # Ignore based on name prefix
                if not effective_name.startswith(element_name):
                    continue
            else:
                # Ignore based on exact name match
                if effective_name != element_name:
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
