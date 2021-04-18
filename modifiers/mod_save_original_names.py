import code_dom


# This modifier just saves a copy of the original fully-qualified name for each field/function,
# so that the code generation knows what the map to in the original API after renaming has happened
def apply(dom_root):
    for element in dom_root.list_all_children_of_type(code_dom.DOMElement):
        element.original_fully_qualified_name = element.get_fully_qualified_name()
