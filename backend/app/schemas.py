from typing import Literal
from pydantic import BaseModel, create_model

from .intake_fields import ALL_FIELDS

CASE_STATUSES = Literal["new", "reviewed", "contacted", "closed"]


class StatusUpdate(BaseModel):
    status: CASE_STATUSES


class AssignmentUpdate(BaseModel):
    assigned_to: str | None = None


class CourtStatusUpdate(BaseModel):
    court_status: str | None = None
    next_hearing_date: str | None = None
    hearing_attorney: str | None = None


# Staff corrections to intake fields the extraction got wrong.
#
# Built from the intake field spec rather than written out, so a field added
# to app/intake_fields.py is correctable in the dashboard without a second
# edit here — the two lists drifting apart is how a field ends up displayed
# but not fixable. Every field is optional and only those actually sent are
# applied (`exclude_unset`), so the dashboard can PATCH one corrected name
# without blanking everything else on the record.
RecordFieldsUpdate = create_model(
    "RecordFieldsUpdate",
    from_number=(str | None, None),
    case_category=(str | None, None),
    case_subcategory=(str | None, None),
    **{
        f.name: ((bool | None) if f.kind == "bool" else (str | None), None)
        for f in ALL_FIELDS
    },
)


class StaffCreate(BaseModel):
    name: str
    role: str | None = None
    phone: str | None = None
    extension: str | None = None


class StaffUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    extension: str | None = None
    active: bool | None = None


class MessageCreate(BaseModel):
    message_text: str
    call_id: str | None = None
    case_number: str | None = None
    caller_name: str | None = None
    callback_phone: str | None = None
    for_staff_id: str | None = None


class MessageUpdate(BaseModel):
    delivered: bool


# The mid-call case-lookup endpoint deliberately has no Pydantic model: it
# parses its body by hand, because Retell custom functions send either
# {name, call, args} or flat args depending on configuration, and the LLM
# sometimes passes the case number as a JSON number. See main.case_lookup.
