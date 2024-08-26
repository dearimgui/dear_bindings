Dear Bindings
-------------

Dear Bindings is tool to generate a C API for [Dear ImGui](https://github.com/ocornut/imgui), and metadata so other languages can easily generate their own bindings on top (see our [Software using Dear Bindings](https://github.com/dearimgui/dear_bindings/wiki/Software-using-Dear-Bindings) list). 

At present, it only converts `imgui.h` (i.e. the main Dear ImGui API), but in the future it should also support `imgui_internal.h` and potentially other ImGui-related files that may be useful for advanced users.

It should be compatible with Dear ImGui v1.84 onwards (some earlier versions also work but compatibility isn't guaranteed).

The intention with Dear Bindings is to try and **produce a C header file which is as close as reasonably possible to what a human would generate**, and thus special attention has been given to preserving formatting, comments and the like such that (maybe!) a user won't even necessarily realise that they are working with a wrapper.

# Latest Prebuilt Versions

You can find prebuilt versions (consisting of cimgui.h, cimgui.cpp, cimgui.json) for both `master` and `docking` branch in our [Continuous Integration (Actions)](https://github.com/dearimgui/dear_bindings/actions) page. For a given build, click "Artifacts" to find them.

# Requirements

* Python 3.8x+ (3.7x+ most likely works but 3.8 is the currently tested version)
* [ply](https://www.dabeaz.com/ply/) (Python Lex-Yacc, v3.11 tested)

# Recent changes

* v0.07 adds some new metadata elements, new examples and fixes a number of bugs (especially around metadata and backends).
* v0.06 fixes a small issue with ImGui v1.90.0 WIP where `ListBox()` and `ComboBox()` have deprecated variants that cause name clashes. Those variants are now renamed to `ImGui_ListBoxObsolete()` and `ImGui_ComboBoxObsolete()` respectively.
* v0.05 introduced significantly enhanced type information in the JSON output, and experimental support for generating bindings for ImGui backends
  * Note that there are a number of small changes in the JSON format related to this that will require modification to code that consumes the JSON files - search [Changelog.txt](Changelog.txt) for `BREAKING CHANGE` for full details
* v0.04 introduced a number of bugfixes and other tweaks

You can see a full list of recent changes [here](Changelog.txt).

# Differences with cimgui

Dear Bindings was designed as a potential replacement to the [cimgui](https://github.com/cimgui/cimgui) project.

| dear_bindings | cimgui |
|----|----|
| Written in Python | Written in Lua |
| Preserve comments and alignment | -- |
| Use more polished rules to name functions, resolve overloads and offer simplified and \*Ex alternatives. | -- |
| Currently cannot generates bindings for imgui_internal.h. | Can generate bindings for imgui_internal.h (but output is in the same header, making it difficult to tell if you are using a public or internal function). |
| Currently not mature, more likely to have issues | Has been used for years. |

# Usage

```
python dear_bindings.py -o cimgui ../imgui/imgui.h
```

With a target `imgui.h`, Dear Bindings generates `cimgui.h` (defines the C
API), `cimgui.cpp` (implements the C binding to the underlying C++ code), and
`cimgui.json` (a metadata file, see below).

Using a C++ compiler, you can compile `cimgui.cpp` along with `imgui/*.cpp`
into a static library. This can be used to integrate with a C program, for
example, by including the generated C header `cimgui.h` and linking against
this library.

Other command line arguments:

```
usage: dear_bindings.py [-h] -o OUTPUT [-t TEMPLATEDIR]
                        [--nopassingstructsbyvalue] [--backend]
                        src

positional arguments:
  src                   Path to source header file to process (generally
                        imgui.h)

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Path to output files (generally cimgui). This should
                        have no extension, as <output>.h, <output>.cpp and
                        <output>.json will be written.
  -t TEMPLATEDIR, --templatedir TEMPLATEDIR
                        Path to the implementation template directory
                        (default: ./src/templates)
  --nopassingstructsbyvalue
                        Convert any by-value struct arguments to pointers (for
                        other language bindings)
  --generateunformattedfunctions
                        Generate unformatted variants of format string
                        supporting functions
  --backend             Indicates that the header being processed is a backend
                        header (experimental)
  --imgui-include-dir IMGUI_INCLUDE_DIR
                        Path to ImGui headers to use in emitted include files.
                        Should include a trailing slash (eg "Imgui/").
                        (default: blank)
  --include INCLUDED_FILE
                        Path to additional .h files to include (e.g. imgui.h
                        if converting imgui_internal.h, and/or the file you
                        set IMGUI_USER_CONFIG to, if any)

Result code 0 is returned on success, 1 on conversion failure and 2 on
parameter errors
```

# Generated metadata

You can find details of the `cimgui.json` file format [here](MetadataFormat.md).

# Generated code differences

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
ImGuiOnceUponAFrame, ImNewDummy, ImNewWrapper, ImGui::Value
```

### Converting backends

A semi-experimental feature has been added to generate binding for the various backends.
To convert a backend header, use `--backend` on the command line - for example:

```commandline
python dear_bindings.py --backend -o cimgui_impl_opengl3 imgui\backends\imgui_impl_opengl3.h
```

Tested Backends:
* Win32
* DirectX 9
* DirectX 11
* DirectX 12
* OpenGL 2
* OpenGL 3
* Vulkan
* SDL 2

All other backends (except Metal/OSX) at least appear to convert cleanly with reasonable looking results. Further testing (adding to the list above) would be most appreciated.
The Metal/OSX backends have been excluded for now as the Objective-C code in them looks like it would probably make life painful. Please provide feedback if there is a use case for these.
The `BuildAllBindings.bat` file can be used to convert imgui.h and all of the convertable backends.

### Examples

Some simple example/test programs can be found in the `examples/` folder.
They assume that C bindings files have been generated into the `generated/` folder (`BuildAllBindings.bat` can be used to do this automatically on Windows, I'm afraid other OSes will have to do it by hand for now).

`example_null` is a very basic app that simply runs a few cycles of the ImGui update/draw loop. It has no rendering engine so nothing actually gets drawn.
`example_win32_directx9` and `example_sdl2_opengl2` are the ImGui samples of the same names with minimal changes to port it into C.

### Building examples on Windows

The Examples.sln solution file can be used to build all three examples on Windows using Visual Studio 2022 (older versions may work too).
On Windows `ImGuiLib` is used as an ancillary project to provide ImGui wrapped up as a static library with C function exports.
To build `example_sdl2_opengl`, you will need to have SDL2 installed and the SDL2_DIR environment variable set to point to your SDL2 installation.

### Building examples on Linux/OSX

`example_null` and `example_sdl2_opengl2` both contain makefiles that should build correctly on OSX and Linux (tested on Mac OS Sonoma and Ubuntu 22.04.3 LTS).
You'll need SDL2 installed via `brew install SDL2` on OSX or `apt install libsdl2-dev` or similar for that sample to work.
These samples do not use ImGuiLib but just link the required object files directly.

Software using Dear Bindings
----------------------------

See our [Software using Dear Bindings](https://github.com/dearimgui/dear_bindings/wiki/Software-using-Dear-Bindings) wiki page.

License
-------

Dear Bindings is copyright (c) 2021-2024 Ben Carter, and licensed under the MIT license. See [LICENSE.txt](../LICENSE.txt) for full details.

Contact
-------

You can get in touch with me via e-mail at "contact _at-sign_ shironekolabs _dot_ com".
