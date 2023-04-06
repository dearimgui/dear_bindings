from src import type_comprehension


# Represents a user-defined type
class TCUserType(type_comprehension.element.TCElement):
    def __init__(self, name):
        super().__init__()

        self.name = name

    def __str__(self):
        return "User type: " + str(self.name)

    def dump(self, indent=0):
        print("".ljust(indent * 4) + "User-defined type " + str(self.name))
        self.dump_storage_classes(indent + 1)
