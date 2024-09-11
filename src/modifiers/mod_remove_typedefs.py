from src import code_dom

def apply(dom_root, typedefs_names):
    for typedef in dom_root.list_all_children_of_type(code_dom.DOMTypedef):
        if typedef.name in typedefs_names:
            typedef.parent.remove_child(typedef)
