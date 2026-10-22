BASE DE DATOS

Motor recomendado: PostgreSQL 16 + PostGIS 3.4.

Opción A - Docker Compose
1. Copie .env.demo a .env (solo laboratorio).
2. Ejecute: docker compose up -d db
3. El directorio database/init se ejecuta automáticamente en una BD nueva.

Opción B - Motor PostgreSQL existente
1. Cree base y usuario.
2. Ejecute database/init/00_extensions.sql.
3. Ejecute database/init/01_schema.sql.
4. Configure DATABASE_URL en backend/.env o variable de entorno.
5. Ejecute: python -m app.seed desde backend/ para crear datos demo.

Privacidad
- Las coordenadas exactas se guardan cifradas en encrypted_location.
- coarse_lat/coarse_lon sirven como prefiltrado aproximado de laboratorio y no sustituyen controles de acceso.
- Cada checkpoint tiene expires_at; el backend ejecuta eliminación deslizante por registro.
- incident_hold conserva solo registros pertinentes y tiene expiración independiente.
