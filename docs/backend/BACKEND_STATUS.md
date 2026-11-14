# Estado de cierre del backend

## Cerrado para MVP académico

- Auth con Argon2, JWT de acceso y refresh rotatorio.
- Roles USER / TESTER / ADMIN.
- Registro de dispositivos y push token.
- Trusted Circle con revocación inmediata.
- Consent Policy y quórum N-de-M.
- Emergency Location Vault cifrado.
- TTL deslizante por checkpoint y `incident_hold` temporal.
- Grants temporales COARSE/EXACT de ubicación.
- Simulador de sismo, deslizamiento, inundación, incendio y otros eventos.
- Filtro sísmico configurable por magnitud, edad, distancia y vigencia.
- Safety Check, SAFE, HELP_REQUIRED, UNABLE_TO_EXIT y NO_RESPONSE.
- SOS explícito.
- Personal Safety Mode.
- Welfare Check familiar y verificación comunitaria con opt-in.
- Casos ciudadanos + referencias institucionales separadas.
- SIRDEC Open Data/SICLICO read-only.
- SGC adapter configurable e IDEAM adapter sin endpoint inventado.
- Auditoría, transparencia de accesos y revocación.
- Workers de mantenimiento (Celery/Redis) y fallback in-process.
- Nginx con dos instancias API para simulación de failover.
- Registro de experimentos y métricas.
- Pruebas automatizadas.

## Condicionado a terceros / fase experimental

- FCM real requiere credenciales Firebase.
- SMS real requiere proveedor/credenciales.
- P2P/DTN requiere cierre en cliente móvil/dispositivos físicos.
- SGC/IDEAM en vivo requieren verificación del endpoint/capa al ejecutar.
- Integración operacional SIRDEC/Alerta Rosa/Fiscalía/Policía requiere autorización institucional.
- Multi-región real no forma parte del MVP; se simula HA/DR local.
