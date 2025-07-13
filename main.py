from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from schema import Device

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# LOGIN PAGE
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# LOGIN HANDLER
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # Accept any credentials, no auth logic (placeholder)
    return RedirectResponse(url="/dashboard", status_code=303)


# DASHBOARD PAGE
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

