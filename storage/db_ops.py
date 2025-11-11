### storage/db_ops.py
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from storage.models import Event
import os


DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/tidder")
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)


def save_event(event_data):
session = Session()
try:
event = Event(**event_data)
session.add(event)
session.commit()
return event.id
except Exception as e:
session.rollback()
raise e
finally:
session.close()