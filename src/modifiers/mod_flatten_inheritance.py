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
        
        # Create a field with the parent type
        parent_struct = parent_struct.clone()

        dummy_field = code_dom.DOMFieldDeclaration()
        dummy_field.names = ["Parent_" + parent_struct.name]
        dummy_field.is_array = [False]
        dummy_field.width_specifiers = [None]
        dummy_field.accessibility = "public"
        dummy_field.field_type = utils.create_type(parent_struct.name)
        dummy_field.field_type.parent = dummy_field

        comment = code_dom.DOMComment()
        comment.comment_text = "// Appended parent type " + parent_struct.name
        dummy_field.attach_preceding_comments([comment])

        struct.insert_before_child(struct.children[0], 
                                   [code_dom.DOMBlankLines(1),
                                    dummy_field, 
                                    code_dom.DOMBlankLines(2)])
        struct.base_classes = None
