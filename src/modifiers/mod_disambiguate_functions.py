from src import code_dom
from src import utils
import sys


# This modifier finds any overloaded functions with identical names and disambiguates them
def apply(dom_root, name_suffix_remaps, functions_to_ignore):
    # Find all functions with name collisions

    functions_by_name = {}  # Contains lists of functions

    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        if function.name not in functions_by_name:
            # Create list
            functions_by_name[function.name] = [function]
        else:
            # Add to list
            functions_by_name[function.name].append(function)

    # Resolve collisions

    for functions in functions_by_name.values():
        if len(functions) < 2:
            continue  # No collision

        if functions[0].name in functions_to_ignore:
            continue

        if len(functions) == 2:
            # Special case - if we have exactly two functions, and they're in #ifdef or similar blocks that make them
            # mutually exclusive (i.e. they can never both be compiled in), then this isn't a name clash and can be
            # ignored

            conditionals_a = utils.get_preprocessor_conditionals(functions[0])
            conditionals_b = utils.get_preprocessor_conditionals(functions[1])

            no_collision = False

            for conditional_a in conditionals_a:
                for conditional_b in conditionals_b:
                    if conditional_a.condition_is_mutually_exclusive(conditional_b):
                        no_collision = True
                        break
                if no_collision:
                    break

            if no_collision:
                continue

        # Count the number of arguments that are identical across all overloads
        num_common_args = 0
        finished_common_arguments = False
        while num_common_args < len(functions[0].arguments):
            for function in functions:
                if num_common_args >= len(function.arguments):
                    finished_common_arguments = True
                    break  # Ran out of arguments
                if function.arguments[num_common_args].arg_type.to_c_string() != \
                        functions[0].arguments[num_common_args].arg_type.to_c_string():
                    finished_common_arguments = True
                    break  # Arguments don't match
            if finished_common_arguments:
                break
            num_common_args += 1

        # Find the function in the set with the smallest argument count
        lowest_arg_count = sys.maxsize
        lowest_arg_function = None
        for function in functions:
            if len(function.arguments) < lowest_arg_count:
                lowest_arg_count = len(function.arguments)
                lowest_arg_function = function

        # Add suffixes based on non-common arguments

        suffixes_by_function = {}  # Dictionary indexed by function, containing proposed suffix lists

        for function in functions:

            function_suffixes = []
            suffixes_by_function[function] = function_suffixes

            # Do not alter the name of the function with the fewest arguments
            if function == lowest_arg_function:
                continue

            for i in range(num_common_args, len(function.arguments)):
                if not function.arguments[i].is_varargs:  # Don't try and append a suffix for ... arguments
                    # Check to see if the full type name is in the remap list, and if so remap it
                    full_name = function.arguments[i].arg_type.to_c_string()
                    if full_name in name_suffix_remaps:
                        suffix_name = name_suffix_remaps[full_name]
                    else:
                        # Otherwise make a best guess
                        if isinstance(function.arguments[i].arg_type, code_dom.DOMFunctionPointerType):
                            suffix_name = "Callback"  # All function pointers get called "callback" for simplicity
                        else:
                            suffix_name = function.arguments[i].arg_type.get_primary_type_name()
                        # Capitalise the first letter of the name
                        suffix_name = suffix_name[0].upper() + suffix_name[1:]
                        # Slight bodge to differentiate pointers
                        if function.arguments[i].arg_type.to_c_string().endswith('*'):
                            suffix_name += "Ptr"

                    # Semi-hack - "Ref" is rarely meaningful as a disambiguator and just clutters things, so don't
                    # include it
                    suffix_name = suffix_name.replace("&", "")

                    function_suffixes.append(utils.sanitise_name_for_identifier(suffix_name))

        # Optimise the suffix lists - we want the shortest version that differentiates the functions in question, so
        # figure out the minimal number of suffixes that achieves that

        max_suffixes = 0  # Maximum number of suffixes
        for function in functions:
            max_suffixes = max(max_suffixes, len(suffixes_by_function[function]))

        num_suffixes_needed = 1
        while num_suffixes_needed < max_suffixes:
            clash_exists = False
            existing_names = {}
            for function in functions:
                suffixes = suffixes_by_function[function]
                if len(suffixes) > num_suffixes_needed:
                    suffixes = suffixes[:num_suffixes_needed]
                potential_name = ''.join(suffixes)
                if potential_name in existing_names:
                    clash_exists = True
                    break
                existing_names[potential_name] = function

            if clash_exists:
                num_suffixes_needed += 1
            else:
                break

        # Apply the optimised names

        for function in functions:
            suffixes = suffixes_by_function[function]
            if len(suffixes) > num_suffixes_needed:
                suffixes = suffixes[:num_suffixes_needed]
            function.name += ''.join(suffixes)

        # Semi-special case - if we have exactly two functions that still clash at this point, and they differ in
        # the const-ness of their return type, then add _Const to one

        if (len(functions) == 2) and (functions[0].name == functions[1].name):
            if functions[0].return_type.is_const() != functions[1].return_type.is_const():
                if functions[0].return_type.is_const():
                    functions[0].name += "_Const"
                else:
                    functions[1].name += "_Const"

        # Verify we now have no name clashes
        # (note that this only checks that we resolved the collisions between the functions that were initially
        # overloaded, and doesn't check for the possibility that a previously non-colliding function now collides)

        new_names = {}

        for function in functions:
            if function.name in new_names:
                print("Unresolved collision between these functions:")
                for print_function in functions:
                    print(print_function.name + " : " + str(print_function))
                raise Exception("Unresolved function name collision")

            new_names[function.name] = function
