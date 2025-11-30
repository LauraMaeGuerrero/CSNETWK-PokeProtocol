@echo off
echo Compiling PokeProtocol executables with PyInstaller...
echo.

REM Change to the Pokeprotocol directory
cd /d "c:\Users\Mark\Documents\csnetwk\final\CSNETWK-PokeProtocol\Pokeprotocol"

echo Compiling GUI executable...
pyinstaller --onefile --windowed --name "PokeProtocol-GUI" --add-data "sprites;sprites" --add-data "*.gif;." --add-data "*.csv;." gui.py

echo.
echo Compiling CLI executable...
pyinstaller --onefile --console --name "PokeProtocol-CLI" --add-data "sprites;sprites" --add-data "*.gif;." --add-data "*.csv;." main.py

echo.
echo Compilation complete!
echo GUI executable: dist\PokeProtocol-GUI.exe
echo CLI executable: dist\PokeProtocol-CLI.exe
echo.
pause