from src import code_dom
from src import utils


# This modifier takes any structs with inheritance and appends the parent fields at the start.
# Doesn't take multiple inheritance into account, but we're not using it anyway.
def apply(dom_root):
    # Iterate through all structs/classes/unions
    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        # Ignore non-structs
        if struct.structure_type != "STRUCT":
            continue

        if struct.base_classes is None:
            continue

        if len(struct.base_classes) > 1:
            raise Exception("Struct " + parent_struct.name + " with more than one parent class is not supported")

        accessibility, class_name = struct.base_classes[0]
        parent_struct = None
        for other_struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
            if other_struct.name == class_name and len(other_struct.children) > 0:
                parent_struct = other_struct
                break

        if parent_struct is None:
            raise Exception("Failed to find parent class " + parent_struct.name + " for type " + struct.name)

        parent_fields = parent_struct.clone().list_directly_contained_children_of_type(code_dom.DOMFieldDeclaration)

        comment = code_dom.DOMComment()
        comment.comment_text = "// Appended from parent type " + parent_struct.name
        parent_fields[0].attach_preceding_comments([comment])

        struct.insert_before_child(struct.children[0], 
                                   parent_fields + [code_dom.DOMBlankLines(2)]
                                   )
        struct.base_classes = None
