from src import code_dom
from src import utils


# This modifier marks enums whose names have one of the suffixes given as flags enums
def apply(dom_root, suffixes):
    for enum in dom_root.list_all_children_of_type(code_dom.DOMEnum):
        for suffix in suffixes:
            if enum.name.endswith(suffix):
                enum.is_flags_enum = True
                break
