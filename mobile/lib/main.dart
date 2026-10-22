import 'package:flutter/material.dart';
import 'services/api_service.dart';
import 'screens/login_screen.dart';
import 'screens/shell_screen.dart';
import 'screens/safety_mode_screen.dart';

void main(){runApp(const WithYouApp());}
class WithYouApp extends StatefulWidget{const WithYouApp({super.key});@override State<WithYouApp> createState()=>_WithYouAppState();}
class _WithYouAppState extends State<WithYouApp>{final api=ApiService();bool ready=false;bool logged=false;@override void initState(){super.initState();restore();}
 Future<void> restore()async{await api.restoreToken();setState((){logged=api.token!=null;ready=true;});}
 @override Widget build(BuildContext context){return MaterialApp(debugShowCheckedModeBanner:false,title:'With You',theme:ThemeData(useMaterial3:true,colorSchemeSeed:const Color(0xffb6532e),fontFamily:'sans'),routes:{'/safety':(_)=>SafetyModeScreen(api:api)},home:!ready?const Scaffold(body:Center(child:CircularProgressIndicator())):logged?ShellScreen(api:api,onLogout:()=>setState(()=>logged=false)):LoginScreen(api:api,onLogged:()=>setState(()=>logged=true)));}}
