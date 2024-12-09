from .common import *
from src import code_dom


# Class/struct/union
class DOMClassStructUnion(code_dom.element.DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None  # Can be none for anonymous things if they haven't been given a temporary name
        self.is_anonymous = True
        self.is_forward_declaration = True  # Is this a forward-declaration
        self.has_forward_declaration = False
        self.is_by_value = False  # Is this to be passed by value? (set during modification)
        self.structure_type = None  # Will be "STRUCT", "CLASS" or "UNION"
        self.is_imgui_api = False  # Does this use IMGUI_API?
        self.base_classes = None  # List of base classes, as tuples with their accessibility (i.e. ("private", "CBase"))
        self.use_unmodified_name_for_typedef = False  # Should the name be used as-is for the typedef?
        self.single_line_declaration = False  # Should we try to emit the declaration as a single line?

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        dom_element = DOMClassStructUnion()
        tok = stream.get_token_of_type(['STRUCT', 'CLASS', 'UNION'])
        dom_element.structure_type = tok.type

        # We don't really use the token list in this element, but line number detection reads it so add just the
        # initial token so it has somewhere to get information from
        dom_element.tokens.append(tok)

        name_tok = stream.get_token_of_type(['THING'])
        if name_tok is not None:
            dom_element.name = name_tok.value
            dom_element.is_anonymous = False

            # Deal with things like "struct IMGUI_API ImRect"
            if name_tok.value == 'IMGUI_API':
                dom_element.is_imgui_api = True
                name_tok = stream.get_token_of_type(['THING'])
                if name_tok is not None:
                    dom_element.name = name_tok.value

        base_class_separator = stream.get_token_of_type(['COLON'])

        if base_class_separator is not None:
            # We have a base class list
            dom_element.base_classes = []
            next_accessibility = "private"
            while True:
                tok = stream.get_token()
                if tok.type == 'LBRACE':
                    # Start of actual class members
                    stream.rewind_one_token()
                    break
                elif (tok.value == "public") or (tok.value == "private") or (tok.value == "protected"):
                    # Accessibility
                    next_accessibility = tok.value
                else:
                    # Class name
                    dom_element.base_classes.append((next_accessibility, tok.value))
                    next_accessibility = "private"

        # print("Struct/Class/Union: " + dom_element.structure_type + " : " + (dom_element.name or "<anonymous>"))

        current_accessibility = "public" if (dom_element.structure_type != 'CLASS') else "private"

        if stream.get_token_of_type(['LBRACE']) is not None:
            dom_element.is_forward_declaration = False
            while True:
                tok = stream.peek_token()
                if tok.type == 'RBRACE':
                    stream.get_token()  # Eat the closing brace
                    break

                if (tok.value == 'public') or (tok.value == 'private') or (tok.value == 'protected'):
                    # Accessibility modifier
                    stream.get_token()  # Eat token
                    stream.get_token_of_type(['COLON'])  # Eat colon
                    current_accessibility = tok.value
                    continue

                child_element = context.current_content_parser()

                if child_element is not None:
                    child_element.accessibility = current_accessibility
                    if not child_element.no_default_add:
                        dom_element.add_child(child_element, context)
                else:
                    print("Unrecognised element: " + str(vars(tok)) + " in DOMClassStructUnion " + dom_element.name)
                    break

        stream.get_token_of_type(['SEMICOLON'])  # Eat the trailing semicolon

        return dom_element

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        name = self.name or "<anonymous>"
        if leaf_name != "":
            name += "::" + leaf_name
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(name, include_leading_colons)
        else:
            return ("::" if include_leading_colons else "") + name

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)

        declaration = ""

        need_typedef = context.for_c and not self.is_anonymous and not self.has_forward_declaration

        if need_typedef:
            declaration += "typedef "

        if self.structure_type == "STRUCT":
            declaration += "struct"
        elif self.structure_type == "CLASS":
            declaration += "class"
        elif self.structure_type == "UNION":
            declaration += "union"
        else:
            raise Exception("Unsupported struct/class/union type")

        # Forward declarations are always single line and don't need special processing
        using_single_line_declaration = self.single_line_declaration and not self.is_forward_declaration

        if using_single_line_declaration:
            context.suppress_newlines = True
            context.suppress_indent = False

        if not self.is_anonymous:
            declaration += " " + self.name
            # We need the struct name to be different from the typedef name to prevent compiler complaints about
            # forward declarations not matching (except for some special cases like DirectX types)
            if context.for_c and not self.use_unmodified_name_for_typedef:
                declaration += "_t"

        if not self.is_forward_declaration:
            # Add base classes
            if not context.for_c and self.base_classes is not None:
                is_first = True
                for accessibility, class_name in self.base_classes:
                    declaration += " : " if is_first else ", "
                    declaration += accessibility + " " + class_name

            # We want to put attached comments on the declaration, unless we're in single-line mode
            if using_single_line_declaration:
                write_c_line(file, indent, context, declaration)
            else:
                write_c_line(file, indent, context, self.add_attached_comment_to_line(context, declaration))
            write_c_line(file, indent, context, "{")
            for child in self.children:
                child.write_to_c(file, indent + 1, context)
            if need_typedef:
                write_c_line(file, indent, context, "} " + self.name + ";")
            else:
                write_c_line(file, indent, context, "};")
        else:
            if need_typedef:
                write_c_line(file, indent, context, self.add_attached_comment_to_line(context, declaration + " " + self.name + ";"))
            else:
                write_c_line(file, indent, context, self.add_attached_comment_to_line(context, declaration + ";"))

        if using_single_line_declaration:
            context.suppress_newlines = False
            context.suppress_indent = True
            # This will insert the final newline and also reset suppress_indent
            write_c_line(file, indent, context, self.add_attached_comment_to_line(context, ""))

    def __str__(self):
        if self.name is not None:
            return self.structure_type + ": " + self.name
        else:
            return self.structure_type
