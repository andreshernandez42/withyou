import 'package:flutter/material.dart';

class SafetyCheckCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final VoidCallback? onSafe, onHelp, onEmergency;
  final Duration? remaining;
  final bool isTest;

  const SafetyCheckCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.onSafe,
    required this.onHelp,
    required this.onEmergency,
    this.remaining,
    this.isTest = false,
  });

  @override
  Widget build(BuildContext context) {
    final seconds = remaining?.inSeconds ?? 0;
    final countdown = '${(seconds ~/ 60).toString().padLeft(2, '0')}:${(seconds % 60).toString().padLeft(2, '0')}';
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(.08), blurRadius: 30, offset: const Offset(0, 12))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Icon(Icons.monitor_heart_outlined, color: Color(0xffb72f36)),
          const SizedBox(width: 8),
          Expanded(child: Text(isTest ? 'Simulacro · $title' : title,
              style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xffb72f36)))),
        ]),
        const SizedBox(height: 18),
        Text(subtitle, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        const Text('Cuando estés en un lugar seguro, confirma cómo te encuentras.', style: TextStyle(color: Colors.black54)),
        if (remaining != null) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: const Color(0xfffff6d6), borderRadius: BorderRadius.circular(16)),
            child: Row(children: [
              const Icon(Icons.timer_outlined, color: Color(0xff8b6b24)),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(countdown, style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w800)),
                const Text('para confirmar tu estado'),
              ])),
            ]),
          ),
          const SizedBox(height: 12),
          const Text('Si el tiempo termina, tu estado quedará como «Sin confirmar».', style: TextStyle(fontSize: 12, color: Colors.black54)),
        ],
        const SizedBox(height: 20),
        FilledButton.icon(
          key: const Key('safety-safe'), onPressed: onSafe,
          icon: const Icon(Icons.check_circle_outline), label: const Text('Estoy a salvo'),
          style: FilledButton.styleFrom(backgroundColor: const Color(0xffe8f4ed), foregroundColor: const Color(0xff2f7551), padding: const EdgeInsets.all(16)),
        ),
        const SizedBox(height: 10),
        FilledButton.icon(
          key: const Key('safety-help'), onPressed: onHelp,
          icon: const Icon(Icons.volunteer_activism_outlined), label: const Text('Necesito ayuda'),
          style: FilledButton.styleFrom(backgroundColor: const Color(0xffb72f36), padding: const EdgeInsets.all(16)),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          key: const Key('safety-emergency'), onPressed: onEmergency,
          icon: const Icon(Icons.sos_outlined), label: const Text('Reportar emergencia'),
          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xffb72f36), side: const BorderSide(color: Color(0xffb72f36)), padding: const EdgeInsets.all(16)),
        ),
        const SizedBox(height: 12),
        const Text('Tus respuestas se comparten con tus contactos de emergencia que hayan aceptado la invitación. Esta app no sustituye los servicios de emergencia.', style: TextStyle(fontSize: 12, color: Colors.black54)),
      ]),
    );
  }
}
