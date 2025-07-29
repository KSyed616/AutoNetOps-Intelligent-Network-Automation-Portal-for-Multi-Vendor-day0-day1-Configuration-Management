from typing import List

from MySQLdb.constants.ER import QUERY_ON_FOREIGN_DATA_SOURCE
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status

from day1 import day1_hello, get_interfaces, gen_int_temp, get_template_variables, validate, create_temp, \
    delete_int, push_config, gen_ospf_temp, get_interface_ip
from deply_and_day0 import get_deployed, deploy, edit_onboard, day0, day0_single, get_day0, cml_login
from schema import Device

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login")
def login():
    cml_login()
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


@app.post("/day1/configurations")
def day1_options(request: Request, device_id: int = Form(...)):
    print("dev", device_id)
    return templates.TemplateResponse(
        "day1_config.html",
        {"request": request,
         "device_id": device_id}
    )


@app.get("/day1/interface", response_class=HTMLResponse)
def day1_interfaces(request: Request, device_id: int = Query(...)):
    day1_hello(device_id)
    interface_data = get_interfaces(device_id)
    return templates.TemplateResponse(
        "interface_config.html",
        {"request": request, "interfaces": interface_data, "device_id": device_id}
    )


@app.get("/day1/ospf", response_class=HTMLResponse)
def day1_ospf(request: Request, device_id: int = Query(...)):
    day1_hello(device_id)
    fields = get_template_variables("ospf_temp.j2")
    print("fields: ", fields)

    return templates.TemplateResponse("ospf_yang.html", {
        "request": request,
        "fields": fields,
        "device_id": device_id
    })


@app.post("/template")
def template(request: Request, temp_type: str = Form(...)):
    if temp_type == "interface":
        return templates.TemplateResponse("interface_temp.html", {"request": request})
    elif temp_type == "ospf":
        return templates.TemplateResponse("ospf_temp.html", {"request": request})
    else:
        return RedirectResponse("/dashboard")


@app.post("/template/interface")
def interface_template(fields: List[str] = Form(...),
                       ipv4_prefix_option: str = Form(...)):
    gen_int_temp(fields, ipv4_prefix_option)

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/template/ospf")
def ospf_template(fields: List[str] = Form(...)):
    gen_ospf_temp(fields)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/day1/interfaces/template", response_class=HTMLResponse)
def get_int_config(request: Request, interface_name: str = Query(...), interface_status: str = Query(...),
                   device_id: str = Query(...)):
    print(f"Interface selected for config: {interface_name}")
    fields = get_template_variables("interface_temp.j2")

    return templates.TemplateResponse("interface_yang.html", {
        "request": request,
        "interface_name": interface_name,
        "interface_status": interface_status,
        "fields": fields,
        "device_id": device_id
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

    if "ipv4_mtu" in form:
        context["ipv4_mtu"] = form["ipv4_mtu"]

    if "ipv4_neighbor_ip" in form:
        context["ipv4_neighbor_ip"] = form["ipv4_neighbor_ip"]

    if "ipv4_neighbor_mac" in form:
        context["ipv4_neighbor_mac"] = form["ipv4_neighbor_mac"]

    context.setdefault("ipv4_enabled", "false")
    context.setdefault("ipv4_forwarding", "false")

    print("context", context)
    device_id = int(form["device_id"])
    interface_status = str(form["interface_status"])
    interface_name = str(form["interface_name"])

    is_reconfig = True if interface_status == "Enabled" else False

    validate_resp = validate("interface_temp.j2", context, "/app/models", "ietf-interfaces.yang", is_reconfig)

    if validate_resp:
        config_temp = create_temp(
            "interface_temp.j2",
            context,
            is_reconfig
        )

        print(config_temp)
        print(interface_name)

        if is_reconfig:
            delete_int(device_id, interface_name)

        push_config(config_temp, device_id)
        print(get_interface_ip(device_id, interface_name))

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/day1/ospf/config", response_class=HTMLResponse)
async def config_ospf(request: Request):
    form = await request.form()

    context = {
        "process_id": form["process_id"],
        "router_id": form["router_id"],
        "network_ip": form["network_ip"],
        "wildcard_mask": form["wildcard_mask"],
        "area": form["area"]
    }

    # Optional Fields
    if "passive_interface" in form:
        context["passive_interface"] = form["passive_interface"]

    if "reference_bandwidth" in form:
        context["reference_bandwidth"] = form["reference_bandwidth"]

    if "default_information_originate" in form:
        context["default_information_originate"] = "true"

    if "log_adjacency_changes" in form:
        context["log_adjacency_changes"] = "true"

    if "timers_throttle_spf" in form:
        context["timers_throttle_spf"] = form["timers_throttle_spf"]

    if "timers_throttle_lsa" in form:
        context["timers_throttle_lsa"] = form["timers_throttle_lsa"]

    print("OSPF context:", context)

    context_int = {
        "type": form["type"],
        "number": form["number"],
        "network_type": "point-to-point",
        "ospf_process_id": form["process_id"],
        "area": form["area"]
    }

    device_id = int(form["device_id"])
    is_reconfig = True

    config_temp = create_temp("ospf_temp.j2", context, is_reconfig)
    int_ospf_temp = create_temp("ospf_int_config.j2", context, is_reconfig)
    print("Rendered OSPF Config:\n", config_temp)
    push_config(config_temp, device_id)
    push_config(int_ospf_temp, device_id)

    return RedirectResponse("/dashboard", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
