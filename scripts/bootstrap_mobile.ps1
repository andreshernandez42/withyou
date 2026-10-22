$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Mobile = Join-Path $Root "mobile"
$Tmp = Join-Path $env:TEMP ("withyou-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Tmp | Out-Null
Copy-Item (Join-Path $Mobile "lib") $Tmp -Recurse
Copy-Item (Join-Path $Mobile "pubspec.yaml") $Tmp
Copy-Item (Join-Path $Mobile "analysis_options.yaml") $Tmp
Set-Location $Mobile
flutter create . --platforms=android,ios --project-name with_you
Remove-Item (Join-Path $Mobile "lib") -Recurse -Force
Copy-Item (Join-Path $Tmp "lib") $Mobile -Recurse
Copy-Item (Join-Path $Tmp "pubspec.yaml") $Mobile -Force
Copy-Item (Join-Path $Tmp "analysis_options.yaml") $Mobile -Force
flutter pub get
python (Join-Path $Root "scripts/patch_mobile.py")
Write-Host "Mobile bootstrap completado."
