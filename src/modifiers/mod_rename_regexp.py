from src import code_dom
import re

# This modifier renames elements in the DOM using regexps
# The parameter should be a list of tuples with regular expressions + replacement values
# Python re.sub() format can be used for the replacements, so parts of the match can be used in the replacement
# The list is applied in the order it is given
# If verbose is set, then rename operations will be logged
def apply(dom_root, replacement_list, verbose):
    # Compile all the regular expressions first

    compiled_list = []

    for search, replace in replacement_list.items():
        try:
            search_regexp = re.compile(search)
        except re.error as e:
            raise f"Failed to compile regular expression {search} (probably specified in --remap-list JSON): {e}"
        compiled_list.append((search_regexp, search, replace))

    # Now apply them

    for element in dom_root.list_all_children_of_type(code_dom.DOMElement):
        if hasattr(element, 'name'):
            if element.name is not None:
                element.name = process_name(element.name, compiled_list, verbose)
        if hasattr(element, 'names'):
            new_names = []
            for name in element.names:
                name = process_name(name, compiled_list, verbose)
                new_names.append(name)
            element.names = new_names

# Process a single name
def process_name(name, compiled_list, verbose):
    for search_regexp, search, replace in compiled_list:
        new_name = search_regexp.sub(replace, name)
        if new_name != name:
            if verbose:
                print(f"Renamed {name} -> {new_name} (rule: \"{search}\" -> \"{replace}\")")
            name = new_name
    return name