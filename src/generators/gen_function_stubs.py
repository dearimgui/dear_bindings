import itertools
from src import code_dom
from src import utils
from src import conditional_generator
from src.code_dom.common import write_c_line


# Generate a cast between two types (if required)
# Generate a cast from C type to C++ type if to_cpp is true, the opposite if false
# Returns a prefix/suffix pair
def generate_cast(from_type, to_type, imgui_custom_types, nested_classes, to_cpp):

    cast_prefix = ""
    cast_suffix = ""

    if (from_type is not None) and (to_type is not None):
        context = code_dom.WriteContext()
        context.for_c = to_cpp
        context.for_implementation = True
        context.include_leading_colons = True

        from_type_str = from_type.to_c_string(context)
        to_type_str = to_type.to_c_string(context)

        # Treat & and * as synonymous as we handle the reference/dereferencing elsewhere
        munged_from_type_str = from_type_str.replace('&', '*')
        munged_to_type_str = to_type_str.replace('&', '*')

        if to_cpp:
            # Convert any nested class names to fully-qualified form
            # This is a little bit hacky (especially as it assumes leaf names are unique), but it works
            for leaf_name, full_name in nested_classes.items():
                # We use full_name[2:] to strip the leading :: from the fully-qualified name, as that is already there
                to_type_str = to_type_str.replace(leaf_name, full_name[2:])

        if munged_from_type_str != munged_to_type_str:
            is_enum = False

            # Slightly dodgy check for enum-ness - this will fail if the typename is decorated but in that case
            # the cast will likely also be wrong so let's fix that if/when it ever actually happens
            name_without_root_prefix = from_type_str[2:]  # Get the typename without the :: namespace root prefix
            if name_without_root_prefix in imgui_custom_types:
                if isinstance(imgui_custom_types[name_without_root_prefix], code_dom.DOMEnum):
                    is_enum = True

            # If the "convert by-value struct arguments to pointers" option is enabled, then we may need to handle
            # cases where we need to introduce a dereference here to get from the pointer representation to a value
            additional_dereferences = '*' * (munged_from_type_str.count('*') - munged_to_type_str.count('*'))

            if is_enum:
                # Enums need to use static_cast
                cast_prefix = additional_dereferences + "static_cast<" + to_type_str + \
                              additional_dereferences + ">("
                cast_suffix = ")"
            else:
                if from_type.use_pointer_cast_conversion:
                    cast_prefix = additional_dereferences + "(*reinterpret_cast<" + to_type_str + \
                                  additional_dereferences + "*>(&"
                    cast_suffix = "))"
                else:
                    cast_prefix = additional_dereferences + "reinterpret_cast<" + to_type_str + \
                                  additional_dereferences + ">("
                    cast_suffix = ")"

        # Check for by-value types (note that we do *not* want to use original_for_type here, but rather the modified
        # type for the check)

        type_to_check = from_type if to_cpp else to_type  # We want to check the C-style type here

        if len(type_to_check.tokens) >= 1:
            type_name = type_to_check.tokens[len(type_to_check.tokens) - 1].value
            if type_name in imgui_custom_types:
                underlying_type = imgui_custom_types[type_name]
                if isinstance(underlying_type, code_dom.DOMClassStructUnion) and underlying_type.is_by_value:
                    if to_cpp:
                        cast_prefix = "ConvertToCPP_" + underlying_type.name + "("
                    else:
                        cast_prefix = "ConvertFromCPP_" + underlying_type.name + "("
                    cast_suffix = ")"

        # Special case to marshal const char* into ImStr

        if (to_type_str == '::ImStr') and (from_type_str == 'const ::char*'):
            cast_prefix = "MarshalToCPP_ImStr_FromCharStr("
            cast_suffix = ")"

    return cast_prefix, cast_suffix


# Generate function stub bodies
def generate(dom_root, file, imgui_custom_types, indent=0, custom_varargs_list_suffixes={}, is_backend=False):
    generator = conditional_generator.ConditionalGenerator()

    write_context = code_dom.WriteContext()
    write_context.for_c = True
    write_context.for_implementation = True
    write_context.for_backend = is_backend

    # Build a list of any classes which were nested in C++-land, as we need to convert them to fully-qualified form
    # anywhere they appear in types

    nested_classes = {}  # Map of non-qualified names to qualified names
    for struct in dom_root.unmodified_element.list_all_children_of_type(code_dom.DOMClassStructUnion):
        parent_struct = struct.get_parent_class()
        if (parent_struct is not None) and (struct.name is not None):
            nested_classes[struct.name] = struct.get_fully_qualified_name(include_leading_colons=True)

    file.write("\n")
    write_c_line(file, indent, write_context, "// Function stubs")
    # Emit functions
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.is_manual_helper:
            continue  # Don't emit any code for manual helpers, we assume they are implemented by hand in the template

        # Emit conditionals (#ifdefs/etc)
        generator.write_conditionals(function, file, indent)

        # Get a reference to the original (C++) version of the function
        original_function = function.unmodified_element or function

        # Give temporary names to any arguments that lack them
        args_with_temp_names = []

        arg_index = 0
        for arg in function.arguments:
            if arg.name is None:
                arg.name = "__unnamed_arg" + str(arg_index) + "__"
                args_with_temp_names.append(arg_index)
            arg_index += 1

        # Check if this has a self argument we need to turn into a this pointer

        has_self = False
        is_const_function = False
        self_class_type = function.original_class
        # Constructors are a special case as they don't get self passed in
        if self_class_type is not None and (not function.is_constructor or function.is_placement_constructor) and not function.is_static:
            has_self = True
            # The function's own is_const will be false as it has been transformed into a non-const stub, but the
            # self argument will be const in the case it was originally const
            is_const_function = function.arguments[0].arg_type.tokens[0].value == 'const'

        # Check if varargs is involved

        uses_varargs = False
        for arg in function.arguments:
            if arg.is_varargs:
                uses_varargs = True

        # Fudge the function data to map everything into our namespace

        function = function.clone_without_children()  # Clone so we aren't altering the original
        function.name = "cimgui::" + function.name
        for type_data in function.list_all_children_of_type(code_dom.DOMType):
            for tok in type_data.tokens:
                if tok.value in imgui_custom_types:
                    tok.value = "cimgui::" + tok.value

        # We need to remove the "self" argument, partially because we don't want it and partially because if we
        # don't the argument list won't match the original function's
        fudged_function_arguments = function.arguments.copy()
        if has_self:
            fudged_function_arguments = fudged_function_arguments[1:]

        if len(fudged_function_arguments) != len(original_function.arguments):
            raise Exception("Argument list mismatch with original function")

        # Write function declaration

        file.write("\n")
        function.write_to_c(file, indent=indent, context=write_context)
        write_c_line(file, indent, write_context, "{")
        indent += 1

        # Write varargs decoding preamble

        if uses_varargs:
            write_c_line(file, indent, write_context, "va_list args;")
            write_c_line(file, indent, write_context, "va_start(args, fmt);")

        # If the function takes an array of a by-value struct, then we need to generate an intermediate array to convert
        # that into

        converted_arg_name_overrides = {}  # Map of arguments whose names we have changed through conversion,
        #                                    indexed by the original name

        arg_to_original_arg_list = list(zip(fudged_function_arguments, original_function.arguments))
        for (arg, original_arg) in arg_to_original_arg_list:
            if original_arg.is_array and not arg.is_implicit_default:
                if len(original_arg.arg_type.tokens) >= 1:
                    type_name = original_arg.arg_type.tokens[len(original_arg.arg_type.tokens) - 1].value
                    if type_name in imgui_custom_types:
                        underlying_type = imgui_custom_types[type_name]
                        if isinstance(underlying_type, code_dom.DOMClassStructUnion) and underlying_type.is_by_value:
                            # This is an array of a by-value struct, so we need to convert it
                            # Emit a local array of the converted type

                            if arg.array_bounds is None:
                                raise Exception("Cannot convert an array of indeterminate size")

                            converted_array_name = arg.name + "_converted_array"
                            write_c_line(file, indent, write_context,
                                         underlying_type.get_original_fully_qualified_name(include_leading_colons=True)
                                         + " " + converted_array_name + "[" + str(arg.array_bounds) + "];")

                            # And a for loop to do the conversion
                            write_c_line(file, indent, write_context, "for (int i=0; i<" +
                                         str(arg.array_bounds) + "; i++)")
                            write_c_line(file, indent + 1, write_context, converted_array_name + "[i] = " +
                                         "ConvertToCPP_" + underlying_type.name + "(" + arg.name + "[i]);")

                            converted_arg_name_overrides[arg.name] = converted_array_name

        # Write body containing thunk call

        # We need to check if the function has to copy the result to a temporary variable and then
        # return it later, this happens with varargs as we have to call va_end before returning
        returns_temp_result = False
        
        if (function.return_type is None) or (function.return_type.to_c_string() == "void"):
            thunk_call = ""
        else:
            if uses_varargs:
                returns_temp_result = True
                thunk_call = "auto temp_result = "
            else:
                thunk_call = "return "

        # Generate return type cast if necessary

        if function.is_constructor:
            # 'placement new' style constructors don't return anything
            if function.is_placement_constructor:
                return_cast_prefix = ""
                return_cast_suffix = ""
            else:
                # Constructors are a special case that returns the type they are constructing

                # To use generate_cast() we need to generate a type element that represents what the C++ new() call will
                # be returning
                original_type_name = original_function.get_parent_class().get_fully_qualified_name()

                if not function.is_by_value_constructor:
                    original_type_name += "*"

                new_type = code_dom.DOMType()
                new_type.tokens = utils.create_tokens_for_type(original_type_name)

                return_cast_prefix, return_cast_suffix = generate_cast(new_type,
                                                                       function.return_type,
                                                                       imgui_custom_types,
                                                                       nested_classes,
                                                                       to_cpp=False)
        else:
            return_cast_prefix, return_cast_suffix = generate_cast(original_function.return_type,
                                                                   function.return_type,
                                                                   imgui_custom_types,
                                                                   nested_classes,
                                                                   to_cpp=False)
        thunk_call += return_cast_prefix

        function_call_name = function.get_original_fully_qualified_name()

        if uses_varargs:
            if function_call_name in custom_varargs_list_suffixes:
                function_call_name += custom_varargs_list_suffixes[function_call_name]
            else:
                # Make the glorious assumption that if something has varargs, there will be a corresponding
                # <function name>V function that takes a va_list
                function_call_name += "V"

        self_pointer_cast = None
        if has_self:
            # Cast self pointer
            if is_const_function:
                self_pointer_cast = "reinterpret_cast<const " + \
                              self_class_type.get_original_fully_qualified_name(include_leading_colons=True) + \
                              "*>(self)"
            else:
                self_pointer_cast = "reinterpret_cast<" + \
                              self_class_type.get_original_fully_qualified_name(include_leading_colons=True) + \
                              "*>(self)"

            if function.is_placement_constructor:
                thunk_call += "IM_PLACEMENT_NEW(" + self_pointer_cast + ") "
            else:
                thunk_call += self_pointer_cast + "->"
        else:
            # If the function is not a member function, prefix the call with :: to avoid accidentally picking
            # up functions from the wrong namespace
            function_call_name = "::" + function_call_name

        if (function.return_type is not None) and (function.return_type.to_c_string() != "void"):
            # If the return type was a reference that we turned into a pointer, turn it into a pointer here
            # (note that we do no marshalling to make sure this is safe memory-wise!)
            for tok in function.return_type.tokens:
                if hasattr(tok, "was_reference") and tok.was_reference:
                    thunk_call += "&"

        if function.is_constructor:
            if not function.is_by_value_constructor and not function.is_placement_constructor:
                # Add new (unless this is by-value, in which case we don't want it)
                thunk_call += "new "
            # Constructor calls use the typename, not the nominal function name within the type
            function_call_name = self_class_type.get_original_fully_qualified_name(include_leading_colons=True)

        thunk_call += function_call_name + "("

        first_arg = True
        for (arg, original_arg) in arg_to_original_arg_list:
            if arg.is_implicit_default and arg.stub_call_value is None:
                continue  # Skip implicit default arguments

            # Generate a set of dereference operators to convert any pointer that was originally a reference and
            # converted by mod_convert_references_to_pointers back into reference form for passing to the C++ API
            # This isn't perfect but it should deal correctly with all the reasonably simple cases
            dereferences = ""
            if arg.arg_type is not None:
                for tok in arg.arg_type.tokens:
                    if hasattr(tok, "was_reference") and tok.was_reference:
                        dereferences += "*"

            # Generate a cast if required
            cast_prefix, cast_suffix = generate_cast(arg.arg_type, original_arg.arg_type,
                                                     imgui_custom_types, nested_classes, to_cpp=True)

            if not first_arg:
                thunk_call += ", "
            if arg.is_varargs:
                thunk_call += "args"  # Turn ... into our expanded varargs list
            else:
                if arg.name in converted_arg_name_overrides:
                    # If the name got remapped due to conversion, that also means we don't need any casting
                    thunk_call += dereferences + converted_arg_name_overrides[arg.name]
                else:
                    argument_call = arg.name
                    if arg.stub_call_value is not None:
                        argument_call = arg.stub_call_value
                    thunk_call += cast_prefix + dereferences + argument_call + cast_suffix
            first_arg = False

        thunk_call += ")" + return_cast_suffix + ";"

        if function.is_destructor:
            #  Destructors get a totally different bit of code generated
            destructor_func_name = self_class_type.get_original_fully_qualified_name(include_leading_colons=False)
            write_c_line(file, indent, write_context, "self->~" + destructor_func_name + "();")
        else:
            write_c_line(file, indent, write_context, thunk_call)

        # Write varargs teardown

        if uses_varargs:
            write_c_line(file, indent, write_context, "va_end(args);")
        
        if returns_temp_result:
            write_c_line(file, indent, write_context, "return temp_result;")

        # Close off body

        indent -= 1
        write_c_line(file, indent, write_context, "}")

        # Remove temporary argument names
        for arg_index in args_with_temp_names:
            function.arguments[arg_index].name = None

    # Finally close any last conditionals
    generator.finish_writing(file, indent)

