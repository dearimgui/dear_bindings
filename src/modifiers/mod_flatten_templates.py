from src import code_dom
from src import utils


# Extract the param_index-th template parameter for the template name given from a token list
# Returns the parameter as a string (sans whitespace), along with the first and last token indices that
# the parameter occupies (not including any <>s or commas)
# Returns None, -1, -1 if the tokens passed are not an instance of the template name given
def extract_template_parameter(template_name, tokens, param_index):
    for i in range(0, len(tokens) - 3):
        if (tokens[i].value == template_name) and \
                (tokens[i + 1].value == '<'):
            end_index = -1
            for j in range(i + 2, len(tokens)):
                if tokens[j].value == '>':
                    end_index = j
                    break
            if end_index >= 0:
                instantiation_parameter = ""
                current_index = 0
                min_token = len(tokens) + 1
                max_token = -1
                for k in range(i + 2, end_index):
                    if tokens[k].type == 'COMMA':
                        current_index += 1
                    else:
                        if current_index == param_index:
                            min_token = min(min_token, k)
                            max_token = max(max_token, k)
                            instantiation_parameter += tokens[k].value
                            # Make 'const char*' format nicely
                            if k < end_index - 1 and tokens[k + 1].value != "*":
                                instantiation_parameter += " "

                return instantiation_parameter.strip(), min_token, max_token
    return None, -1, -1


# Extract the range in the tokens given that is occupied by template parameters, inclusive of the <>s
def extract_template_parameter_range(template_name, tokens):
    for i in range(0, len(tokens) - 3):
        if (tokens[i].value == template_name) and \
                (tokens[i + 1].value == '<'):
            end_index = -1
            for j in range(i + 2, len(tokens)):
                if tokens[j].value == '>':
                    end_index = j
                    break
            if end_index >= 0:
                return i + 1, end_index
    return -1, -1


# This modifier finds templates and flattens them, creating concrete classes/functions for each required instantiation
# custom_type_fudges can be used to supply strings which will be matched and replaced in modified types within the
# instantiation as a way of working around some issues with the subtleties of template expansion rules (notably
# "const T*" with T as "Blah *" expanding to "Blah* const*" rather than the lexical substitution "const Blah**")
def apply(dom_root, custom_type_fudges={}):
    generated_instantiations = []

    # We potentially need to apply multiple passes to resolve things inside instantiations
    pass_index = 1
    while True:
        # print("Template flatten pass " + str(pass_index))
        more_to_do = apply_single_iteration(dom_root, custom_type_fudges, generated_instantiations)
        if not more_to_do:
            break
        pass_index += 1

    # Remove all the un-instantiated templates
    for template in dom_root.list_all_children_of_type(code_dom.DOMTemplate):
        # Remove the original template
        template.parent.remove_child(template)


class TemplateInstantiationParameter:
    def __init__(self):
        super().__init__()
        self.name = None  # The name of this parameter
        self.is_unresolved = False  # Is this an unresolved parameter?


# Flattens one nesting level of templates. 
# Returns list of template types that still have non-flattened usages.
def apply_single_iteration(dom_root, custom_type_fudges, generated_instantiations) -> bool:
    more_to_do = False  # Do we need another iteration?

    # Iterate through all templates
    for template in dom_root.list_all_children_of_type(code_dom.DOMTemplate):
        templated_obj = template.get_templated_object()
        template_name = templated_obj.name
        template_parameters = template.get_template_parameters()
        num_template_parameters = len(template_parameters)

        # Instantiation parameters sets as they exist in the DOM at present
        instantiation_parameter_sets = []
        # Instantiation parameters in their implementation form (if that exists, None if not)
        implementation_instantiation_parameter_sets = []

        # Find all references to this template
        for type_element in dom_root.list_all_children_of_type(code_dom.DOMType):
            # Don't look for instantiations inside template definitions (those will get expanded on subsequent passes
            # when their instantiations are examined)
            if type_element.is_descendant_of_type(code_dom.DOMTemplate):
                continue

            instantiation_parameters = []  # Array of TemplateInstantiationParameters

            # This checks if the type tokens look like an instance of our template and extracts the parameter list
            if extract_template_parameter(template_name, type_element.tokens, 0)[0] is not None:
                for i in range(0, num_template_parameters):
                    instantiation_parameter, first_token, last_token = (
                        extract_template_parameter(template_name, type_element.tokens, i))
                    if instantiation_parameter is not None:
                        is_unresolved = False
                        for k in range(first_token, last_token):
                            if (hasattr(type_element.tokens[k], 'is_template_parameter') and
                                    type_element.tokens[k].is_template_parameter):
                                # This is itself an unresolved template parameter
                                is_unresolved = True
                                break

                        parameter = TemplateInstantiationParameter()
                        parameter.name = instantiation_parameter
                        parameter.is_unresolved = is_unresolved

                        instantiation_parameters.append(parameter)

            # len(instantiation_parameters) will be 0 if this isn't our template, so this doubles as a check for that
            # too
            if len(instantiation_parameters) == num_template_parameters:
                if instantiation_parameters not in instantiation_parameter_sets:
                    human_readable_param_list = ""
                    first = True
                    for param in instantiation_parameters:
                        if not first:
                            human_readable_param_list += ", "
                        human_readable_param_list += param.name
                        first = False

                    # Check if there are any unresolved template parameters here

                    if type_element.contains_template_parameters():
                        # If the type contains unresolved template parameters, then we can't do anything with them
                        # yet - we need to do another resolution pass
                        #print(
                        #    "Template " + template_name + " referenced in " + str(type_element) + " with parameters " +
                        #    human_readable_param_list + " (but we are ignoring this for now as it is unresolved)")
                        more_to_do = True  # Mark us as needing another resolution pass
                    else:
                        #print("Template " + template_name + " referenced in " + str(type_element) +
                        #      " with parameters " + human_readable_param_list)

                        instantiation_parameter_sets.append(instantiation_parameters)

                        # Figure out what the implementation parameters are and record them
                        implementation_instantiation_parameters = None
                        if type_element.original_name_override is not None:
                            opening_bracket = type_element.original_name_override.index('<')
                            closing_bracket = type_element.original_name_override.index('>')
                            if (opening_bracket >= 0) and (closing_bracket > opening_bracket):
                                implementation_parameters = \
                                    type_element.original_name_override[opening_bracket + 1:closing_bracket]
                                # Split on commas and strip whitespace
                                implementation_instantiation_parameters = [x.strip() for x in
                                                                           implementation_parameters.split(',')]

                        implementation_instantiation_parameter_sets.append(implementation_instantiation_parameters)

        # Reverse so that when we add these to the DOM (which in turn reverses the order), they end up in the original
        # order they were seen
        instantiation_parameter_sets.reverse()
        implementation_instantiation_parameter_sets.reverse()

        # Duplicate the template for each instantiation

        instantiation_names = []  # List of the actual C names for the instantiations
        instantiations = []  # List of the instantiation objects themselves

        for (instantiation_parameters, implementation_instantiation_parameters) in \
                zip(instantiation_parameter_sets, implementation_instantiation_parameter_sets):
            instantiation = templated_obj.clone()
            instantiation.parent = None

            instantiations.append(instantiation)

            # We need to set up an override so that instead of using the original template typename the
            # implementation uses the name with parameter substitution doe
            if instantiation.original_name_override is None:
                instantiation.original_name_override = instantiation.get_fully_qualified_name()

            # Reformat the instantiation parameter list into a string, using the implementation version if possible,
            # so we get "ImVector<ImGuiTextFilter::TextRange>" instead of "ImVector<ImGuiTextFilter_TextRange>"

            instantiation_parameters_as_string = ""
            first = True
            if implementation_instantiation_parameters is not None:
                for param in implementation_instantiation_parameters:
                    if not first:
                        instantiation_parameters_as_string += ", "
                    instantiation_parameters_as_string += param.strip()
                    first = False
            else:
                for param in instantiation_parameters:
                    if not first:
                        instantiation_parameters_as_string += ", "
                    instantiation_parameters_as_string += param.name.strip()
                    first = False
            instantiation.original_name_override += "<" + instantiation_parameters_as_string + ">"

            # Generate a new name for the instantiation
            instantiation.name += "_" + utils.sanitise_name_for_identifier(instantiation_parameters_as_string)
            instantiation_names.append(instantiation.name)

            if instantiation.name in generated_instantiations:
                # We already have this instantiation, so we don't actually want to emit it
                continue

            generated_instantiations.append(instantiation.name)

            # print("Generating template instantiation: " + instantiation.original_name_override)

            # Look for any template parameters in the instantiation and replace them as appropriate

            for element in instantiation.list_all_children_of_type(code_dom.DOMType):
                expanded_anything = False

                # Look for any cases where a template parameter is used as part of _another_ template, and expand them
                # e.g.
                # template<typename T> struct Foo
                # {
                #   T<int> Bar; // <-- T here is the case we are considering
                # }

                # Look for the THING preceding the first LTRIANGLE to get the template name
                element_type_name = None
                for token_index, token in enumerate(element.unmodified_element.tokens):
                    if token.type == 'LTRIANGLE':
                        thing_token = element.unmodified_element.tokens[token_index - 1]
                        if thing_token.type == 'THING':
                            element_type_name = thing_token.value

                # Check if this matches one of our parameter names
                for j in range(0, num_template_parameters):
                    element_instantiation_parameter, first_token, last_token = (
                        extract_template_parameter(element_type_name, element.unmodified_element.tokens, j))

                    if template_parameters[j].name == element_instantiation_parameter:

                        # Replace the type with a template instance

                        original_element = element
                        element = element.unmodified_element.clone()

                        # Replace the template parameter with type instance

                        for tok in element.tokens:
                            if tok.value == element_instantiation_parameter:
                                tok.value = instantiation_parameters[j].name
                                # Reset the "is unresolved template parameter" flag on the token
                                tok.is_template_parameter = instantiation_parameters[j].is_unresolved

                        # Replace the original element

                        original_element.parent.replace_child(original_element, [element])
                        element.parent.field_type = element

                        expanded_anything = True

                if expanded_anything:
                    # At this point, we've created another template instance type,
                    # but it itself is not flattened yet. We'll need another iteration
                    # to resolve the newly created type.
                    more_to_do = True
                    continue

                # Now replace all occurrences of the type parameters with the instantiation parameters

                modified_anything = False

                for i in range(0, len(element.tokens)):
                    for j in range(0, num_template_parameters):
                        if element.tokens[i].value == template_parameters[j].name:
                            element.tokens[i].value = instantiation_parameters[j].name
                            # Reset the "is unresolved template parameter" flag on the token
                            element.tokens[i].is_template_parameter = instantiation_parameters[j].is_unresolved
                            # We've just generated an instantiation with an unresolved parameter, so we need another
                            # iteration to resolve that
                            if instantiation_parameters[j].is_unresolved:
                                more_to_do = True
                            modified_anything = True

                if modified_anything:
                    # Do the same for any original name overrides, using the original override version of
                    # the parameter
                    if implementation_instantiation_parameters is not None:
                        for j in range(0, num_template_parameters):
                            if element.original_name_override is None:
                                write_context = code_dom.WriteContext()
                                write_context.for_implementation = True
                                element.original_name_override = element.to_c_string(write_context)
                                element.original_name_override = element.original_name_override \
                                    .replace(instantiation_parameters[j].name,
                                             implementation_instantiation_parameters[j])
                            else:
                                # This is kinda dubious because parameter names can be things like T, which will then
                                # match *any* T in the type, but for now I'm banking on that not happening as template
                                # types aren't very complicated and have little aside from the odd "const", * or & on
                                # them.
                                element.original_name_override = element.original_name_override \
                                    .replace(template_parameters[j].name,
                                             implementation_instantiation_parameters[j])

                    # Apply any custom fudges

                    full_type = element.to_c_string()

                    for fudge_key in custom_type_fudges.keys():
                        if fudge_key in full_type:
                            full_type = full_type.replace(fudge_key, custom_type_fudges[fudge_key])

                            # Figure out if any of our source type had reference->pointer conversions done on it
                            num_converted_references = 0
                            for tok in element.tokens:
                                if hasattr(tok, "was_reference") and tok.was_reference:
                                    num_converted_references += 1

                            # Supporting this wouldn't be horrifically difficult, but right now it's hard due to the
                            # way we collapse all the tokens into one here. If this proves necessary then it's probably
                            # a question of either redoing fudges to use token sequences, or adding something to
                            # re-parse the fudged string into tokens and then map the was_reference flag across.
                            if num_converted_references > 1:
                                raise Exception("Fudged type has more than one converted reference - this is not "
                                                "supported")

                            element.tokens = utils.create_tokens_for_type(full_type)

                            if num_converted_references > 0:
                                element.tokens[0].was_reference = True

                            if element.original_name_override is not None:
                                element.original_name_override = element.original_name_override \
                                    .replace(fudge_key, custom_type_fudges[fudge_key])

            # Optionally insert new struct instances into the DOM at the very end to avoid problems with referencing
            # things that aren't declared yet at the point the template appears
            place_instantiation_at_end = False

            if place_instantiation_at_end:
                # Create a forward-declaration of the template at the point it was originally declared

                declaration_comment = code_dom.DOMComment()
                declaration_comment.comment_text = "// Forward declaration of " + template_name + \
                                                   "<" + instantiation_parameters_as_string + ">"

                declaration = instantiation.clone()
                declaration.children.clear()
                declaration.is_forward_declaration = True

                template.parent.insert_after_child(template, [declaration_comment, declaration])

                # Add at end of file
                dom_root.add_children([instantiation])
            else:
                # Insert new instance at point of template
                template.parent.insert_after_child(template,
                                                   [instantiation])

            # Create a comment to note where this came from
            comment = code_dom.DOMComment()
            comment.comment_text = "// Instantiation of " + template_name + "<" + instantiation_parameters_as_string + ">"
            instantiation.attach_preceding_comments([comment])

        # Replace any references to the original template types with the new instantiations
        for (instantiation_parameters, instantiation_name, instantiation) in \
                zip(instantiation_parameter_sets, instantiation_names, instantiations):
            first_reference = True
            for type_element in dom_root.list_all_children_of_type(code_dom.DOMType):
                all_match = True
                for i in range(0, num_template_parameters):
                    element_instantiation_parameter, _, _ = \
                        extract_template_parameter(template_name, type_element.tokens, i)
                    if element_instantiation_parameter != instantiation_parameters[i].name:
                        all_match = False

                # Skip anything that doesn't match the parameter set for this instantiation
                if not all_match:
                    continue

                # Get the range of tokens occupied by the template parameters
                first_token, last_token = extract_template_parameter_range(template_name, type_element.tokens)
                # Set the original (parameterised) name as the override so it gets used for the
                # implementation code
                write_context = code_dom.WriteContext()
                write_context.use_original_names = True
                type_element.original_name_override = type_element.to_c_string(write_context)
                # ...then replace the main name with our instance name

                # -1 because first_token is the <, so we need to step back over the template name
                first_token_of_reference = first_token - 1

                type_element.tokens[first_token_of_reference].value = instantiation_name
                del type_element.tokens[first_token_of_reference + 1:last_token + 1]  # +1 to eat the closing >

                # Next check to see if the template was declared in a different header from this reference
                # and has not been used previously -  if so, we want to move the instantiation into this header
                # instead. This is mostly relevant to the Vulkan backend at the moment, which has a couple of
                # unique ImVector<> instantiations.

                if first_reference:
                    instantiation_header = utils.find_nearest_parent_of_type(instantiation, code_dom.DOMHeaderFile)
                    reference_header = utils.find_nearest_parent_of_type(type_element, code_dom.DOMHeaderFile)
                    if instantiation_header is not reference_header:
                        # Insert at the start of the referencing header by default
                        insert_point = reference_header.children[0]

                        # Scan the header to see if any of the parameter types are declared and if so insert after that
                        # declaration (this is largely a "this makes sense for ImVector<>" mechanic)
                        for insert_point_candidate in reference_header.list_all_children_of_types(
                                [code_dom.DOMClassStructUnion, code_dom.DOMTypedef]):
                            for instantiation_parameter in instantiation_parameters:
                                if insert_point_candidate.name == instantiation_parameter.name:
                                    insert_point = insert_point_candidate
                                    break

                        # Move the instantiation here
                        insert_point.parent.insert_after_child(insert_point, [instantiation])

                first_reference = False
    
    return more_to_do
