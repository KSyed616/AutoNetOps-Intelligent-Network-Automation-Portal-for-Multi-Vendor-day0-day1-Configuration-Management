from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status

from day1 import day1_hello
from deply_and_day0 import get_deployed, deploy, edit_onboard, cml_login, day0, day0_single, get_day0
from schema import Device, Login

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    user = Login(username=username,
                 pwd=password)
    token = cml_login(user)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/devices", response_class=HTMLResponse)
def get_devices(request: Request):
    devices = get_deployed()
    return templates.TemplateResponse("devices.html",
                                      {
                                          "request": request,
                                          "devices": devices
                                      })


@app.get("/deploy_device", response_class=HTMLResponse)
def deploy_device_page(request: Request):
    return templates.TemplateResponse("deploy_device.html", {"request": request})


@app.get("/day0_menu", response_class=HTMLResponse)
def select_day0_devices(request: Request):
    devices = get_day0()
    return templates.TemplateResponse("day0_devices.html", {"request": request, "devices": devices})


@app.get("/day1_menu", response_class=HTMLResponse)
def select_day1_devices(request: Request):
    devices = get_day0()
    return templates.TemplateResponse("day1_devices.html", {"request": request, "devices": devices})


@app.get("/devices/deploy_edit/{device_id}", response_class=HTMLResponse)
def edit_device_page(device_id: int, request: Request):
    return templates.TemplateResponse(
        "edit_device.html",
        {
            "request": request,
            "device_id": device_id
        }
    )


@app.post("/devices/deploy")
def deploy_device(hostname: str = Form(...),
                  ip_address: str = Form(...),
                  platform: str = Form(...),
                  username: str = Form(...),
                  password: str = Form(...),
                  device_type: str = Form(...)
                  ):
    device = Device(
        hostname=hostname,
        ip_address=ip_address,
        platform=platform,
        netconf_port=830,
        username=username,
        password=password,
        device_type=device_type
    )
    deploy(device)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/devices/deploy/{device_id}")
def edit_device(
        device_id: int,
        hostname: str = Form(...),
        ip_address: str = Form(...),
        platform: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
        device_type: str = Form(...)
):
    device = Device(
        hostname=hostname,
        ip_address=ip_address,
        platform=platform,
        netconf_port=830,
        username=username,
        password=password,
        device_type=device_type
    )

    edit_onboard(device_id, device)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/day0/all")
def day0_all_devices():
    day0()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/day0/single")
def day0_single_device(device_id: int = Form(...)):
    day0_single(device_id)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/day1")
def day1(device_id: int = Form(...)):
    day1_hello(device_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
