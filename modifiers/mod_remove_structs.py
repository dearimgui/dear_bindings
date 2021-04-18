import code_dom


# This modifier removes structs/classes with the (fully-qualified) names specified
def apply(dom_root, struct_names):
    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if struct.get_fully_qualified_name() in struct_names:
            struct.parent.remove_child(struct)
