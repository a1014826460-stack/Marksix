$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Version = '0.69.0'
$InstallDir = 'C:\frp'
$Zip = "$env:TEMP\frp_${Version}_windows_amd64.zip"
$Url = "https://github.com/fatedier/frp/releases/download/v${Version}/frp_${Version}_windows_amd64.zip"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Invoke-WebRequest -Uri $Url -OutFile $Zip
Expand-Archive -Path $Zip -DestinationPath $env:TEMP -Force
Copy-Item "$env:TEMP\frp_${Version}_windows_amd64\frpc.exe" "$InstallDir\frpc.exe" -Force

@'
serverAddr = "8.163.93.151"
serverPort = 7000
auth.method = "token"
auth.token = "094b849eecfa4873a3bc374c5a82dddd"

[[proxies]]
name = "target-b-ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 60022
'@ | Set-Content -Path "$InstallDir\frpc.toml" -Encoding ASCII

if (-not (Get-Service -Name frpc-target-b -ErrorAction SilentlyContinue)) {
    New-Service `
        -Name frpc-target-b `
        -BinaryPathName "`"$InstallDir\frpc.exe`" -c `"$InstallDir\frpc.toml`"" `
        -DisplayName "FRP Client target-B" `
        -StartupType Automatic
}

sc.exe failure frpc-target-b reset= 60 actions= restart/3000/restart/3000/restart/3000 | Out-Null
Restart-Service frpc-target-b
Get-Service frpc-target-b
