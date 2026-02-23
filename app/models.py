from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    reviews = relationship("Review", back_populates="author")

class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    image = Column(String, default="borsch.jpg")
    ingredients = Column(Text, nullable=False)
    steps = Column(Text, nullable=False)
    calories = Column(Integer, nullable=False)
    cooking_time = Column(Integer, nullable=False)
    servings = Column(Integer, default=4)
    rating = Column(Float, default=0.0)
    reviews = relationship("Review", back_populates="dish")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="reviews")
    dish_id = Column(Integer, ForeignKey("dishes.id"))
    dish = relationship("Dish", back_populates="reviews")
