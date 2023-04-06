# The base class for all type comprehension elements
class TCElement:
    def __init__(self):
        self.storage_classes = []
        self.parent = None

    def dump_storage_classes(self, indent=0):
        if len(self.storage_classes) > 0:
            print("".ljust((indent + 1) * 4) + "Storage classes:")
            for storage_class in self.storage_classes:
                storage_class.dump(indent + 2)

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + "Unknown element")
        self.dump_storage_classes(indent + 1)
