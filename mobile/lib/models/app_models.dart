class AppUser {
  final String id;
  final String fullName;
  final String email;
  AppUser({required this.id, required this.fullName, required this.email});
  factory AppUser.fromJson(Map<String,dynamic> j)=>AppUser(id:j['id'],fullName:j['full_name'],email:j['email']);
}

class AppNotification {
  final String id,type,title,body,status;
  final Map<String,dynamic> metadata;
  AppNotification({required this.id,required this.type,required this.title,required this.body,required this.status,required this.metadata});
  factory AppNotification.fromJson(Map<String,dynamic> j)=>AppNotification(
    id:j['id'],type:j['type'],title:j['title'],body:j['body'],status:j['status'],
    metadata:Map<String,dynamic>.from(j['metadata']??{}));
}
