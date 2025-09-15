from typing import List, Optional

from pydantic import BaseModel


class Test(BaseModel):
    name: str
    command: List[str]
    on_host: bool = False
    context: Optional[dict]


class Reboot(BaseModel):
    command: List[str]


class Repeat(BaseModel):
    total: int = -1
    delay_seconds: int = 3600


class Sequence(BaseModel):
    tests: Optional[List[Test]]
    reboot: Optional[Reboot]
    repeat: Optional[Repeat]


class TestSpec(BaseModel):
    sequence: List[Sequence]
