import sys
import os

# Add parent dir to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.auth import models, jwt

def create_admin(email, password):
    db = SessionLocal()
    try:
        # Check if exists
        admin = db.query(models.User).filter(models.User.email == email).first()
        if admin:
            print(f"User {email} already exists.")
            return

        hashed_pw = jwt.get_password_hash(password)
        admin_user = models.User(
            email=email,
            hashed_password=hashed_pw,
            role=models.UserRole.ADMIN.value
        )
        db.add(admin_user)
        db.commit()
        print(f"Admin user {email} created successfully.")
    except Exception as e:
        print(f"Error creating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password>")
    else:
        create_admin(sys.argv[1], sys.argv[2])
