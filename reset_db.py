import os
from app import app, db

def reset_db():
    db_path = os.path.join('instance', 'database.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed {db_path}")
    
    with app.app_context():
        db.create_all()
        # Seed the default admin
        from app import create_tables
        create_tables()
        print("Database schema recreated successfully.")

if __name__ == "__main__":
    reset_db()
