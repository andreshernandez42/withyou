import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../widgets/safety_check_card.dart';

class HomeScreen extends StatefulWidget{
  final ApiService api; const HomeScreen({super.key,required this.api});
  @override State<HomeScreen> createState()=>_HomeScreenState();
}
class _HomeScreenState extends State<HomeScreen>{
  Map<String,dynamic>? me; List<dynamic> notes=[]; Timer? timer; bool busy=false; String? flash;
  late final LocationService location;
  @override void initState(){super.initState();location=LocationService(widget.api);refresh();timer=Timer.periodic(const Duration(seconds:5),(_)=>refresh(silent:true));}
  @override void dispose(){timer?.cancel();super.dispose();}
  Future<void> refresh({bool silent=false}) async{try{final u=await widget.api.me();final n=await widget.api.notifications(pendingOnly:true);if(mounted)setState((){me=u;notes=n;});}catch(e){if(!silent&&mounted)setState(()=>flash=e.toString());}}
  Map<String,dynamic>? get activeSafety{for(final n in notes){if(n['type']=='SAFETY_CHECK'||n['type']=='WELFARE_CHECK')return Map<String,dynamic>.from(n);}return null;}
  Future<void> respond(String status)async{final n=activeSafety;if(n==null)return;setState(()=>busy=true);try{final md=Map<String,dynamic>.from(n['metadata']??{});await widget.api.respondSafety(status,eventId:md['event_id'],welfareCheckId:md['welfare_check_id']);await widget.api.markRead(n['id']);await refresh();if(mounted)setState(()=>flash='Estado enviado correctamente');}catch(e){if(mounted)setState(()=>flash=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
  Future<void> capture()async{setState(()=>busy=true);try{final r=await location.captureAndUpload();if(mounted)setState(()=>flash=r==null?'Activa ubicación y permisos':'Checkpoint cifrado sincronizado');}catch(e){if(mounted)setState(()=>flash=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
  Future<void> simulate(String type)async{setState(()=>busy=true);try{await widget.api.createTestEvent(type:type);await Future.delayed(const Duration(milliseconds:500));await refresh();if(mounted)setState(()=>flash='Evento de prueba $type creado');}catch(e){if(mounted)setState(()=>flash=e.toString());}finally{if(mounted)setState(()=>busy=false);}}
  @override Widget build(BuildContext context){final n=activeSafety;return RefreshIndicator(onRefresh:refresh,child:ListView(padding:const EdgeInsets.fromLTRB(18,18,18,110),children:[
    Row(mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('With You',style:TextStyle(fontSize:24,fontWeight:FontWeight.w800,color:Color(0xffa74e2d))),Text(me==null?'Cargando...':'Estamos contigo, ${me!['full_name']}.',style:const TextStyle(fontSize:19,fontWeight:FontWeight.w700))]),const CircleAvatar(radius:24,child:Icon(Icons.person))]),
    if(flash!=null)...[const SizedBox(height:12),Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xfffff3cf),borderRadius:BorderRadius.circular(14)),child:Text(flash!))],
    const SizedBox(height:18),
    if(n!=null) SafetyCheckCard(title:n['type']=='SAFETY_CHECK'?'Alerta de emergencia':'Verificación solicitada',subtitle='¿Estás bien?',onSafe:busy?(){}:()=>respond('SAFE'),onHelp:busy?(){}:()=>respond('HELP_REQUIRED'),onUnable:busy?(){}:()=>respond('UNABLE_TO_EXIT'))
    else Container(padding:const EdgeInsets.all(22),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(24)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Icon(Icons.verified_user_outlined,color:Color(0xff4d795f),size:34),SizedBox(height:10),Text('Sin alertas activas',style:TextStyle(fontSize:22,fontWeight:FontWeight.w800)),SizedBox(height:6),Text('Tu estado no se infiere por silencio. Si ocurre un evento relevante, la app solicitará confirmación.',style:TextStyle(color:Colors.black54))])),
    const SizedBox(height:18),
    Row(children:[Expanded(child:FilledButton.icon(onPressed:busy?null:capture,icon:const Icon(Icons.my_location),label:const Text('Guardar checkpoint'),style:FilledButton.styleFrom(backgroundColor:const Color(0xff4d795f),padding:const EdgeInsets.all(14)))),const SizedBox(width:10),Expanded(child:OutlinedButton.icon(onPressed:()=>Navigator.pushNamed(context,'/safety'),icon:const Icon(Icons.shield_outlined),label:const Text('Modo seguridad'),style:OutlinedButton.styleFrom(padding:const EdgeInsets.all(14))))]),
    const SizedBox(height:24),const Text('Laboratorio de escenarios',style:TextStyle(fontSize:18,fontWeight:FontWeight.w800)),const SizedBox(height:8),const Text('Solo para entorno académico: genera eventos TEST que recorren el mismo motor de correlación.',style:TextStyle(color:Colors.black54)),const SizedBox(height:10),
    Wrap(spacing:8,runSpacing:8,children:[ActionChip(label:const Text('Sismo M6.6'),onPressed:busy?null:()=>simulate('EARTHQUAKE')),ActionChip(label:const Text('Deslizamiento'),onPressed:busy?null:()=>simulate('LANDSLIDE')),ActionChip(label:const Text('Inundación'),onPressed:busy?null:()=>simulate('FLOOD')),ActionChip(label:const Text('Incendio'),onPressed:busy?null:()=>simulate('FIRE'))]),
    const SizedBox(height:24),const Text('Notificaciones pendientes',style:TextStyle(fontSize:18,fontWeight:FontWeight.w800)),const SizedBox(height:8),...notes.where((x)=>x!=n).take(5).map((x)=>Card(child:ListTile(leading:const Icon(Icons.notifications_none),title:Text(x['title']),subtitle:Text(x['body'])))),
  ]));}
}
