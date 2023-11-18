from src import code_dom


# This modifier marks types as requiring pointer-based casting in the function stub generator
def apply(dom_root, type_names):
    for dom_type in dom_root.list_all_children_of_type(code_dom.DOMType):
        if dom_type.get_primary_type_name() in type_names:
            dom_type.use_pointer_cast_conversion = True
