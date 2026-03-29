from src import code_dom
from src import utils


# This modifier adds the specified guard to a list of #defines.
# This is primarily intended as a way to avoid duplicate definitions when both the C and C++ headers are included
# in the same file.
def apply(dom_root, define_names, guard_name):
    for define in dom_root.list_all_children_of_type(code_dom.DOMDefine):
        if define.name in define_names:
            # Add #ifndef check
            ifguard = code_dom.DOMPreprocessorIf()
            ifguard.is_ifdef = True
            ifguard.is_negated = True
            ifguard.expression_tokens = [utils.create_token(guard_name)]

            # Insert at the same point as the original define
            define.parent.insert_after_child(define, [ifguard])

            # Move the define into the guard
            ifguard.add_child(define)
