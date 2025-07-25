from typing import List

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status

from day1 import day1_hello, get_interfaces, gen_int_temp, get_template_variables, validate
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
    token = cml_login()
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


@app.get("/template_menu", response_class=HTMLResponse)
def template_menu(request: Request):
    return templates.TemplateResponse("template_menu.html", {"request": request})


@app.get("/interface/config", response_class=HTMLResponse)
def display_int_info(request: Request):
    return templates.TemplateResponse("interface_config.html", {"request": request})


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


@app.post("/day1/interfaces", response_class=HTMLResponse)
def day1_interfaces(request: Request, device_id: int = Form(...)):
    day1_hello(device_id)
    interface_data = get_interfaces(device_id)
    return templates.TemplateResponse(
        "interface_config.html",
        {"request": request, "interfaces": interface_data}
    )


@app.post("/template")
def template(request: Request, temp_type: str = Form(...)):
    if temp_type == "interface":
        return templates.TemplateResponse("interface_temp.html", {"request": request})
    elif temp_type == "rip":
        return templates.TemplateResponse("rip_config.html", {"request": request})
    elif temp_type == "ospf":
        return templates.TemplateResponse("ospf_config.html", {"request": request})
    else:
        return RedirectResponse("/dashboard")


@app.post("/template/interface")
def interface_template(request: Request,
                       fields: List[str] = Form(...),
                       ipv4_prefix_option: str = Form(...)):

    gen_int_temp(fields, ipv4_prefix_option)

    return RedirectResponse("/dashboard", status_code=303)


@app.get("/day1/interfaces/template", response_class=HTMLResponse)
def get_int_config(request: Request, interface_name: str = Form(...)):

    print(f"Interface selected for config: {interface_name}")
    fields = get_template_variables("interface_temp.j2")

    return templates.TemplateResponse("interface_yang.html", {
        "request": request,
        "interface_name": interface_name,
        "fields": fields
    })


@app.post("/day1/interfaces/config", response_class=HTMLResponse)
async def config_int(request: Request):
    form = await request.form()

    context = {
        "name": form["interface_name"],
        "enabled": "true" if "enabled" in form else "false"
    }

    if "description" in form:
        context["description"] = form["description"]

    if "link-up-down-trap-enable" in form:
        context["link_up_down_trap_enable"] = "true"

    if "ipv4_address" in form:
        context["ipv4_address"] = form["ipv4_address"]

    if "prefix_length" in form:
        context["prefix_length"] = form["prefix_length"]

    if "netmask" in form:
        context["netmask"] = form["netmask"]

    if "ipv4_enabled" in form:
        context["ipv4_enabled"] = "true"

    if "ipv4_forwarding" in form:
        context["ipv4_forwarding"] = "true"

    if "ipv4_mtu" in form:
        context["ipv4_mtu"] = form["ipv4_mtu"]

    if "ipv4_neighbor_ip" in form:
        context["ipv4_neighbor_ip"] = form["ipv4_neighbor_ip"]

    if "ipv4_neighbor_mac" in form:
        context["ipv4_neighbor_mac"] = form["ipv4_neighbor_mac"]

    context.setdefault("ipv4_enabled", "false")
    context.setdefault("ipv4_forwarding", "false")

    print("context", context)

    validate("interface_template.j2", context, "app/models", "ietf-interfaces.yang")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
