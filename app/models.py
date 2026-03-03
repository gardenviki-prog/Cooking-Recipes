from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, Table
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    allergens = Column(Text, nullable=True, default="")
    reviews = relationship("Review", back_populates="author")


class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)

    dish_ingredients = relationship("DishIngredient", back_populates="ingredient")


class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    is_optional = Column(Integer, default=0)

    dish = relationship("Dish", back_populates="dish_ingredients")
    ingredient = relationship("Ingredient", back_populates="dish_ingredients")


class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    image = Column(String, default="borsch.jpg")
    ingredients = Column(Text, nullable=False)
    optional_ingredients = Column(Text, nullable=True, default="")
    steps = Column(Text, nullable=False)
    calories = Column(Integer, nullable=False)
    cooking_time = Column(Integer, nullable=False)
    servings = Column(Integer, default=4)
    rating = Column(Float, default=0.0)
    reviews = relationship("Review", back_populates="dish")
    dish_ingredients = relationship("DishIngredient", back_populates="dish")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="reviews")
    dish_id = Column(Integer, ForeignKey("dishes.id"))
    dish = relationship("Dish", back_populates="reviews")
