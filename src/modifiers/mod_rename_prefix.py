from src import code_dom


# This modifier renames one or more prefix on everything in the DOM
# The parameter should be a map mapping old prefixes to new ones
# Behaviour is undefined if there are multiple potential matches or overlapping old/new patterns
def apply(dom_root, prefixes_map):
    for element in dom_root.list_all_children_of_type(code_dom.DOMElement):
        if hasattr(element, 'name'):
            for old_prefix in prefixes_map:
                if (element.name is not None) and element.name.startswith(old_prefix):
                    element.name = prefixes_map[old_prefix] + element.name[len(old_prefix):]
