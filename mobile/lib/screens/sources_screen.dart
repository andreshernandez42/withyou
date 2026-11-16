import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SourcesScreen extends StatefulWidget {
  final ApiService api;
  const SourcesScreen({super.key, required this.api});
  @override State<SourcesScreen> createState() => _SourcesScreenState();
}

class _SourcesScreenState extends State<SourcesScreen> {
  Map<String, dynamic>? state;
  bool admin = false, busy = false;
  String? message;

  @override void initState() { super.initState(); load(); }

  Future<void> load() async {
    try {
      final me = await widget.api.me();
      final status = await widget.api.sgcStatus();
      if (mounted) setState(() {
        admin = me['role'] == 'ADMIN' || me['role'] == 'TESTER';
        state = status;
      });
    } catch (_) {
      if (mounted) setState(() => message = 'No se pudo consultar el estado de la fuente oficial.');
    }
  }

  Future<void> sync() async {
    setState(() => busy = true);
    try {
      final result = await widget.api.syncSgc();
      if (mounted) setState(() => message =
        'Consulta completada: ${result['fetched']} eventos examinados, ${result['created']} nuevos.');
      await load();
    } catch (_) {
      if (mounted) setState(() => message = 'La fuente oficial no respondió correctamente. Intenta nuevamente.');
    } finally { if (mounted) setState(() => busy = false); }
  }

  @override Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: load,
    child: ListView(padding: const EdgeInsets.fromLTRB(20, 24, 20, 100), children: [
      const Text('Información sísmica', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 24)),
      const SizedBox(height: 8),
      const Text('Eventos reportados por el Servicio Geológico Colombiano. Las publicaciones pueden tener demora; WithYou no predice terremotos.',
        style: TextStyle(color: Colors.black54)),
      const SizedBox(height: 18),
      Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(
        crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [Icon(Icons.public, color: Color(0xffb44b28)),
            SizedBox(width: 10), Expanded(child: Text('Servicio Geológico Colombiano',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)))]),
          const SizedBox(height: 12),
          Text(state?['last_sync_at'] == null
            ? 'Aún no hay una consulta automática confirmada.'
            : 'Última consulta: ${state!['last_sync_at']} (UTC)'),
          const SizedBox(height: 6),
          Text(state?['recent_feed_verified'] == true
            ? 'Se ha recibido al menos un evento reciente.'
            : 'La fuente de eventos recientes todavía no está verificada.',
            style: const TextStyle(color: Colors.black54)),
          if (admin) ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(onPressed: busy ? null : sync,
              icon: const Icon(Icons.sync), label: const Text('Comprobar fuente')),
          ],
        ]))),
      if (message != null) Padding(padding: const EdgeInsets.only(top: 12),
        child: Card(color: const Color(0xffedf3f7), child: Padding(
          padding: const EdgeInsets.all(14), child: Text(message!)))),
      const SizedBox(height: 18),
      const Text('Ante un sismo', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      const Text('Prioriza tu seguridad física y sigue las indicaciones de las autoridades. WithYou ayuda a confirmar tu bienestar con tus contactos; no sustituye los sistemas oficiales de emergencia.'),
    ]),
  );
}
