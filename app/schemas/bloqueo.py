from datetime import datetime
from pydantic import BaseModel


class BloqueoCreate(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime

class BloqueoUpdate(BaseModel):
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
