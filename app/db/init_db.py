from app.db.session import engine, Base
from app.models.user import User  # Import all models here

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
