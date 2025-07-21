from src import code_dom
from src import utils


# This modifier adds one or more new defines to the appropriate section of the file
# defines should be a list of strings each containing a valid define
# required_defines can contain a list of prerequisite defines which will be added around the emitted defines
def apply(dom_root, defines, required_defines=None):
    # Generate a list of DOM elements to add

    elements_to_append = []
    define_container = None

    # Generate #if statement as required
    if required_defines is not None:
        for define in required_defines:
            check = code_dom.DOMPreprocessorIf()
            check.expression_tokens = [utils.create_token(define)]
            if define_container is not None:
                define_container.add_child(check)
            else:
                elements_to_append.append(check)
            define_container = check

    # Generate defines
    for define in defines:
        define_element = utils.create_preprocessor_declaration(define)
        if define_container is not None:
            define_container.add_child(define_element)
        else:
            elements_to_append.append(define_element)

    if len(elements_to_append) == 0:
        return

    # Add an explanatory comment, if it isn't there already

    existing_explanatory_comment = None
    for comment in dom_root.list_all_children_of_type(code_dom.DOMComment):
        if "Extra defines set by Dear Bindings for internal purposes" in comment.comment_text:
            existing_explanatory_comment = comment

    if existing_explanatory_comment is None:
        comment = code_dom.DOMComment()
        comment.comment_text = "// Extra defines set by Dear Bindings for internal purposes"
        elements_to_append.insert(0, comment)
        # ...and a blank line before it to be neat
        elements_to_append.insert(0, code_dom.DOMBlankLines(1))

    # Add to the file

    insert_point = dom_root.children[0]  # Default to adding at the top of the file if we can't find anywhere else

    # Look for the right section to add these to - if we can, we want to put them under the normal ImGui defines
    if existing_explanatory_comment is not None:
        # If we already started a section, just insert at the end of that
        insert_point = existing_explanatory_comment
    else:
        for comment in dom_root.list_all_children_of_type(code_dom.DOMComment):
            if "Library Version" in comment.comment_text:
                insert_point = comment
                # No early-out here because we actually want the /last/ instance of this comment

    # Skip down past any existing content there
    next_line = insert_point.parent.get_next_child(insert_point)
    while (next_line is not None) and (not isinstance(next_line, code_dom.DOMBlankLines)):
        insert_point = next_line
        next_line = insert_point.parent.get_next_child(insert_point)

    if insert_point is not None:
        # Skip down past any other comments
        next_line = insert_point.parent.get_next_child(insert_point)
        while isinstance(next_line, code_dom.DOMComment):
            insert_point = next_line
            next_line = insert_point.parent.get_next_child(insert_point)

    insert_point.parent.insert_after_child(insert_point, elements_to_append)
