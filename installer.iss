[Setup]
AppId=ALSHAFAQLAB
AppName=AL-SHAFAQ LAB
AppVersion=1.0.5
AppPublisher=AL-SHAFAQ LAB
DefaultDirName={autopf}\AL-SHAFAQ LAB
DefaultGroupName=AL-SHAFAQ LAB
UninstallDisplayIcon={app}\AL-SHAFAQ LAB.exe
OutputDir=output
OutputBaseFilename=AL-SHAFAQ-LAB-Setup-1.0.5
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=yes
AppMutex=ALSHAFaqLabMutex

[Files]
Source: "dist\AL-SHAFAQ LAB\AL-SHAFAQ LAB.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace
Source: "dist\AL-SHAFAQ LAB\update_helper.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace
Source: "dist\AL-SHAFAQ LAB\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace

[Icons]
Name: "{autoprograms}\AL-SHAFAQ LAB"; Filename: "{app}\AL-SHAFAQ LAB.exe"
Name: "{autodesktop}\AL-SHAFAQ LAB"; Filename: "{app}\AL-SHAFAQ LAB.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\AL-SHAFAQ LAB.exe"; Description: "Launch AL-SHAFAQ LAB"; Flags: nowait postinstall