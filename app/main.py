from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import engine
import models

from routers import profile_controler, search_controler, comments_controler

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="change-this-secret")

models.Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(search_controler.router)
app.include_router(comments_controler.router)
app.include_router(profile_controler.router)
