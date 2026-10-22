import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'home_screen.dart';
import 'people_screen.dart';
import 'sources_screen.dart';
import 'profile_screen.dart';

class ShellScreen extends StatefulWidget{final ApiService api;final VoidCallback onLogout;const ShellScreen({super.key,required this.api,required this.onLogout});@override State<ShellScreen> createState()=>_ShellScreenState();}
class _ShellScreenState extends State<ShellScreen>{int index=0;@override Widget build(BuildContext context){final screens=[HomeScreen(api:widget.api),PeopleScreen(api:widget.api),SourcesScreen(api:widget.api),ProfileScreen(api:widget.api,onLogout:widget.onLogout)];return Scaffold(backgroundColor:const Color(0xfff4efe8),body:SafeArea(child:IndexedStack(index:index,children:screens)),bottomNavigationBar:NavigationBar(selectedIndex:index,onDestinationSelected:(i)=>setState(()=>index=i),destinations:const [NavigationDestination(icon:Icon(Icons.home_outlined),label:'Inicio'),NavigationDestination(icon:Icon(Icons.people_outline),label:'Personas'),NavigationDestination(icon:Icon(Icons.hub_outlined),label:'Mi red'),NavigationDestination(icon:Icon(Icons.person_outline),label:'Perfil')])) ;}}
