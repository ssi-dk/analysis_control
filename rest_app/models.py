from __future__ import annotations

from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Extra, Field, validator


class JobStatus(Enum):
    Initializing = 'Initializing'
    Rejected = 'Rejected'
    Accepted = 'Accepted'
    Queued = 'Queued'
    Running = 'Running'
    Succeeded = 'Succeeded'
    Failed = 'Failed'
    Stored = 'Stored'


class JobId(BaseModel):
    __root__: str = Field(
        ..., description='A job id that is valid for the specific type of job.'
    )


class Job(BaseModel):
    job_id: Optional[str] = None
    status: Optional[JobStatus] = JobStatus.Initializing
    error: Optional[str] = None
    finished_at: Optional[datetime] = None
    seconds: Optional[int] = None


class ComparativeAnalysis(Job):
    species: str
    sequences: Optional[List[str]] = None
    allele_hash_ids: Optional[List[str]] = None

    # Todo: add a validator that makes sure only sequences or allele_profiles is specified.


class NearestNeighbors(ComparativeAnalysis):
    cutoff: int
    result: Optional[List[str]] = None


class CgMLSTMethod(Enum):
    single_linkage = 'single_linkage'
    complete_linkage = 'complete_linkage'


class StCutoffMap(BaseModel):
    pass

    class Config:
        extra = Extra.allow


class NewickTree(BaseModel):
    __root__: str = Field(
        ..., description='Newick representation of a comparative analysis'
)


class CgMLST(ComparativeAnalysis):
    method: Optional[CgMLSTMethod] = None
    identified_species: Optional[str] = None
    st: Optional[StCutoffMap] = None
    result: Optional[NewickTree] = None

    @validator('sequences')
    def at_least_two_sequences(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('CgMLST analyses require at least two sequences.')
        return v


class BifrostAnalysis(BaseModel):
    identifier: str
    version: Optional[str] = None


class BifrostAnalysisList(BaseModel):
    analyses: Optional[List[BifrostAnalysis]] = list()


class BifrostJob(Job):
    sequences: Optional[List[str]] = None
    analyses: Optional[List[str]] = None
    run_id: Optional[str] = None  # _id on run in MongoDB