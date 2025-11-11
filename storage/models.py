### storage/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime


Base = declarative_base()


class Event(Base):
__tablename__ = "events"


id = Column(Integer, primary_key=True, autoincrement=True)
category = Column(String, nullable=False)
source = Column(String, nullable=False)
title = Column(String, nullable=False)
description = Column(Text)
region = Column(String)
impact_level = Column(String) # High, Medium, Low
event_time = Column(DateTime, default=datetime.datetime.utcnow)
created_at = Column(DateTime, default=datetime.datetime.utcnow)