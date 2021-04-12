# generated by fastapi-codegen:
#   filename:  api.yaml
#   timestamp: 2021-04-08T13:43:15+00:00

from __future__ import annotations

from typing import Optional
import asyncio

from fastapi import FastAPI

from .models import (
    BifrostAnalyses,
    InitBifrostReprocessRequest,
    InitCgmlstRequest,
    InitNearestNeighborRequest,
    InitSnpRequest,
    JobId,
    JobResponse,
    JobResult,
    JobStatus,
)

app = FastAPI(
    title='Analysis Control',
    version='0.6',
    description='API for controlling analysis jobs on the SOFI platform',
    contact={'name': 'ssi.dk'},
)


@app.post('/bifrost/reprocess', response_model=JobResponse)
def init_bifrost_reprocess(body: InitBifrostReprocessRequest = None) -> JobResponse:
    """
    Initiate reprocessing of a sequence
    """
    pass


@app.post('/comparison/cgmlst', response_model=JobResponse)
async def init_cgmlst(body: InitCgmlstRequest = None) -> JobResponse:
    """
    Initiate a cgMLST comparative analysis job
    """
    cmd = 'python generate_newick.py 1>&2'
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')
    job_response = JobResponse()
    job_response.job_id = 1
    return job_response


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


@app.get('/list/bifrost_analyses', response_model=BifrostAnalyses)
def get_bifrost_analysis_list() -> BifrostAnalyses:
    """
    Get the current list of Bifrost analyses
    """
    pass


@app.get('/result/status', response_model=JobResult)
def get_job_status(job_id: Optional[JobId] = None) -> JobResult:
    """
    Get the current status of a job
    """
    job_status = JobStatus(value="Succeeded")
    job_result = JobResult()
    job_result.status = job_status
    return job_result


@app.post('/result/store', response_model=JobResult)
def post_job_store(job_id: Optional[JobId] = None) -> JobResult:
    """
    Store a job result for later retrieval
    """
    pass
