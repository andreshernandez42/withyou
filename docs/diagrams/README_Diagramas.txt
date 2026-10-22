DIAGRAMAS - ANTEPROYECTO PLATAFORMA RESILIENTE

Contenido del ZIP
- plantuml/: fuentes .puml editables en PlantUML.
- png/: imágenes PNG listas para insertar en Word/PowerPoint.
- svg/: versiones vectoriales editables/escalables.
- dot/: fuentes Graphviz usadas para los renderizados entregados.

Índice
01_continuidad_personal           Modelo conceptual de continuidad personal.
02_motor_disparadores             Motor de eventos, solicitudes y check-in automático.
03_maquina_estados                Estados de persona/caso y prohibición de inferencias automáticas.
04_trusted_quorum                 Quórum N-de-M para solicitudes familiares.
05_vault_retencion_deslizante     Emergency Location Vault, TTL individual e Incident Hold.
06_adaptive_sampling              Muestreo adaptativo de ubicación.
07_multicanal_dtn                 Push/SMS/P2P/store-and-forward.
08_arquitectura_logica            Arquitectura lógica modular.
09_casos_uso                      Actores y casos de uso principales.
10_modelo_datos                   Modelo conceptual de datos.
11_secuencia_evento               Secuencia evento -> check-in -> escalamiento -> Welfare Check.
12_integracion_sirdec             SIRDEC Open Data, SICLICO y futura integración institucional.
13_infraestructura_entornos       DEV/TEST y arquitectura objetivo HA/DR.
14_seguridad_zonas_confianza      Zonas de confianza y controles de seguridad.
15_roadmap                        Roadmap evolutivo.
16_metodologia_dsr                Flujo metodológico de Design Science Research.
17_personal_safety_mode           Modo de seguridad personal ante vulnerabilidad inmediata.
18_gantt_16_semanas               Cronograma de 16 semanas.
19_evolucion_reportes_2026        Gráfica de reportes oficiales (no es diagrama PlantUML funcional).

Notas
1. Los .puml usan sintaxis PlantUML estándar, sin dependencia C4-PlantUML externa.
2. Los PNG/SVG fueron renderizados localmente a partir de representaciones equivalentes en Graphviz/matplotlib, para asegurar legibilidad en el entregable.
3. Puedes editar los .puml y renderizarlos con PlantUML Desktop, extensión de VS Code o plantuml.jar.
4. El documento Word utiliza una selección de estos diagramas; el ZIP conserva el conjunto completo para reorganización o futuras versiones.
