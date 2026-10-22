from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]/'mobile'
manifest=root/'android/app/src/main/AndroidManifest.xml'
if manifest.exists():
    s=manifest.read_text(encoding='utf-8')
    perms=[
        '<uses-permission android:name="android.permission.INTERNET" />',
        '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />',
        '<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />',
    ]
    for p in perms:
        if p not in s:
            s=s.replace('<manifest', '<manifest',1)
            pos=s.find('>')+1
            s=s[:pos]+'\n    '+p+s[pos:]
    manifest.write_text(s,encoding='utf-8')
plist=root/'ios/Runner/Info.plist'
if plist.exists():
    s=plist.read_text(encoding='utf-8')
    key='<key>NSLocationWhenInUseUsageDescription</key>'
    if key not in s:
        insert='\n\t<key>NSLocationWhenInUseUsageDescription</key>\n\t<string>La aplicación usa ubicación para generar checkpoints de emergencia autorizados.</string>\n'
        s=s.replace('</dict>',insert+'</dict>')
    plist.write_text(s,encoding='utf-8')
print('Parches de permisos aplicados.')
