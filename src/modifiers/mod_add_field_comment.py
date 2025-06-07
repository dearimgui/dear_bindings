from src import code_dom
from src import utils


# This modifier adds a comment to the field with the fully-qualified name given
# If a comment already exists the comment text will be appended to it with a space
def apply(dom_root, field_name, comment):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFieldDeclaration):
        if function.get_fully_qualified_name() == field_name:
            utils.append_comment_text(function, comment)
