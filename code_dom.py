import token_stream
import ply.lex as lex
import copy


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


def write_c_line(file, indent, text):
    file.write("".ljust(indent * 4) + text + "\n")


class DOMElement:
    def __init__(self):
        self.tokens = []
        self.parent = None  # The parent element
        self.children = []  # Basic child elements (note that some elements have multiple child lists)
        self.pre_comments = []  # If this element is preceded with comments that are related to it, they go here
        self.attached_comment = None  # If a comment appears after this element (on the same line), this is it
        self.no_default_add = False  # Should this element not be added to the DOM upon creation? (mainly for
        #                              attached comments)
        self.unmodified_element = None  # The original (unmodified) element, as part of a complete clone of the
        #                                 pre-modification document structure
        self.original_name_override = None  # Optional name to use for the original name of this type
        #                                     (primarily for template parameter expansion and the like)

    # Parse tokens that can appear anywhere, returning an appropriate element if possible or None if not
    @staticmethod
    def parse_common(context, stream):
        tok = stream.peek_token(skip_newlines=False)
        if tok is None:
            return None
        if (tok.type == 'LINE_COMMENT') or (tok.type == 'BLOCK_COMMENT'):
            return DOMComment.parse(context, stream)
        elif tok.type == 'PPDEFINE':
            return DOMDefine.parse(context, stream)
        elif tok.type == 'PPUNDEF':
            return DOMUndef.parse(context, stream)
        elif (tok.type == 'PPIF') or (tok.type == 'PPIFDEF') or (tok.type == 'PPIFNDEF'):
            return DOMPreprocessorIf.parse(context, stream)
        elif tok.type == 'PRAGMA':
            return DOMPragma.parse(context, stream)
        elif tok.type == 'PPERROR':
            return DOMError.parse(context, stream)
        elif tok.type == 'PPINCLUDE':
            return DOMInclude.parse(context, stream)
        elif tok.type == 'NEWLINE':
            blank_lines = DOMBlankLines.parse(context, stream)
            # A little bit of a convenience hack here - we don't really want tons of "zero blank lines"
            # entries cluttering up the DOM every time we see a newline, so only return blank line elements if they
            # actually represent a blank line as opposed to just a single newline
            if blank_lines.num_blank_lines > 0:
                return blank_lines
            else:
                context.last_element = None  # Clear last_element to avoid comments attaching across newlines
                return DOMElement.parse_common(context, stream)
        else:
            return None

    # Parse tokens that can appear in most scopes, returning an appropriate element if possible or None if not
    @staticmethod
    def parse_basic(context, stream):
        common_element = DOMElement.parse_common(context, stream)
        if common_element is not None:
            return common_element

        tok = stream.peek_token()
        if tok is None:
            return None
        if (tok.type == 'STRUCT') or (tok.type == 'CLASS') or (tok.type == 'UNION'):
            return DOMClassStructUnion.parse(context, stream)
        elif tok.type == 'PPDEFINE':
            return DOMDefine.parse(context, stream)
        elif tok.type == 'PPUNDEF':
            return DOMUndef.parse(context, stream)
        elif (tok.type == 'PPIF') or (tok.type == 'PPIFDEF') or (tok.type == 'PPIFNDEF'):
            return DOMPreprocessorIf.parse(context, stream)
        elif tok.type == 'PRAGMA':
            return DOMPragma.parse(context, stream)
        elif tok.type == 'PPERROR':
            return DOMError.parse(context, stream)
        elif tok.type == 'PPINCLUDE':
            return DOMInclude.parse(context, stream)
        elif tok.type == 'NAMESPACE':
            return DOMNamespace.parse(context, stream)
        elif tok.type == 'TYPEDEF':
            return DOMTypedef.parse(context, stream)
        elif tok.type == 'ENUM':
            return DOMEnum.parse(context, stream)
        elif tok.type == 'TEMPLATE':
            return DOMTemplate.parse(context, stream)
        elif (tok.type == 'THING') or (tok.type == 'CONST') or (tok.type == 'SIGNED') or (tok.type == 'UNSIGNED') or \
                (tok.type == '~'):  # ~ is necessary because destructor names start with it
            # This could be either a field declaration or a function declaration, so try both

            function_declaration = DOMFunctionDeclaration.parse(context, stream)
            if function_declaration is not None:
                return function_declaration

            field_declaration = DOMFieldDeclaration.parse(context, stream)
            if field_declaration is not None:
                return field_declaration

            # It may be a macro or something else we don't understand, so record it as unparsable and move on
            return DOMUnparsableThing.parse(context, stream)
        else:
            return None

    # Attach preceding comments
    def attach_preceding_comments(self, comments):
        for comment in comments:
            self.pre_comments.append(comment)
            if comment.parent:
                comment.parent.remove_child(comment)
            comment.parent = self
            comment.is_preceding_comment = True

    # Get any attached comment for this element as a C string
    def get_attached_comment_as_c_string(self):
        if self.attached_comment is not None:
            return " " + self.attached_comment.to_c_string()
        else:
            return ""

    # Write any preceding comments
    def write_preceding_comments(self, file, indent=0, context=WriteContext()):
        if context.for_implementation:
            return  # No comments in implementation code
        for comment in self.pre_comments:
            write_c_line(file, indent, comment.to_c_string())

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, " // Unsupported element " + str(self))
        for child in self.children:
            child.write_to_c(file, indent + 1, context)
        write_c_line(file, indent, " // End of unsupported element " + str(self) +
                     self.get_attached_comment_as_c_string())

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + str(self))
        for child in self.children:
            child.dump(indent + 1)

    # Gets the fully-qualified name (C++-style) of this element (including namespaces/etc)
    # If include_leading_colons is true then the name will be returned in a genuinely "fully-qualified" fashion -
    # i.e. "::MyClass::Something"
    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(leaf_name, include_leading_colons)
        else:
            return ("::" if include_leading_colons else "") + leaf_name

    # Gets the original (i.e. unmodified) fully-qualified name of this element for implementation purposes
    def get_original_fully_qualified_name(self, include_leading_colons=False):
        if self.original_name_override is not None:
            return self.original_name_override
        if self.unmodified_element is not None:
            return self.unmodified_element.get_fully_qualified_name("", include_leading_colons)
        else:
            return self.get_fully_qualified_name("", include_leading_colons)

    # Gets the class/struct that contains this element (if one exists)
    def get_parent_class(self):
        current = self.parent
        while current is not None:
            if isinstance(current, DOMClassStructUnion):
                return current
            current = current.parent
        return None

    # Add a new child to this element, optionally setting the last element information in the context
    # Removes the child from any previous parent element
    # Note that for elements with multiple child lists this will add to the default one - insert_after_child() is
    # preferably generally for that reason
    def add_child(self, child, context=None):
        if child.parent is not None:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)
        if context is not None:
            context.last_element = child

    # Add multiple children
    def add_children(self, children, context=None):
        for child in children:
            self.add_child(child, context)

    # Remove a child from this element
    def remove_child(self, child):
        if child.parent is not self:
            raise Exception("Attempt to remove child from element other than parent")
        for child_list in self.get_writable_child_lists():
            if child in child_list:
                child_list.remove(child)
                child.parent = None
                return
        # Types are not stored in a list, but are returned in one for traversal purposes. Thus they cannot be
        # removed with remove_child() (because the temporary list returned by get_child_lists() is not returned
        # by get_writable_child_lists()).
        raise Exception("Child not found in any list - this may be because it is attached as a type or similar")

    # Find the element immediately prior to the child given
    def get_prev_child(self, child):
        for child_list in self.get_child_lists():
            for i in range(0, len(child_list)):
                if child_list[i] == child:
                    if i > 0:
                        return child_list[i - 1]
                    else:
                        return None
        raise Exception("Child not found in any list")

    # Find the element immediately after the child given
    def get_next_child(self, child):
        for child_list in self.get_child_lists():
            for i in range(0, len(child_list)):
                if child_list[i] == child:
                    if i < (len(child_list) - 1):
                        return child_list[i + 1]
                    else:
                        return None
        raise Exception("Child not found in any list")

    # Debug function - raises exception if the hierarchy is not valid
    def validate_hierarchy(self):
        for child_list in self.get_child_lists():
            for child in child_list:
                if child.parent is not self:
                    raise Exception("Node " + str(child) + " has parent " + str(child.parent) + " when it should be " +
                                    str(self))
                child.validate_hierarchy()

    # Returns a list of all the lists in this element that contain children
    def get_child_lists(self):
        if self.attached_comment is not None:
            return [self.children, self.pre_comments, [self.attached_comment]]
        else:
            return [self.children, self.pre_comments]

    # Returns a list of all the lists in this element that contain children and can be modified
    # This may be different from get_child_lists in that the former can return temporary lists to enumerate children
    # which are not part of a normal list (e.g. types) and thus cannot be manipulated that way.
    def get_writable_child_lists(self):
        return [self.children, self.pre_comments]

    # Tests if this element is a descendant of (or the same as) the element given
    def is_descendant_of(self, parent):
        if self is parent:
            return True
        if self.parent is None:
            return False
        return self.parent.is_descendant_of(parent)

    # Walk this element and all children, calling a function on them
    def walk(self, func):
        func(self)
        for child_list in self.get_child_lists():
            for child in child_list:
                child.walk(func)

    # Recursively find all the children of this element (and this element itself) that match the type supplied,
    # and return them as a list
    def list_all_children_of_type(self, element_type):
        result = []

        def walker(element):
            if isinstance(element, element_type):
                result.append(element)

        self.walk(walker)

        return result

    # Override for pickling that removes unmodified_element (mainly for cloning, as otherwise we would basically
    # end up cloning the entire unmodified tree every time we cloned anything)
    def __getstate__(self):
        state = self.__dict__.copy()
        if "unmodified_element" in state:
            state["unmodified_element"] = None
        return state

    # Performs a deep clone of this element and all children
    def clone(self):
        # We need to temporarily remove our parent reference to prevent the tree above us getting cloned
        temp_parent = self.parent
        self.parent = None
        clone = copy.deepcopy(self)
        self.parent = temp_parent
        clone.__reconnect_unmodified(self)
        return clone

    # Clone this element but without any children, where "children" means explicit children, such as contained
    # function/fields or similar, but not technically-children like types/arguments/etc. Attached comments are cloned.
    def clone_without_children(self):
        temp_children = self.children
        self.children = []
        clone = self.clone()
        self.children = temp_children
        return clone

    # Reconnect "unmodified_element" on a whole tree of elements
    # (used after cloning, as we don't clone unmodified_element)
    def __reconnect_unmodified(self, original):
        self.unmodified_element = original.unmodified_element

        for child_list, original_child_list in zip(self.get_child_lists(), original.get_child_lists()):
            for child, original_child in zip(child_list, original_child_list):
                child.__reconnect_unmodified(original_child)

    # This creates a clone of this element and all children, stored in the "unmodified_element" field of each
    # corresponding element
    def save_unmodified_clones(self):
        clone = copy.deepcopy(self)
        self.__attach_unmodified_clones(clone)

    # Attach unmodified clones to the tree recursively
    def __attach_unmodified_clones(self, clone):

        # This shouldn't really be necessary, but as a sanity check make sure we're matching (probably) the correct
        # elements to each other
        if str(self) != str(clone):
            raise Exception("Unmodified clone mismatch error")

        self.unmodified_element = clone

        if len(self.get_child_lists()) != len(clone.get_child_lists()):
            raise Exception("Unmodified clone mismatch error")

        for child_list, clone_child_list in zip(self.get_child_lists(), clone.get_child_lists()):
            if len(child_list) != len(clone_child_list):
                raise Exception("Unmodified clone mismatch error")

            for child, clone_child in zip(child_list, clone_child_list):
                child.__attach_unmodified_clones(clone_child)

    # Is this element a preprocessor container (#if or similar)?
    def __is_preprocessor_container(self):
        return False

    # Get a list of the directly contained children of this element - this means all immediate children and
    # all children inside preprocessor #if blocks, but not children of contained structs/namespaces/etc
    # (so in other words, what the C compiler would consider children, after preprocessing has been done)
    def list_directly_contained_children(self):
        result = []
        for child_list in self.get_child_lists():
            for child in child_list:
                if child.__is_preprocessor_container():
                    # Recurse into preprocessor containers
                    for container_child in child.list_directly_contained_children():
                        result.append(container_child)
                else:
                    result.append(child)
        return result

    # Get a list of all directly contained children that match the type supplied
    # (see list_directly_contained_children() for a definition of what "directly contained" means here)
    def list_directly_contained_children_of_type(self, element_type):
        result = []

        for element in self.list_directly_contained_children():
            if isinstance(element, element_type):
                result.append(element)

        return result

    # Replace the direct child element given with one or more new children
    # Removes the child from any previous parent
    def replace_child(self, old_child, new_children):
        old_child.parent = None
        new_children.reverse()  # We're going to insert in backwards order
        for child_list in self.get_child_lists():
            for i in range(0, len(child_list)):
                if child_list[i] == old_child:
                    child_list.remove(old_child)
                    for new_child in new_children:
                        if new_child.parent is not None:
                            new_child.parent.remove_child(new_child)
                        child_list.insert(i, new_child)
                        new_child.parent = self
                    return
        raise Exception("Unable to find child to replace")

    # Insert children before the direct child element given
    # Removes the children from any previous parent
    def insert_before_child(self, existing_child, new_children):
        new_children.reverse()  # We're going to insert in backwards order
        for child_list in self.get_child_lists():
            for i in range(0, len(child_list)):
                if child_list[i] == existing_child:
                    for new_child in new_children:
                        if new_child.parent is not None:
                            new_child.parent.remove_child(new_child)
                        child_list.insert(i, new_child)
                        new_child.parent = self
                    return
        raise Exception("Unable to find child to insert after")

    # Insert children after the direct child element given
    # Removes the children from any previous parent
    def insert_after_child(self, existing_child, new_children):
        new_children.reverse()  # We're going to insert in backwards order
        for child_list in self.get_child_lists():
            for i in range(0, len(child_list)):
                if child_list[i] == existing_child:
                    for new_child in new_children:
                        if new_child.parent is not None:
                            new_child.parent.remove_child(new_child)
                        child_list.insert(i + 1, new_child)
                        new_child.parent = self
                    return
        raise Exception("Unable to find child to insert after")


# A #define statement
class DOMDefine(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['PPDEFINE'])
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMDefine()

        dom_element.tokens = [token]

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, collapse_tokens_to_string(self.tokens) + self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Define: " + str(self.tokens)


# A #undef statement
class DOMUndef(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        initial_token = stream.get_token_of_type(['PPUNDEF'])
        if initial_token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMUndef()

        # Tokens up until the line end are part of the expression
        while True:
            token = stream.get_token(skip_newlines=False)
            if token is None:
                break

            if token.type == 'NEWLINE':
                break

            dom_element.tokens.append(token)

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, "#undef " + collapse_tokens_to_string(self.tokens) +
                     self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Undef: " + collapse_tokens_to_string(self.tokens)


# A #if or #ifdef block (or #elif inside one)
class DOMPreprocessorIf(DOMElement):
    def __init__(self):
        super().__init__()
        self.is_ifdef = False
        self.is_elif = False
        self.is_negated = False
        self.is_include_guard = False  # Set externally, indicates if this was an added include guard
        self.expression_tokens = []
        self.else_children = []

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        initial_token = stream.get_token_of_type(['PPIFDEF', 'PPIFNDEF', 'PPIF', 'PPELIF'])
        if initial_token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMPreprocessorIf()

        dom_element.is_ifdef = (initial_token.type == 'PPIFDEF') or (initial_token.type == 'PPIFNDEF')
        dom_element.is_elif = initial_token.type == 'PPELIF'
        dom_element.is_negated = initial_token.type == 'PPIFNDEF'

        # Tokens up until the line end are part of the expression
        while True:
            token = stream.get_token(skip_newlines=False)
            if token is None:
                break

            if (token.type == 'LINE_COMMENT') or (token.type == 'BLOCK_COMMENT'):
                stream.rewind_one_token()
                dom_element.attached_comment = DOMComment.parse(context, stream)
                dom_element.attached_comment.is_attached_comment = True
                dom_element.attached_comment.parent = dom_element
            elif token.type == 'NEWLINE':
                break
            else:
                dom_element.expression_tokens.append(token)

        # Then we have the actual body of the conditional
        in_else = False

        while True:
            # "Peek" not "get" here because we need to parse the elif if it exists
            if stream.peek_token_of_type(['PPELIF']) is not None:
                # We expand elifs into a new if inside the else clause
                elif_clause = DOMPreprocessorIf.parse(context, stream)
                if elif_clause is None:
                    stream.rewind(checkpoint)
                    return None
                if not dom_element.no_default_add:
                    dom_element.add_child_to_else(elif_clause, context)
                break

            if stream.get_token_of_type(['PPELSE']) is not None:
                in_else = True

            if stream.get_token_of_type(['PPENDIF']) is not None:
                break

            child_element = context.current_content_parser()

            if child_element is not None:
                if not child_element.no_default_add:
                    if in_else:
                        dom_element.add_child_to_else(child_element, context)
                    else:
                        dom_element.add_child(child_element, context)
            else:
                print("Unrecognised element " + str(stream.peek_token()))
                break

        return dom_element

    # Returns true if this has the same condition (expression+flags) as another
    def condition_matches(self, other):
        return (self.get_expression() == other.get_expression()) and \
               (self.is_ifdef == other.is_ifdef) and \
               (self.is_elif == other.is_elif) and \
               (self.is_negated == other.is_negated)

    # Returns true if this is mutually exclusive with another condition
    # (i.e. it is impossible for both to be active at the same time)
    # Note that this currently only detects #ifdef/#ifndef pairs, not more complex expressions, nor does it check for
    # the effect of being in the else-side of a conditional
    def condition_is_mutually_exclusive(self, other):
        return (self.get_expression() == other.get_expression()) and \
               (self.is_ifdef == other.is_ifdef) and \
               (self.is_elif == other.is_elif) and \
               (self.is_negated != other.is_negated)

    # Get the expression used as a string
    def get_expression(self):
        return collapse_tokens_to_string(self.expression_tokens)

    # Get the opening clause as a string
    def get_opening_clause(self):
        if self.is_ifdef:
            if self.is_negated:
                return "#ifndef " + collapse_tokens_to_string(self.expression_tokens)
            else:
                return "#ifdef " + collapse_tokens_to_string(self.expression_tokens)
        else:
            return "#if " + collapse_tokens_to_string(self.expression_tokens)

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)

        opening_clause = self.get_opening_clause()
        write_c_line(file, 0, opening_clause)

        for child in self.children:
            child.write_to_c(file, indent, context)

        if len(self.else_children) > 0:
            write_c_line(file, 0, "#else")
            for child in self.else_children:
                child.write_to_c(file, indent, context)

        # If we don't have an existing attached comment, note the opening clause
        if self.attached_comment is not None:
            comment = self.get_attached_comment_as_c_string()
        else:
            comment = " // " + opening_clause

        write_c_line(file, 0, "#endif" + comment)

    # Add a new child to the else list of this element, optionally setting the last element information in the context
    def add_child_to_else(self, child, context=None):
        child.parent = self
        self.else_children.append(child)
        if context is not None:
            context.last_element = child

    # Remove a child from the else list of this element
    def remove_child_from_else(self, child):
        if child.parent is not self:
            raise Exception("Attempt to remove child from element other than parent")
        self.else_children.remove(child)
        child.parent = None

    def __is_preprocessor_container(self):
        return True

    def get_child_lists(self):
        lists = DOMElement.get_child_lists(self)
        lists.append(self.else_children)
        return lists

    def get_writable_child_lists(self):
        lists = DOMElement.get_writable_child_lists(self)
        lists.append(self.else_children)
        return lists

    def clone_without_children(self):
        temp_else_children = self.else_children
        self.else_children = []
        clone = DOMElement.clone_without_children(self)
        self.else_children = temp_else_children
        return clone

    def __str__(self):
        if self.is_ifdef:
            if self.is_negated:
                return "Ifndef: " + collapse_tokens_to_string(self.expression_tokens)
            else:
                return "Ifdef: " + collapse_tokens_to_string(self.expression_tokens)
        else:
            return "If: " + collapse_tokens_to_string(self.expression_tokens)

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + str(self))
        print("".ljust((indent + 1) * 4) + "If-block:")
        for child in self.children:
            child.dump(indent + 2)
        if len(self.else_children) > 0:
            print("".ljust((indent + 1) * 4) + "Else-block:")
            for child in self.else_children:
                child.dump(indent + 2)


# A #pragma
class DOMPragma(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['PRAGMA'])
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMPragma()

        # The pragma token contains the entire pragma body, so we don't need to do much here

        dom_element.tokens = [token]

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, collapse_tokens_to_string(self.tokens) + self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Pragma: " + str(self.tokens)

    def get_pragma_text(self):
        return collapse_tokens_to_string(self.tokens)


# A #error statement
class DOMError(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['PPERROR'])
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMError()

        # The error token contains the entire error body, so we don't need to do much here

        dom_element.tokens = [token]

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, collapse_tokens_to_string(self.tokens) + self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Error: " + str(self.tokens)


# A #include
class DOMInclude(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['PPINCLUDE'])
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMInclude()

        dom_element.tokens = [token]

        # Tokens up until the line end or line comment are part of the directive
        while True:
            token = stream.get_token(skip_newlines=False)
            if token is None:
                break

            if (token.type == 'NEWLINE') or (token.type == 'LINE_COMMENT'):
                break

            dom_element.tokens.append(token)

        return dom_element

    # Get the referred include file
    def get_include_file_name(self):
        # Skip token 0 as that is the #include itself
        return collapse_tokens_to_string(self.tokens[1:])

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, collapse_tokens_to_string(self.tokens) + self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Include: " + str(self.tokens)


# A blank line
class DOMBlankLines(DOMElement):
    def __init__(self, num_lines=0):
        super().__init__()
        self.num_blank_lines = num_lines

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['NEWLINE'], skip_newlines=False)
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMBlankLines()

        # Eat as many newlines as exist

        while stream.get_token_of_type(['NEWLINE'], skip_newlines=False):
            dom_element.num_blank_lines += 1

        dom_element.tokens.append(token)

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        if self.num_blank_lines > 0:
            newline_str = collapse_tokens_to_string_with_whitespace(self.tokens)
            for i in range(0, len(newline_str)):
                write_c_line(file, indent, "")

    def __str__(self):
        return "Blank lines: " + str(self.num_blank_lines)


# A generic unparsable... something
class DOMUnparsableThing(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['THING'])
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMUnparsableThing()

        dom_element.tokens.append(token)

        stream.get_token_of_type(['SEMICOLON'])  # Eat semicolons after unparsables

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, collapse_tokens_to_string(self.tokens) + self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Unparsable: " + str(self.tokens)


# Namespace
class DOMNamespace(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        token = stream.get_token_of_type(['NAMESPACE'])
        if token is None:
            stream.rewind(checkpoint)
            return None

        dom_element = DOMNamespace()

        name_token = stream.get_token()
        if name_token is None:
            stream.rewind(checkpoint)
            return None

        dom_element.name = name_token.value

        if stream.get_token_of_type(['LBRACE']) is None:
            stream.rewind(checkpoint)
            return None

        while True:
            tok = stream.peek_token()
            if tok.type == 'RBRACE':
                stream.get_token()  # Eat the closing brace
                stream.get_token_of_type(['SEMICOLON'])  # Eat the trailing semicolon too
                break

            child_element = context.current_content_parser()

            if child_element is not None:
                if not child_element.no_default_add:
                    dom_element.add_child(child_element, context)
            else:
                print("Unrecognised element: " + str(vars(tok)))
                break

        return dom_element

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        name = self.name
        if leaf_name != "":
            name += "::" + leaf_name
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(name, include_leading_colons)
        else:
            return ("::" if include_leading_colons else "") + name

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, "namespace " + self.name + self.get_attached_comment_as_c_string())
        write_c_line(file, indent, "{")
        for child in self.children:
            child.write_to_c(file, indent + 1, context)
        write_c_line(file, indent, "}")

    def __str__(self):
        return "Namespace: " + self.name


# A field declaration
class DOMFieldDeclaration(DOMElement):
    def __init__(self):
        super().__init__()
        self.field_type = None
        self.names = []
        self.is_static = False
        self.is_array = []  # One per name, because C
        self.width_specifiers = []  # One per name
        self.array_bounds_tokens = []  # One list of tokens per name
        self.is_imgui_api = False  # Does this use IMGUI_API?
        self.accessibility = None  # The field accessibility

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMFieldDeclaration()

        # Parse prefixes
        while True:
            prefix_token = stream.peek_token_of_type(["THING"])
            if prefix_token is None:
                break

            if prefix_token.value == 'IMGUI_API':
                stream.get_token()  # Eat token
                dom_element.is_imgui_api = True
            elif prefix_token.value == 'static':
                stream.get_token()  # Eat token
                dom_element.is_static = True
            else:
                break

        # Parse field type
        dom_element.field_type = DOMType.parse(context, stream)
        if dom_element.field_type is None:
            stream.rewind(checkpoint)
            return None
        dom_element.field_type.parent = dom_element

        if isinstance(dom_element.field_type, DOMFunctionPointerType):
            # Function pointers contain their own name
            dom_element.names.append(dom_element.field_type.name)
            dom_element.is_array.append(False)
            dom_element.array_bounds_tokens.append(None)
            dom_element.width_specifiers.append(None)

            stream.get_token_of_type(["SEMICOLON"])

            return dom_element
        else:
            while True:
                name_token = stream.get_token_of_type(["THING"])
                if name_token is None:
                    stream.rewind(checkpoint)
                    return None

                dom_element.tokens.append(name_token)
                dom_element.names.append(name_token.value)

                # Check for an array specifier

                if stream.get_token_of_type(["LSQUARE"]) is not None:
                    dom_element.is_array.append(True)
                    token_list = []
                    while True:
                        tok = stream.get_token()
                        if tok is None:
                            stream.rewind(checkpoint)
                            return None
                        if tok.type == 'RSQUARE':
                            break

                        token_list.append(tok)
                    dom_element.array_bounds_tokens.append(token_list)
                else:
                    dom_element.is_array.append(False)
                    dom_element.array_bounds_tokens.append(None)

                # Check for a width specifier

                if stream.get_token_of_type(['COLON']):
                    width_specifier_token = stream.get_token_of_type(['DECIMAL_LITERAL'])
                    if width_specifier_token is None:
                        stream.rewind(checkpoint)
                        return None
                    dom_element.width_specifiers.append(int(width_specifier_token.value))
                else:
                    dom_element.width_specifiers.append(None)

                separator_token = stream.get_token_of_type(["SEMICOLON", "COMMA"])
                if separator_token is None:
                    stream.rewind(checkpoint)
                    return None

                if separator_token.type == 'SEMICOLON':
                    # Field declaration finished
                    return dom_element

    def get_child_lists(self):
        lists = DOMElement.get_child_lists(self)
        if self.field_type is not None:
            lists.append([self.field_type])
        return lists

    def get_writable_child_lists(self):
        return DOMElement.get_writable_child_lists(self)

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(self.names[0] if len(self.names) > 0 else leaf_name,
                                                        include_leading_colons)
        else:
            return self.names[0] if len(self.names) > 0 else leaf_name

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        declaration = self.field_type.to_c_string(context)

        if self.is_imgui_api:
            if context.for_c:
                declaration = "CIMGUI_API " + declaration  # Use CIMGUI_API instead of IMGUI_API as our define here
            else:
                declaration = "IMGUI_API " + declaration

        if self.is_static:
            declaration = "static " + declaration

        # Function pointers have the name/etc included
        if not isinstance(self.field_type, DOMFunctionPointerType):
            first_name = True
            for i in range(0, len(self.names)):
                if first_name:
                    declaration += " "
                else:
                    declaration += ", "
                declaration += self.names[i]
                if self.is_array[i]:
                    declaration += "["
                    if self.array_bounds_tokens[i] is not None:
                        declaration += collapse_tokens_to_string(self.array_bounds_tokens[i])
                    declaration += "]"
                if self.width_specifiers[i] is not None:
                    declaration += " : " + str(self.width_specifiers[i])
                first_name = False

        write_c_line(file, indent, declaration + ";" + self.get_attached_comment_as_c_string())

    def __str__(self):
        result = "Field: Type=" + str(self.field_type) + " Names="
        for i in range(0, len(self.names)):
            result += " " + self.names[i]
            if self.is_array[i]:
                result += "["
                if self.array_bounds_tokens[i] is not None:
                    result += collapse_tokens_to_string(self.array_bounds_tokens[i])
                result += "]"
            if self.width_specifiers[i] is not None:
                result += " : " + str(self.width_specifiers[i])
        return result


# A single function argument
class DOMFunctionArgument(DOMElement):
    def __init__(self):
        super().__init__()
        self.arg_type = None
        self.name = None  # May be none as arguments can be unnamed
        self.default_value_tokens = None
        self.is_varargs = False
        self.is_array = False
        self.array_bounds = None

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMFunctionArgument()

        # First check for varargs (...) as an argument

        if stream.get_token_of_type(['ELLIPSES']) is not None:
            dom_element.is_varargs = True
            return dom_element

        # Type

        dom_element.arg_type = DOMType.parse(context, stream)
        if dom_element.arg_type is None:
            stream.rewind(checkpoint)
            return None
        dom_element.arg_type.parent = dom_element

        if isinstance(dom_element.arg_type, DOMFunctionPointerType):
            # Function pointers have a name specified as part of their declaration
            dom_element.name = dom_element.arg_type.name

        # Argument names are optional, so we have to check for that
        arg_name_token = stream.get_token_of_type(["THING", "COMMA", "RBRACKET"])

        if arg_name_token is not None:
            if arg_name_token.type == "COMMA" or arg_name_token.type == "RBRACKET":
                stream.rewind_one_token()
                return dom_element

            dom_element.name = arg_name_token.value

        # Check for an array specifier

        if stream.get_token_of_type(["LSQUARE"]) is not None:
            dom_element.is_array = True
            # Check for bounds (todo: support multiple bounds)
            tok = stream.get_token_of_type(['DECIMAL_LITERAL'])
            if tok is not None:
                dom_element.array_bounds = int(tok.value)
            if stream.get_token_of_type(["RSQUARE"]) is None:
                stream.rewind_one_token()
                return dom_element

        # Check for a default value

        if stream.get_token_of_type("EQUAL"):
            dom_element.default_value_tokens = []

            bracket_count = 1

            while True:
                token = stream.get_token()
                if token.type == "LPAREN":
                    bracket_count += 1
                elif token.type == "RPAREN":
                    bracket_count -= 1
                    if bracket_count == 0:
                        stream.rewind_one_token()
                        break
                elif token.type == "COMMA":
                    if bracket_count == 1:  # Comma at the top level terminates the expression
                        stream.rewind_one_token()
                        break

                dom_element.default_value_tokens.append(token)

        return dom_element

    def get_child_lists(self):
        lists = DOMElement.get_child_lists(self)
        if self.arg_type is not None:
            lists.append([self.arg_type])
        return lists

    def get_writable_child_lists(self):
        return DOMElement.get_writable_child_lists(self)

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(self.name, include_leading_colons)
        else:
            return self.name

    def to_c_string(self, context=WriteContext()):
        if self.is_varargs:
            return "..."
        result = self.arg_type.to_c_string(context)
        # Don't write the name if this is a function pointer, because the type declaration already includes the name
        if (self.name is not None) and not isinstance(self.arg_type, DOMFunctionPointerType):
            result += " " + str(self.name)
        if self.is_array:
            result += "[" + str(self.array_bounds or "") + "]"
        if (self.default_value_tokens is not None) and not context.for_implementation:
            if context.for_c:
                #  C doesn't support default arguments, so just include them as a comment
                result += " /* = " + collapse_tokens_to_string(self.default_value_tokens) + " */"
            else:
                result += " = " + collapse_tokens_to_string(self.default_value_tokens)
        return result

    def __str__(self):
        if self.is_varargs:
            return "Arg: ..."
        result = "Arg: Type=" + str(self.arg_type) + " Name=" + str(self.name)
        if self.is_array:
            result += " (array type)"
        if self.default_value_tokens is not None:
            result += " Default=" + collapse_tokens_to_string(self.default_value_tokens)
        return result


# A code block
class DOMCodeBlock(DOMElement):
    def __init__(self):
        super().__init__()
        self.tokens = []
        self.code_on_different_line_to_braces = False

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMCodeBlock()

        # Opening brace

        if stream.get_token_of_type(['LBRACE']) is None:
            stream.rewind(checkpoint)
            return None

        # If there's a newline after the brace, record that fact so we can format the block appropriately when
        # writing it
        if stream.get_token_of_type('NEWLINE', skip_newlines=False) is not None:
            dom_element.code_on_different_line_to_braces = True

        # Eat all tokens until a matching closing brace
        brace_count = 1

        while True:
            # We turn off skip_newlines/skip_whitespace here to preserve the original code formatting
            token = stream.get_token(skip_newlines=False, skip_whitespace=False)
            if token.type == 'LBRACE':
                brace_count += 1
            elif token.type == 'RBRACE':
                brace_count -= 1
                if brace_count == 0:
                    break
            dom_element.tokens.append(token)

        return dom_element

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        if self.code_on_different_line_to_braces:
            write_c_line(file, indent, "{")
            write_c_line(file, indent + 1, collapse_tokens_to_string_with_whitespace(self.tokens))
            write_c_line(file, indent, "};" + self.get_attached_comment_as_c_string())
        else:
            write_c_line(file, indent + 1, "{ " + collapse_tokens_to_string_with_whitespace(self.tokens) + " }"
                         + self.get_attached_comment_as_c_string())

    def __str__(self):
        return "CodeBlock: Length=" + str(len(self.tokens))


# A function declaration
class DOMFunctionDeclaration(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None
        self.return_type = None
        self.arguments = []
        self.initialiser_list_tokens = None  # List of tokens making up the initialiser list if one exists
        self.body = None
        self.is_const = False
        self.is_static = False
        self.is_inline = False
        self.is_operator = False
        self.is_constructor = False
        self.is_by_value_constructor = False  # Is this a by-value type constructor? (set during flattening)
        self.is_destructor = False
        self.is_imgui_api = False
        self.im_fmtargs = None
        self.im_fmtlist = None
        self.accessibility = None  # The function accessibility (if part of a class)
        self.original_class = None  # The class this function belonged to pre-flattening
        #                             (set when functions are flattened)

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMFunctionDeclaration()

        # Parse prefixes
        while True:
            prefix_token = stream.peek_token_of_type(["THING"])
            if prefix_token is None:
                break

            if prefix_token.value == 'IMGUI_API':
                stream.get_token()  # Eat token
                dom_element.is_imgui_api = True
            elif prefix_token.value == 'inline':
                stream.get_token()  # Eat token
                dom_element.is_inline = True
            elif prefix_token.value == 'static':
                stream.get_token()  # Eat token
                dom_element.is_static = True
            elif prefix_token.value == 'operator':
                # Copy constructors can look like this "operator ImVec4() const;" and thus have "operator" as a prefix
                stream.get_token()  # Eat token
                dom_element.is_operator = True
            else:
                break

        # Check for a leading ~ as used on destructors
        name_prefix = ""
        leading_tilde = stream.get_token_of_type(["~"])
        if leading_tilde is not None:
            dom_element.tokens.append(leading_tilde)
            name_prefix = leading_tilde.value
            dom_element.is_destructor = True

        # Because constructors/destructors have no return type declaration, we need to peek ahead to see if the first
        # token is a type or the function name

        has_no_return_type = False
        name_token = stream.get_token_of_type(["THING"])
        if name_token is not None:
            if stream.peek_token_of_type(["LPAREN"]) is not None:
                # If we see a name-like-thing followed by a bracket, we assume this is a return-type-less function
                has_no_return_type = True
            stream.rewind_one_token()

        # If it has no return type and hasn't already been identified as a destructor, it must be a constructor
        if has_no_return_type and not dom_element.is_destructor:
            dom_element.is_constructor = True

        # Return type

        if not has_no_return_type:
            dom_element.return_type = DOMType.parse(context, stream)
            if dom_element.return_type is None:
                stream.rewind(checkpoint)
                return None
            dom_element.return_type.parent = dom_element

        # Function name

        name_token = stream.get_token_of_type(["THING"])
        if name_token is None:
            stream.rewind(checkpoint)
            return None
        dom_element.tokens.append(name_token)

        if name_token.value == "operator":
            # If we got "operator" then we need to read the real name from the next tokens too
            # (tokens because of things like "operator[]" and "operator*=")

            operator_name_tokens = []
            while True:
                next_token = stream.get_token()
                if next_token is None:
                    stream.rewind(checkpoint)
                    return None
                if next_token.type == 'LPAREN':
                    #  We found the opening parentheses
                    stream.rewind_one_token()  # Give this back as we want to parse it in a moment
                    break
                else:
                    operator_name_tokens.append(next_token)
            dom_element.is_operator = True

            dom_element.name = "operator " + name_prefix + collapse_tokens_to_string(operator_name_tokens)
        else:
            dom_element.name = name_prefix + name_token.value

        # Arguments

        if stream.get_token_of_type(["LPAREN"]) is None:
            # Not a valid function declaration
            stream.rewind(checkpoint)
            return None

        while True:
            # Check if we've reached the end of the argument list
            if stream.get_token_of_type(['RPAREN']) is not None:
                break

            arg = DOMFunctionArgument.parse(context, stream)
            if arg is None:
                stream.rewind(checkpoint)
                return None

            dom_element.add_argument(arg)

            # Eat any trailing comma
            stream.get_token_of_type(["COMMA"])

        # Check for function declaration suffix

        if stream.get_token_of_type(['CONST']) is not None:
            dom_element.is_const = True

        # Check for IM_FMTARGS()

        if (stream.peek_token() is not None) and (stream.peek_token().value == 'IM_FMTARGS'):
            stream.get_token()  # Eat token
            if stream.get_token_of_type(['LPAREN']) is None:
                stream.rewind(checkpoint)
                return None
            dom_element.im_fmtargs = stream.get_token().value
            if stream.get_token_of_type(['RPAREN']) is None:
                stream.rewind(checkpoint)
                return None

        # Check for IM_FMTLIST()

        if (stream.peek_token() is not None) and (stream.peek_token().value == 'IM_FMTLIST'):
            stream.get_token()  # Eat token
            if stream.get_token_of_type(['LPAREN']) is None:
                stream.rewind(checkpoint)
                return None
            dom_element.im_fmtlist = stream.get_token().value
            if stream.get_token_of_type(['RPAREN']) is None:
                stream.rewind(checkpoint)
                return None

        # Possible attached comment
        # (this is kinda hacky as there are a bunch of places comments can legitimately be that aren't properly parsed
        # at the moment, but it'll do and this is arguably a valid special case as we want to treat a comment here
        # as attached to the function rather than part of the body)

        attached_comment = stream.get_token_of_type(["LINE_COMMENT", "BLOCK_COMMENT"])
        if attached_comment is not None:
            stream.rewind_one_token()
            dom_element.attached_comment = DOMComment.parse(context, stream)
            dom_element.attached_comment.is_attached_comment = True
            dom_element.attached_comment.parent = dom_element

        # Possible initialiser list

        initialiser_list_opener = stream.get_token_of_type(["COLON"])
        if initialiser_list_opener is not None:
            dom_element.initialiser_list_tokens = []
            dom_element.initialiser_list_tokens.append(initialiser_list_opener)

            while True:
                tok = stream.get_token()

                if tok.type == 'LBRACE':
                    # Start of code block
                    stream.rewind_one_token()
                    break
                elif tok.type == 'SEMICOLON':
                    # End of declaration
                    stream.rewind_one_token()
                    break
                else:
                    dom_element.initialiser_list_tokens.append(tok)

        # Possible body

        body_opener = stream.get_token_of_type(["LBRACE", "SEMICOLON"])
        if body_opener is None:
            stream.rewind(checkpoint)
            return None

        if body_opener.type == 'LBRACE':
            stream.rewind_one_token()
            dom_element.body = DOMCodeBlock.parse(context, stream)

        # print(dom_element)
        return dom_element

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False,
                                 return_fqn_even_for_member_functions=False):
        if self.parent is not None:
            # When referring to non-static class member functions we use the leaf name (as the class name is supplied
            # by the instance)
            if (self.get_parent_class() is not None) and not self.is_static and \
                    not return_fqn_even_for_member_functions:
                return self.name
            return self.parent.get_fully_qualified_name(self.name, include_leading_colons)
        else:
            return self.name

    # Add a new argument to this element
    def add_argument(self, child):
        child.parent = self
        self.arguments.append(child)

    # Remove an argument from this element
    def remove_argument(self, child):
        if child.parent is not self:
            raise Exception("Attempt to remove argument from element other than parent")
        self.arguments.remove(child)
        child.parent = None

    def get_child_lists(self):
        lists = DOMElement.get_child_lists(self)
        lists.append(self.arguments)
        if self.return_type is not None:
            lists.append([self.return_type])
        return lists

    def get_writable_child_lists(self):
        lists = DOMElement.get_writable_child_lists(self)
        lists.append(self.arguments)
        return lists

    def clone(self):
        # We don't want to clone the original class, but just keep a shallow reference to it
        old_original_class = self.original_class
        self.original_class = None
        clone = DOMElement.clone(self)
        self.original_class = old_original_class
        clone.original_class = old_original_class
        return clone

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        declaration = ""
        if self.is_imgui_api:
            if context.for_c:
                declaration += "CIMGUI_API "  # Use CIMGUI_API instead of IMGUI_API as our define here
            else:
                declaration += "IMGUI_API "
        if self.is_static and (not context.for_implementation):
            declaration += "static "
        if self.is_inline and (not context.for_implementation):
            declaration += "inline "
        if self.return_type is not None:
            declaration += self.return_type.to_c_string(context) + " "
        if context.for_implementation:
            declaration += str(self.get_fully_qualified_name()) + "("
        else:
            declaration += str(self.name) + "("
        if len(self.arguments) > 0:
            first_arg = True
            for arg in self.arguments:
                if not first_arg:
                    declaration += ", "
                declaration += arg.to_c_string(context)
                first_arg = False
        else:
            if context.for_c:
                declaration += "void"  # Explicit void for C
        declaration += ")"
        if self.is_const:
            declaration += " const"
        if not context.for_implementation:
            if self.im_fmtargs is not None:
                declaration += " IM_FMTARGS(" + self.im_fmtargs + ")"
            if self.im_fmtlist is not None:
                declaration += " IM_FMTLIST(" + self.im_fmtlist + ")"

        if context.for_implementation:
            write_c_line(file, indent, declaration)
        else:
            if self.body is not None:
                write_c_line(file, indent, declaration + self.get_attached_comment_as_c_string())
                if self.initialiser_list_tokens is not None:
                    write_c_line(file, indent, collapse_tokens_to_string(self.initialiser_list_tokens))
                self.body.write_to_c(file, indent, context)  # No +1 here because we want the body braces at our level
            else:
                write_c_line(file, indent, declaration + ";" + self.get_attached_comment_as_c_string())

    def __str__(self):
        result = "Function: Return type=" + str(self.return_type) + " Name=" + str(self.name)
        if len(self.arguments) > 0:
            result += " Arguments="
            for arg in self.arguments:
                result += " [" + str(arg) + "]"
        result += " Body=" + str(self.body)
        if self.is_const:
            result += " Const"
        if self.is_inline:
            result += " Inline"
        if self.is_static:
            result += " Static"
        if self.is_imgui_api:
            result += " IMGUI_API"
        if self.im_fmtargs is not None:
            result += " IM_FMTARGS(" + self.im_fmtargs + ")"
        if self.im_fmtlist is not None:
            result += " IM_FMTLIST(" + self.im_fmtlist + ")"
        return result


# A function pointer type
class DOMFunctionPointerType(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None
        self.return_type = None
        self.arguments = []

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMFunctionPointerType()

        # Return type
        # *Technically* there's nothing stopping someone declaring a function pointer that returns a function
        # pointer, but that generates an annoying infinite loop in the parsing here so we'll disallow it for now

        dom_element.return_type = DOMType.parse(context, stream, allow_function_pointer=False)
        if dom_element.return_type is None:
            stream.rewind(checkpoint)
            return None
        dom_element.return_type.parent = dom_element

        # We expect a bracket and asterisk before the name

        if stream.get_token_of_type(["LPAREN"]) is None:
            stream.rewind(checkpoint)
            return None

        if stream.get_token_of_type(["ASTERISK"]) is None:
            stream.rewind(checkpoint)
            return None

        # Function name

        name_token = stream.get_token_of_type(["THING"])
        if name_token is None:
            stream.rewind(checkpoint)
            return None
        dom_element.name = name_token.value

        # Closing bracket

        if stream.get_token_of_type(["RPAREN"]) is None:
            stream.rewind(checkpoint)
            return None

        # Arguments

        if stream.get_token_of_type(["LPAREN"]) is None:
            # Not a valid function declaration
            stream.rewind(checkpoint)
            return None

        while True:
            # Check if we've reached the end of the argument list
            if stream.get_token_of_type(['RPAREN']) is not None:
                break

            arg = DOMFunctionArgument.parse(context, stream)
            if arg is None:
                stream.rewind(checkpoint)
                return None

            arg.parent = dom_element
            dom_element.arguments.append(arg)

            # Eat any trailing comma
            stream.get_token_of_type(["COMMA"])

        # print(dom_element)
        return dom_element

    def get_child_lists(self):
        lists = DOMElement.get_child_lists(self)
        lists.append(self.arguments)
        if self.return_type is not None:
            lists.append([self.return_type])
        return lists

    def get_writable_child_lists(self):
        lists = DOMElement.get_writable_child_lists(self)
        lists.append(self.arguments)
        return lists

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(self.name, include_leading_colons)
        else:
            return self.name

    # Returns true if this type is const
    def is_const(self):
        return False  # Not implemented

    def get_primary_type_name(self):
        return "FnPtr"

    def to_c_string(self, context=WriteContext()):
        result = self.return_type.to_c_string(context) + " (*" + str(self.name) + ")("
        if len(self.arguments) > 0:
            first_arg = True
            for arg in self.arguments:
                if not first_arg:
                    result += ", "
                result += arg.to_c_string(context)
                first_arg = False
        result += ")"
        return result

    def __str__(self):
        result = "Function pointer: Return type=" + str(self.return_type) + " Name=" + str(self.name)
        if len(self.arguments) > 0:
            result += " Arguments="
            for arg in self.arguments:
                result += " [" + str(arg) + "]"
        return result


# A type, represented by a sequence of tokens that define it
class DOMType(DOMElement):
    def __init__(self):
        super().__init__()

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream, allow_function_pointer=True):

        if allow_function_pointer:
            # Types may be a function pointer, so check for that first

            dom_element = DOMFunctionPointerType.parse(context, stream)
            if dom_element is not None:
                return dom_element

        # If it wasn't a function pointer, it's probably a normal type

        checkpoint = stream.get_checkpoint()
        dom_element = DOMType()
        have_valid_type = False
        while True:
            tok = stream.get_token_of_type(['THING', 'ASTERISK', 'AMPERSAND', 'CONST', 'SIGNED', 'UNSIGNED',
                                            'LSQUARE', 'LTRIANGLE', 'COLON'])
            if tok is None:
                if not have_valid_type:
                    stream.rewind(checkpoint)
                    return None
                else:
                    # We have a valid type
                    return dom_element

            if have_valid_type:
                if tok.type == 'LSQUARE':
                    # Array indicator
                    dom_element.tokens.append(tok)
                    # Check for bounds (todo: support multiple bounds)
                    tok = stream.get_token_of_type(['DECIMAL_LITERAL'])
                    if tok is not None:
                        dom_element.tokens.append(tok)
                    tok = stream.get_token_of_type(['RSQUARE'])
                    if tok is None:
                        # Malformed array bounds
                        print("Expected ] to terminate array bounds")
                        stream.rewind(checkpoint)
                        return None
                    dom_element.tokens.append(tok)
                elif tok.type == 'LTRIANGLE':
                    # Template parameters
                    dom_element.tokens.append(tok)
                    brace_count = 1

                    while True:
                        token = stream.get_token()
                        dom_element.tokens.append(token)
                        if token.type == 'LTRIANGLE':
                            brace_count += 1
                        elif token.type == 'RTRIANGLE':
                            brace_count -= 1
                            if brace_count == 0:
                                break
                elif (tok.type == 'ASTERISK') or (tok.type == 'AMPERSAND') or (tok.type == 'CONST'):
                    # Type suffix
                    dom_element.tokens.append(tok)
                elif tok.type == 'COLON':
                    # Namespace separator
                    dom_element.tokens.append(tok)
                    have_valid_type = False  # Go back to the state of expecting a type name
                elif tok.value == 'long':
                    # "long long" is... a thing :-(
                    dom_element.tokens.append(tok)
                else:
                    # Something else, so stop here
                    stream.rewind_one_token()
                    return dom_element
            else:
                if (tok.type == 'CONST') or (tok.type == 'SIGNED') or (tok.type == 'UNSIGNED'):
                    # Type prefix
                    dom_element.tokens.append(tok)
                elif tok.type == 'COLON':
                    # Leading namespace separator
                    dom_element.tokens.append(tok)
                else:
                    # Type name
                    dom_element.tokens.append(tok)
                    have_valid_type = True

    # Returns true if this type is const
    # (very conservative - considers the type const if const appears anywhere in it)
    def is_const(self):
        for tok in self.tokens:
            if tok.type == 'CONST':
                return True
        return False

    # Gets the "primary" type name involved (i.e. without any prefixes or suffixes)
    # This is mostly useful for trying to construct overload disambiguation suffixes
    def get_primary_type_name(self):
        primary_name = None
        triangle_bracket_count = 0
        for tok in self.tokens:
            if (tok.type == 'ASTERISK') or (tok.type == 'AMPERSAND') or (tok.type == 'CONST') \
                    or (tok.type == 'SIGNED') or (tok.type == 'UNSIGNED'):
                continue  # These are never the type name
            elif tok.type == 'LTRIANGLE':
                triangle_bracket_count += 1
            elif tok.type == 'RTRIANGLE':
                triangle_bracket_count -= 1

            if triangle_bracket_count == 0:
                primary_name = tok.value  # We use the last of the "name-like" things we see
        return primary_name

    # Gets the fully-qualified name (C++-style) of this element (including namespaces/etc)
    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        context = WriteContext()
        context.include_leading_colons=include_leading_colons
        return self.to_c_string(context)

    def to_c_string(self, context=WriteContext()):
        # Return the original name if requested
        if context.use_original_names:
            if self.original_name_override is not None:
                return self.original_name_override
            elif self.unmodified_element is not None:
                return self.unmodified_element.to_c_string(context)

        if context.include_leading_colons:
            # Add leading colons to anything that looks like a user type
            fudged_tokens = []
            for tok in self.tokens:
                new_tok = copy.deepcopy(tok)
                if new_tok.type == 'THING':
                    new_tok.value = "::" + new_tok.value
                fudged_tokens.append(new_tok)
            return collapse_tokens_to_string(fudged_tokens)
        else:
            return collapse_tokens_to_string(self.tokens)

    def __str__(self):
        result = "Type: " + collapse_tokens_to_string(self.tokens)
        if self.original_name_override is not None:
            result += " (original name " + self.original_name_override + ")"
        return result


# A single header file
class DOMHeaderFile(DOMElement):
    def __init__(self):
        super().__init__()
        self.filename = None  # The filename this header came from (or will be saved as)

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        dom_element = DOMHeaderFile()

        # Set up the default context parser
        old_content_parser = context.current_content_parser
        context.current_content_parser = lambda: DOMHeaderFile.parse_content(context, stream)

        while True:
            child_element = context.current_content_parser()

            if child_element is not None:
                if not child_element.no_default_add:
                    dom_element.add_child(child_element, context)
            else:
                break

        dom_element.parse_content(context, stream)

        context.current_content_parser = old_content_parser

        return dom_element

    @staticmethod
    def parse_content(context, stream):
        return DOMElement.parse_basic(context, stream)

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        for child in self.children:
            child.write_to_c(file, indent=indent, context=context)

    def __str__(self):
        if self.filename is not None:
            return "Header file: " + self.filename
        else:
            return "Header file"


# A collection of header files
class DOMHeaderFileSet(DOMElement):
    def __init__(self):
        super().__init__()

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        for child in self.children:
            child.write_to_c(file, indent=indent, context=context)

    def __str__(self):
        return "Header file set"


class DOMComment(DOMElement):
    def __init__(self):
        super().__init__()
        self.comment_text = None
        self.is_attached_comment = False
        self.is_preceding_comment = False

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        dom_element = DOMComment()
        tok = stream.get_token_of_type(['LINE_COMMENT', 'BLOCK_COMMENT'])
        dom_element.tokens = [tok]
        dom_element.comment_text = tok.value
        # print("Comment: " + dom_element.commentText)

        # If this comment appeared immediately after another element on the same line, attach it
        if tok.type == 'LINE_COMMENT' and context.last_element is not None \
                and not isinstance(context.last_element, DOMComment) \
                and not isinstance(context.last_element, DOMBlankLines):
            context.last_element.attached_comment = dom_element
            dom_element.is_attached_comment = True
            dom_element.parent = context.last_element
            dom_element.no_default_add = True  # Suppress the normal add behaviour as we have added the element here

        return dom_element

    def to_c_string(self):
        return self.comment_text

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        if context.for_implementation:
            return  # No comments in implementation code
        # Attached/preceding comments are written by their attached element
        if not self.is_attached_comment and not self.is_preceding_comment:
            write_c_line(file, indent, self.comment_text)

    def __str__(self):
        if self.is_attached_comment or self.is_preceding_comment:
            return "Attached/preceding comment: " + self.comment_text
        else:
            return "Comment: " + self.comment_text


# Class/struct/union
class DOMClassStructUnion(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None  # Can be none for anonymous things
        self.is_forward_declaration = True
        self.is_by_value = False  # Is this to be passed by value? (set during modification)
        self.structure_type = None  # Will be "STRUCT", "CLASS" or "UNION"
        self.is_imgui_api = False  # Does this use IMGUI_API?
        self.base_classes = None  # List of base classes, as tuples with their accessibility (i.e. ("private", "CBase"))

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        dom_element = DOMClassStructUnion()
        tok = stream.get_token_of_type(['STRUCT', 'CLASS', 'UNION'])
        dom_element.structure_type = tok.type

        name_tok = stream.get_token_of_type(['THING'])
        if name_tok is not None:
            dom_element.name = name_tok.value

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

        # print("Struct/Class/Union: " + dom_element.structure_type + " : " + (dom_element.name or "Anonymous"))

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
                child_element.accessibility = current_accessibility

                if child_element is not None:
                    if not child_element.no_default_add:
                        dom_element.add_child(child_element, context)
                else:
                    print("Unrecognised element: " + str(vars(tok)))
                    break

        stream.get_token_of_type(['SEMICOLON'])  # Eat the trailing semicolon

        return dom_element

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        name = self.name or "anonymous"
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

        if context.for_c and (self.name is not None):
            declaration += "typedef "

        if self.structure_type == "STRUCT":
            declaration += "struct"
        elif self.structure_type == "CLASS":
            declaration += "class"
        elif self.structure_type == "UNION":
            declaration += "union"
        else:
            raise Exception("Unsupported struct/class/union type")

        if self.name is not None:
            declaration += " " + self.name

        # Add base classes
        if self.base_classes is not None:
            is_first = True
            for accessibility, class_name in self.base_classes:
                declaration += " : " if is_first else ", "
                declaration += accessibility + " " + class_name

        if not self.is_forward_declaration:
            write_c_line(file, indent, declaration + self.get_attached_comment_as_c_string())
            write_c_line(file, indent, "{")
            for child in self.children:
                child.write_to_c(file, indent + 1, context)
            if context.for_c and (self.name is not None):
                write_c_line(file, indent, "} " + self.name + ";")
            else:
                write_c_line(file, indent, "};")
        else:
            # Forward-declarations need to be C++-compatible, so we have this ugliness
            # Todo: Less ugliness

            if context.for_c:
                write_c_line(file, 0, "#ifdef __cplusplus")
                self.write_to_c(file, indent)  # Write C++-compatible declaration
                write_c_line(file, 0, "#else")

            if context.for_c and (self.name is not None):
                write_c_line(file, indent, declaration + " " + self.name + ";" +
                             self.get_attached_comment_as_c_string())
            else:
                write_c_line(file, indent, declaration + ";" + self.get_attached_comment_as_c_string())

            if context.for_c:
                write_c_line(file, 0, "#endif")

    def __str__(self):
        if self.name is not None:
            return self.structure_type + ": " + self.name
        else:
            return self.structure_type


class DOMTypedef(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None
        self.type = None

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        if stream.get_token_of_type(['TYPEDEF']) is None:
            return None

        dom_element = DOMTypedef()

        dom_element.type = DOMType.parse(context, stream)
        if dom_element.type is None:
            stream.rewind(checkpoint)
            return None
        dom_element.type.parent = dom_element

        if isinstance(dom_element.type, DOMFunctionPointerType):
            # Function pointers have the name as part of the declaration
            dom_element.name = dom_element.type.name
        else:
            name_tok = stream.get_token_of_type(['THING'])
            if name_tok is None:
                stream.rewind(checkpoint)
                return None
            dom_element.name = name_tok.value

        stream.get_token_of_type(['SEMICOLON'])  # Eat the trailing semicolon

        return dom_element

    def get_child_lists(self):
        lists = DOMElement.get_child_lists(self)
        if self.type is not None:
            lists.append([self.type])
        return lists

    def get_writable_child_lists(self):
        return DOMElement.get_writable_child_lists(self)

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(self.name, include_leading_colons)
        else:
            return self.name

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)

        # Function pointers have the name/etc included
        if isinstance(self.type, DOMFunctionPointerType):
            write_c_line(file, indent, "typedef " + self.type.to_c_string() + ";" +
                         self.get_attached_comment_as_c_string())
        else:
            write_c_line(file, indent, "typedef " + self.type.to_c_string() + " " + self.name + ";" +
                         self.get_attached_comment_as_c_string())

    def __str__(self):
        return "Typedef: " + self.name + " type=" + str(self.type)


class DOMEnumElement(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None
        self.value_tokens = None

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        dom_element = DOMEnumElement()

        # It's possible to have a comment here in very rare cases that we don't have a good way to deal with, so
        # for now eat it
        stream.get_token_of_type(['LINE_COMMENT', 'BLOCK_COMMENT'])

        name_tok = stream.get_token_of_type(['THING'])
        if name_tok is None:
            stream.rewind(checkpoint)
            return None

        dom_element.name = name_tok.value

        if stream.get_token_of_type(['EQUAL']) is not None:
            # We have a value
            dom_element.value_tokens = []
            while True:
                tok = stream.get_token(skip_newlines=False)
                # This is a fudge - enum elements can span multiple lines, but we have cases where the comma is inside
                # a #ifdef block on a new line, which causes chaos if we don't break out of the item parser before then
                if tok.type == 'NEWLINE':
                    stream.rewind_one_token(skip_newlines=False)
                    break
                # The same fudge as above is necessary for line comments
                if tok.type == 'LINE_COMMENT':
                    stream.rewind_one_token(skip_newlines=False)
                    break
                if tok.type == 'RBRACE':
                    stream.rewind_one_token(skip_newlines=False)  # Leave the brace for the enum itself to parse
                    break
                if tok.type == 'COMMA':
                    # We're going to eat this in a second, but we don't want to accidentally eat two commas
                    stream.rewind_one_token(skip_newlines=False)
                    break

                dom_element.value_tokens.append(tok)

        stream.get_token_of_type(['COMMA'])  # Eat any trailing comma
        return dom_element

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.parent is not None:
            return self.parent.get_fully_qualified_name(self.name, include_leading_colons)
        else:
            return self.name

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        if self.value_tokens is not None:
            write_c_line(file, indent, self.name + " = " + collapse_tokens_to_string(self.value_tokens) + "," +
                         self.get_attached_comment_as_c_string())
        else:
            write_c_line(file, indent, self.name + "," + self.get_attached_comment_as_c_string())

    def __str__(self):
        if self.value_tokens is None:
            return "EnumElement: " + self.name
        else:
            return "EnumElement: " + self.name + " Value:" + collapse_tokens_to_string(self.value_tokens)


class DOMEnum(DOMElement):
    def __init__(self):
        super().__init__()
        self.name = None
        self.is_enum_class = False

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()
        dom_element = DOMEnum()
        tok = stream.get_token_of_type(['ENUM'])

        if stream.get_token_of_type(['CLASS']):
            dom_element.is_enum_class = True

        name_tok = stream.get_token_of_type(['THING'])

        dom_element.tokens = [tok, name_tok]

        dom_element.name = name_tok.value

        # We need a custom content parser from enums
        old_content_parser = context.current_content_parser
        context.current_content_parser = lambda: DOMEnum.parse_content(context, stream)

        if stream.get_token_of_type(['LBRACE']) is not None:
            while True:
                tok = stream.peek_token()
                if tok.type == 'RBRACE':
                    stream.get_token()  # Eat the closing brace
                    break

                element = context.current_content_parser()

                if element is not None:
                    if not element.no_default_add:
                        dom_element.add_child(element, context)
                else:
                    stream.rewind(checkpoint)
                    return None

        context.current_content_parser = old_content_parser

        stream.get_token_of_type(['SEMICOLON'])  # Eat the trailing semicolon

        return dom_element

    @staticmethod
    def parse_content(context, stream):
        # Allow common element types (comments/etc)
        common_element = DOMElement.parse_common(context, stream)
        if common_element is not None:
            return common_element

        # Eat commas - technically we shouldn't really need to do this but there are some constructs involving
        # #ifdefs inside enums that are hard to parse "correctly" without it
        stream.get_token_of_type(['COMMA'])

        # Anything not a common element type must be an enum element
        element = DOMEnumElement.parse(context, stream)

        if element is not None:
            return element
        else:
            return None

    def get_fully_qualified_name(self, leaf_name="", include_leading_colons=False):
        if self.is_enum_class:
            # Namespaced "enum class" enum
            name = self.name
            if leaf_name != "":
                name += "::" + leaf_name
            if self.parent is not None:
                return self.parent.get_fully_qualified_name(name, include_leading_colons)
            else:
                return name
        else:
            # Non-namespaced old-style enum
            if self.parent is not None:
                return ("::" if include_leading_colons else "") + \
                       self.parent.get_fully_qualified_name(self.name, include_leading_colons)
            else:
                return ("::" if include_leading_colons else "") + self.name

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, "enum " + self.name + self.get_attached_comment_as_c_string())
        write_c_line(file, indent, "{")
        for child in self.children:
            child.write_to_c(file, indent + 1, context)
        write_c_line(file, indent, "};")

    def __str__(self):
        return "Enum: " + self.name


class DOMTemplate(DOMElement):
    def __init__(self):
        super().__init__()
        self.template_parameter_tokens = []

    # Parse tokens from the token stream given
    @staticmethod
    def parse(context, stream):
        checkpoint = stream.get_checkpoint()

        if stream.get_token_of_type(['TEMPLATE']) is None:
            stream.rewind(checkpoint)
            return

        dom_element = DOMTemplate()

        if stream.get_token_of_type(['LTRIANGLE']) is None:
            stream.rewind(checkpoint)
            return

        # Now we expect a list of parameters, terminated with a >

        brace_count = 1

        while True:
            token = stream.get_token()
            if token.type == 'LTRIANGLE':
                brace_count += 1
            elif token.type == 'RTRIANGLE':
                brace_count -= 1
                if brace_count == 0:
                    break
            dom_element.template_parameter_tokens.append(token)

        # The next thing will either be a struct or a function

        while True:
            # Allow common element types (comments/etc)
            common_element = DOMElement.parse_common(context, stream)
            if common_element is not None:
                if not common_element.no_default_add:
                    dom_element.add_child(common_element, context)
            else:
                tok = stream.peek_token()

                if (tok.type == 'STRUCT') or (tok.type == 'CLASS'):
                    element = DOMClassStructUnion.parse(context, stream)

                    if element is None:
                        stream.rewind(checkpoint)
                        return None

                    if not element.no_default_add:
                        dom_element.add_child(element, context)
                else:
                    element = DOMFunctionDeclaration.parse(context, stream)

                    if element is None:
                        stream.rewind(checkpoint)
                        return None

                    if not element.no_default_add:
                        dom_element.add_child(element, context)

                # template<> only has a single (non-comment-like) child, so stop here
                break

        return dom_element

    # Get the class/function this template is for
    def get_templated_object(self):
        for child in self.children:
            if isinstance(child, DOMClassStructUnion) or isinstance(child, DOMFunctionDeclaration):
                return child
        return None

    # Write this element out as C code
    def write_to_c(self, file, indent=0, context=WriteContext()):
        self.write_preceding_comments(file, indent, context)
        write_c_line(file, indent, "template <" + collapse_tokens_to_string(self.template_parameter_tokens) + ">" +
                     self.get_attached_comment_as_c_string())
        for child in self.children:
            child.write_to_c(file, indent, context)

    def __str__(self):
        return "Template: " + collapse_tokens_to_string(self.template_parameter_tokens)
