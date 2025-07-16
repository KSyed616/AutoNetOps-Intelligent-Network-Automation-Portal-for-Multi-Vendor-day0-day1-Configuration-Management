from typing import List

from pydantic import BaseModel


class Login(BaseModel):
    cml_url: str
    username: str
    pwd: str


class Device(BaseModel):
    hostname: str
    ip_address: str
    platform: str
    netconf_port: int
    username: str
    password: str


class TemplateParameter(BaseModel):
    name: str
    type: str
    required: bool
    description: str | None = None


class Template(BaseModel):
    name: str
    description: str | None = None
    vendor: str
    yang_module: str
    yang_paths: List[str]
    parameters: List[TemplateParameter]
