import code_dom
import ply.lex as lex
import c_lexer


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


# Create a set of tokens for a type from a string
def create_tokens_for_type(text):
    stream = c_lexer.tokenize(text)
    context = code_dom.ParseContext()
    return code_dom.DOMType.parse(context, stream, allow_function_pointer=True).tokens


# Get all #if/#ifdef/etc blocks an element is contained in as a list in order from the outermost
def get_preprocessor_conditionals(element):
    result = []
    while element is not None:
        if isinstance(element, code_dom.DOMPreprocessorIf):
            result.append(element)
        element = element.parent
    result.reverse()
    return result


# Turn a name into something suitable to use in a C identifier
def sanitise_name_for_identifier(name):
    return name \
        .replace('*', 'Ptr') \
        .replace('&', 'Ref') \
        .replace(' ', '_')
