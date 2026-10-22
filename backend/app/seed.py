from sqlalchemy import select
from app.core.database import Base,engine,SessionLocal
from app.core.security import hash_password
from app.models import User,TrustedContact,ConsentPolicy

DEMO=[
 ('Andrés Demo','andres@example.com','DemoAndres2026!'),
 ('Mamá Demo','mama@example.com','DemoMama2026!'),
 ('Amiga Demo','amiga@example.com','DemoAmiga2026!'),
]

def run():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        users={}
        for name,email,pw in DEMO:
            u=db.scalar(select(User).where(User.email==email))
            if not u:
                u=User(full_name=name,email=email,password_hash=hash_password(pw))
                db.add(u); db.flush(); db.add(ConsentPolicy(user_id=u.id,quorum_required=2,allow_exact_location=True))
            users[email]=u
        owner=users['andres@example.com']
        for email,name in [('mama@example.com','Mamá Demo'),('amiga@example.com','Amiga Demo')]:
            target=users[email]
            existing=db.scalar(select(TrustedContact).where(TrustedContact.owner_user_id==owner.id,TrustedContact.contact_user_id==target.id))
            if not existing:
                db.add(TrustedContact(owner_user_id=owner.id,contact_user_id=target.id,contact_name=name,contact_email=email,status='ACCEPTED',can_receive_sos=True,can_view_checkpoint=True,can_request_welfare=True))
        db.commit()
        print('Seed completado. Usuarios demo:')
        for _,email,pw in DEMO: print(f'  {email} / {pw}')
    finally: db.close()

if __name__=='__main__': run()
