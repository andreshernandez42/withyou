import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget{ final ApiService api; final VoidCallback onLogged; const LoginScreen({super.key,required this.api,required this.onLogged}); @override State<LoginScreen> createState()=>_LoginScreenState(); }
class _LoginScreenState extends State<LoginScreen>{
  final email=TextEditingController(text:'andres@example.com');
  final pass=TextEditingController(text:'DemoAndres2026!');
  bool busy=false; String? error;
  Future<void> go() async { setState(()=>busy=true); try{ await widget.api.login(email.text.trim(),pass.text); widget.onLogged(); }catch(e){setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);} }
  @override Widget build(BuildContext context)=>Scaffold(backgroundColor:const Color(0xfff4efe8),body:SafeArea(child:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(28),child:ConstrainedBox(constraints:const BoxConstraints(maxWidth:420),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
    const Icon(Icons.shield_outlined,size:64,color:Color(0xffb6532e)),const SizedBox(height:12),const Text('With You',textAlign:TextAlign.center,style:TextStyle(fontSize:30,fontWeight:FontWeight.w800,color:Color(0xff3b322d))),const SizedBox(height:8),const Text('Continuidad personal y verificación de bienestar',textAlign:TextAlign.center,style:TextStyle(color:Colors.black54)),const SizedBox(height:28),
    TextField(controller:email,decoration:const InputDecoration(labelText:'Correo',filled:true,fillColor:Colors.white,border:OutlineInputBorder())),const SizedBox(height:12),
    TextField(controller:pass,obscureText:true,decoration:const InputDecoration(labelText:'Contraseña',filled:true,fillColor:Colors.white,border:OutlineInputBorder())),const SizedBox(height:16),
    if(error!=null) Text(error!,style:const TextStyle(color:Colors.red)),
    FilledButton(onPressed:busy?null:go,style:FilledButton.styleFrom(backgroundColor:const Color(0xffb6532e),padding:const EdgeInsets.all(16)),child:Text(busy?'Ingresando...':'Ingresar')),
    const SizedBox(height:14),const Text('Credenciales demo incluidas en LOCAL_DEMO_CREDENTIALS.txt. Cambiarlas antes de exponer el sistema.',textAlign:TextAlign.center,style:TextStyle(fontSize:12,color:Colors.black45)),
  ]))))));
}
