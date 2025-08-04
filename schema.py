from typing import List

from pydantic import BaseModel


class Device(BaseModel):
    hostname: str
    ip_address: str
    platform: str
    netconf_port: int
    username: str
    password: str
    device_type: str


class Network(BaseModel):
    ip: str
    wildcard: str
    area: str
