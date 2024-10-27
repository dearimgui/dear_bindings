from .common import *
from src import code_dom


# An "extern C" statement
class DOMExternC(code_dom.element.DOMElement):
    def __init__(self):
        super().__init__()
        self.is_cpp_guarded = False  # Is this extern block surrounded with an implicit #ifdef __cplusplus guard?
        #                              (only used for synthetic blocks - the parser isn't smart enough to autodetect
        #                               that situation yet)

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMExternC()
        tok = stream.get_token_of_type(['THING'])
        if tok is None or tok.value != "extern":
            stream.rewind(checkpoint)
            return None

        dom_element.tokens.append(tok)

        tok = stream.get_token_of_type(['STRING_LITERAL'])
        if tok is None or (tok.value != '"C"' and tok.value != '"c"'):
            stream.rewind(checkpoint)
            return None

        has_braces = stream.get_token_of_type(['LBRACE'])

        while True:
            tok = stream.peek_token()
            if has_braces and (tok.type == 'RBRACE'):
                stream.get_token()  # Eat the closing brace
                break

            child_element = context.current_content_parser()
            if child_element is not None:
                if not child_element.no_default_add:
                    dom_element.add_child(child_element, context)
            else:
                print("Unrecognised element: " + str(vars(tok)) + " in DOMExternC")
                break

            if not has_braces:
                break  # Only parse one element if there were no braces

        if not has_braces:
            stream.get_token_of_type(['SEMICOLON'])  # Eat the trailing semicolon

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        if self.is_cpp_guarded:
            write_c_line(file, indent, context, '#ifdef __cplusplus')
        write_c_line(file, indent, context, self.add_attached_comment_to_line(context, 'extern "C"'))

        # We only emit a single-line extern if this is a typedef/structure definition or function
        # This is important because it avoids an awkward bug where if an extern wraps something like a
        # preprocessor directive it thinks it is single-line but actually from the compiler's perspective isn't
        # (since single-line is purely here for aesthetic reasons, we take the conservative route and only allow
        # it for cases that are clearly safe).
        if (len(self.children) == 1) and (isinstance(self.children[0], code_dom.DOMTypedef) or
                                          isinstance(self.children[0], code_dom.DOMClassStructUnion) or
                                          isinstance(self.children[0], code_dom.DOMFunctionDeclaration)):
            # Single-line(-ish) version
            if self.is_cpp_guarded:
                write_c_line(file, indent, context, '#endif')
            for child in self.children:
                child.write_to_c(file, indent + 1, context)
        else:
            # Multi-line version
            write_c_line(file, indent, context, "{")
            if self.is_cpp_guarded:
                write_c_line(file, indent, context, '#endif')
            for child in self.children:
                # Only indent in the non-guarded case, for aesthetic purposes
                child.write_to_c(file, indent + (0 if self.is_cpp_guarded else 1), context)
            if self.is_cpp_guarded:
                write_c_line(file, indent, context, '#ifdef __cplusplus')
            write_c_line(file, indent, context, '} // End of extern "C" block')
            if self.is_cpp_guarded:
                write_c_line(file, indent, context, '#endif')

    def __str__(self):
        return "Extern C block"
