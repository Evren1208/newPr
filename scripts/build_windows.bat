@echo off
cd /d %~dp0\..
if not exist .venv (
  py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name ClassTeacherToolbox --collect-all pptx --collect-all docx main.py
if not exist dist\config mkdir dist\config
copy /Y config\ai.example.json dist\config\ai.example.json >nul

echo.
echo Build complete: dist\ClassTeacherToolbox.exe
pause
