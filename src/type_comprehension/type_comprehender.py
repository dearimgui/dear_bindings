from src import type_comprehension

# This takes a C type as a string and builds a description of it in machine-usable form


# Check if c is considered whitespace
def is_whitespace(c):
    return (c == ' ') or (c == '\t') or (c == '\n') or (c == '\r')


# Extract a single word from instr and return it along with the new current position in the string
def extract_word(instr, current):
    result = ''

    # Skip whitespace
    while current < len(instr):
        if is_whitespace(instr[current]):
            current += 1
        else:
            break

    while current < len(instr):
        c = instr[current]
        if ((c >= 'a') and (c <= 'z')) or \
                ((c >= 'A') and (c <= 'Z')) or \
                ((c >= '0') and (c <= '9')) or \
                (c == '_') or (c == ':') or (c == '.') or (c == '<') or (c == '>'):
            result += c
            current += 1
        else:
            break
    return result, current


# Extract characters until a given terminator character is reached, then return
# the extracted characters along with the new current position in the string
def extract_until_char(instr, current, terminator):
    result = ''

    # Skip whitespace
    while current < len(instr):
        if is_whitespace(instr[current]):
            current += 1
        else:
            break

    while current < len(instr):
        c = instr[current]
        if c != terminator:
            result += c
            current += 1
        else:
            break
    return result, current


# Add a type to the end of the current type chain
def chain_type(current_type, new_type):
    if current_type is not None:
        if isinstance(current_type, type_comprehension.TCFunction):
            # Functions are a special case where chaining binds to their return type
            current_type.return_type = new_type
        else:
            current_type.target = new_type
    new_type.parent = current_type
    current_type = new_type
    return current_type


def get_type_description(type_str):
    # print("Reading: " + type_str)

    current = 0  # Current parse position

    result_type = type_comprehension.TCType()

    # First get the underlying type, including any modifiers

    underlying_type_storage_classes = []
    is_unsigned = False
    while True:
        (underlying_type_str, current) = extract_word(type_str, current)

        if underlying_type_str == 'signed':
            # print("Type is signed")
            pass
        elif underlying_type_str == 'unsigned':
            # print("Type is unsigned")
            is_unsigned = True
        elif underlying_type_str == 'struct':
            # print("Type is explicitly struct")
            pass
        elif underlying_type_str == 'class':
            # print("Type is explicitly class")
            pass
        elif underlying_type_str == 'union':
            # print("Type is explicitly union")
            pass
        elif underlying_type_str == 'enum':
            # print("Type is explicitly enum")
            pass
        elif underlying_type_str == 'const':
            # print("Type is const")
            underlying_type_storage_classes.append(
                type_comprehension.TCStorageClass(type_comprehension.storage_class.StorageClass.const))
        elif underlying_type_str == 'volatile':
            # print("Type is volatile")
            underlying_type_storage_classes.append(
                type_comprehension.TCStorageClass(type_comprehension.storage_class.StorageClass.volatile))
        elif underlying_type_str == 'mutable':
            # print("Type is mutable")
            underlying_type_storage_classes.append(
                type_comprehension.TCStorageClass(type_comprehension.storage_class.StorageClass.mutable))
        elif underlying_type_str == 'long':
            # This is fiddly - the next token _may_ form a double-word type, or it may not

            (next_type, next_current) = extract_word(type_str, current)

            if (next_type == 'long') or (next_type == 'double'):
                # Type was "long long" or "long double"
                underlying_type_str += ' ' + next_type
                current = next_current
                break

            # Type was just "long"
            break
        else:
            break

    if is_unsigned:
        underlying_type_str = "unsigned " + underlying_type_str

    # print("Underlying type is " + underlying_type_str)

    # If the type parses as a builtin type then treat it as such, otherwise treat it as a generic user type
    underlying_type = type_comprehension.TCBuiltInType(underlying_type_str)
    if underlying_type.type == type_comprehension.builtin_type.BuiltinType.unknown:
        underlying_type = type_comprehension.TCUserType(underlying_type_str)

    underlying_type.storage_classes = underlying_type_storage_classes

    current_type = None

    end_of_underlying_type_name = current

    # Next we need to figure out where the field name is (if one is specified)

    field_name = None

    while current < len(type_str):
        c = type_str[current]

        if is_whitespace(c):
            pass  # Ignore whitespace
        elif c == '(':
            pass  # Ignore group starts
        elif (c == '*') or (c == '^') or (c == '&'):
            pass  # Ignore pointers for the moment
        elif c == '[':
            break  # If we hit an array declaration, then there is no field name
        elif c == ')':
            break  # If we hit the end of a grouping, then there is no field name
        elif type_str[current:(current + 5)] == 'const':
            # const is not a field name
            current += 4
            pass
        elif type_str[current:(current + 8)] == 'volatile':
            # volatile is not a field name
            current += 7
            pass
        elif type_str[current:(current + 7)] == 'mutable':
            # mutable is not a field name
            current += 6
            pass
        else:
            # Anything that isn't a bracket or a pointer is the start of the field name
            (field_name, current) = extract_word(type_str, current)
            break
        current = current + 1

    field_name_length = 0
    if field_name is not None:
        # print("Field name is " + field_name)
        field_name_length = len(field_name)

    # At this point current points at the character immediately after the field name

    # Since storage classes apply to the thing on their left, we need to keep a buffer of them here to apply
    # when we hit something (a pointer, basically)
    buffered_storage_classes = []

    # Set up our two parse points
    left_parse_point = current - (field_name_length + 1)
    right_parse_point = current

    while (left_parse_point >= end_of_underlying_type_name) or (right_parse_point < len(type_str)):
        # First see if we can parse to the right
        while right_parse_point < len(type_str):
            c = type_str[right_parse_point]
            if is_whitespace(c):
                right_parse_point += 1  # Ignore whitespace
            elif c == '[':
                # Array bounds
                right_parse_point += 1
                (array_bound, right_parse_point) = extract_until_char(type_str, right_parse_point, ']')
                right_parse_point += 1  # Skip ]

                if len(array_bound) > 0:
                    # print("Array with bound " + array_bound)
                    current_type = chain_type(current_type, type_comprehension.TCArray(array_bound))

                else:
                    # print("Array with no bounds")
                    current_type = chain_type(current_type, type_comprehension.TCArray())
            elif c == '(':
                # Opening bracket - start of function parameters

                right_parse_point += 1

                function = type_comprehension.TCFunction()
                current_type = chain_type(current_type, function)

                # We need to split any content into parameters and then recursively examine each of those
                paren_level = 0
                current_parameter = ''
                while right_parse_point < len(type_str):
                    c = type_str[right_parse_point]
                    right_parse_point += 1
                    if c == '(':
                        paren_level += 1
                    elif c == ')':
                        if paren_level > 0:
                            paren_level -= 1
                        else:
                            # This was the closing bracket, so we are done
                            if len(current_parameter) > 0:
                                # If we had a final parameter declaration, examine it
                                # print("Function parameter " + current_parameter)
                                function.parameters.append(get_type_description(current_parameter))
                            break
                    elif c == ',':
                        if paren_level > 0:
                            pass  # We're inside parenthesis, so this isn't a separator for us
                        else:
                            if len(current_parameter) > 0:
                                # If we had a parameter declaration, examine it
                                # print("Function parameter " + current_parameter)
                                function.parameters.append(get_type_description(current_parameter))
                                current_parameter = ''
                    else:
                        current_parameter += c

            elif c == ')':
                # Closing bracket, need to parse everything on the left now
                right_parse_point += 1
                break
            else:
                raise Exception("Parse error - unexpected " + c + " in '" + type_str + "'")

        # Storage classes don't propagate through brackets, so reset them here
        buffered_storage_classes = []

        # Then parse things on the left
        while left_parse_point >= end_of_underlying_type_name:
            c = type_str[left_parse_point]
            if is_whitespace(c):
                left_parse_point -= 1  # Ignore whitespace
            elif (left_parse_point > 4) and (type_str[(left_parse_point - 4):(left_parse_point + 1)] == 'const'):
                # print("Const")
                buffered_storage_classes.append(
                    type_comprehension.TCStorageClass(type_comprehension.storage_class.StorageClass.const))
                left_parse_point -= 5
            elif (left_parse_point > 7) and (type_str[(left_parse_point - 7):(left_parse_point + 1)] == 'volatile'):
                # print("Volatile")
                buffered_storage_classes.append(
                    type_comprehension.TCStorageClass(type_comprehension.storage_class.StorageClass.volatile))
                left_parse_point -= 8
            elif (left_parse_point > 6) and (type_str[(left_parse_point - 6):(left_parse_point + 1)] == 'mutable'):
                # print("Mutable")
                buffered_storage_classes.append(
                    type_comprehension.TCStorageClass(type_comprehension.storage_class.StorageClass.mutable))
                left_parse_point -= 7
            elif (c == '*') or (c == '^') or (c == '&'):  # ^ indicates a non-nullable pointer
                # Pointer (or a reference, which we treat as a case of a non-nullable pointer)
                left_parse_point -= 1
                # print("Pointer")
                pointer_type = type_comprehension.TCPointer()
                pointer_type.storage_classes = buffered_storage_classes
                if c == '^':
                    pointer_type.nullable = False
                if c == '&':
                    pointer_type.reference = True
                    pointer_type.nullable = False
                current_type = chain_type(current_type, pointer_type)
                buffered_storage_classes = []
            elif c == '(':
                # Opening bracket, eat it and go back to parsing on the right if we can
                left_parse_point -= 1
                break
            else:
                raise Exception("Parse error - unexpected " + c + " in '" + type_str + "'")

    # If we had any "unused" storage class modifiers at the end, they apply to the underlying type

    for storage_class in buffered_storage_classes:
        underlying_type.storage_classes.append(storage_class)

    # The underlying type is the last thing in the chain

    current_type = chain_type(current_type, underlying_type)

    # Now walk up to the head of the chain and set that as the result type

    while current_type.parent is not None:
        current_type = current_type.parent
    result_type.type = current_type
    result_type.name = field_name

    # Semi-special-case - if the type wrapper is not adding anything, then simplify down to the inner type
    # (so, for example, "int" is just a TCBuiltinType not a TCType containing a TCBuiltinType)
    # Todo: It would probably make more sense to do this recursively down the tree

    if (isinstance(result_type, type_comprehension.TCType)) and \
            (result_type.name is None) and \
            (len(result_type.storage_classes) == 0):
        result_type = result_type.type

    # All done
    return result_type
