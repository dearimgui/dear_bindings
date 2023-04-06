from enum import Enum
from src import type_comprehension


# The possible C storage classes
class StorageClass(Enum):
    unknown = 0
    const = 1
    volatile = 2
    mutable = 3


# Represents a C storage class
class TCStorageClass(type_comprehension.element.TCElement):
    def __init__(self, storage_class=StorageClass.unknown):
        super().__init__()

        self.storage_class = storage_class

    def __str__(self):
        return "Storage class: " + str(self.storage_class)

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + str(self.storage_class))
