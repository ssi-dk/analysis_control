# generated by fastapi-codegen:
#   filename:  api.yaml
#   timestamp: 2021-04-08T13:43:15+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Extra, Field


class SequenceId(BaseModel):
    __root__: str = Field(
        ...,
        description="A unique identifier for a sequence formatted as 'IsolateId_RunId'. Corresponds to the sequence file, but doesn't contain the file extension\n",
    )


class JobId(BaseModel):
    __root__: str = Field(..., description='Unique identifier for a Job')


class JobResponse(BaseModel):
    job_id: Optional[JobId] = None


class JobStatus(Enum):
    Queued = 'Queued'
    Running = 'Running'
    Succeeded = 'Succeeded'
    Failed = 'Failed'
    Other = 'Other'


class NewickTree(BaseModel):
    __root__: str = Field(
        ..., description='Newick representation of a comparative analysis'
    )


class SequenceIdList(BaseModel):
    __root__: List[SequenceId] = Field(..., description="List of SequenceId's")


class Result(NewickTree, SequenceIdList):
    pass


class JobResult(BaseModel):
    status: Optional[JobStatus] = None
    error: Optional[str] = Field(
        None, description="Error message. Null if the status is not 'Failed'.\n"
    )
    result: Optional[Result] = None
    seconds: Optional[int] = None


class CgmlstMethod(Enum):
    single_linkage = 'single_linkage'
    complete_linkage = 'complete_linkage'


class StCutoffMap(BaseModel):
    pass

    class Config:
        extra = Extra.allow


class InitNearestNeighborRequest(BaseModel):
    sequences: Optional[List[SequenceId]] = None


class InitSnpRequest(BaseModel):
    sequences: Optional[List[SequenceId]] = None


class InitCgmlstRequest(BaseModel):
    sequences: Optional[List[SequenceId]] = None
    method: Optional[CgmlstMethod] = None
    identified_species: Optional[str] = None
    st: Optional[StCutoffMap] = None


class InitBifrostRequest(BaseModel):
    sequences: Optional[List[SequenceId]] = None
    analysis_identifier: Optional[str] = None


class BifrostAnalysis(BaseModel):
    identifier: Optional[str] = None
    version: Optional[str] = None


class BifrostAnalyses(BaseModel):
    analyses: Optional[List[BifrostAnalysis]] = list()
