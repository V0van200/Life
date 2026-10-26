import argparse
import getpass
from sqlalchemy import select
from .db import Session
from .models import User, LoginSession
from .security import hash_password

def main():
    parser=argparse.ArgumentParser(description="Local Life account administration")
    parser.add_argument("action",choices=["create-user","reset-password"])
    parser.add_argument("username")
    args=parser.parse_args()
    password=getpass.getpass("Password (12+ characters): ")
    if len(password)<12: parser.error("Password must contain at least 12 characters")
    if password!=getpass.getpass("Repeat password: "): parser.error("Passwords differ")
    with Session() as db:
        user=db.scalar(select(User).where(User.username==args.username))
        if args.action=="create-user":
            if user: parser.error("User already exists")
            db.add(User(username=args.username,password=hash_password(password)))
        else:
            if not user: parser.error("User not found")
            user.password=hash_password(password)
            for row in db.scalars(select(LoginSession).where(LoginSession.owner==user.id)): db.delete(row)
        db.commit()
    print("Done")

if __name__=="__main__": main()
