from sqlalchemy import Column, Integer, String, Text
from database import Base

class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    ingredients = Column(Text, nullable=False)
    steps = Column(Text, nullable=False)

    calories = Column(Integer, nullable=False)
    cooking_time = Column(Integer, nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
