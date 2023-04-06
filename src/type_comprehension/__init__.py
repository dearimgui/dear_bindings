from . import element
from . import array
from . import builtin_type
from . import function
from . import pointer
from . import storage_class
from . import type
from . import type_comprehender
from . import usertype


__all__ = ["array", "builtin_type", "element", "function", "pointer", "storage_class",
           "type", "type_comprehender", "usertype"]

# Aliases

TCArray = array.TCArray
TCBuiltInType = builtin_type.TCBuiltInType
TCElement = element.TCElement
TCFunction = function.TCFunction
TCPointer = pointer.TCPointer
TCStorageClass = storage_class.TCStorageClass
TCType = type.TCType
TCUserType = usertype.TCUserType
