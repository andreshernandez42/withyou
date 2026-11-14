from sqlalchemy import select
from app.core.database import Base,engine,SessionLocal
from app.core.security import hash_password
from app.models import User,TrustedContact,ConsentPolicy

DEMO=[
 ('Andrés Demo','andres@example.com','DemoAndres2026!','TESTER',False),
 ('Mamá Demo','mama@example.com','DemoMama2026!','USER',True),
 ('Amiga Demo','amiga@example.com','DemoAmiga2026!','USER',True),
 ('Vecino Demo','vecino@example.com','DemoVecino2026!','USER',True),
]

def run():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        users={}
        for name,email,pw,role,community in DEMO:
            u=db.scalar(select(User).where(User.email==email))
            if not u:
                u=User(full_name=name,email=email,password_hash=hash_password(pw),role=role,community_opt_in=community)
                db.add(u);db.flush()
                db.add(ConsentPolicy(user_id=u.id,quorum_required=2,allow_exact_location=True,allow_coarse_location=True,
                                     allow_community_check=(email=='andres@example.com'),release_after_quorum=True,
                                     release_on_official_event_no_response=True,access_ttl_minutes=60))
            else:
                u.role=role;u.community_opt_in=community
            users[email]=u
        owner=users['andres@example.com']
        for email,name in [('mama@example.com','Mamá Demo'),('amiga@example.com','Amiga Demo')]:
            target=users[email]
            existing=db.scalar(select(TrustedContact).where(TrustedContact.owner_user_id==owner.id,TrustedContact.contact_email==email))
            if not existing:
                db.add(TrustedContact(owner_user_id=owner.id,contact_user_id=target.id,contact_name=name,contact_email=email,status='ACCEPTED',can_receive_sos=True,can_view_checkpoint=True,can_request_welfare=True))
        db.commit()
        print('Seed completado. Usuarios demo:')
        for _,email,pw,role,_ in DEMO:print(f'  {email} / {pw} [{role}]')
    finally:db.close()

if __name__=='__main__':run()
