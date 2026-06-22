#define MyAppName "DesktopWidget"
#define MyAppVersion "1.1.6"
#define MyAppPublisher "Cherish"
#define MyAppExeName "DesktopWidget.exe"
#define MyAppId "{{8E2B3C4D-5F6A-7B8C-9D0E-1F2A3B4C5D6E}}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist
OutputBaseFilename=DesktopWidget-v{#MyAppVersion}-win64-Cherish-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
DisableWelcomePage=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\DesktopWidget\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
; 只给当前用户创建快捷方式（不需要管理员权限）
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userstartmenu}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent