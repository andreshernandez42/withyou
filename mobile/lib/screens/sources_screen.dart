import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/api_service.dart';

class SourcesScreen extends StatefulWidget {
  final ApiService api;
  const SourcesScreen({super.key, required this.api});
  @override State<SourcesScreen> createState() => _SourcesScreenState();
}

class _SourcesScreenState extends State<SourcesScreen> {
  String? message;
  String sourceMessage = 'Consultando disponibilidad de los reportes.';
  Future<void> loadStatus() async {
    var next = 'No pudimos actualizar la información de sismos.';
    try {
      final status = await widget.api.sgcStatus();
      next = switch (status['state']) {
        'ACTIVE' => 'La consulta al SGC está activa.',
        'UNAVAILABLE' => 'Por ahora no hay conexión con el SGC.',
        'DELAYED' => 'Esperando la próxima actualización del SGC.',
        'PAUSED' => 'La consulta automática está pausada.',
        _ => 'Esperando la primera consulta al SGC.',
      };
    } catch (_) {
      // Show a connection message instead of stale diagnostics.
    }
    if (mounted) setState(() => sourceMessage = next);
  }
  bool busy = false, admin = false;
  @override void initState() { super.initState(); loadRole(); loadStatus(); }
  Future<void> loadRole() async {
    try { final user = await widget.api.me(); if (mounted) setState(() => admin = user['role'] == 'ADMIN'); }
    catch (_) { /* Diagnostic controls remain hidden until authorization is known. */ }
  }
  Future<void> synchronize() async {
    setState(() => busy = true);
    try {
      final result = await widget.api.syncSgc();
      if (mounted) setState(() => message = 'SGC: ${result['fetched']} consultados, ${result['created']} incorporados.');
    } catch (e) { if (mounted) setState(() => message = e.toString()); }
    finally { if (mounted) setState(() => busy = false); await loadStatus(); }
  }
  Future<void> openOfficialSite() async {
    try {
      final opened = await launchUrl(Uri.parse('https://www.sgc.gov.co/'), mode: LaunchMode.externalApplication);
      if (!opened && mounted) setState(() => message = 'No pudimos abrir el sitio. Inténtalo de nuevo.');
    } catch (_) { if (mounted) setState(() => message = 'No pudimos abrir el sitio. Inténtalo de nuevo.'); }
  }
  @override Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(20), children: [
    const Text('Información sobre sismos', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
    const SizedBox(height: 12),
    const Text('With You consulta los reportes del Servicio Geológico Colombiano y te pide confirmar tu estado cuando un evento es relevante para tu última ubicación guardada.'),
    const SizedBox(height: 12),
    const Text('Los avisos dependen de la publicación de la fuente y de tu conexión. No son una predicción ni un sistema de alerta temprana.'),
    const SizedBox(height: 20),
    Text(sourceMessage),
    TextButton(onPressed: loadStatus, child: const Text('Actualizar estado')),
    Card(child: ListTile(leading: const Icon(Icons.public), title: const Text('Servicio Geológico Colombiano'), subtitle: const Text('Consulta la información de la fuente oficial.'), trailing: IconButton(onPressed: openOfficialSite, tooltip: 'Abrir sitio oficial', icon: const Icon(Icons.open_in_new)))),
    if (admin) ...[
      const SizedBox(height: 20), const Text('Administración', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      OutlinedButton.icon(onPressed: busy ? null : synchronize, icon: const Icon(Icons.sync), label: const Text('Sincronizar SGC ahora')),
    ],
    if (message != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(message!)),
  ]);
}
