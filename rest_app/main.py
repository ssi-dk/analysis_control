# generated by fastapi-codegen:
#   filename:  api.yaml
#   timestamp: 2021-04-07T15:16:09+00:00

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from .models import (
    InitCgmlstRequest,
    InitNearestNeighborRequest,
    InitSnpRequest,
    InitSofiReprocessRequest,
    JobId,
    JobResponse,
    JobResult,
)

app = FastAPI(
    title='Analysis Control',
    version='0.3',
    description='API for controlling analysis jobs on the SOFI platform',
    contact={'name': 'ssi.dk'},
)


@app.post('/comparison/cgmlst', response_model=JobResponse)
def init_cgmlst(body: InitCgmlstRequest = None) -> JobResponse:
    """
    Initiate a cgMLST comparative analysis job
    """
    pass


@app.post('/comparison/nearest_neighbors', response_model=JobResponse)
def init_nearest_neighbors(body: InitNearestNeighborRequest = None) -> JobResponse:
    """
    Initiate an Nearest Neighbors comparative analysis job
    """
    pass


@app.post('/comparison/snp', response_model=JobResponse)
def init_snp(body: InitSnpRequest = None) -> JobResponse:
    """
    Initiate an SNP comparative analysis job
    """
    pass


@app.get('/result/status', response_model=JobResult)
def get_job_status(job_id: Optional[JobId] = None) -> JobResult:
    """
    Get the current status of a job
    """
    pass


@app.post('/result/store', response_model=JobResult)
def post_job_store(job_id: Optional[JobId] = None) -> JobResult:
    """
    Store a job result for later retrieval
    """
    pass


@app.post('/sofi/reprocess', response_model=JobResponse)
def init_sofi_reprocess(body: InitSofiReprocessRequest = None) -> JobResponse:
    """
    Initiate reprocessing of a sequence
    """
    pass
