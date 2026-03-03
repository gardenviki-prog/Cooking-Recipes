from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models
from routers.profile_controler import get_current_user

router = APIRouter(tags=["Search & Recipes"])
templates = Jinja2Templates(directory="templates")


@router.get("/api/ingredients")
async def get_ingredients(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Ingredient.id,
            models.Ingredient.name,
            func.count(models.DishIngredient.dish_id).label("dish_count"),
        )
        .outerjoin(models.DishIngredient)
        .group_by(models.Ingredient.id)
        .order_by(models.Ingredient.name)
        .all()
    )
    return JSONResponse([{"id": r.id, "name": r.name, "dish_count": r.dish_count} for r in rows])


@router.get("/")
async def home(request: Request, q: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    selected_ing_ids = [int(v) for v in request.query_params.getlist("ing") if v.isdigit()]

    user_allergen_names = []
    if user and user.allergens:
        user_allergen_names = [a.strip().lower() for a in user.allergens.split(",") if a.strip()]

    # Всі страви
    dishes_query = db.query(models.Dish)
    if q:
        dishes_query = dishes_query.filter(models.Dish.name.ilike(f"%{q}%"))
    dishes = dishes_query.all()

    # Завантажити всі dish_ingredients одним запитом
    all_di = db.query(models.DishIngredient).all()
    dish_ing_map = {}
    for di in all_di:
        if di.dish_id not in dish_ing_map:
            dish_ing_map[di.dish_id] = {"required": set(), "optional": set()}
        if di.is_optional == 0:
            dish_ing_map[di.dish_id]["required"].add(di.ingredient_id)
        else:
            dish_ing_map[di.dish_id]["optional"].add(di.ingredient_id)

    # Фільтр за алергенами
    if user_allergen_names:
        ing_name_map = {i.id: i.name.lower() for i in db.query(models.Ingredient).all()}
        safe = []
        for dish in dishes:
            ing_data = dish_ing_map.get(dish.id, {"required": set(), "optional": set()})
            all_ids = ing_data["required"] | ing_data["optional"]
            dish_ing_names = {ing_name_map.get(iid, "") for iid in all_ids}
            if not any(a in dish_ing_names for a in user_allergen_names):
                safe.append(dish)
        dishes = safe

    if selected_ing_ids:
        selected_set = set(selected_ing_ids)

        # Для кожної страви рахуємо скільки обов'язкових інгредієнтів не вистачає
        scored = []
        for dish in dishes:
            ing_data = dish_ing_map.get(dish.id, {"required": set(), "optional": set()})
            required_ids = ing_data["required"]

            if not required_ids:
                # Страва без зв'язків — показуємо внизу
                scored.append((dish, 9999))
                continue

            # Скільки обов'язкових інгредієнтів є у вибраних
            have = required_ids & selected_set
            missing = required_ids - selected_set
            missing_count = len(missing)

            # Показуємо страву якщо хоча б 1 обов'язковий інгредієнт співпадає
            if have:
                scored.append((dish, missing_count))

        # Сортуємо: спочатку ті де менше бракує (0 = можна готувати зараз)
        scored.sort(key=lambda x: x[1])
        dishes = [d for d, _ in scored]

        # Зберігаємо missing_count для шаблону
        dish_missing = {d.id: m for d, m in scored}
    else:
        # Без фільтру — сортування за рейтингом
        dishes.sort(key=lambda d: d.rating, reverse=True)
        dish_missing = {}

    # Інгредієнти для дропдауну
    all_ingredients = (
        db.query(
            models.Ingredient.id,
            models.Ingredient.name,
            func.count(models.DishIngredient.dish_id).label("dish_count"),
        )
        .outerjoin(models.DishIngredient)
        .group_by(models.Ingredient.id)
        .order_by(func.count(models.DishIngredient.dish_id).desc(), models.Ingredient.name)
        .all()
    )

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "dishes": dishes,
        "dish_missing": dish_missing,
        "search_query": q,
        "all_ingredients": all_ingredients,
        "selected_ing_ids": selected_ing_ids,
    })


@router.get("/recipe/{dish_id}")
async def recipe_page(request: Request, dish_id: int, sort: str = "newest", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    dish = db.query(models.Dish).filter(models.Dish.id == dish_id).first()
    if not dish:
        return RedirectResponse(url="/", status_code=303)

    ingredients_list = [i.strip() for i in dish.ingredients.split("\n") if i.strip()]
    optional_list = [i.strip() for i in (dish.optional_ingredients or "").split("\n") if i.strip()]
    steps_list = [s.strip() for s in dish.steps.split("\n") if s.strip()]

    reviews_query = db.query(models.Review).filter(models.Review.dish_id == dish_id)
    if sort == "highest":
        reviews_query = reviews_query.order_by(models.Review.rating.desc())
    elif sort == "lowest":
        reviews_query = reviews_query.order_by(models.Review.rating.asc())
    else:
        reviews_query = reviews_query.order_by(models.Review.created_at.desc())

    return templates.TemplateResponse("recipe.html", {
        "request": request,
        "user": user,
        "dish": dish,
        "ingredients": ingredients_list,
        "optional_ingredients": optional_list,
        "steps": steps_list,
        "reviews": reviews_query.all(),
        "current_sort": sort,
    })
