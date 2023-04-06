from src import type_comprehension


# Represents a function
class TCFunction(type_comprehension.element.TCElement):
    def __init__(self):
        super().__init__()

        self.parameters = []
        self.return_type = None

    def __str__(self):
        return "Function: " + str(self.return_type) + " (" + str(self.parameters) + ")"

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + "Function")
        self.dump_storage_classes(indent + 1)
        print("".ljust((indent + 1) * 4) + "Return type:")
        self.return_type.dump(indent + 2)
        index = 0
        for param in self.parameters:
            print("".ljust((indent + 1) * 4) + "Parameter " + str(index) + ":")
            param.dump(indent + 2)
            index += 1
