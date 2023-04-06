from src import type_comprehension


# Represents a pointer to a C type
class TCPointer(type_comprehension.element.TCElement):
    def __init__(self):
        super().__init__()

        self.target = None

    def __str__(self):
        return "Pointer to: " + str(self.target)

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + "Pointer")
        self.dump_storage_classes(indent + 1)
        print("".ljust(indent * 4) + "Target:")
        self.target.dump(indent + 1)
