Dear Bindings
-------------

Dear Bindings is tool to generate a C API for [Dear ImGui](https://github.com/ocornut/imgui), and metadata so other languages can easily generate their own bindings on top (see our [Software using Dear Bindings](https://github.com/dearimgui/dear_bindings/wiki/Software-using-Dear-Bindings) list). 

At present, it can convert `imgui.h` (i.e. the main Dear ImGui API), and has (semi-experimental, but not totally untested) support for `imgui_internal.h` and most of the backend headers.

It should be compatible with Dear ImGui v1.84 onwards (some earlier versions also work but compatibility isn't guaranteed).

The intention with Dear Bindings is to try and **produce a C header file which is as close as reasonably possible to what a human would generate**, and thus special attention has been given to preserving formatting, comments and the like such that (maybe!) a user won't even necessarily realise that they are working with a wrapper.

# Latest Prebuilt Versions

You can find prebuilt versions (consisting of `dcimgui.h`, `dcimgui.cpp`, `dcimgui.json` 
and their equivalents for `imgui_internal.h`) 
for both `master` and `docking` branch in our 
[Continuous Integration (Actions)](https://github.com/dearimgui/dear_bindings/actions) page. 
For a given build, click "Artifacts" to find them.

# Requirements

* Python 3.10+
* [ply](https://www.dabeaz.com/ply/) (Python Lex-Yacc, v3.11 tested)

(ply can be automatically installed via `requirements.txt` - see "Usage" below for more details)

# Recent changes

* v0.11 (WIP) introduces a small-but-significant breaking change as the output file names are now `dcimgui` instead of `cimgui` (to disambiguate in cases where people are using multiple binding generators) 
* v0.10 adds (somewhat experimental) support for comverting `imgui_internal.h`.
* v0.08 adds structure default values to metadata, and fixes a few bugs.
* v0.07 adds some new metadata elements, new examples and fixes a number of bugs (especially around metadata and backends).
* v0.06 fixes a small issue with ImGui v1.90.0 WIP where `ListBox()` and `ComboBox()` have deprecated variants that cause name clashes. Those variants are now renamed to `ImGui_ListBoxObsolete()` and `ImGui_ComboBoxObsolete()` respectively.
* v0.05 introduced significantly enhanced type information in the JSON output, and experimental support for generating bindings for ImGui backends
  * Note that there are a number of small changes in the JSON format related to this that will require modification to code that consumes the JSON files - search [Changelog.txt](Changelog.txt) for `BREAKING CHANGE` for full details
* v0.04 introduced a number of bugfixes and other tweaks

You can see a full list of recent changes [here](Changelog.txt).

# Differences from cimgui

Dear Bindings was designed as a potential replacement to the [cimgui](https://github.com/cimgui/cimgui) project.

| dear_bindings                                                                                            | cimgui |
|----------------------------------------------------------------------------------------------------------|----|
| Written in Python                                                                                        | Written in Lua |
| Preserve comments and alignment                                                                          | -- |
| Use more polished rules to name functions, resolve overloads and offer simplified and \*Ex alternatives. | -- |
| Experimental bindings for imgui_internal.h (as a separate file).                                         | Can generate bindings for imgui_internal.h (but output is in the same header, making it difficult to tell if you are using a public or internal function). |
| Currently not mature, more likely to have issues                                                         | Has been used for years. |

# Usage

If you don't have a Python environment, then install Python (at least version 3.10), and then in the project directory run:

```commandline
pip install -r requirements.txt
```

...which should install the prerequisite Python libraries automatically.

Then you can do:

```commandline
python dear_bindings.py -o dcimgui ../imgui/imgui.h
```

...and if you want imgui_internal.h available as well:

```commandline
python dear_bindings.py -o dcimgui_internal --include ../imgui/imgui.h ../imgui/imgui_internal.h
```

For an all-in-one build (Windows-only right now), you can do:

```commandline
BuildAllBindings.bat
```

With a target `imgui.h`, Dear Bindings generates `dcimgui.h` (defines the C
API), `dcimgui.cpp` (implements the C binding to the underlying C++ code), and
`dcimgui.json` (a metadata file, see below).

Correspondingly, `dcimgui_internal.h`, `dcimgui_internal.cpp` and 
`dcimgui_internal.json` contain the bindings for `imgui_internal.h`, which has
a lot of useful functions for more advanced use-cases that are not exposed in the
main public API for one reason or another.

Using a C++ compiler, you can compile `dcimgui.cpp` along with `imgui/*.cpp`
into a static library. This can be used to integrate with a C program, for
example, by including the generated C header `dcimgui.h` and linking against
this library.

### Customising prefixes

By default, Dear Bindings will use namespaces/class names to generate prefixes
for names in the output - for example, `ImGui::Begin()` will become `ImGui_Begin()`.

However, you may want to customise these, especially if you are looking for
compatibility with cimgui or similar. To achieve this, you can specify 
`--custom-namespace-prefix` to replace `ImGui_` with something else - for example,
`--custom-namespace-prefix ig` will result in `ImGui::Begin()` becoming `igBegin()`
instead. For more detailed customisation, you can use `--replace-prefix`, which
allows any arbitrary name prefix to be replaced - for example, 
`--replace-prefix ImFont_=if` will result in `ImFont_FindGlyph()` becoming
`ifFontGlyph()` (and all other `ImFont_` names following suit). You can specify as
many `--replace-prefix` arguments as you like (although the results are undefined
if you specify overlapping prefixes).

(for reference, `--custom-namespace-prefix Foo` is just a simplified syntax for
`--replace-prefix ImGui_=Foo`)


### All command line arguments

```commandline
Dear Bindings: parse Dear ImGui headers, convert to C and output metadata.
usage: dear_bindings.py [-h] -o OUTPUT [-t TEMPLATEDIR]
                        [--nopassingstructsbyvalue]
                        [--nogeneratedefaultargfunctions]
                        [--generateunformattedfunctions] [--backend]
                        [--imgui-include-dir IMGUI_INCLUDE_DIR]
                        [--backend-include-dir BACKEND_INCLUDE_DIR]
                        [--include INCLUDE] [--imconfig-path IMCONFIG_PATH]
                        [--emit-combined-json-metadata]
                        [--custom-namespace-prefix CUSTOM_NAMESPACE_PREFIX]
                        [--replace-prefix REPLACE_PREFIX]
                        src

positional arguments:
  src                   Path to source header file to process (generally
                        imgui.h)

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Path to output files (generally dcimgui). This should
                        have no extension, as <output>.h, <output>.cpp and
                        <output>.json will be written.
  -t TEMPLATEDIR, --templatedir TEMPLATEDIR
                        Path to the implementation template directory
                        (default: ./src/templates)
  --nopassingstructsbyvalue
                        Convert any by-value struct arguments to pointers (for
                        other language bindings)
  --nogeneratedefaultargfunctions
                        Do not generate function variants with implied default
                        values
  --generateunformattedfunctions
                        Generate unformatted variants of format string
                        supporting functions
  --backend             Indicates that the header being processed is a backend
                        header (experimental)
  --imgui-include-dir IMGUI_INCLUDE_DIR
                        Path to ImGui headers to use in emitted include files.
                        Should include a trailing slash (eg "Imgui/").
                        (default: blank)
  --backend-include-dir BACKEND_INCLUDE_DIR
                        Path to ImGui backend headers to use in emitted files.
                        Should include a trailing slash (eg
                        "Imgui/Backends/"). (default: same as --imgui-include-
                        dir)
  --include INCLUDE     Path to additional .h files to include (e.g. imgui.h
                        if converting imgui_internal.h, and/or the file you
                        set IMGUI_USER_CONFIG to, if any)
  --imconfig-path IMCONFIG_PATH
                        Path to imconfig.h. If not specified, imconfig.h will
                        be assumed to be in the same directory as the source
                        file, or the directory immediately above it if
                        --backend is specified
  --emit-combined-json-metadata
                        Emit a single combined metadata JSON file instead of
                        emitting separate metadata JSON files for each header
  --custom-namespace-prefix CUSTOM_NAMESPACE_PREFIX
                        Specify a custom prefix to use on emitted
                        functions/etc in place of the usual namespace-derived
                        ImGui_
  --replace-prefix REPLACE_PREFIX
                        Specify a name prefix and something to replace it with
                        as a pair of arguments of the form <old prefix>=<new
                        prefix>. For example, "--replace-prefix ImFont_=if
                        will" result in ImFont_FindGlyph() becoming
                        ifFontGlyph() (and all other ImFont_ names following
                        suit)

Result code 0 is returned on success, 1 on conversion failure and 2 on
parameter errors
```

# Generated metadata

You can find details of the `dcimgui.json` file format [here](MetadataFormat.md).

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
python dear_bindings.py --backend --include ..\imgui\imgui.h -o dcimgui_impl_opengl3 imgui\backends\imgui_impl_opengl3.h
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

All other backends (except Metal/OSX) at least appear to convert cleanly with reasonable looking results. Further
testing (adding to the list above) would be most appreciated.
The Metal/OSX backends have been excluded for now as the Objective-C code in them looks like it would probably make life
painful. Please provide feedback if there is a use-case for these.
The `BuildAllBindings.bat` file can be used to convert `imgui.h`, `imgui_internal.h` and all of the convertable backends.

### Examples

Some simple example/test programs can be found in the `examples/` folder.
They assume that C bindings files (for both `imgui.h` and `imgui_internal.h`) have been generated into the `generated/` folder (`BuildAllBindings.bat` can be used to do this automatically on Windows, I'm afraid other OSes will have to do it by hand for now).

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

Credits
-------

Developed by Ben Carter and other [contributers](https://github.com/dearimgui/dear_bindings/graphs/contributors).

Much of the `imgui_internal.h` support was added by @ZimM-LostPolygon.

License
-------

Dear Bindings is copyright (c) 2021-2024 and licensed under the MIT license. See [LICENSE.txt](../LICENSE.txt) for full details.

Contact
-------

You can get in touch with me via e-mail at "contact _at-sign_ shironekolabs _dot_ com".
