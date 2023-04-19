from enum import Enum
from src import type_comprehension


# The possible built-in C types
class BuiltinType(Enum):
    unknown = 0
    void = 1
    char = 2
    unsigned_char = 3
    short = 4
    unsigned_short = 5
    int = 6
    unsigned_int = 7
    long = 8
    unsigned_long = 9
    long_long = 10
    unsigned_long_long = 11
    float = 12
    double = 13
    long_double = 14
    bool = 15


# Represents a built-in C type
class TCBuiltInType(type_comprehension.element.TCElement):
    def __init__(self, c_name):
        super().__init__()

        if c_name == 'void':
            self.type = BuiltinType.void
        elif c_name == 'char':
            self.type = BuiltinType.char
        elif c_name == 'unsigned char':
            self.type = BuiltinType.unsigned_char
        elif c_name == 'short':
            self.type = BuiltinType.short
        elif c_name == 'unsigned short':
            self.type = BuiltinType.unsigned_short
        elif c_name == 'int':
            self.type = BuiltinType.int
        elif c_name == 'unsigned int':
            self.type = BuiltinType.unsigned_int
        elif c_name == 'long':
            self.type = BuiltinType.long
        elif c_name == 'unsigned long':
            self.type = BuiltinType.unsigned_long
        elif c_name == 'long long':
            self.type = BuiltinType.long_long
        elif c_name == 'unsigned long long':
            self.type = BuiltinType.unsigned_long_long
        elif c_name == 'float':
            self.type = BuiltinType.float
        elif c_name == 'double':
            self.type = BuiltinType.double
        elif c_name == 'long double':
            self.type = BuiltinType.long_double
        elif c_name == 'bool':
            self.type = BuiltinType.bool
        else:
            self.type = BuiltinType.unknown

    def __str__(self):
        return "Builtin type: " + str(self.type)

    # Dump this element for debugging
    def dump(self, indent=0):
        print("".ljust(indent * 4) + "Builtin type: " + str(self.type))
        self.dump_storage_classes(indent + 1)
