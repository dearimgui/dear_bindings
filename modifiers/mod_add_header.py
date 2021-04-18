import code_dom
import utils


# This modifier adds some header stuff to the file
def apply(dom_root):

    # We need stdbool.h to get bool defined
    stdbool_include = code_dom.DOMInclude()
    stdbool_include.tokens = [utils.create_token("#include <stdbool.h>")]

    first_element = dom_root.children[0]

    dom_root.insert_before_child(first_element, [stdbool_include])
