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
        user_allergen_names = [a.strip() for a in user.allergens.split(",") if a.strip()]

    dishes_query = db.query(models.Dish)
    if q:
        dishes_query = dishes_query.filter(models.Dish.name.ilike(f"%{q}%"))
    dishes = dishes_query.all()

    all_di = db.query(models.DishIngredient).all()
    dish_ing_map = {}
    for di in all_di:
        if di.dish_id not in dish_ing_map:
            dish_ing_map[di.dish_id] = {"required": set(), "optional": set()}
        if di.is_optional == 0:
            dish_ing_map[di.dish_id]["required"].add(di.ingredient_id)
        else:
            dish_ing_map[di.dish_id]["optional"].add(di.ingredient_id)

    ing_allergen_map = {}
    if user_allergen_names:
        for ing in db.query(models.Ingredient).all():
            tags = {t.strip() for t in (ing.allergen_tags or "").split(",") if t.strip()}
            ing_allergen_map[ing.id] = tags

    dish_allergen_warning = {}
    if user_allergen_names:
        user_allergen_set = set(user_allergen_names)
        for dish in dishes:
            ing_data = dish_ing_map.get(dish.id, {"required": set(), "optional": set()})
            all_ids = ing_data["required"] | ing_data["optional"]
            matched = set()
            for iid in all_ids:
                tags = ing_allergen_map.get(iid, set())
                matched |= (tags & user_allergen_set)
            if matched:
                dish_allergen_warning[dish.id] = matched

    if selected_ing_ids:
        selected_set = set(selected_ing_ids)

        scored = []
        for dish in dishes:
            ing_data = dish_ing_map.get(dish.id, {"required": set(), "optional": set()})
            required_ids = ing_data["required"]

            if not required_ids:
                scored.append((dish, 9999))
                continue

            have = required_ids & selected_set
            missing = required_ids - selected_set
            missing_count = len(missing)

            if have:
                scored.append((dish, missing_count))

        scored.sort(key=lambda x: x[1])
        dishes = [d for d, _ in scored]
        dish_missing = {d.id: m for d, m in scored}
    else:
        dishes.sort(key=lambda d: d.rating, reverse=True)
        dish_missing = {}

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
        "dish_allergen_warning": dish_allergen_warning,
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

    user_allergen_set = set()
    if user and user.allergens:
        user_allergen_set = {a.strip() for a in user.allergens.split(",") if a.strip()}

    dish_ingredients_db = (
        db.query(models.DishIngredient, models.Ingredient)
        .join(models.Ingredient)
        .filter(models.DishIngredient.dish_id == dish_id)
        .all()
    )

    ingredient_danger_map = {}
    dish_allergens_found = set()

    for di, ing in dish_ingredients_db:
        tags = {t.strip() for t in (ing.allergen_tags or "").split(",") if t.strip()}
        if tags:
            ingredient_danger_map[ing.name.lower()] = tags & user_allergen_set if user_allergen_set else set()
            dish_allergens_found |= tags

    def is_dangerous(line: str) -> set:
        """Повертає множину алергенів для рядка, або порожню множину."""
        line_lower = line.lower()
        for ing_name_lower, matched in ingredient_danger_map.items():
            if ing_name_lower in line_lower:
                return matched
        return set()

    def get_all_tags(line: str) -> set:
        """Повертає всі allergen_tags для рядка (без прив'язки до юзера)."""
        line_lower = line.lower()
        for di2, ing2 in dish_ingredients_db:
            if ing2.name.lower() in line_lower:
                return {t.strip() for t in (ing2.allergen_tags or "").split(",") if t.strip()}
        return set()

    ingredients_list = []
    for line in dish.ingredients.split("\n"):
        line = line.strip()
        if line:
            ingredients_list.append({
                "text": line,
                "danger": is_dangerous(line),
                "all_tags": get_all_tags(line),
            })

    optional_list = []
    for line in (dish.optional_ingredients or "").split("\n"):
        line = line.strip()
        if line:
            optional_list.append({
                "text": line,
                "danger": is_dangerous(line),
                "all_tags": get_all_tags(line),
            })

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
        "dish_allergens_found": dish_allergens_found,
        "user_allergen_set": user_allergen_set,
    })
