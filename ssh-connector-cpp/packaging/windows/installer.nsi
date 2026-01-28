; SSH Connector NSIS Installer Script

!include "MUI2.nsh"

; General
Name "SSH Connector"
OutFile "ssh-connector-installer.exe"
InstallDir "$PROGRAMFILES\SSH Connector"
InstallDirRegKey HKLM "Software\SSH Connector" "Install_Dir"
RequestExecutionLevel admin

; Interface Settings
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Install"
    SetOutPath $INSTDIR

    ; Copy files
    File "ssh-connector.exe"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Create start menu shortcuts
    CreateDirectory "$SMPROGRAMS\SSH Connector"
    CreateShortcut "$SMPROGRAMS\SSH Connector\SSH Connector.lnk" "$INSTDIR\ssh-connector.exe"
    CreateShortcut "$SMPROGRAMS\SSH Connector\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    ; Create desktop shortcut
    CreateShortcut "$DESKTOP\SSH Connector.lnk" "$INSTDIR\ssh-connector.exe"

    ; Write registry keys
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "DisplayName" "SSH Connector"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "Publisher" "SSH Connector"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "DisplayVersion" "1.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector" "NoRepair" 1
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\ssh-connector.exe"
    Delete "$INSTDIR\Uninstall.exe"

    ; Remove shortcuts
    Delete "$SMPROGRAMS\SSH Connector\SSH Connector.lnk"
    Delete "$SMPROGRAMS\SSH Connector\Uninstall.lnk"
    RMDir "$SMPROGRAMS\SSH Connector"
    Delete "$DESKTOP\SSH Connector.lnk"

    ; Remove directories
    RMDir "$INSTDIR"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SSH Connector"
    DeleteRegKey HKLM "Software\SSH Connector"
SectionEnd
