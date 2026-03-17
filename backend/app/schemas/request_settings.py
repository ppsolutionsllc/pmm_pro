from typing import List
from pydantic import BaseModel


class SetPlannedActivitiesIn(BaseModel):
    planned_activity_ids: List[int]
