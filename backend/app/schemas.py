from typing import Literal
from pydantic import BaseModel

CASE_STATUSES = Literal["new", "reviewed", "contacted", "closed"]


class StatusUpdate(BaseModel):
    status: CASE_STATUSES


class AssignmentUpdate(BaseModel):
    assigned_to: str | None = None


class CourtStatusUpdate(BaseModel):
    court_status: str | None = None
    next_hearing_date: str | None = None
    hearing_attorney: str | None = None


class RecordFieldsUpdate(BaseModel):
    """Staff corrections to intake fields the extraction got wrong.

    Every field is optional and only those actually sent are applied
    (`exclude_unset`), so the dashboard can PATCH one corrected name without
    blanking everything else on the record.
    """

    caller_name: str | None = None
    callback_phone: str | None = None
    email: str | None = None
    from_number: str | None = None
    case_category: str | None = None
    case_subcategory: str | None = None
    case_subtype: str | None = None
    incident_date: str | None = None
    location: str | None = None
    opposing_party: str | None = None
    key_date_or_deadline: str | None = None
    case_summary: str | None = None
    additional_details: str | None = None
    represented_already: bool | None = None
    injured: bool | None = None
    police_report_filed: bool | None = None


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
