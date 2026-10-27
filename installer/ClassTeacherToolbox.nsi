Unicode true

!include "MUI2.nsh"

!define APP_NAME "班主任工具箱"
!define APP_VERSION "0.2.0"
!define APP_EXE "ClassTeacherToolbox.exe"
!define APP_PUBLISHER "Evren"
!define APP_REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\ClassTeacherToolbox"

Name "${APP_NAME}"
OutFile "..\installer-output\ClassTeacherToolbox-Setup-V0.2.exe"
InstallDir "$LOCALAPPDATA\Programs\ClassTeacherToolbox"
InstallDirRegKey HKCU "Software\ClassTeacherToolbox" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "启动班主任工具箱"
!define MUI_FINISHPAGE_LINK "打开项目主页"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/Evren1208/newPr"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"

Section "主程序" SEC_MAIN
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File "..\dist\${APP_EXE}"

  CreateDirectory "$APPDATA\ClassTeacherToolbox"
  SetOutPath "$APPDATA\ClassTeacherToolbox"
  File "/oname=ai.example.json" "..\config\ai.example.json"

  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\ClassTeacherToolbox" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${APP_REGKEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${APP_REGKEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${APP_REGKEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${APP_REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${APP_REGKEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${APP_REGKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${APP_REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${APP_REGKEY}" "NoRepair" 1

  CreateDirectory "$SMPROGRAMS\班主任工具箱"
  CreateShortcut "$SMPROGRAMS\班主任工具箱\班主任工具箱.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\班主任工具箱\卸载班主任工具箱.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\班主任工具箱.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "Uninstall"
  SetShellVarContext current

  Delete "$DESKTOP\班主任工具箱.lnk"
  Delete "$SMPROGRAMS\班主任工具箱\班主任工具箱.lnk"
  Delete "$SMPROGRAMS\班主任工具箱\卸载班主任工具箱.lnk"
  RMDir "$SMPROGRAMS\班主任工具箱"

  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "${APP_REGKEY}"
  DeleteRegKey HKCU "Software\ClassTeacherToolbox"

  ; 用户自己的 AI 配置和生成材料不自动删除，避免误删数据。
SectionEnd
