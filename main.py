from typing import List

from fastapi import FastAPI, Request, Form, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cml import get_deployed, deploy, edit_onboard
from schema import Device

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # Accept all credentials for now (placeholder logic)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


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
def edit_device(
        device_id: int = Path(...),
        device: Device = None
):
    edit_onboard(device_id, device)
    return {"Deployed Device Edited"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
