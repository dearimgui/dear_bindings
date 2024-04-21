from src import code_dom
from src import utils


# This modifier takes a list of defines and performs a simple search/replace on their contents
# define_names should be a list of define names
# mapping should be a set mapping search strings to replace strings
def apply(dom_root, define_names, mappings):
    for define in dom_root.list_all_children_of_type(code_dom.DOMDefine):
        if define.name in define_names:
            define_content = define.get_content()
            if define_content is not None:
                for search in mappings:
                    define_content = define_content.replace(search, mappings[search])
                define.set_content(define_content)
