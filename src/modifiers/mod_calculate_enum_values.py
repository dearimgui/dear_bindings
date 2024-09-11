from src import code_dom
from src import utils


# This modifier calculates the actual values for enum values
def apply(dom_root):

    # Dictionary of known existing name/value pairs for evaluation
    # There is at least one case where a value from one enum is used in another (ImDrawFlags_RoundCornersNone),
    # so we have to make this a global
    # We initialise this to set __builtins__ to empty to prevent access to Python default functions
    existing_values = {"__builtins__": {}}

    for enum in dom_root.list_all_children_of_type(code_dom.DOMEnum):
        last_value = -1  # By default the first value should be zero

        for enum_element in enum.list_all_children_of_type(code_dom.DOMEnumElement):
            value_string = enum_element.get_value_expression_as_string()

            if len(value_string) == 0:
                # No specified value expression, so this is automatically the previous value +1
                value = last_value + 1
            else:
                # We need to evaluate this expression

                # Fudge some odd values that have '(int)' casts in them.
                # This is not perfect, but shouldn't cause any problems.
                value_string = value_string.replace("(int)", "")

                compiled = compile(value_string, "<string>", "eval")

                # This is partly about checking for unknown values, but mostly about preventing the use of anything
                # not on our list above for security purposes (so that a theoretical malicious modification to the
                # input file can't cause arbitrary code execution here). This likely isn't perfect, though, so
                # care should be exercised when converting untrusted headers.
                for name in compiled.co_names:
                    if name not in existing_values:
                        raise Exception("Enum " + enum.name + " element " + enum_element.name + " references " +
                                        name + " in expression " + value_string + ", which is not a known enum value")

                value = eval(compiled, existing_values, {})

            # print(enum_element.name + " = " + value_string + " = " + str(value))
            enum_element.value = value
            existing_values[enum_element.name] = value
            last_value = value
