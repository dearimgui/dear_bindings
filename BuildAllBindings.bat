@echo off
setlocal enableDelayedExpansion

rem Path to Dear ImGui files
set IMGUI_PATH=..\imgui

rem Output path
set OUTPUT_PATH=generated

if not exist "generated" mkdir "generated"
if not exist "generated\backends" mkdir "generated\backends"

rem Process main imgui.h header

echo.
echo Processing imgui.h
echo.
python dear_bindings.py -o %OUTPUT_PATH%\dcimgui %IMGUI_PATH%\imgui.h
IF ERRORLEVEL 1 GOTO fail

rem Process imgui_internal.h header

echo.
echo Processing imgui_internal.h
echo.
python dear_bindings.py -o %OUTPUT_PATH%\dcimgui_internal --include %IMGUI_PATH%\imgui.h %IMGUI_PATH%\imgui_internal.h
IF ERRORLEVEL 1 GOTO fail

rem Process backends

for %%n in (
	allegro5
	android
	dx9
	dx10
	dx11
	dx12
	glfw
	glut
	opengl2
	opengl3
	sdl2
	sdlrenderer2
	sdl3
	sdlrenderer3
	vulkan
	wgpu
	win32
) do (
	echo.
	echo Processing %%n
	echo.
	python dear_bindings.py --backend --include %IMGUI_PATH%\imgui.h --imconfig-path %IMGUI_PATH%\imconfig.h -o %OUTPUT_PATH%\backends\dcimgui_impl_%%n %IMGUI_PATH%\backends\imgui_impl_%%n.h
	IF ERRORLEVEL 1 GOTO fail
)

echo.
echo Processing completed
goto end

:fail
echo.
echo Processing failed
:end
