; AI Touch Desktop — Inno Setup installer script
; Produces a real Windows installer (Setup.exe) that:
;   - Installs the app into Program Files
;   - Creates a Start Menu shortcut
;   - Creates a Desktop shortcut
;   - Adds an Uninstall entry in "Apps & Features"
;
; To build: install Inno Setup (https://jrsoftware.org/isinfo.php) on
; Windows, open this file in the Inno Setup Compiler, and click Compile.
; (The GitHub Actions workflow does this automatically — see
; .github/workflows/build.yml — so you don't need to do this by hand.)

#define MyAppName "AI Touch Desktop"
#define MyAppVersion "1.0"
#define MyAppPublisher "Muslim Islam Organization"
#define MyAppExeName "AITouchDesktop.exe"

[Setup]
AppId={{8F3B2C1A-6D4E-4A9B-9C2D-AI-TOUCH-DESK}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AI Touch Desktop
DefaultGroupName=AI Touch Desktop
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=AITouchDesktop-Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AITouchDesktop.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
