import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../widgets/safety_check_card.dart';

class HomeScreen extends StatefulWidget {
  final ApiService api;
  const HomeScreen({super.key, required this.api});
  @override State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  Map<String, dynamic>? me, checkpoint;
  List<dynamic> notes = [], pending = [];
  Timer? timer, clock;
  bool busy = false, refreshing = false, foreground = true;
  String? flash;
  late final LocationService location;

  @override void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    location = LocationService(widget.api);
    refresh();
    timer = Timer.periodic(const Duration(seconds: 5), (_) { if (foreground) refresh(silent: true); });
    clock = Timer.periodic(const Duration(seconds: 1), (_) { if (mounted && foreground && pending.isNotEmpty) setState(() {}); });
  }
  @override void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    timer?.cancel(); clock?.cancel(); super.dispose();
  }
  @override void didChangeAppLifecycleState(AppLifecycleState state) {
    foreground = state == AppLifecycleState.resumed;
    if (foreground) refresh(silent: true);
  }

  Future<void> refresh({bool silent = false}) async {
    if (refreshing) return;
    refreshing = true;
    try {
      final values = await Future.wait<dynamic>([widget.api.me(), widget.api.notifications(pendingOnly: true), widget.api.pendingSafety()]);
      if (mounted) setState(() { me = values[0]; notes = values[1]; pending = values[2]; });
      try {
        final saved = await widget.api.latestCheckpoint();
        if (mounted) setState(() => checkpoint = saved);
      } on ApiException catch (e) {
        if (e.statusCode == 404 && mounted) setState(() => checkpoint = null);
      }
    } catch (e) {
      if (!silent && mounted) setState(() => flash = e.toString());
    } finally { refreshing = false; }
  }

  Map<String, dynamic>? get activeSafety => pending.isEmpty ? null : Map<String, dynamic>.from(pending.first);
  Map<String, dynamic>? get activeNote {
    final active = activeSafety;
    if (active == null) return null;
    for (final value in notes) {
      final metadata = value['metadata'] as Map?;
      if (metadata != null && ((active['event_id'] != null && metadata['event_id'] == active['event_id']) ||
          (active['welfare_check_id'] != null && metadata['welfare_check_id'] == active['welfare_check_id']))) {
        return Map<String, dynamic>.from(value);
      }
    }
    return null;
  }

  Future<void> respond(String status) async {
    if (busy) return;
    final active = activeSafety;
    final note = activeNote;
    setState(() => busy = true);
    try {
      await widget.api.respondSafety(status, eventId: active?['event_id'], welfareCheckId: active?['welfare_check_id']);
      // A notification acknowledgement must not turn a saved response into an apparent failure.
      if (note != null) { try { await widget.api.markRead(note['id']); } catch (_) { /* The saved safety status remains authoritative if acknowledgement fails. */ } }
      if (mounted) setState(() { pending.removeWhere((row) => row['id'] == active?['id']); flash = 'Tu estado se guardó correctamente.'; });
      await refresh(silent: true);
    } catch (e) { if (mounted) setState(() => flash = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> emergency() async {
    if (busy) return;
    final active = activeSafety;
    final isTest = active?['is_test'] == true;
    final confirmed = await showDialog<bool>(context: context, builder: (context) => AlertDialog(
      title: Text(isTest ? 'Registrar emergencia de simulacro' : 'Reportar una emergencia'),
      content: Text(isTest ? 'El reporte se guardará dentro del simulacro.' : 'Avisaremos a tus contactos de emergencia y compartiremos tu última ubicación guardada, si está disponible.'),
      actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Enviar aviso'))],
    ));
    if (confirmed != true || !mounted) return;
    setState(() => busy = true);
    try {
      final result = await widget.api.reportEmergency(eventId: active?['event_id'] as String?);
      if (mounted) setState(() => flash = result['is_test'] == true ? 'Emergencia registrada en el simulacro.' : 'Emergencia registrada. Se enviará el aviso a tus contactos habilitados.');
      await refresh(silent: true);
    } catch (e) { if (mounted) setState(() => flash = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> capture() async {
    if (busy) return;
    setState(() => busy = true);
    try {
      final saved = await location.captureAndUpload();
      if (mounted) setState(() { if (saved != null) checkpoint = saved; flash = saved == null ? 'Activa la ubicación y permite el acceso para guardar tu posición.' : 'Tu ubicación se guardó de forma privada.'; });
    } catch (_) { if (mounted) setState(() => flash = 'No pudimos guardar tu ubicación. Revisa los permisos y la conexión e inténtalo de nuevo.'); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> simulate() async {
    if (busy) return;
    setState(() => busy = true);
    try {
      if (checkpoint == null) throw const ApiException('Guarda primero una ubicación para participar en el simulacro.');
      final lat = (checkpoint!['location']?['lat'] as num?)?.toDouble();
      final lon = (checkpoint!['location']?['lon'] as num?)?.toDouble();
      if (lat == null || lon == null) throw const ApiException('Actualiza tu ubicación antes de iniciar el simulacro.');
      await widget.api.createTestEvent(lat: lat, lon: lon);
      await refresh();
      if (mounted) setState(() => flash = 'Simulacro de sismo creado.');
    } catch (e) { if (mounted) setState(() => flash = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }

  @override Widget build(BuildContext context) {
    final active = activeSafety;
    final name = (me?['full_name'] as String?)?.split(' ').first ?? '';
    final expires = DateTime.tryParse(active?['expires_at']?.toString() ?? '');
    final difference = expires?.difference(DateTime.now());
    final remaining = difference == null ? null : difference.isNegative ? Duration.zero : difference;
    final savedAt = DateTime.tryParse(checkpoint?['created_at']?.toString() ?? '')?.toLocal();
    return RefreshIndicator(onRefresh: refresh, child: ListView(
      physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
      children: [
        const Row(children: [Icon(Icons.shield_outlined, color: Color(0xffbc4e1b)), SizedBox(width: 8), Text('With You', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: Color(0xffbc4e1b)))]),
        const SizedBox(height: 24),
        Text(name.isEmpty ? 'Estamos contigo' : 'Estamos contigo,\n$name.', style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w800)),
        if (flash != null) ...[const SizedBox(height: 12), Semantics(liveRegion: true, child: Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: const Color(0xfffff3cf), borderRadius: BorderRadius.circular(14)), child: Text(flash!)))],
        const SizedBox(height: 18),
        SafetyCheckCard(
          title: active == null ? 'Tu red de cuidado' : active['event_type'] == 'EARTHQUAKE' ? 'Evento sísmico reportado' : active['event_id'] != null ? 'Evento reportado' : 'Verificación solicitada',
          subtitle: active == null ? '¿Cómo te encuentras?' : name.isEmpty ? '¿Estás bien?' : '$name, ¿estás bien?',
          remaining: remaining, isTest: active?['is_test'] == true,
          onSafe: busy ? null : () => respond('SAFE'), onHelp: busy ? null : () => respond('HELP_REQUIRED'), onEmergency: busy ? null : emergency,
        ),
        if (active != null) TextButton(onPressed: busy ? null : () => respond('UNABLE_TO_EXIT'), child: const Text('No puedo salir del lugar donde estoy')),
        const SizedBox(height: 18),
        FilledButton.icon(onPressed: busy ? null : capture, icon: const Icon(Icons.my_location), label: const Text('Guardar mi ubicación'), style: FilledButton.styleFrom(backgroundColor: const Color(0xff4d795f), padding: const EdgeInsets.all(14))),
        Text(checkpoint == null ? 'Aún no tienes una ubicación guardada. Guárdala para recibir avisos relevantes para tu zona.' : savedAt == null ? 'Tu última ubicación se recuperó de forma segura.' : 'Última ubicación guardada: ${savedAt.day}/${savedAt.month} ${savedAt.hour.toString().padLeft(2, '0')}:${savedAt.minute.toString().padLeft(2, '0')}.', style: const TextStyle(color: Colors.black54)),
        const SizedBox(height: 8),
        OutlinedButton.icon(onPressed: () => Navigator.pushNamed(context, '/safety'), icon: const Icon(Icons.shield_outlined), label: const Text('Modo seguridad')),
        if (me?['role'] == 'ADMIN') ...[
          const SizedBox(height: 24), const Text('Laboratorio de pruebas', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const Text('Simulacro identificado como prueba. Solo avisa a administradores cercanos.'),
          Align(alignment: Alignment.centerLeft, child: ActionChip(label: const Text('Simular sismo'), onPressed: busy ? null : simulate)),
        ],
        const SizedBox(height: 24), const Text('Notificaciones', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        ...notes.where((x) => x['type'] != 'SAFETY_CHECK' && x['type'] != 'WELFARE_CHECK').take(5).map((x) => Card(child: ListTile(leading: const Icon(Icons.notifications_none), title: Text(x['title'] ?? 'Aviso'), subtitle: Text(x['body'] ?? '')))),
      ],
    ));
  }
}
