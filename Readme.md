Dear Bindings
-------------

Dear Bindings is tool to generate a C API for [Dear ImGui](https://github.com/ocornut/imgui), and metadata so other languages can easily generate their own bindings on top.

At present, it only converts `imgui.h` (i.e. the main Dear ImGui API), but in the future it should also support `imgui_internal.h` and potentially other ImGui-related files that may be useful for advanced users. 

It should be compatible with ImGui v1.82 onwards (some earlier versions also work but compatibility isn't guaranteed).

The intention with Dear Bindings is to try and produce a C header file which is as close as reasonably possible to what a human would generate, and thus special attention has been given to preserving formatting, comments and the like such that (maybe!) a user won't even necessarily realise that they are working with a wrapper.

## Generated code differences

The generated header should hopefully be relatively self-explanatory, but here are some of the key differences between it and the original ImGui C++ API:

| C++ | C | Notes |
|-----|---|-------|
| `ImGui::Text()` | `ImGui_Text()` | The ImGui namespace is removed and everything inside it prefixed with `ImGui_`. |
| `void ImGuiStyle::ScaleAllSizes(float scale_factor)` | `void ImGuiStyle_ScaleAllSizes(ImGuiStyle* self, float scale_factor)` | Structures are also flattened, with member functions renamed to prefix the structure name and (if not static) take a pointer to the structure as the first argument. |
| `void ColorConvertRGBtoHSV(float r, float g, float b, float& out_h, float& out_s, float& out_v)` | `void ImGui_ColorConvertRGBtoHSV(float r, float g, float b, float* out_h, float* out_s, float* out_v)` | Non-const references are converted to pointers. |
| `ImDrawList::PathLineTo(const ImVec2& pos)` | `ImDrawList_PathLineTo(ImDrawList* self, ImVec2 pos)` | Const references are simply passed by-value. |

### Default parameters

Since default parameters aren't available in C, multiple versions of functions are generated as a way of emulating them. Specifically, the "vanilla" version of a function will have all of the default arguments elided and set to their default, which a new version with `Ex` appended to the name will be generated that allows all arguments to be set. For example, this function:

```c
bool IsMouseDragging(ImGuiMouseButton button, float lock_threshold = -1.0f);
```

...becomes:

```c
bool ImGui_IsMouseDraggingEx(ImGuiMouseButton button, float lock_threshold /* = -1.0f */);
bool ImGui_IsMouseDragging(ImGuiMouseButton button); // Implied lock_threshold = -1.0f
```

As can be seen, `ImGui_IsMouseDragging()` takes just the (non-defaulted) `button` argument and internally defaults `lock_threshold` to `-1.0f`, whilst the `ImGui_IsMouseDraggingEx()` version allows both parameters to be set.

### Overloaded functions

In cases of overloaded functions in the original API, since C does not support this the function names are changed to disambiguate them. The code attempts to generate a reasonably sensible disambiguation by using a minimal set of the argument types necessary to uniquely identify each version of the function. This behaviour combines with the expansion for default parameters, so for example:

```c
bool ListBoxHeader(const char* label, int items_count, int height_in_items = -1);
bool ListBoxHeader(const char* label, const ImVec2& size = ImVec2(0, 0));
```

Becomes these four functions in the C header:

```c
bool ImGui_ListBoxHeaderExInt(const char* label, int items_count, int height_in_items /* = -1 */);
bool ImGui_ListBoxHeaderInt(const char* label, int items_count); // Implied height_in_items = -1
bool ImGui_ListBoxHeaderEx(const char* label, ImVec2 size /* = ImVec2(0, 0) */);
bool ImGui_ListBoxHeader(const char* label);     
```

The generated code and metadata preserves `#define` settings for various options (such as `IMGUI_USE_BGRA_PACKED_COLOR`), so those can be utilised as normal. If the original ImGui code and user code is being compiled separately then care must be taken that the `#define` settings are the same. For programmatic binding generation, the exported metadata contains information on which elements are affected by `#ifdef` checks so appropriate action to match behaviour in the target language can be taken.

### Constructors/destructors

Constructors/destructors for heap objects are removed from the API, as ensuring the correct allocation/deallocation behaviour across library boundaries can be awkward and so it seemed safer to avoid them. ImGui support zero-clear construction, so data structures can almost always safely be constructed with a simple `memset()`.

The one exception to this is `ImVector`. There is one specific case where the ImGui API - `ImFontGlyphRangesBuilder::BuildRanges()` -  requires the user to construct a vector that the library will then write into (potentially performing allocations library-side). To facilitate this, two helper functions called `ImVector_Construct()` and `ImVector_Destruct()` are provided which can be used to construct and subsequently destroy an ImVector (of any type).

Utilising these, the safe pattern for using `ImFontGlyphRangesBuilder::BuildRanges()` looks like this:

```c
ImFontGlyphRangesBuilder builder;
memset(&builder, 0, sizeof(builder));

ImFontGlyphRangesBuilder_Clear(&builder);
ImFontGlyphRangesBuilder_AddChar(&builder, L'!');
ImFontGlyphRangesBuilder_AddChar(&builder, L'?');

ImVector_ImWchar ranges;
ImVector_Construct(&ranges); // Construct new vector using ImGui's heap functions

ImFontGlyphRangesBuilder_BuildRanges(&builder, &ranges);

for (int i = 0; i < ranges.Size; i++)
{
  // Do something with ranges.Data[i]
}

ImVector_Destruct(&ranges); // Free the vector using ImGui's heap functions
```

### Templates

Templates are expanded into their concrete instantiations, so for example `ImVector<char>` gets expanded to `ImVector_char`. Functions are removed from templates because at present in the cases where they presently exist they are generally hard to use correctly from C (see the above notes about constructors) and thus it seemed simpler/safer to have users interact directly with the structure contents if they need to.

> See the note above about `ImVector_Construct` for an exception to this rule.

### Removed functionality

These minor features are removed, mostly because they either rely on C++ language features to function correctly or are helpers that don't make sense as part of the bindings.

```
ImGuiOnceUponAFrame
ImNewDummy
ImNewWrapper
```

---

# Requirements

* Python 3.8x+ (3.7x+ most likely works but 3.8 is the currently tested version)
* [ply](https://www.dabeaz.com/ply/) (Python Lex-Yacc, v3.11 tested)

# Usage

Assuming you have `imgui.h` in the project directory, and would like to generate `cimgui.h`, `cimgui.cpp` and `cimgui.json`:

```
python main.py -o cimgui imgui.h
```

Once you have generated `cimgui.h` and `cimgui.cpp` they can be compiled in a project to generate a C API (`cimgui.h` defines the API, whilst `cimgui.cpp` implements the binding to the underlying C++ code).

Other command line arguments:

```
usage: main.py [-h] --output OUTPUT [--templatedir TEMPLATEDIR] src

Convert Dear ImGui headers to C

positional arguments:
  src                   Path to source header file to process (generally
                        imgui.h)

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Path to output file(s). This should have no extension,
                        as <output>.h, <output>.cpp and <output>.json will be
                        written.
  --templatedir TEMPLATEDIR, -t TEMPLATEDIR
                        Path to the implementation template directory
                        (default: ./src/templates)

Result code 0 is returned on success, 1 on conversion failure and 2 on
parameter errors

Process finished with exit code 0
```

Generated metadata
------------------

You can find details of the `cimgui.json` file format [here](MetadataFormat.md).

License
-------

Dear Bindings is copyright (c) 2021 Ben Carter, and licensed under the MIT license. See [LICENSE.txt](LICENSE.txt) for full details.

Contact
-------

You can get in touch with me via e-mail at "contact _at-sign_ shironekolabs _dot_ com".