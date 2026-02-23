from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

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
    text: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()
    if not dish:
        return RedirectResponse(url="/", status_code=303)

    new_review = models.Review(rating=rating, text=text, user_id=user.id, dish_id=dish.id)
    db.add(new_review)
    db.commit()

    all_reviews = db.query(models.Review).filter(models.Review.dish_id == dish.id).all()
    if all_reviews:
        total_rating = sum(r.rating for r in all_reviews)
        dish.rating = round(total_rating / len(all_reviews), 1)
        db.commit()

    return RedirectResponse(url=f"/recipe/{dish_id}", status_code=303)
