#define MyAppName "DesktopWidget"
#define MyAppVersion "1.5.4"
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
OutputBaseFilename=DesktopWidget-v{#MyAppVersion}-windows-x64-Setup
SetupIconFile=icons\app.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableDirPage=no
UninstallDisplayIcon={app}\{#MyAppExeName}

AppPublisherURL=https://github.com/Cherish95279
AppSupportURL=https://github.com/Cherish95279/DesktopWidget/issues
AppUpdatesURL=https://github.com/Cherish95279/DesktopWidget/releases
VersionInfoDescription=珍爱桌面小工具安装程序
VersionInfoCopyright=Copyright (C) 2026 Cherish
VersionInfoCompany=Cherish
VersionInfoTextVersion=1.5.4

[Languages]
Name: "chinesesimplified"; MessagesFile: "installer\ChineseSimplified.isl"
Name: "english"; MessagesFile: "installer\Default.isl"
Name: "chinesetraditional"; MessagesFile: "installer\ChineseTraditional.isl"
Name: "japanese"; MessagesFile: "installer\Japanese.isl"
Name: "french"; MessagesFile: "installer\French.isl"
Name: "spanish"; MessagesFile: "installer\Spanish.isl"
Name: "korean"; MessagesFile: "installer\Korean.isl"
Name: "german"; MessagesFile: "installer\German.isl"

[Files]
Source: "dist\DesktopWidget\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userstartmenu}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
  i: Integer;
  CmdLine: String;
begin
  // 静默结束所有正在运行的 DesktopWidget.exe 进程
  Exec('taskkill', '/f /im DesktopWidget.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 检测 MSIX 包是否已安装
  Result := True;
  TempFile := ExpandConstant('{tmp}') + '\msix_check.txt';
  // 删除可能残留的旧文件
  DeleteFile(TempFile);

  // 使用 PowerShell 的 Out-File 写入结果，避免 > 重定向的转义问题
  CmdLine := '-NoProfile -ExecutionPolicy Bypass -Command "if (Get-AppxPackage -Name ''Cherish95279.DesktopWidget'') { ''found'' | Out-File -FilePath ''';
  CmdLine := CmdLine + TempFile + ''' -Encoding UTF8 }"';

  Exec('powershell.exe', CmdLine, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if LoadStringsFromFile(TempFile, Lines) then
  begin
    for i := 0 to GetArrayLength(Lines) - 1 do
    begin
      if Pos('found', Lines[i]) > 0 then
      begin
        // MSIX 已安装，弹窗确认
        if MsgBox(ExpandConstant('{cm:MsixDetectedMsg}'),
                  mbConfirmation, MB_YESNO) = IDNO then
        begin
          Result := False;
        end;
        Break;
      end;
    end;
  end;
  DeleteFile(TempFile);
end;