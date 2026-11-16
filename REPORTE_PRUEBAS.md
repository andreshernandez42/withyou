# Validación de WithYou · 16 de noviembre de 2026

| Comprobación | Resultado |
| --- | --- |
| Catálogo reciente SGC consultado en vivo | 89 registros oficiales en una ventana de 24 horas, consultada a las 13:22, hora de Colombia. Último registro devuelto a las 10:25:22, magnitud 3,2. Ningún registro satisfizo el umbral de magnitud 4,5 dentro de los últimos 30 minutos. |
| Suite del backend | 48 pruebas aprobadas, 77 % de cobertura de líneas en esa ejecución. Una prueba adicional del flujo completo del catálogo reciente pasó tras el ajuste final. |
| Prueba del flujo | GeoJSON controlado, checkpoint cercano y lejano, fallo del origen, recuperación, deduplicación y retiro del aviso al responder «Estoy a salvo». |
| App | Ajustes en la tarjeta y en el estado de la fuente. Prueba final del APK, fidelidad visual exacta y entrega a una app cerrada pendientes en Android. |
| Despliegue | Incluye configuración y script de arranque. Docker Desktop y Flutter no están disponibles para repetir el despliegue y la compilación móvil de este ZIP. |

La evidencia está en `docs/validation/sgc_recent_live.json`, `pytest_actual.txt` y `pytest_sgc_recent.txt`. `sgc_live.json` contiene la comprobación previa de metadatos de EPIS y no corresponde al feed de avisos. El resultado controlado demuestra el procesamiento de la aplicación, mientras la consulta de 24 horas confirma la lectura de datos del proveedor.
