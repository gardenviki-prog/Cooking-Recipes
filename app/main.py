from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import engine, get_db
import models

# створюємо додаток
app = FastAPI()

# додаємо підтримку сесій (щоб пам'ятати хто залогінений)
app.add_middleware(SessionMiddleware, secret_key="change-this-secret")

# створюємо всі таблиці в базі даних якщо їх ще немає
models.Base.metadata.create_all(bind=engine)

# підключаємо папку зі статичними файлами (css, картинки)
app.mount("/static", StaticFiles(directory="static"), name="static")

# підключаємо папку з html шаблонами
templates = Jinja2Templates(directory="templates")


# --- ХЕШУВАННЯ ПАРОЛІВ ---

# налаштовуємо bcrypt для хешування
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# функція яка перетворює пароль в хеш
def hash_password(password: str):
    return pwd_context.hash(password)

# функція яка перевіряє чи пароль правильний
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# функція яка повертає поточного користувача з сесії
def get_current_user(request: Request, db: Session):
    # дістаємо імя користувача з сесії
    username = request.session.get("user")

    # якщо нікого немає - повертаємо None
    if not username:
        return None

    # шукаємо користувача в базі даних по імені
    return db.query(models.User).filter(models.User.username == username).first()


# --- ГОЛОВНА СТОРІНКА ---

@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    # дізнаємось хто зараз залогінений
    user = get_current_user(request, db)

    # відкриваємо головну сторінку і передаємо user в шаблон
    return templates.TemplateResponse("base.html", {"request": request, "user": user})


# --- РЕЄСТРАЦІЯ ---

# сторінка з формою реєстрації (GET - просто показуємо форму)
@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# обробка форми реєстрації (POST - коли натиснули кнопку)
@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),     # дістаємо імя з форми
    password: str = Form(...),     # дістаємо пароль з форми
    password2: str = Form(...),    # дістаємо підтвердження паролю
    db: Session = Depends(get_db)
):
    # перевіряємо чи паролі співпадають
    if password != password2:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Паролі не співпадають"}
        )

    # перевіряємо чи пароль достатньо довгий
    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пароль має бути щонайменше 6 символів"}
        )

    # перевіряємо чи такий користувач вже є в базі
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Користувач з таким іменем вже існує"}
        )

    # створюємо нового користувача з хешованим паролем
    new_user = models.User(username=username, hashed_password=hash_password(password))

    # додаємо в базу і зберігаємо
    db.add(new_user)
    db.commit()

    # перенаправляємо на логін з повідомленням що реєстрація успішна
    return RedirectResponse(url="/login?registered=1", status_code=303)

# --- ЛОГІН ---

# сторінка з формою входу (GET)
@app.get("/login")
async def login_page(request: Request):
    # якщо щойно зареєструвались - показуємо повідомлення
    message = "Реєстрація успішна! Тепер увійдіть." if request.query_params.get("registered") else None

    return templates.TemplateResponse("login.html", {"request": request, "message": message})

# обробка форми входу (POST)
@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),   # імя з форми
    password: str = Form(...),   # пароль з форми
    db: Session = Depends(get_db)
):
    # шукаємо користувача в базі
    user = db.query(models.User).filter(models.User.username == username).first()

    # якщо не знайшли - показуємо помилку
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Користувача не знайдено"}
        )

    # перевіряємо чи пароль правильний
    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Невірний пароль"}
        )

    # зберігаємо імя користувача в сесію (щоб він залишався залогіненим)
    request.session["user"] = username

    # перенаправляємо на головну сторінку
    return RedirectResponse(url="/", status_code=303)

# --- ВИХІД ---

@app.get("/logout")
def logout(request: Request):
    # очищаємо сесію - користувач виходить
    request.session.clear()

    # перенаправляємо на логін
    return RedirectResponse(url="/login", status_code=303)


# --- ПРОФІЛЬ ---

# сторінка профілю (GET)
@app.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    # дізнаємось хто залогінений
    user = get_current_user(request, db)

    # якщо не залогінений - відправляємо на логін
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # показуємо сторінку профілю
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


# зміна паролю (POST)
@app.post("/profile/change-password")
def change_password(
    request: Request,
    old_password: str = Form(...),    # поточний пароль
    new_password: str = Form(...),    # новий пароль
    new_password2: str = Form(...),   # підтвердження нового паролю
    db: Session = Depends(get_db)
):
    # дістаємо поточного користувача
    user = get_current_user(request, db)

    # якщо не залогінений - відправляємо на логін
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # перевіряємо чи старий пароль правильний
    if not verify_password(old_password, user.hashed_password):
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "Поточний пароль невірний"})

    # перевіряємо чи нові паролі співпадають
    if new_password != new_password2:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "Нові паролі не співпадають"})

    # перевіряємо довжину нового паролю
    if len(new_password) < 6:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": "Пароль має бути щонайменше 6 символів"})

    # хешуємо новий пароль і зберігаємо в базу
    user.hashed_password = hash_password(new_password)
    db.commit()

    # показуємо повідомлення що пароль змінено
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "message": "Пароль успішно змінено!"})
