from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
import models
from routers.profile_controler import get_current_user

router = APIRouter(tags=["Search & Recipes"])
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def home(request: Request, q: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    query = db.query(models.Dish)

    if q:
        query = query.filter(models.Dish.name.ilike(f"%{q}%"))

    dishes = query.order_by(models.Dish.rating.desc()).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "dishes": dishes,
        "search_query": q
    })

@router.get("/recipe/{dish_id}")
async def recipe_page(
    request: Request,
    dish_id: int,
    sort: str = "newest",
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()

    if not dish:
        return RedirectResponse(url="/", status_code=303)

    ingredients_list = [i.strip() for i in dish.ingredients.split('\n') if i.strip()]
    steps_list = [s.strip() for s in dish.steps.split('\n') if s.strip()]

    reviews_query = db.query(models.Review).filter(models.Review.dish_id == dish_id)

    if sort == "highest":
        reviews_query = reviews_query.order_by(models.Review.rating.desc())
    elif sort == "lowest":
        reviews_query = reviews_query.order_by(models.Review.rating.asc())
    else:
        reviews_query = reviews_query.order_by(models.Review.created_at.desc())

    reviews = reviews_query.all()

    return templates.TemplateResponse("recipe.html", {
        "request": request,
        "user": user,
        "dish": dish,
        "ingredients": ingredients_list,
        "steps": steps_list,
        "reviews": reviews,
        "current_sort": sort
    })
