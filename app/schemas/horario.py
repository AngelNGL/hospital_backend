from datetime import time
from pydantic import BaseModel, Field


class HorarioCreate(BaseModel):
    dia: int = Field(ge=1, le=7)
    hora_inicio: time
    hora_fin: time

class HorarioUpdate(BaseModel):
    dia: int | None = Field(default=None, ge=1, le=7)
    hora_inicio: time | None = None
    hora_fin: time | None = None
