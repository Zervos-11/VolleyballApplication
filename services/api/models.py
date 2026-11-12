from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Literal, Dict

class CameraInfo(BaseModel):
    fps: float
    width: int
    height: int
    mount: Literal["baseline", "sideline", "other"] = "baseline"

class Homography(BaseModel):
    points_px: List[Tuple[float, float]]
    points_court_m: List[Tuple[float, float]]

class RosterItem(BaseModel):
    jersey: int
    name: Optional[str] = None

class TeamInfo(BaseModel):
    name: str
    # Revert to simple default list without Field factory
    roster: List[RosterItem] = []

class Rally(BaseModel):
    rally_id: str
    t_start: float
    t_end: float
    context: Literal["sideout", "serve_hold", "unknown"] = "unknown"
    outcome: Optional[Literal["win", "loss"]] = None

class InitMatchRequest(BaseModel):
    match_id: str
    set_number: int = 1

class Metadata(BaseModel):
    schema_version: str = Field(default="v1")
    match_id: str
    set_number: int
    camera: CameraInfo
    homography: Optional[Homography] = None
    rallies: List[Rally]
    teams: Dict[str, TeamInfo]

class ProcessResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "done"] = "queued"

# (YouTube models removed in revert)

class MetricsPerRally(BaseModel):
    rally_id: str
    rotation_home: Optional[str] = None
    quality: Dict[str, object] = Field(default_factory=dict)
    coverage: Dict[str, float | str | None]
    transition: Dict[str, float | None]
    outcome_pred: Dict[str, float | None]

class MetricsResponse(BaseModel):
    schema_version: str = "v1"
    match_id: str
    per_rally: List[MetricsPerRally]
    # Revert to plain dict default
    artifacts: Dict[str, str] = {}
    
