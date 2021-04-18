import code_dom
import utils
import conditional_generator
from code_dom import write_c_line


# Generate function stub bodies
def generate(dom_root, file, indent=0, custom_varargs_list_suffixes={}):
    generator = conditional_generator.ConditionalGenerator()

    write_context = code_dom.WriteContext()
    write_context.for_implementation = True

    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):

        # Emit conditionals (#ifdefs/etc)
        generator.write_conditionals(function, file, indent)

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
        self_class_type = None
        if hasattr(function, "original_class"):
            if not function.is_constructor:  # Constructors are a special case as they don't get self passed in
                has_self = True
            self_class_type = function.original_class

        # Check if varargs is involved

        uses_varargs = False
        for arg in function.arguments:
            if arg.is_varargs:
                uses_varargs = True

        # Write function declaration

        file.write("\n")
        file.write("IMGUI_CAPI ")
        function.write_to_c(file, indent=indent, context=write_context)
        write_c_line(file, indent, "{")
        indent += 1

        # Write varargs decoding preamble

        if uses_varargs:
            write_c_line(file, indent, "va_list args;")
            write_c_line(file, indent, "va_start(args, fmt);")

        # Write body containing thunk call

        if (function.return_type is None) or (function.return_type.to_c_string() == "void"):
            thunk_call = ""
        else:
            thunk_call = "return "

            # If the return type was a reference that we turned into a pointer, turn it into a pointer here
            # (note that we do no marshalling to make sure this is safe memory-wise!)
            for tok in function.return_type.tokens:
                if hasattr(tok, "was_reference") and tok.was_reference:
                    thunk_call += "&"

        function_call_name = function.original_fully_qualified_name

        if uses_varargs:
            if function_call_name in custom_varargs_list_suffixes:
                function_call_name += custom_varargs_list_suffixes[function_call_name]
            else:
                # Make the glorious assumption that if something has varargs, there will be a corresponding
                # <function name>V function that takes a va_list
                function_call_name += "V"

        if has_self:
            # Cast self pointer
            # thunk_call += "reinterpret_cast<" + self_class_type.original_fully_qualified_name + "*>(self)->"
            thunk_call += "self->"

        if function.is_constructor:
            # Add new
            thunk_call += "new "
            # Constructor calls use the typename, not the nominal function name within the type
            function_call_name = self_class_type.original_fully_qualified_name

        thunk_call += function_call_name + "("

        first_arg = True
        for arg in function.arguments:
            if has_self and (arg.name == "self"):  # Omit "self" argument
                continue

            # Generate a set of dereference operators to convert any pointer that was originally a reference and
            # converted by mod_convert_references_to_pointers back into reference form for passing to the C++ API
            # This isn't perfect but it should deal correctly with all the reasonably simple cases
            dereferences = ""
            if arg.arg_type is not None:
                for tok in arg.arg_type.tokens:
                    if hasattr(tok, "was_reference") and tok.was_reference:
                        dereferences += "*"

            if not first_arg:
                thunk_call += ", "
            if arg.is_varargs:
                thunk_call += "args"  # Turn ... into our expanded varargs list
            else:
                thunk_call += dereferences + arg.name
            first_arg = False

        thunk_call += ");"

        if function.is_destructor:
            #  Destructors get a totally different bit of code generated
            write_c_line(file, indent, "delete self;")
        else:
            write_c_line(file, indent, thunk_call)

        # Write varargs teardown

        if uses_varargs:
            write_c_line(file, indent, "va_end(args);")

        # Close off body

        indent -= 1
        write_c_line(file, indent, "}")

        # Remove temporary argument names
        for arg_index in args_with_temp_names:
            function.arguments[arg_index].name = None

    # Finally close any last conditionals
    generator.finish_writing(file, indent)

