from src import code_dom
from src import utils


# This modifier excludes any function-style defines from the metadata, except those whose names
# are in the do_not_exclude list
# If required_defines is not empty, only defines wrapped in 
# any matching preprocessor ifs will be excluded
def apply(dom_root, do_not_exclude, required_defines=None):
    for define in dom_root.list_all_children_of_type(code_dom.DOMDefine):
        if "(" in define.name:
            if define.name not in do_not_exclude:
                if required_defines is not None:
                    if isinstance(define.parent , code_dom.DOMPreprocessorIf):
                        for required_define in required_defines:
                            check = utils.create_preprocessor_if(required_define)
                            if define.parent.condition_matches(check):
                                define.exclude_from_metadata = True
                else:
                    define.exclude_from_metadata = True
