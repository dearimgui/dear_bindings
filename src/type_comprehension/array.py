from src import type_comprehension


# Represents a single-dimensional array of types
class TCArray(type_comprehension.element.TCElement):
    def __init__(self, bounds=None):
        super().__init__()

        self.target = None
        self.bounds = bounds

    # Dump this element for debugging
    def dump(self, indent=0):
        if self.bounds is not None:
            print("".ljust(indent * 4) + "Array with bounds: " + str(self.bounds))
        else:
            print("".ljust(indent * 4) + "Unbounded array: ")
        self.dump_storage_classes(indent + 1)
        print("".ljust(indent * 4) + "Target:")
        self.target.dump(indent + 1)