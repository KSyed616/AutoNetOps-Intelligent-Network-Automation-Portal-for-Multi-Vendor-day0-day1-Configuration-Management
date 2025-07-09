from typing import List

from fastapi import FastAPI

from schema import Device, Login

from cml import cml_login, day0

app = FastAPI()


@app.post("/login")
async def login(info: Login):
    cml_login(info)
    return {"login"}


@app.get("/devices")
def get_devices():
    return {"Current Onboarded devices"}


@app.post("/devices/deploy")
def deploy_device(devices: List[Device]):
    for device in devices:
        day0(device)
    return {"ret"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
