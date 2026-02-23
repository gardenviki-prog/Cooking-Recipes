import os
import shutil
import uuid

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
import models

router = APIRouter(tags=["Profile"])
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

@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
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

@router.get("/login")
async def login_page(request: Request):
    message = "Реєстрація успішна! Увійдіть." if request.query_params.get("registered") else None
    return templates.TemplateResponse("login.html", {"request": request, "message": message})

@router.post("/login")
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

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@router.post("/profile/change-password")
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

@router.get("/profile/edit")
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("profile_edit.html", {"request": request, "user": user})

@router.post("/profile/edit")
def edit_profile(
    request: Request,
    username: str = Form(...),
    email: str = Form(""),
    goals: list[str] = Form(default=[]),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if username != user.username:
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user:
            return templates.TemplateResponse("profile_edit.html", {
                "request": request, "user": user, "error": "Це ім'я користувача вже зайнято"
            })
        user.username = username
        request.session["user"] = username

    user.email = email
    user.goals = ", ".join(goals)

    if avatar and avatar.filename:
        avatars_dir = "static/images/avatars"
        os.makedirs(avatars_dir, exist_ok=True)

        file_ext = avatar.filename.split(".")[-1]
        unique_filename = f"{user.id}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(avatars_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        user.avatar = f"images/avatars/{unique_filename}"

    db.commit()

    return templates.TemplateResponse("profile_edit.html", {
        "request": request,
        "user": user,
        "message": "Профіль успішно оновлено!"
    })
