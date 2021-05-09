import code_dom
import utils
import json


# Add comments attached to an element to the dictionary given
def add_comments(element, root):
    comments_root = {}
    had_any_comments = False
    if element.pre_comments:
        preceding_root = []
        comments_root["preceeding"] = preceding_root
        for comment in element.pre_comments:
            preceding_root.append(comment.to_c_string())
            had_any_comments = True
    if element.attached_comment:
        comments_root["attached"] = element.attached_comment.to_c_string()
        had_any_comments = True

    if had_any_comments:
        root["comments"] = comments_root


# Add preprocessor conditional information for an element to the dictionary given
def add_preprocessor_conditionals(element, root):
    conditionals_root = []
    had_any_conditionals = False

    conditionals = utils.get_preprocessor_conditionals(element)

    for conditional in conditionals:
        if conditional.is_include_guard:
            continue  # Don't include include guards

        expression = code_dom.collapse_tokens_to_string(conditional.expression_tokens)

        if conditional.is_ifdef and conditional.is_negated and (expression == "IMGUI_DISABLE"):
            # Semi-hack - don't clutter up the metadata with "#ifndef IMGUI_DISABLE" as it's kinda redundant
            continue

        conditional_root = {}
        conditionals_root.append(conditional_root)
        if conditional.is_ifdef:
            if conditional.is_negated:
                conditional_root["condition"] = "ifndef"
            else:
                conditional_root["condition"] = "ifdef"
        else:
            conditional_root["condition"] = "if"
        conditional_root["expression"] = expression
        had_any_conditionals = True

    if had_any_conditionals:
        root["conditionals"] = conditionals_root


# Emit data for a single type
def emit_type(type_info):
    return type_info.to_c_string()


# Emit data for an enum element
def emit_enum_element(enum):
    result = {}

    result["name"] = enum.name
    if enum.value_tokens is not None:
        result["value"] = code_dom.collapse_tokens_to_string(enum.value_tokens)

    add_comments(enum, result)
    add_preprocessor_conditionals(enum, result)

    return result


# Emit data for an enum
def emit_enum(enum):
    result = {}

    result["name"] = enum.name

    elements_root = []
    result["elements"] = elements_root

    for element in enum.list_all_children_of_type(code_dom.DOMEnumElement):
        elements_root.append(emit_enum_element(element))

    add_comments(enum, result)
    add_preprocessor_conditionals(enum, result)

    return result


# Emit data for a single field
def emit_field(field):
    result = {}

    names_root = []
    result["names"] = names_root

    # Emit all the field names
    for i in range(0, len(field.names)):
        name_root = {}
        names_root.append(name_root)

        name_root["name"] = field.names[i]
        name_root["is_array"] = field.is_array[i]
        if field.is_array[i]:
            name_root["array_bounds"] = code_dom.collapse_tokens_to_string(field.array_bounds_tokens[i])

        if field.width_specifiers[i] is not None:
            name_root["width"] = str(field.width_specifiers[i])

    # Emit the type
    result["type"] = emit_type(field.field_type)

    add_comments(field, result)
    add_preprocessor_conditionals(field, result)

    return result


# Emit data for a single struct
def emit_struct(struct):
    result = {}

    result["name"] = struct.name
    result["type"] = struct.structure_type.lower()  # Lowercase this for consistency with C
    result["by_value"] = struct.is_by_value

    fields_root = []
    result["fields"] = fields_root

    for field in struct.list_all_children_of_type(code_dom.DOMFieldDeclaration):
        fields_root.append(emit_field(field))

    add_comments(struct, result)
    add_preprocessor_conditionals(struct, result)

    return result


# Emit data for a single function argument
def emit_function_argument(argument):
    result = {}

    if argument.name is not None:
        result["name"] = argument.name
    if argument.arg_type is not None:
        result["type"] = emit_type(argument.arg_type)
    result["is_array"] = argument.is_array
    result["is_varargs"] = argument.is_varargs
    if argument.is_array:
        result["array_bounds"] = str(argument.array_bounds)
    if argument.default_value_tokens is not None:
        result["default_value"] = code_dom.collapse_tokens_to_string(argument.default_value_tokens)

    return result


# Emit data for a single function
def emit_function(function):
    result = {}

    result["name"] = function.name

    if function.return_type is not None:
        result["return_type"] = emit_type(function.return_type)

    arguments_root = []
    result["arguments"] = arguments_root

    for argument in function.arguments:
        arguments_root.append(emit_function_argument(argument))

    add_comments(function, result)
    add_preprocessor_conditionals(function, result)

    return result


# Write metadata about our file to a JSON file
def generate(dom_root, file):
    metadata_root = {}

    # Emit enums
    enums_root = []
    metadata_root["enums"] = enums_root

    for enum in dom_root.list_all_children_of_type(code_dom.DOMEnum):
        enums_root.append(emit_enum(enum))

    # Emit struct declarations
    structs_root = []
    metadata_root["structs"] = structs_root

    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if struct.is_forward_declaration:
            continue  # Don't emit anything for forward declarations

        structs_root.append(emit_struct(struct))

    # Emit function declarations
    functions_root = []
    metadata_root["functions"] = functions_root

    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        functions_root.append(emit_function(function))

    # Write JSON to file
    json.dump(metadata_root, file, indent=4)
