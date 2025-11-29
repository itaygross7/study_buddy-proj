from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/summarize", response_class=HTMLResponse)
async def summarize_page(request: Request):
    return templates.TemplateResponse("summarize.html", {"request": request})

@router.get("/flashcards", response_class=HTMLResponse)
async def flashcards_page(request: Request):
    return templates.TemplateResponse("flashcards.html", {"request": request})

@router.get("/assess", response_class=HTMLResponse)
async def assess_page(request: Request):
    return templates.TemplateResponse("assess.html", {"request": request})

@router.get("/homework", response_class=HTMLResponse)
async def homework_page(request: Request):
    return templates.TemplateResponse("homework.html", {"request": request})
