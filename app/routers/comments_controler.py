from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
import models
from routers.profile_controler import get_current_user

router = APIRouter(tags=["Comments & Reviews"])
templates = Jinja2Templates(directory="templates")

@router.get("/recipe/{dish_id}/review")
async def review_page(request: Request, dish_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()
    if not dish:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("comment.html", {
        "request": request,
        "user": user,
        "dish": dish
    })

@router.post("/recipe/{dish_id}/review")
def add_review(
    request: Request,
    dish_id: int,
    rating: int = Form(...),
    text: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()
    if not dish:
        return RedirectResponse(url="/", status_code=303)

    existing_review = db.query(models.Review).filter(
        models.Review.user_id == user.id,
        models.Review.dish_id == dish.id
    ).first()

    if existing_review:
        existing_review.rating = rating
        existing_review.text = text
        existing_review.created_at = datetime.utcnow()
    else:
        new_review = models.Review(rating=rating, text=text, user_id=user.id, dish_id=dish.id)
        db.add(new_review)

    db.commit()

    all_reviews = db.query(models.Review).filter(models.Review.dish_id == dish.id).all()
    if all_reviews:
        total_rating = sum(r.rating for r in all_reviews)
        dish.rating = round(total_rating / len(all_reviews), 1)
        db.commit()

    return RedirectResponse(url=f"/recipe/{dish_id}", status_code=303)

@router.post("/review/delete/{review_id}")
def delete_review(request: Request, review_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    review = db.query(models.Review).filter(models.Review.id == review_id).first()

    if review and review.user_id == user.id:
        dish_id = review.dish_id
        db.delete(review)
        db.commit()

        all_reviews = db.query(models.Review).filter(models.Review.dish_id == dish_id).all()
        dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()

        if all_reviews:
            total_rating = sum(r.rating for r in all_reviews)
            dish.rating = round(total_rating / len(all_reviews), 1)
        else:
            dish.rating = 0.0

        db.commit()
        return RedirectResponse(url=f"/recipe/{dish_id}", status_code=303)

    return RedirectResponse(url="/", status_code=303)
