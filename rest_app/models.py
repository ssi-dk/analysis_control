from __future__ import annotations

from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Extra, Field


class Sequence(BaseModel):
    __root__: str = Field(
        description="A unique identifier for a sequence. A sequence with this sequence id should exist in the Bifrost database."
    )


class JobResponse(BaseModel):
    job_id: Optional[str] = None
    accepted: Optional[bool] = True
    error_msg: Optional[str] = None


class JobStatus(Enum):
    Initializing = 'Initializing'
    Rejected = 'Rejected'
    Accepted = 'Accepted'
    Queued = 'Queued'
    Running = 'Running'
    Succeeded = 'Succeeded'
    Failed = 'Failed'
    Other = 'Other'


class NewickTree(BaseModel):
    __root__: str = Field(
        ..., description='Newick representation of a comparative analysis'
    )


class SequenceList(BaseModel):
    __root__: List[Sequence] = Field(..., description="List of SequenceId's")


class Result(NewickTree, SequenceList):
    pass


class Job(BaseModel):
    job_id: Optional[str] = None
    status: Optional[JobStatus] = JobStatus.Initializing
    error: Optional[str] = None
    result: Optional[Result] = None
    finished_at: Optional[datetime] = None
    seconds: Optional[int] = None


class CgMLSTMethod(Enum):
    single_linkage = 'single_linkage'
    complete_linkage = 'complete_linkage'


class StCutoffMap(BaseModel):
    pass

    class Config:
        extra = Extra.allow


class NearestNeighbors(BaseModel):
    sequences: Optional[List[Sequence]] = None


class CgMLST(BaseModel):
    sequences: Optional[List[Sequence]] = None
    method: Optional[CgMLSTMethod] = None
    identified_species: Optional[str] = None
    st: Optional[StCutoffMap] = None


class BifrostAnalysis(BaseModel):
    identifier: Optional[str] = None
    type: str = None
    version: Optional[str] = None


class BifrostAnalysisList(BaseModel):
    analyses: Optional[List[BifrostAnalysis]] = list()


class BifrostRun(Job):
    sequences: List[Sequence]
    analyses: List[str] = None