from src import type_comprehension


# Represents a single type declaration
class TCType(type_comprehension.element.TCElement):
    def __init__(self):
        super().__init__()

        self.name = None
        self.type = None

    def __str__(self):
        return "Type: " + str(self.type) + " name = " + str(self.name)

    # Dump this element for debugging
    def dump(self, indent=0):
        if self.name is not None:
            print("".ljust(indent * 4) + "Type named " + str(self.name))
        else:
            print("".ljust(indent * 4) + "Unnamed type")
        self.dump_storage_classes(indent + 1)
        self.type.dump(indent + 1)
