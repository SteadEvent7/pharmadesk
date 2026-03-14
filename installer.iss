[Setup]
AppId={{2D380CEF-AEAA-4450-8259-9E90F81EA902}
AppName=PharmaDesk
AppVersion=1.0.0.4
AppPublisher=Votre pharmacie
DefaultDirName={autopf}\PharmaDesk
DefaultGroupName=PharmaDesk
SetupIconFile=assets\Logo2.ico
OutputDir=dist\installer
OutputBaseFilename=PharmaDeskSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\PharmaDesk\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\PharmaDesk"; Filename: "{app}\PharmaDesk.exe"
Name: "{commondesktop}\PharmaDesk"; Filename: "{app}\PharmaDesk.exe"

[Run]
Filename: "{app}\PharmaDesk.exe"; Description: "Lancer PharmaDesk"; Flags: nowait postinstall skipifsilent