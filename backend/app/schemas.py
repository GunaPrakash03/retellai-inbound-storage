from typing import Literal
from pydantic import BaseModel

CASE_STATUSES = Literal["new", "reviewed", "contacted", "closed"]


class StatusUpdate(BaseModel):
    status: CASE_STATUSES
