from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import engine, get_db
import models

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="change-this-secret")

models.Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_current_user(request: Request, db: Session):
    username = request.session.get("user")
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()

@app.get("/")
async def home(request: Request, q: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    query = db.query(models.Dish)

    if q:
        query = query.filter(models.Dish.name.ilike(f"%{q}%"))

    dishes = query.all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "dishes": dishes,
        "search_query": q
    })

@app.get("/recipe/{dish_id}")
async def recipe_page(request: Request, dish_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()

    if not dish:
        return RedirectResponse(url="/", status_code=303)

    ingredients_list = [i.strip() for i in dish.ingredients.split('\n') if i.strip()]
    steps_list = [s.strip() for s in dish.steps.split('\n') if s.strip()]
    reviews = db.query(models.Review).filter(models.Review.dish_id == dish_id).all()

    return templates.TemplateResponse("recipe.html", {
        "request": request,
        "user": user,
        "dish": dish,
        "ingredients": ingredients_list,
        "steps": steps_list,
        "reviews": reviews
    })

@app.get("/recipe/{dish_id}/review")
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

@app.post("/recipe/{dish_id}/review")
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
    total_rating = sum(r.rating for r in all_reviews)
    dish.rating = round(total_rating / len(all_reviews), 1)
    db.commit()

    return RedirectResponse(url=f"/recipe/{dish_id}", status_code=303)

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != password2:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Паролі не співпадають"})
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Мінімум 6 символів"})

    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Користувач вже існує"})

    new_user = models.User(username=username, hashed_password=hash_password(password))
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login?registered=1", status_code=303)

@app.get("/login")
async def login_page(request: Request):
    message = "Реєстрація успішна! Увійдіть." if request.query_params.get("registered") else None
    return templates.TemplateResponse("login.html", {"request": request, "message": message})

@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Невірні дані"})

    request.session["user"] = username
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.post("/profile/change-password")
def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    new_password2: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not verify_password(old_password, user.hashed_password):
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "Невірний поточний пароль"})
    if new_password != new_password2:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "Нові паролі не співпадають"})
    if len(new_password) < 6:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "Мінімум 6 символів"})

    user.hashed_password = hash_password(new_password)
    db.commit()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "message": "Пароль змінено!"})
