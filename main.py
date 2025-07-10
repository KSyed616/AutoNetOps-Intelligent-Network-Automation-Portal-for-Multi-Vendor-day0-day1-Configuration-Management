from typing import List

from fastapi import FastAPI, Path

from schema import Device, Login

from cml import cml_login, deploy, edit_onboard, get_deployed

app = FastAPI()

#this is a test
@app.post("/login")
async def login(info: Login):
    cml_login(info)
    return {"login"}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
