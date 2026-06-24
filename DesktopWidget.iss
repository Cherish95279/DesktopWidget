#define MyAppName "DesktopWidget"
#define MyAppVersion "1.2.0"
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
SetupIconFile=icons\app.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
DisableWelcomePage=no
UninstallDisplayIcon={app}\{#MyAppExeName}

AppPublisherURL=https://github.com/Cherish95279
AppSupportURL=https://github.com/Cherish95279/DesktopWidget/issues
AppUpdatesURL=https://github.com/Cherish95279/DesktopWidget/releases
VersionInfoDescription=珍爱桌面小工具安装程序
VersionInfoCopyright=Copyright (C) 2026 Cherish
VersionInfoCompany=Cherish
VersionInfoTextVersion=1.2.0

[Files]
Source: "dist\DesktopWidget\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userstartmenu}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent