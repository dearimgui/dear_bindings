from src import code_dom
from src import utils
from typing import cast

def apply(dom_root, typedefs_names_and_sizes):
    for typedef in cast(list[code_dom.DOMTypedef], dom_root.list_all_children_of_type(code_dom.DOMTypedef)):
        for typedef_name_and_size in typedefs_names_and_sizes:
            typedef_name = typedef_name_and_size[0]
            typedef_size = typedef_name_and_size[1]
            if typedef.name in typedef_name:
                new_type = utils.create_classstructunion("struct " + typedef.name + " { char __dummy[" + str(typedef_size) + "]; }")
                typedef.parent.replace_child(typedef, [new_type])
