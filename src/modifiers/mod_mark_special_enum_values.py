from src import code_dom
from src import utils


# This modifier marks enum values with specific suffixes as being special in some fashion
def apply(dom_root, internal_suffixes, count_suffixes):
    for enum in dom_root.list_all_children_of_type(code_dom.DOMEnum):
        for enum_element in enum.list_all_children_of_type(code_dom.DOMEnumElement):
            # Mark as internal
            for suffix in internal_suffixes:
                if enum_element.name.endswith(suffix):
                    enum_element.is_internal = True
                    break

            # Mark as a count value
            for suffix in count_suffixes:
                if enum_element.name.endswith(suffix):
                    enum_element.is_count = True
