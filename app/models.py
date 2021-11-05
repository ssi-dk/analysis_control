from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
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
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    seconds: Optional[int] = None


class ComparativeAnalysis(Job):
    species: str
    sequences: Optional[List[str]] = None
    allele_hash_ids: Optional[List[str]] = None
    result: Optional[Any] = None

    # Todo: add a validator that makes sure only sequences or allele_profiles is specified.


class NearestNeighbors(ComparativeAnalysis):
    cutoff: int
    result: Optional[List[str]] = None


class BifrostAnalysis(BaseModel):
    identifier: str
    version: Optional[str] = None


class BifrostAnalysisList(BaseModel):
    analyses: Optional[List[BifrostAnalysis]] = list()


class BifrostJob(Job):
    sequences: Optional[List[str]] = None
    analyses: Optional[List[str]] = None
    process_out: Optional[str] = None
    process_error: Optional[str] = None
    job_id: Optional[str] = None