import 'package:flutter/material.dart';

/// Tarjeta de verificación basada en 01_alerta_sismica_confirmacion.png.
class SafetyCheckCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool isTest;
  final VoidCallback onSafe;
  final VoidCallback onHelp;
  final VoidCallback onReport;
  final VoidCallback onUnable;

  const SafetyCheckCard({
    super.key, required this.title, required this.subtitle,
    required this.onSafe, required this.onHelp,
    required this.onReport, required this.onUnable, this.isTest = false,
  });

  @override Widget build(BuildContext context) => Card(
    elevation: 4,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Icon(Icons.crisis_alert, color: isTest ? Colors.amber.shade800 : const Color(0xffbb303a)),
          const SizedBox(width: 8),
          Expanded(child: Text(isTest ? 'Simulación · $title' : title,
            style: const TextStyle(color: Color(0xffbb303a), fontWeight: FontWeight.w700))),
        ]),
        const SizedBox(height: 12),
        Text(subtitle, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        const Text('Cuando estés en un lugar seguro, confirma cómo te encuentras.',
          style: TextStyle(color: Colors.black54)),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: onSafe, icon: const Icon(Icons.check_circle_outline),
          label: const Text('Estoy a salvo'),
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xffe5f4e9), foregroundColor: const Color(0xff277451),
            padding: const EdgeInsets.all(15)),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: onHelp, icon: const Icon(Icons.volunteer_activism_outlined),
          label: const Text('Necesito ayuda'),
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xffc8303c), padding: const EdgeInsets.all(15)),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: onReport, icon: const Icon(Icons.notification_important_outlined),
          label: const Text('Reportar emergencia'),
          style: OutlinedButton.styleFrom(
            foregroundColor: const Color(0xffbb303a), padding: const EdgeInsets.all(15)),
        ),
        TextButton(onPressed: onUnable, child: const Text('No puedo salir')),
        Text(isTest
          ? 'Prueba interna. No se notifica a usuarios normales ni a autoridades.'
          : 'WithYou informa a contactos autorizados; no reemplaza los servicios de emergencia.',
          style: const TextStyle(fontSize: 12, color: Colors.black54)),
      ]),
    ),
  );
}
