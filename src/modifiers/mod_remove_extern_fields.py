from src import code_dom


# This modifier removes any extern fields
# (on the basis that we'd need to add accessor functions, and right now there aren't any
# extern fields that are actually particularly useful to expose)
def apply(dom_root):
    for field in dom_root.list_all_children_of_type(code_dom.DOMFieldDeclaration):
        if field.is_extern:
            field.parent.remove_child(field)
