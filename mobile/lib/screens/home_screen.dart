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

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic>? me;
  Map<String, dynamic>? checkpoint;
  List<dynamic> notes = [], pending = [], events = [];
  Timer? timer;
  bool busy = false;
  String? flash;
  late final LocationService location;

  @override void initState() {
    super.initState();
    location = LocationService(widget.api);
    refresh();
    timer = Timer.periodic(const Duration(seconds: 8), (_) => refresh(silent: true));
  }

  @override void dispose() { timer?.cancel(); super.dispose(); }

  Future<void> refresh({bool silent = false}) async {
    try {
      final u = await widget.api.me();
      final n = await widget.api.notifications(pendingOnly: true);
      final p = await widget.api.pendingSafety();
      final e = await widget.api.officialEvents();
      Map<String, dynamic>? cp;
      try { cp = await widget.api.latestCheckpoint(); } catch (_) { /* Aún no tiene uno. */ }
      if (mounted) setState(() {
        me = u; notes = n; pending = p; events = e; checkpoint = cp;
      });
    } catch (_) {
      if (!silent && mounted) setState(() => flash = 'No fue posible actualizar la información. Comprueba tu conexión.');
    }
  }

  bool get isAdmin => me?['role'] == 'ADMIN' || me?['role'] == 'TESTER';

  Map<String, dynamic>? get activeSafety {
    if (pending.isEmpty) return null;
    final s = Map<String, dynamic>.from(pending.first);
    for (final raw in notes) {
      final n = Map<String, dynamic>.from(raw);
      final md = Map<String, dynamic>.from(n['metadata'] ?? {});
      if ((s['event_id'] != null && md['event_id'] == s['event_id']) ||
          (s['welfare_check_id'] != null && md['welfare_check_id'] == s['welfare_check_id'])) {
        return n;
      }
    }
    return {
      'id': null, 'type': 'SAFETY_CHECK',
      'metadata': {'event_id': s['event_id'], 'welfare_check_id': s['welfare_check_id'], 'is_test': s['is_test'] == true},
    };
  }

  Future<void> respond(String status) async {
    final n = activeSafety;
    if (n == null || busy) return;
    setState(() => busy = true);
    try {
      final md = Map<String, dynamic>.from(n['metadata'] ?? {});
      await widget.api.respondSafety(status,
        eventId: md['event_id']?.toString(),
        welfareCheckId: md['welfare_check_id']?.toString());
      if (n['id'] != null) await widget.api.markRead(n['id'].toString());
      await refresh();
      if (mounted) setState(() => flash = 'Tu estado quedó registrado.');
    } catch (e) {
      if (mounted) setState(() => flash = 'No se pudo registrar tu respuesta: $e');
    } finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> reportEmergency(bool isTest) async {
    if (isTest) {
      setState(() => flash = 'Esta simulación no puede enviar un SOS real.');
      return;
    }
    final confirm = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: const Text('¿Avisar a tus contactos?'),
      content: const Text('WithYou notificará a tus contactos autorizados. No contacta automáticamente a las autoridades ni garantiza rescate.'),
      actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
        FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Enviar SOS'))],
    ));
    if (confirm != true || !mounted) return;
    setState(() => busy = true);
    try {
      await widget.api.startSos(message: 'Necesito ayuda tras evento sísmico');
      if (mounted) setState(() => flash = 'Solicitud enviada a tus contactos autorizados.');
    } catch (e) {
      if (mounted) setState(() => flash = 'No se pudo enviar la solicitud: $e');
    } finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> capture() async {
    setState(() => busy = true);
    try {
      final cp = await location.captureAndUpload();
      if (mounted) setState(() => flash = cp == null
        ? 'Activa la ubicación del dispositivo y concede el permiso.'
        : 'Ubicación de referencia guardada de forma segura.');
      if (cp != null) await refresh();
    } catch (e) {
      if (mounted) setState(() => flash = 'No pudimos guardar tu ubicación: $e');
    } finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> simulate(String type) async {
    if (busy) return;
    setState(() => busy = true);
    try {
      final cp = await widget.api.latestCheckpoint();
      final loc = Map<String, dynamic>.from(cp['location'] ?? {});
      if (loc['lat'] == null || loc['lon'] == null) {
        throw StateError('Guarda un checkpoint antes de simular.');
      }
      final result = await widget.api.createTestEvent(type: type,
        lat: (loc['lat'] as num).toDouble(), lon: (loc['lon'] as num).toDouble());
      await refresh();
      if (mounted) setState(() => flash =
        'Simulación creada. ${result['affected_users']?.length ?? 0} usuarios de laboratorio incluidos.');
    } catch (e) {
      if (mounted) setState(() => flash = 'Para probar una alerta, primero guarda tu ubicación. $e');
    } finally { if (mounted) setState(() => busy = false); }
  }

  @override Widget build(BuildContext context) {
    final alert = activeSafety;
    final metadata = Map<String, dynamic>.from(alert?['metadata'] ?? {});
    final isTest = metadata['is_test'] == true;
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(padding: const EdgeInsets.fromLTRB(20, 20, 20, 100), children: [
        Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('With You', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 23, color: Color(0xffb44b28))),
            const SizedBox(height: 4),
            Text(me == null ? 'Cargando...' : 'Estamos contigo, ${me!['full_name']}.',
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
          ])),
          const CircleAvatar(child: Icon(Icons.person)),
        ]),
        if (flash != null) Padding(padding: const EdgeInsets.only(top: 12), child: Card(
          color: const Color(0xfffff4cd), child: Padding(padding: const EdgeInsets.all(12), child: Text(flash!)))),
        const SizedBox(height: 16),
        if (alert != null)
          SafetyCheckCard(
            title: 'Sismo reportado', subtitle: '¿Estás bien?', isTest: isTest,
            onSafe: busy ? () {} : () => respond('SAFE'),
            onHelp: busy ? () {} : () => respond('HELP_REQUIRED'),
            onUnable: busy ? () {} : () => respond('UNABLE_TO_EXIT'),
            onReport: busy ? () {} : () => reportEmergency(isTest),
          )
        else Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(
          crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Icon(Icons.verified_user_outlined, color: Color(0xff4d795f), size: 32),
            const SizedBox(height: 8),
            const Text('Sin verificaciones pendientes', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Cuando un evento relevante afecte tu zona, te preguntaremos cómo estás.',
              style: TextStyle(color: Colors.black54)),
          ]))),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: FilledButton.icon(onPressed: busy ? null : capture,
            icon: const Icon(Icons.my_location), label: const Text('Guardar ubicación'),
            style: FilledButton.styleFrom(backgroundColor: const Color(0xff4d795f)))),
          const SizedBox(width: 8),
          Expanded(child: OutlinedButton.icon(
            onPressed: () => Navigator.pushNamed(context, '/safety'),
            icon: const Icon(Icons.shield_outlined), label: const Text('Modo seguridad'))),
        ]),
        if (checkpoint != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(
          'Última ubicación guardada: ${checkpoint!['created_at']?.toString().replaceFirst('T', ' ').split('.').first ?? 'disponible'}',
          style: const TextStyle(color: Colors.black54, fontSize: 12))),
        const SizedBox(height: 22),
        const Text('Sismos publicados', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        const Text('Reportes oficiales recibidos por WithYou. No son predicciones ni alertas tempranas.',
          style: TextStyle(fontSize: 12, color: Colors.black54)),
        if (events.isEmpty)
          const Padding(padding: EdgeInsets.symmetric(vertical: 12),
            child: Text('Aún no hay eventos oficiales sincronizados.')),
        ...events.take(4).map((raw) {
          final e = Map<String, dynamic>.from(raw);
          return Card(child: ListTile(
            leading: const Icon(Icons.waves_outlined, color: Color(0xffb44b28)),
            title: Text('Sismo M${e['magnitude'] ?? '?'} · ${e['source'] ?? ''}'),
            subtitle: Text('Fecha UTC: ${e['starts_at'] ?? 'no disponible'}'),
          ));
        }),
        if (isAdmin) ...[
          const SizedBox(height: 22),
          const Text('Laboratorio de escenarios', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 5),
          const Text('Solo cuentas de prueba. Los eventos TEST no se envían a usuarios normales.',
            style: TextStyle(fontSize: 12, color: Colors.black54)),
          const SizedBox(height: 9),
          Wrap(spacing: 8, runSpacing: 8, children: [
            ActionChip(label: const Text('Sismo M6.6'), onPressed: busy ? null : () => simulate('EARTHQUAKE')),
            ActionChip(label: const Text('Deslizamiento'), onPressed: busy ? null : () => simulate('LANDSLIDE')),
            ActionChip(label: const Text('Inundación'), onPressed: busy ? null : () => simulate('FLOOD')),
            ActionChip(label: const Text('Incendio'), onPressed: busy ? null : () => simulate('FIRE')),
          ]),
        ],
        const SizedBox(height: 22),
        const Text('Mis notificaciones', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        ...notes.where((n) => n['id'] != alert?['id']).take(5).map((n) => Card(child: ListTile(
          leading: const Icon(Icons.notifications_none),
          title: Text(n['title']?.toString() ?? 'Notificación'),
          subtitle: Text(n['body']?.toString() ?? ''),
        ))),
      ]),
    );
  }
}
