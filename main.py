from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Existing imports
from app import database, deviceConfig
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

# ADD DEVICE PAGE
@app.get("/add_device", response_class=HTMLResponse)
async def add_device_page(request: Request):
    return templates.TemplateResponse("add_device.html", {"request": request})

# PUSH CONFIG PAGE
@app.get("/push_config", response_class=HTMLResponse)
async def push_config_page(request: Request):
    return templates.TemplateResponse("push_config.html", {"request": request})

# VIEW DEVICES PAGE
@app.get("/view_devices", response_class=HTMLResponse)
async def view_devices(request: Request):
    devices = database.get_all_devices()
    return templates.TemplateResponse("view_devices.html", {"request": request, "devices": devices})

# POST: Save device to DB
@app.post("/device/add")
async def save_device(device: Device):
    database.insert_device(device)
    return RedirectResponse(url="/dashboard", status_code=303)

# POST: Push config to actual device
@app.post("/device/push")
async def push_day0(device: Device):
    deviceConfig.push_day0_config(device)
    database.insert_device(device)  # Also save in DB
    return RedirectResponse(url="/dashboard", status_code=303)
