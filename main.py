from typing import List

from click import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cml import get_deployed, deploy, edit_onboard
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


@app.get("/devices")
def get_devices():
    devices = get_deployed()
    return {"Current Onboarded devices": devices}


@app.post("/devices/deploy")
def deploy_device(devices: List[Device]):
    for device in devices:
        deploy(device)
    return {"Device Deployed"}


@app.put("/devices/deploy/{device_id}")
def edit_device(devices_id: int = Path(...),
                device: Device = None):
    edit_onboard(devices_id, device)
    return {"Deployed Device Edited"}


# DASHBOARD PAGE
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
