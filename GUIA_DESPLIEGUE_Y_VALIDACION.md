# WithYou · Consumo de avisos sísmicos

Actualización del 16 de noviembre de 2026.

El backend consulta el [catálogo oficial de sismos recientes del SGC](https://api.sgc.gov.co/biweekly/biweekly_earthquakes) cada 30 segundos. La app consulta las verificaciones pendientes cada 5 segundos en primer plano. Los avisos se generan después de la publicación del reporte y según magnitud, edad, distancia y vigencia de la ubicación guardada.

## Actualización en Windows

Usa la carpeta completa para una instalación nueva o aplica el ZIP de parche desde la raíz de la instalación existente. El parche conserva `.env.demo` y los volúmenes. Mantén la misma carpeta y nombre de proyecto de Docker.

En tu `.env.demo`, verifica que aparezcan estas opciones una sola vez.

```dotenv
SGC_SOURCE=biweekly
SGC_POLL_ENABLED=true
SGC_POLL_INTERVAL_SECONDS=30
EARTHQUAKE_MIN_MAGNITUDE=4.5
EARTHQUAKE_MAX_AGE_MINUTES=30
EARTHQUAKE_CHECKPOINT_MAX_AGE_MINUTES=60
EARTHQUAKE_MAX_DISTANCE_KM=150
```

```powershell
cd C:\dev\withyou
.\scripts\start_demo.ps1
docker compose --env-file .env.demo logs --tail=60 worker beat
```

En una instalación demo nueva puedes usar `.\scripts\start_demo.ps1 -Seed` para crear cuentas. La cuenta inicial debe tener rol ADMIN. El endpoint autenticado `GET /api/v1/official/sgc/status` devuelve el estado y la última consulta exitosa. Una consulta exitosa puede no traer avisos elegibles.

```powershell
cd C:\dev\withyou\mobile
flutter pub get
flutter analyze
flutter test
flutter devices
flutter run -d emulator-5554
```

En el emulador guarda una ubicación y verifica que se restaure al reabrir la app. Con el administrador puedes simular un sismo y probar **Estoy a salvo**, **Necesito ayuda** y **Reportar emergencia**. El simulacro se registra aparte y no produce SOS reales. El acceso a diagnósticos y simulación requiere ADMIN. Un usuario habitual recibe únicamente las verificaciones que le correspondan.

Para producción, usa HTTPS, claves propias, PostgreSQL respaldado y `ALLOW_TEST_ENDPOINTS=false`. La entrega con la app cerrada requiere completar y verificar la integración del cliente con Firebase Cloud Messaging y un teléfono Android; el sondeo de Flutter funciona en primer plano.
