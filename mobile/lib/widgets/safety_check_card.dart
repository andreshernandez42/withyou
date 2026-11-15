import 'package:flutter/material.dart';

class SafetyCheckCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final VoidCallback onSafe,onHelp,onUnable;
  const SafetyCheckCard({super.key,required this.title,required this.subtitle,required this.onSafe,required this.onHelp,required this.onUnable});
  @override Widget build(BuildContext context){
    return Container(
      margin:const EdgeInsets.all(18),padding:const EdgeInsets.all(20),
      decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(28),boxShadow:[BoxShadow(color:Colors.black.withOpacity(.08),blurRadius:30,offset:const Offset(0,12))]),
      child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        Row(children:[const Icon(Icons.monitor_heart_outlined,color:Color(0xffc3542b)),const SizedBox(width:8),Text(title,style:const TextStyle(fontWeight:FontWeight.w700,color:Color(0xffa74928)))]),
        const SizedBox(height:18),Text(subtitle,style:const TextStyle(fontSize:26,fontWeight:FontWeight.w800)),
        const SizedBox(height:8),const Text('Cuando estés en un lugar seguro, confirma cómo te encuentras.',style:TextStyle(color:Colors.black54)),
        const SizedBox(height:20),FilledButton.icon(onPressed:onSafe,icon:const Icon(Icons.check_circle_outline),label:const Text('Estoy a salvo'),style:FilledButton.styleFrom(backgroundColor:const Color(0xffe6f5eb),foregroundColor:const Color(0xff2f7551),padding:const EdgeInsets.all(16))),
        const SizedBox(height:10),FilledButton.icon(onPressed:onHelp,icon:const Icon(Icons.volunteer_activism_outlined),label:const Text('Necesito ayuda'),style:FilledButton.styleFrom(backgroundColor:const Color(0xffc83539),padding:const EdgeInsets.all(16))),
        const SizedBox(height:10),OutlinedButton.icon(onPressed:onUnable,icon:const Icon(Icons.lock_outline),label:const Text('No puedo salir'),style:OutlinedButton.styleFrom(foregroundColor:const Color(0xffb93438),padding:const EdgeInsets.all(16))),
      ])
    );
  }
}
