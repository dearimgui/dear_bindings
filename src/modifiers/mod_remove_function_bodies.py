from src import code_dom


# This modifier removes any function bodies. Inline functions are set to be IMGUI_API and the inline modifier removed.
def apply(dom_root):
    for function in dom_root.list_all_children_of_type(code_dom.DOMFunctionDeclaration):
        function.body = None
        if function.is_loose_function_body:
            # This entire declaration is just for the body, so remove it entirely
            # (i.e. this is a separate body declared outside the class)
            function.parent.remove_child(function)
        elif function.is_inline or function.is_static:
            function.is_inline = False
            function.is_imgui_api = True
