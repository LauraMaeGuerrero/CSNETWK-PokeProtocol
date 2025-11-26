@echo off
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building PokeProtocol executable...
cd Pokeprotocol
pyinstaller --onefile --name PokeProtocol --add-data "pokemon.csv;." main.py

echo.
echo Build complete! Executable is in: Pokeprotocol\dist\PokeProtocol.exe
echo.
pause
