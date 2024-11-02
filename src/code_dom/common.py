# Common stuff for the code DOM


class ParseContext:
    def __init__(self):
        self.current_content_parser = None
        self.last_element = None


class WriteContext:
    def __init__(self):
        self.for_implementation = False  # Are we outputting code for an implementation file (i.e. not a header)?
        self.use_original_names = False  # Do we want to use the original (unmodified C++) names for things?
        self.for_c = False  # Are we outputting C (as opposed to C++) code?
        self.known_structs = None  # List of known struct names, for applying struct tags when writing C
        self.include_leading_colons = False  # Do we want to include leading colons to fully-qualify all names?
        self.mark_non_nullable_pointers = False  # Do we want to emit non-nullable pointers as ^ instead of *?
        self.for_backend = False  # Are we outputting backend code?
        self.suppress_newlines = False  # Do we want to remove all newlines from the output?
        self.suppress_indent = False  # Do we want to skip adding indent? (set automatically by write_c_line())


# Collapse a list of tokens back into a C-style string, attempting to be reasonably intelligent and/or aesthetic
# about the use of whitespace
def collapse_tokens_to_string(tokens):
    result = ""
    need_space = False
    need_forced_space = False
    for token in tokens:
        token_is_punctuation = token.value in ['+', '-', '<', '>', '(', ')', '=', '/', '\\', '!', '~',
                                               '[', ']', '&', '"', "'", '%', '^', '*', ':', ';', '?',
                                               '!', ',', '.', '{', '}']
        if (need_space and not token_is_punctuation) or need_forced_space:
            result += " "
        result += token.value
        need_space = not token_is_punctuation
        # Special-case here - semicolon and comma do not get a space before them, but do get a space after them,
        # even if the next character is punctuation
        need_forced_space = token.value in [';', ',']
    return result


# Collapse a list of tokens back into a C-style string, assuming the tokens already have suitable whitespace
def collapse_tokens_to_string_with_whitespace(tokens):
    result = ""
    for token in tokens:
        result += token.value
    return result


# Remove any redundant whitespace (i.e. not part of a string literal) from the string given
def remove_redundant_whitespace(str):
    result = ""
    in_single_quote_literal = False
    in_double_quote_literal = False
    last_was_whitespace = False
    for c in str:
        if in_double_quote_literal:
            if c == '"':
                in_double_quote_literal = False
            result += c
        elif in_single_quote_literal:
            if c == "'":
                in_single_quote_literal = False
            result += c
        else:
            if c == '"':
                in_double_quote_literal = True
            if c == "'":
                in_single_quote_literal = True
            if c == ' ':
                if last_was_whitespace:
                    continue  # Skip emitting character
                last_was_whitespace = True
            else:
                last_was_whitespace = False
            result += c

    return result


# Write a C-style line with indentation, and any trailing whitespace removed
# If suppress_indent is set on the context, we emit a single space instead of the requested amount of indent
# (this is so that writing multiple things to the same line works sensibly)
def write_c_line(file, indent, context, text):
    # We check for # here because if a line starts with a preprocessor directive we can't combine it with other lines
    # safely
    if context.suppress_newlines and (len(text) > 0) and (text[0] != '#'):
        text = remove_redundant_whitespace(text.replace('\n', ' '))
        if context.suppress_indent:
            file.write(" " + text.rstrip())
        else:
            file.write("".ljust(indent * 4) + text.rstrip())
            context.suppress_indent = True  # We don't want indentation on following output
    else:
        if context.suppress_indent:
            file.write(" " + text.rstrip() + "\n")
        else:
            file.write("".ljust(indent * 4) + text.rstrip() + "\n")
        context.suppress_indent = False
