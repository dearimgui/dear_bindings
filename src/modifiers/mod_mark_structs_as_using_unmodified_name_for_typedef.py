from src import code_dom


# This modifier marks structs with "use_unmodified_name_for_typedef", which prevents "_t" being added to their
# typedef name.
def apply(dom_root, struct_names):
    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if struct.name in struct_names:
            struct.use_unmodified_name_for_typedef = True
