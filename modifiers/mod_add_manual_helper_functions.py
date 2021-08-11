import code_dom
import utils


# This modifier adds one or more new helper functions to the appropriate section of the file
# functions should be a list of strings each containing a valid function declaration
# No actual implementation code will be emitted for these - the assumption is that they are hand-implemented in
# the appropriate header template cpp file
def apply(dom_root, functions):
    # Generate a list of DOM elements to add

    elements_to_append = []

    for function in functions:
        function_element = utils.create_function_declaration(function)
        function_element.is_manual_helper = True  # This prevents the implementation backend trying to emit code
        elements_to_append.append(function_element)

    if len(elements_to_append) == 0:
        return

    # Add an explanatory comment
    comment = code_dom.DOMComment()
    comment.comment_text = "// Extra helpers for C applications"
    elements_to_append.insert(0, comment)

    # ...and a blank line before it to be neat
    elements_to_append.insert(0, code_dom.DOMBlankLines(1))

    # Add to the file

    insert_point = dom_root.children[0]  # Default to adding at the top of the file if we can't find anywhere else

    # Look for the right section to add these to - if we can, we want to put them in the same place as other
    # helper functions
    for comment in dom_root.list_all_children_of_type(code_dom.DOMComment):
        if "[SECTION] Helpers" in comment.comment_text and "ImVector<>" in comment.comment_text:
            insert_point = comment
            # No early-out here because we actually want the /last/ instance of this comment

    if insert_point is not None:
        # Skip down past any other comments
        next_line = insert_point.parent.get_next_child(insert_point)
        while isinstance(next_line, code_dom.DOMComment):
            insert_point = next_line
            next_line = insert_point.parent.get_next_child(insert_point)

    insert_point.parent.insert_after_child(insert_point, elements_to_append)
