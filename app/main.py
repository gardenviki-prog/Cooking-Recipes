from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})



@app.get("/recipe")
async def show_recipe(request: Request):
    # Фейковий рецепт, поки не підключені БД
    fake_recipe = {
        "title": "Справжній Український Борщ",
        "image": "borsch.jpg",
        "time": "1.5 години",
        "kcal": "250",
        "rating": "4.9",
        "steps": [
            "Зварити наваристий м'ясний бульйон.",
            "Нарізати картоплю та капусту.",
            "Зробити засмажку з буряка, моркви та цибулі.",
            "Додати засмажку в бульйон і варити до готовності."
        ],
        "servings": 4,
        "ingredients": [
            "Свинина на кістці - 500г",
            "Буряк - 2 шт.",
            "Капуста - 300г",
            "Картопля - 4 шт.",
            "Сметана для подачі"
        ]
    }

    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": fake_recipe})
