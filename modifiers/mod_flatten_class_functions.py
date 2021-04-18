import code_dom
import utils


# This modifier converts any classes to structs, and moves member functions inside classes/structs outside
def apply(dom_root):
    # Iterate through all structs/classes/unions
    for struct in dom_root.list_all_children_of_type(code_dom.DOMClassStructUnion):
        # Convert classes to structs
        if struct.structure_type == "CLASS":
            struct.structure_type = "STRUCT"

        current_add_point = struct

        # Find any child functions
        # Note that this doesn't handle functions in nested classes correctly
        # (but that isn't an issue because we flatten them beforehand)
        for function in struct.list_all_children_of_type(code_dom.DOMFunctionDeclaration):

            # Special handling for constructors/destructors
            if function.is_constructor:
                # Constructors get modified to return a pointer to the newly-created object
                function.return_type = code_dom.DOMType()
                function.return_type.tokens = [utils.create_token(struct.name),
                                               utils.create_token("*")]
                # Set implementation override to keep original name if this was a flattened template or similar
                function.return_type.implementation_name_override = struct.original_fully_qualified_name + "*"
                function.return_type.parent = function
            elif function.is_destructor:
                # Remove ~ and add suffix to name
                function.name = function.name[1:] + "_destroy"
                # Destructors get modified to return void
                function.return_type = code_dom.DOMType()
                function.return_type.tokens = [utils.create_token("void")]
                function.return_type.parent = function

            # Remove const-ness as that has no meaning when the function is moved outside
            function.is_const = False

            # Prefix structure name onto the function
            function.name = struct.name + "_" + function.name

            # Note the class it came from originally
            function.original_class = struct

            if not function.is_constructor:
                # Add a self argument as the first argument of the function
                self_arg = code_dom.DOMFunctionArgument()
                self_arg.arg_type = code_dom.DOMType()
                self_arg.arg_type.parent = self_arg
                self_arg.arg_type.tokens = [utils.create_token(struct.name), utils.create_token("*")]
                # Set implementation override to keep original name if this was a flattened template or similar
                self_arg.arg_type.implementation_name_override = struct.original_fully_qualified_name + "*"
                self_arg.name = "self"
                self_arg.parent = function
                function.arguments.insert(0, self_arg)

            # Move the function out into the scope the structure is in

            # See if we need to change any conditionals
            add_point_conditionals = utils.get_preprocessor_conditionals(current_add_point)
            wanted_conditionals = utils.get_preprocessor_conditionals(function)

            while (len(add_point_conditionals) > len(wanted_conditionals)) or \
                    ((len(add_point_conditionals) > 0) and
                     (not add_point_conditionals[len(add_point_conditionals) - 1]
                        .condition_matches(wanted_conditionals[len(add_point_conditionals) - 1]))):
                # We need to remove a conditional
                conditional = add_point_conditionals.pop(len(add_point_conditionals) - 1)
                if not current_add_point.parent.condition_matches(conditional):
                    # In broad theoretical terms this *should* be impossible, but there may be some corner-case where
                    # a pre-existing conditional in the DOM somehow gets used in a weird way or another element happens
                    # to get inserted between things here
                    raise Exception("Needed to remove conditional " + str(conditional) + " but it wasn't the parent")
                current_add_point = current_add_point.parent

            add_inside_conditional = None  # If we need to add the function into a conditional, this will be it

            # Add any new conditionals that are needed
            while len(add_point_conditionals) < len(wanted_conditionals):
                conditional = wanted_conditionals[len(add_point_conditionals)]
                new_conditional = conditional.clone_without_children()
                new_conditional.parent = None

                if add_inside_conditional is not None:
                    add_inside_conditional.add_child(new_conditional)
                else:
                    current_add_point.parent.insert_after_child(current_add_point, [new_conditional])

                add_point_conditionals.append(new_conditional)
                add_inside_conditional = new_conditional

            if add_inside_conditional is not None:
                add_inside_conditional.add_child(function)
            else:
                current_add_point.parent.insert_after_child(current_add_point, [function])
            current_add_point = function  # Add next function after this one
