from src import code_dom
import ply.lex as lex
from src import c_lexer


# Create a new LexToken with the text given
def create_token(text):
    token = lex.LexToken()
    # Technically we don't care about token types any more since we're done parsing, so we set a non-existent token type
    # to make it clear where this came from
    token.type = 'SYNTHETIC'
    token.value = text
    token.lineno = 0
    token.lexpos = 0
    return token


# Create a type from a string
def create_type(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    return code_dom.DOMType.parse(context, stream, allow_function_pointer=True)


# Create a class/struct/union from a string
def create_classstructunion(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    context.current_content_parser = lambda: code_dom.DOMHeaderFile.parse_content(context, stream)
    return code_dom.DOMClassStructUnion.parse(context, stream)


# Create a set of tokens for a type from a string
def create_tokens_for_type(text):
    return create_type(text).tokens


# Create a function declaration DOM element from a string
def create_function_declaration(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    element = code_dom.DOMFunctionDeclaration.parse(context, stream)
    # There may be a comment following the declaration, so check for it and attach if there is
    attached_comment = code_dom.DOMComment.parse(context, stream)
    if attached_comment is not None:
        element.attached_comment = attached_comment
        element.attached_comment.is_attached_comment = True
        element.attached_comment.parent = element
    return element


# Create a typedef DOM element from a string
def create_typedef(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    element = code_dom.DOMTypedef.parse(context, stream)
    # There may be a comment following the declaration, so check for it and attach if there is
    attached_comment = code_dom.DOMComment.parse(context, stream)
    if attached_comment is not None:
        element.attached_comment = attached_comment
        element.attached_comment.is_attached_comment = True
        element.attached_comment.parent = element
    return element


# Create a preprocessor if DOM element from a string
def create_preprocessor_if(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    context.current_content_parser = lambda: code_dom.DOMHeaderFile.parse_content(context, stream)
    element = code_dom.DOMPreprocessorIf.parse(context, stream)
    # There may be a comment following the declaration, so check for it and attach if there is
    attached_comment = code_dom.DOMComment.parse(context, stream)
    if attached_comment is not None:
        element.attached_comment = attached_comment
        element.attached_comment.is_attached_comment = True
        element.attached_comment.parent = element
    return element


# Create a preprocessor definition DOM element from a string
def create_preprocessor_declaration(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    element = code_dom.DOMDefine.parse(context, stream)
    # There may be a comment following the define, so check for it and attach if there is
    attached_comment = code_dom.DOMComment.parse(context, stream)
    if attached_comment is not None:
        element.attached_comment = attached_comment
        element.attached_comment.is_attached_comment = True
        element.attached_comment.parent = element
    return element


# Create a code block DOM element from a string (e.g. "{ return 1.0f; }")
def create_code_block(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    element = code_dom.DOMCodeBlock.parse(context, stream)
    return element


# Get all #if/#ifdef/etc blocks an element is contained in as a list in order from the outermost
def get_preprocessor_conditionals(element):
    result = []
    while element is not None:
        if isinstance(element, code_dom.DOMPreprocessorIf):
            result.append(element)
        element = element.parent
    result.reverse()
    return result


# Returns true if the passed element is part of the else (i.e. negated) block of the conditional given
def is_in_else_clause(element, conditional_element):
    while element is not None:
        if element.parent == conditional_element:
            return conditional_element.is_element_in_else_block(element)
        element = element.parent
    return False


# Check if two elements are mutually exclusive, in the sense that #ifdefs mean that they can never both
# be active at the same time. This check isn't exhaustive, and can be confused by non-trivial #ifdef constructs,
# but it's good enough for our purposes. It's conservative in that it may miss cases that are actually mutually
# exclusive and return False, but it should never return True for elements that can in fact both get compiled
# simultaneously.
def are_elements_mutually_exclusive(element_a, element_b):
    conditionals_a = get_preprocessor_conditionals(element_a)
    conditionals_b = get_preprocessor_conditionals(element_b)

    for conditional_a in conditionals_a:
        conditional_a_negated = is_in_else_clause(element_a, conditional_a)
        for conditional_b in conditionals_b:
            conditional_b_negated = is_in_else_clause(element_b, conditional_b)
            if conditional_a_negated == conditional_b_negated:
                # If both elements are in the same block (normal/else) then check if the conditions are exclusive
                if conditional_a.condition_is_mutually_exclusive(conditional_b):
                    return True
            else:
                # If one element is in an else block and the other isn't, check if the conditions match
                if conditional_a.condition_matches(conditional_b):
                    return True

    return False


# Turn a name into something suitable to use in a C identifier
def sanitise_name_for_identifier(name):
    # We replace ", " and " , " first as a way to avoid getting multiple __s in the result when those patterns appear
    return name \
        .replace(' , ', '_') \
        .replace(', ', '_') \
        .replace('*', 'Ptr') \
        .replace('&', 'Ref') \
        .replace(',', '_') \
        .replace(' ', '_')


# Append comment text to an element
# Mainly useful for debugging
def append_comment_text(element, message):
    if element.attached_comment is not None:
        element.attached_comment.comment_text += " " + message
    else:
        comment = code_dom.DOMComment()
        comment.comment_text = "// " + message
        comment.is_attached_comment = True
        comment.parent = element
        element.attached_comment = comment


# Migrate comments from one element to another - useful when replacing an element with another one
def migrate_comments(from_element, to_element):
    # Move preceding comments
    comments_to_move = from_element.pre_comments.copy()  # Copy to avoid altering the list as we iterate
    to_element.attach_preceding_comments(comments_to_move)

    # Move attached comment
    if from_element.attached_comment is not None:
        if to_element.attached_comment is not None:
            # This isn't actually hard to fix - it just requires appending one comment's text onto the other,
            # but for 99% of use-cases it will never happen (as I imagine this will mostly be used when swapping
            # an old element for a newly-created one, and thus the new element will not have any comments), so for
            # now let's just treat it as an error.
            raise Exception("Comment migration would overwrite existing comment")

        to_element.attached_comment = from_element.attached_comment
        to_element.attached_comment.parent = to_element
        from_element.attached_comment = None


# Build a list of all the classes/structs/enums ImGui defines, so we know which things need casting/name-fudging
# (we also put function pointers in here as they need the same treatment, hence the "callbacks" bit)
def get_imgui_custom_types(dom_root):
    imgui_custom_types = {}

    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        if struct.name is not None:
            imgui_custom_types[struct.name] = struct
            imgui_custom_types["cimgui::" + struct.name] = struct  # Also add the qualified version
            # And the original names
            if struct.unmodified_element is not None:
                imgui_custom_types[struct.unmodified_element.name] = struct

    for enum in dom_root.list_all_children_of_type(code_dom.DOMEnum):
        if not enum.is_forward_declaration:
            imgui_custom_types[enum.name] = enum
            imgui_custom_types["cimgui::" + enum.name] = enum  # Also add the qualified version
            # And the original names
            if enum.unmodified_element is not None:
                imgui_custom_types[enum.unmodified_element.name] = enum

    # Also include function pointer definitions, as we basically need to treat them like class/structs for casting
    # purposes
    for typedef in dom_root.list_all_children_of_type(code_dom.DOMTypedef):
        if isinstance(typedef.type, code_dom.DOMFunctionPointerType):
            imgui_custom_types[typedef.name] = typedef

    return imgui_custom_types


def find_nearest_parent_of_type(child, parent_type):
    current = child
    while current is not None:
        current = current.parent
        if isinstance(current, parent_type):
            break

    return current
