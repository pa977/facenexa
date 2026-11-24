[Setup]
AppName=Face Nexa
AppVersion=1.0.0
DefaultDirName={autopf}\Face Nexa
DefaultGroupName=Face Nexa
UninstallDisplayIcon={app}\FaceNexa.exe
Compression=lzma2
SolidCompression=yes
OutputDir=userdocs:Inno Setup Examples Output
OutputBaseFilename=FaceNexaSetup
PrivilegesRequired=lowest

[Files]
Source: "dist\FaceNexa.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Face Nexa"; Filename: "{app}\FaceNexa.exe"
Name: "{group}\Uninstall Face Nexa"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Face Nexa"; Filename: "{app}\FaceNexa.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\FaceNexa.exe"; Description: "Launch Face Nexa"; Flags: nowait postinstall skipifsilent
