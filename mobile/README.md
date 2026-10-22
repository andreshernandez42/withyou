# Mobile Flutter - With You

El código de `lib/` está listo para integrarse en un proyecto Flutter. Este paquete no incluye binarios ni secretos de Firebase.

## Crear carpetas de plataforma si no existen

Con Flutter instalado, desde `mobile/`:

```bash
flutter create . --platforms=android,ios --project-name with_you
flutter pub get
```

Luego verifica que los archivos `lib/` entregados se conserven. Si `flutter create` reemplaza `lib/main.dart`, restaura el archivo desde el ZIP.

## Ejecutar

Android emulator:
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Android físico en la misma LAN:
```bash
flutter run --dart-define=API_BASE_URL=http://IP_DE_TU_PC:8000/api/v1
```

El MVP usa polling de notificaciones mientras la app está abierta. FCM queda como integración opcional posterior porque exige credenciales de un proyecto Firebase propio que no deben inventarse ni compartirse en el repositorio.
