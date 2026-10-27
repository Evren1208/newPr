@echo off
setlocal
cd /d %~dp0\..

if not exist .venv (
  py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1

pyinstaller --noconfirm --clean --onefile --windowed --name ClassTeacherToolbox --collect-all pptx --collect-all docx main.py
if errorlevel 1 exit /b 1

if not exist dist\config mkdir dist\config
copy /Y config\ai.example.json dist\config\ai.example.json >nul

set MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe
if not exist "%MAKENSIS%" set MAKENSIS=C:\Program Files\NSIS\makensis.exe
if not exist "%MAKENSIS%" (
  echo.
  echo NSIS is not installed.
  echo Install NSIS first, then run this script again.
  echo https://nsis.sourceforge.io/Download
  exit /b 1
)

if not exist installer-output mkdir installer-output
pushd installer
"%MAKENSIS%" ClassTeacherToolbox.nsi
set BUILD_RESULT=%ERRORLEVEL%
popd

if not "%BUILD_RESULT%"=="0" exit /b %BUILD_RESULT%

echo.
echo Installer created:
echo installer-output\ClassTeacherToolbox-Setup-V0.2.exe
endlocal
pause
