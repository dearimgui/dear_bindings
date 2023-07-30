from src import code_dom
from src import utils


# This modifier changes the listed includes to point to a different file
# include_filenames should be a map of old filenames to new filenames in include syntax (e.g. "<stdio.h>" or similar)
def apply(dom_root, include_filenames):
    for include in dom_root.list_all_children_of_type(code_dom.DOMInclude):
        if include.get_include_file_name() in include_filenames:
            include.tokens = [utils.create_token("#include"),
                              utils.create_token(include_filenames[include.get_include_file_name()])]
