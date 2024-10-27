from src import code_dom


# This modifier marks structs such that their definition will be emitted on a single line if possible
# It takes a list of name prefixes to apply this to
def apply(dom_root, struct_name_prefixes):
    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        for prefix in struct_name_prefixes:
            if struct.name.startswith(prefix):
                struct.single_line_declaration = True
                # For neatness we want any preceding comments to become attached ones at this point
                struct.move_preceding_comments_to_attached()
