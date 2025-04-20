Dear Bindings Metadata Format
-----------------------------

The `cimgui.json` file contains JSON metadata about the generated bindings.
Note that unlike the generated `.h` and `.cpp` files, the JSON metadata contains information from any associated
configuration files (e.g. `imconfig.h`) as well. This is because the `.h` file will include those directly,
but a consumer of the JSON data probably wants to know about any settings made in them without the burden of parsing
them manually.

As a general rule-of-thumb, if an element described here is missing from the JSON metadata then that means it is
either not applicable to the object in question, or the generator doesn't have enough information to derive the
correct value (for example, `is_nullable` is omitted when a determination cannot be made about the nullability of
the pointer in question).

The JSON format looks like this:

### Top level

```json
{
  "defines": [],
  "enums": [],
  "typedefs": [],
  "structs": [],
  "functions": []
}
```

Each of the top-level keys contains information about one type of object in the generated header.

### Defines

```json
{
  "name": "IMGUI_VERSION",
  "content": "\"1.83 WIP\""
}
```

Defines represent `#define` values.

> Note that the content includes quotes if the define was a string in the original header (as seen above), but _does_
> remove brackets from around values (so in the case of `IM_DRAWLIST_TEX_LINES_WIDTH_MAX`, the content is `63`
> not `(63)`).

| Key     | Description                       |
|---------|-----------------------------------|
| name    | The name of the define            |
| content | The textual content of the define |

### Enums

```json
{
  "name": "ImGuiTableRowFlags_",
  "original_fully_qualified_name": "ImGuiTableRowFlags_",
  "is_flags_enum": true,
  "elements": [
    {
      "name": "ImGuiTableRowFlags_None",
      "value_expression": "0",
      "value": 0
    },
    {
      "name": "ImGuiTableRowFlags_Headers",
      "value_expression": "1<<0",
      "value": 1
    }
  ]
}
```

| Key                           | Description                                                              |
|-------------------------------|--------------------------------------------------------------------------|
| name                          | The name of the enum                                                     |
| original_fully_qualified_name | The name of the enum as it appeared in the original C++ API              |
| storage_type                  | The storage type of the enum (if specified)                              |
| is_flags_enum                 | Is this enum a bitfield composed of multiple flags?                      |
| elements                      | A list of elements                                                       |
| elements.name                 | The name of the element                                                  |
| elements.value_expression     | The value of the element as it originally appeared in the source         |
| elements.value                | The calculated value of the element as an integer                        |
| elements.is_count             | Indicates that the value is used to store the count of items in the enum |

Note that `value_expression` may not be present in the case where an enum element uses an implicit value
(i.e. enum auto-numbering), but `value` will always be present.

`is_count` is used in cases where an enum has a final element that is used to store the count of items
in that enum (for array sizing and similar). In some languages it may make sense not to expose these to
the user if there are other more appropriate idiomatic methods to determine this.

### Typedefs

```json
{
  "name": "ImGuiWindowFlags",
  "type": {
    "declaration": "int"
  }
}
```

A C `typedef`.

| Key  | Description                                  |
|------|----------------------------------------------|
| name | The name of the typedef                      |
| type | The defined type (as a generic type element) |

### Types

```json
{
  "declaration": "int"
}
```

```json
{
  "declaration": "void*"
}
```

```json
{
  "name": "ImGuiInputTextCallback",
  "type": {
    "declaration": "int (*ImGuiInputTextCallback)(ImGuiInputTextCallbackData* data)",
    "type_details": {
      "flavour": "function_pointer",
      "return_type": {
        "declaration": "int",
        "description": {
          "kind": "Builtin",
          "builtin_type": "int"
        }
      },
      "arguments": [
        {
          "name": "data",
          "type": {
            "declaration": "ImGuiInputTextCallbackData*",
            "description": {
              "kind": "Pointer",
              "inner_type": {
                "kind": "User",
                "name": "ImGuiInputTextCallbackData"
              }
            }
          },
          "is_array": false,
          "is_varargs": false
        }
      ]
    },
    "description": {
      // Contents omitted for brevity, see below
    }
  }
}
```

These are used in various elements in the JSON data, and represent a C type. Simple cases just have a
single `declaration` key that is the C-style declaration of the type, but more complex examples (currently limited to
function pointers) also have a `type_details` key that contains parsed details of the type in question.

| Key                  | Description                                                                   |
|----------------------|-------------------------------------------------------------------------------|
| declaration          | The C-style declaration of the type                                           |
| type_details         | Parsed details of the type (where applicable)                                 |
| type_details.flavour | The "flavour" (variant) of the type for which the details are supplied        |
| description          | A description of the type in machine-readable terms (see "type descriptions") |

`type_details.flavour` values:

| Value            | Meaning                                                                                                               |
|------------------|-----------------------------------------------------------------------------------------------------------------------|
| function_pointer | The type is a function pointer - the rest of the `type_details` block can be parsed as a normal function pointer type |

Function pointer `type_details` keys:

| Key         | Description                                             |
|-------------|---------------------------------------------------------|
| return_type | The function return type                                |
| arguments   | A list of function arguments (see "function arguments") |

### Type descriptions

Type descriptions (or "type comprehensions" as they are sometimes referred to in the Dear Bindings code) provide an
alternative mechanism for binding tools to understand the nature of a C type. Dear Bindings parses the C type data and
constructs a tree representing those elements. For binding to languages that cannot easily consume C-like declaration
syntax this is likely an easier starting point than the raw textual 'declaration' field.

An example type declaration for `int (*ImGuiInputTextCallback)(ImGuiInputTextCallbackData* data)` looks like this:

```json
{
  "kind": "Type",
  "name": "ImGuiInputTextCallback",
  "inner_type": {
    "kind": "Pointer",
    "inner_type": {
      "kind": "Function",
      "return_type": {
        "kind": "Builtin",
        "builtin_type": "int"
      },
      "parameters": [
        {
          "kind": "Type",
          "name": "data",
          "inner_type": {
            "kind": "Pointer",
            "inner_type": {
              "kind": "User",
              "name": "ImGuiInputTextCallbackData"
            }
          }
        }
      ]
    }
  }
}
```

It is formed from a nested series of elements that form a graph, each of which has a
`kind` key that indicates what it is.
So in the case above, we have the following type graph:

```
                                                                    // English-language breakdown:
Type (named ImGuiInputTextCallback)                                 // This is a type named "ImGuiInputTextCallback" 
\-- Pointer                                                         // That is a pointer to
    \-- Function                                                    // A function
        |-- [return type]                                           // With a return type of
        |   \- Builtin type (int)                                   // int
        \-- [parameters]                                            // And parameters, of which the first is
            \-- Type (named data)                                   // Named "data"
                \-- Pointer                                         // That is a pointer to
                    \-- User type (ImGuiInputTextCallbackData)      // The user type named "ImGuiInputTextCallbackData"                               
```

The possible `kind` values are:

| Kind     | Description                             |
|----------|-----------------------------------------|
| Type     | A type (usually, but not always, named) |
| Function | A function                              |
| Array    | An array of elements                    |
| Pointer  | A pointer to something                  |
| Builtin  | A built-in (intrinsic) type             |
| User     | A user-defined type                     |

Most of these contain a sub-type in their `inner_type` key - for example, an element with kind `Pointer` has
an `inner_type` key that contains the type it points to.

There are also a shared key that is applied to all types:

| Key             | Description                                                   |
|-----------------|---------------------------------------------------------------|
| storage_classes | The storage classes of the type (not applicable to functions) |

`storage_classes` is an array of zero or more of the following:

| Storage class |
|---------------|
| const         |
| volatile      |
| mutable       |

These correspond directly to the C storage classes of the same names.

The various types look like this:

#### Type

| Key        | Description                          |
|------------|--------------------------------------|
| name       | The name of the type (if it has one) |
| inner_type | The contained type                   |

A simple type declaration.

#### Function

| Key         | Description                         |
|-------------|-------------------------------------|
| return_type | The return type of the function     |
| parameters  | A list of the function's parameters |

A function declaration

#### Array

| Key        | Description                |
|------------|----------------------------|
| bounds     | The array bounds, if known |
| inner_type | The contained type         |

A simple array

#### Pointer

| Key          | Description                                              |
|--------------|----------------------------------------------------------|
| is_nullable  | Indicates if it is expected that the value can be null   |
| is_reference | Indicates the pointer was originally a C++ reference (&) |
| inner_type   | The contained type                                       |

`is_nullable` is emitted only when known - if omitted it should be taken to mean "it may or may not be valid for this to
be null".
`True` indicates that the pointer can be null, whilst `False` indicates that the pointer should never be null.

> At present, `is_nullable` is only ever not specified or `false` (in other words, Dear Bindings does not currently
> distinguish cases where a pointer is _definitely_ allowed to be null, only those where it is clearly _not_)

`is_reference` indicates that the pointer started out as a C++ reference (and thus could be turned into one in languages where that is a concept).
For obvious reasons, if `is_reference` is true then `is_nullable` will be false. 

#### Builtin

| Key          | Description       |
|--------------|-------------------|
| builtin_type | The specific type |

`Builtin` represents a known intrinsic type, from the following list:

| Type name          | Description                                                     |
|--------------------|-----------------------------------------------------------------|
| void               | No type                                                         |
| char               | Signed 8-bit integer                                            |
| unsigned_char      | Unsigned 8-bit integer                                          |
| short              | Signed 16-bit integer                                           |
| unsigned_short     | Unsigned 16-bit integer                                         |
| int                | Signed 32-bit integer (C `int`)                                 |
| unsigned_int       | Unsigned 32-bit integer (C `int`)                               |
| long               | Signed 32-bit integer (C `long`)                                |
| unsigned_long      | Unsigned 32-bit integer (C `long`)                              |
| long_long          | Signed 64-bit integer (C `long long`)                           |
| unsigned_long_long | Unsigned 64-bit integer  (C `long long`)                        |
| float              | 32-bit floating point value                                     |
| double             | 64-bit floating point value                                     |
| long_double        | Whatever your C compiler decides `long double` is               |
| bool               | Boolean (size dependent on what your compiler thinks `bool` is) |

(note that the nature of the C standard makes some of the precise type definitions here compiler-dependent,
so strictly speaking these are "best guesses")

#### User

| Key  | Description   |
|------|---------------|
| name | The type name |

This represents a reference to a user-defined type with the name given.

### Structs

A C structure. Forward-declarations for structures that do not have definitions provided in the header are included here
for reference, but without any internal details.

```json
{
  "name": "ImVec2",
  "original_fully_qualified_name": "ImVec2",
  "kind": "struct",
  "by_value": true,
  "forward_declaration": false,
  "is_anonymous": false,
  "fields": [
    {
      "name": "x",
      "is_array": false,
      "is_anonymous": false,
      "type": {
        "declaration": "float",
        "description": {
          "kind": "Builtin",
          "builtin_type": "float"
        }
      },
      "source_location": {
        "filename": "imgui.h",
        "line": 262
      }
    },
    {
      "name": "y",
      "is_array": false,
      "is_anonymous": false,
      "type": {
        "declaration": "float",
        "description": {
          "kind": "Builtin",
          "builtin_type": "float"
        }
      },
      "source_location": {
        "filename": "imgui.h",
        "line": 262
      }
    }
  ],
  "source_location": {
    "filename": "imgui.h"
  }
}
```

| Key                           | Description                                            |
|-------------------------------|--------------------------------------------------------|
| name                          | The C name of the structure                            |
| original_fully_qualified_name | The original C++ name of the structure                 |
| kind _(previously "type")_    | The type of the structure (either `struct` or `union`) |
| by_value                      | Is this structure normally pass-by-value?              |
| forward_declaration           | Is this a forward-declaration of the structure?        |
| is_anonymous                  | Is this an anonymous struct?                           |
| fields                        | List of contained fields                               |
| fields.name                   | The field name                                         |
| fields.is_array               | Is this field declared as an array?                    |
| fields.array_bounds           | The array bounds, if the field is an array             |
| fields.width                  | The bit width of the field, if specified               |
| fields.is_anonymous           | Is this field anonymous?                               |
| fields.type                   | The type of the field (see "types" for more details)   |
| fields.default_value          | The default value of the field, if specified           |

> Note that in versions v0.03 and earlier there was a `names` array that could contain multiple names if
> the original C++ declaration used a single declaration with multiple names. This was confusing and complicated
> matters for languages with no such concept, so instead such declarations are now emitted as multiple separate
> fields.

> Note that in versions v0.03 and earlier the `kind` key was called `type`. It was renamed to avoid
> confusion with the actual type information.

> The members of anonymous fields should be treated as being part of the owning struct, and thus their name is not
> relevant, but they are assigned a synthetic name for convenience.

#### Anonymous structs/unions

If a struct or union is anonymous, `is_anonymous` will be `true`, and the struct name will be set to a value of the
form `<anonymous0>`, where the trailing index makes it unique within the file (to avoid clashes, this naming is
deliberately chosen so as to not be a valid C++ type name). This name can be used to match
anonymous structures to their point-of-use in the `fields` list, where the `type` will contain the same name (
and `is_anonymous` will be set if the field is also anonymous). For example:

```json
{
  "fields": [
    {
      "names": [
        {
          "name": "<anonymous0>",
          "is_array": false
        }
      ],
      "is_anonymous": true,
      "type": {
        "declaration": "<anonymous0>"
      }
    }
  ]
}
```

#### Array fields

Array fields look like this, with the bounds given in `array_bounds`. Note that `array_bounds` can contain non-integer
values (such as enum elements or defines).

```json

{
  "names": [
    {
      "name": "MouseDown",
      "is_array": true,
      "array_bounds": "5"
    }
  ],
  "is_anonymous": false,
  "type": {
    "declaration": "bool"
  }
}
```

### Functions

Functions provided by the API.

Languages which support default function arguments can probably ignore any functions with `is_default_argument_helper`
set to `true`, as those are additional functions added to support simulating default arguments in C.

When using a version of ImGui with `ImStr` (string view) support, languages which use string views should probably
ignore any functions with `is_imstr_helper` set, as these are generated functions that give an alternative interface
using `const char*` instead of `ImStr`. Conversely, if you are using `const char*` for your strings, then you probably
want to ignore any functions with `has_imstr_helper` set.

```json
{
  "name": "ImGui_CreateContext",
  "original_fully_qualified_name": "ImGui::CreateContext",
  "return_type": {
    "declaration": "ImGuiContext*"
  },
  "arguments": [],
  "is_default_argument_helper": true,
  "is_manual_helper": false
}
```

| Key                           | Description                                                                                                                                                                       |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| name                          | The C name of the function                                                                                                                                                        |
| original_fully_qualified_name | The original C++ name of the function                                                                                                                                             |
| return_type                   | The return type of the function (as a type)                                                                                                                                       |
| arguments                     | A list of the function arguments                                                                                                                                                  |
| is_default_argument_helper    | Is this function a variant generated to simulate default arguments?                                                                                                               |
| is_manual_helper              | Is this a manually added function that doesn't exist in the original C++ API but was added specially to the C API? (at present only `ImVector_Construct` and `ImVector_Destruct`) |
| is_imstr_helper               | Is this function a helper variant added that takes `const char*` instead of `ImStr` arguments?                                                                                    |
| has_imstr_helper              | Is this function one which takes `ImStr` arguments and has had a `const char*` helper variant generated?                                                                          |                                                 |
| is_unformatted_helper         | Is this function a helper variant of a format string accepting function that accepts an pre-formatted string instead                                                              |
| is_static                     | Was this function originally static?                                                                                                                                              |
| original_class                | The name of the class this method originally belonged to, if any                                                                                                                  |

### Function arguments

Function arguments as they appear in function (and function pointer) metadata.

```json
{
  "name": "ctx",
  "type": {
    "declaration": "ImGuiContext*"
  },
  "is_array": false,
  "is_varargs": false,
  "default_value": "NULL"
}
```

```json
{
  "name": "v",
  "type": {
    "declaration": "float"
  },
  "is_array": true,
  "is_varargs": false,
  "array_bounds": "4"
}
```

| Key                 | Description                                                                  |
|---------------------|------------------------------------------------------------------------------|
| name                | The argument name                                                            |
| type                | The argument type                                                            |
| is_array            | Is this an array argument?                                                   |
| array_bounds        | Array bounds, if this is an array argument                                   |
| is_varargs          | Is this a varargs argument?                                                  |
| is_instance_pointer | Is this the instance pointer? (i.e. the 'this' pointer for a class function) | 
| default_value       | The default value, if present                                                |

### Generic keys

These are generic keys that can appear in the majority of primary elements (defines/typedefs/enums/enum
members/structs/fields/functions).

The `is_internal` key is intended as a broad hint that the function/struct/enum member in question may not be part of
the primary API and should probably be "hidden by default" if such a feature is available in the target language.
However, it is equally possible that advanced users may want or need to access these, so removing them entirely or
completely blocking access is not recommended either.

| Key             | Description                                                               |
|-----------------|---------------------------------------------------------------------------|
| comment         | Any comments related to this element (see "comments")                     |
| is_internal     | Is this an internal API member?                                           |
| conditionals    | What preprocessor conditionals apply to this element (see "Conditionals") |
| source_location | The location of this element in the original source header                |

#### Comments

Comment keys contain any comments which are related to an element. There are two types of comment - `preceding` comments
which appear immediately before an element in the source code, `attached` comments which appear immediately after the
element (on the same line). An element can have many preceding comments but only one attached comment.

```json
{
  "preceding": [
    "// Sizing Extra Options"
  ],
  "attached": "// Make outer width auto-fit to columns, overriding outer_size.x value. Only available when ScrollX/ScrollY are disabled and Stretch columns are not used."
}
```

A comment as it appears on an enum element:

```json
{
  "name": "ImGuiWindowFlags_NoTitleBar",
  "value": "1<<0",
  "comments": {
    "attached": "// Disable title-bar"
  }
},
```

| Key       | Description                                 |
|-----------|---------------------------------------------|
| preceding | An array of preceding comments (if present) |
| attached  | The attached comment (if present)           |

#### Conditionals

The `conditionals` key contains details on any preprocessor conditionals (`#ifdef`/`#if` blocks) that apply to a given
element.

Conditionals as they appear on two typedefs:

```json
[
  {
    "name": "ImWchar",
    "type": {
      "declaration": "ImWchar32"
    },
    "conditionals": [
      {
        "condition": "ifdef",
        "expression": "IMGUI_USE_WCHAR32"
      }
    ]
  },
  {
    "name": "ImWchar",
    "type": {
      "declaration": "ImWchar16"
    },
    "conditionals": [
      {
        "condition": "ifndef",
        "expression": "IMGUI_USE_WCHAR32"
      }
    ]
  }
]
```

| Key                     | Description                              |
|-------------------------|------------------------------------------|
| conditionals            | An array of conditionals for the element |
| conditionals.condition  | The condition applied (see below)        |
| conditionals.expression | The expression                           |

Conditional conditions are:

| Condition | Description                                                                                                              |
|-----------|--------------------------------------------------------------------------------------------------------------------------|
| ifdef     | Checks if a define is set (`#ifdef DEFINE`)                                                                              |
| ifndef    | Checks if a define is not set (`#ifndef DEFINE`)                                                                         |
| if        | Checks if the expression evaluates to a non-zero value (`#if EXPRESSION`)                                                |
| ifnot     | Checks if the expression evaluates to a zero value (no direct C equivalent, but behaves the same as `#if !(EXPRESSION)`) |

The `ifnot` conditional is used in the case where the element appears in the `#else` block of a `#if`, and thus
indicates that the element is used in the case where the `#if` evaluates to false.

#### Source location

`source_location` contains information about where the element originally appeared in the source file.

| Key      | Description              |
|----------|--------------------------|
| filename | The original filename    |
| line     | The original line number |

Either `filename` or `line` may be missing if that information is not known (for example, due to an element having been
generated
dynamically as part of the binding process). If neither is known then the entire `source_location` element will not be
present in the JSON.

For example:

```json
"source_location": {
"filename": "imgui.h",
"line": 570
}
```
