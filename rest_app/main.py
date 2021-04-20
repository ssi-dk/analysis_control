# generated by fastapi-codegen:
#   filename:  api.yaml
#   timestamp: 2021-04-08T13:43:15+00:00

from __future__ import annotations

from typing import Optional
import asyncio
from uuid import uuid4
from datetime import datetime
import os
import pathlib
import json

from fastapi import FastAPI
import redis
from pymongo import MongoClient
import yaml

from .models import (
    BifrostAnalyses,
    BifrostAnalysis,
    InitBifrostRequest,
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

r = redis.Redis(charset="utf-8", decode_responses=True)

BIFROST_DB_KEY = os.getenv("BIFROST_DB_KEY")
mongo_client = MongoClient(BIFROST_DB_KEY)
db = mongo_client.get_database()

with open('config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)


@app.get('/bifrost/list_analyses', response_model=BifrostAnalyses)
def get_bifrost_analysis_list() -> BifrostAnalyses:
    """
    Get the current list of Bifrost analyses that can be used for reprocessing
    """
    response = BifrostAnalyses()
    for conf in config['bifrost_components']:
        response.analyses.append(BifrostAnalysis(identifier=conf['identifier'], version=conf['version']))
    return response


@app.post('/bifrost/reprocess', response_model=JobResponse)
def init_bifrost_reprocess(body: InitBifrostRequest = None) -> JobResponse:
    """
    Initiate reprocessing of a sequence
    """
    pass


@app.post('/comparison/cgmlst', response_model=JobResponse)
async def init_cgmlst(body: InitCgmlstRequest = None) -> JobResponse:
    """
    Initiate a cgMLST comparative analysis job
    """
    job_id = str(uuid4()) + '.internal'
    r.hmset(job_id, {'status': 'Running'})
    asyncio.create_task(do_cgmlst(job_id, body))
    job_response = JobResponse(job_id=job_id)
    return job_response

async def do_cgmlst(job_id: str, body:InitCgmlstRequest):
    start_time = datetime.now()
    app_root = pathlib.Path(os.path.realpath(__file__)).parent.parent
    # For now, we just use a test file
    profile_file = app_root.joinpath('test_data').joinpath('Achromobacter.tsv')
    cmd = f"python commands/generate_newick.py {profile_file}"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    end_time = datetime.now()
    processing_time = end_time - start_time
    if proc.returncode == 0:
        r.hmset(job_id, {'result': stdout, 'status': 'Succeeded', 'seconds': processing_time.seconds})
    else:
        r.hmset(job_id, {'error': stderr, 'status': 'Failed', 'seconds': processing_time.seconds})


@app.post('/comparison/nearest_neighbors', response_model=JobResponse)
async def init_nearest_neighbors(body: InitNearestNeighborRequest = None) -> JobResponse:
    """
    Initiate an Nearest Neighbors comparative analysis job
    """
    job_id = str(uuid4()) + '.internal'
    r.hmset(job_id, {'status': 'Running'})
    asyncio.create_task(do_nearest_neighbors(job_id, body))
    job_response = JobResponse(job_id=job_id)
    return job_response


async def do_nearest_neighbors(job_id: str, body:InitCgmlstRequest):
    start_time = datetime.now()
    # For now, we just return the first 10 sample ID's
    try:
        sample_ids_cursor = db.samples.find({}, {"_id": 1}, limit=10)
        sample_ids = [ str(element['_id']) for element in sample_ids_cursor ]
        end_time = datetime.now()
        processing_time = end_time - start_time
        r.hmset(job_id, {'result': json.dumps(sample_ids), 'status': 'Succeeded', 'seconds': processing_time.seconds})
    except Exception as e:
        end_time = datetime.now()
        processing_time = end_time - start_time
        r.hmset(job_id, {'error': str(e), 'status': 'Failed', 'seconds': processing_time.seconds})
        

@app.post('/comparison/snp', response_model=JobResponse)
def init_snp(body: InitSnpRequest = None) -> JobResponse:
    """
    Initiate an SNP comparative analysis job
    """
    pass


@app.get('/result/status', response_model=JobResult)
def get_job_status(job_id: str) -> JobResult:
    """
    Get the current status of a job
    """
    status, result, error, seconds = r.hmget(job_id, ('status', 'result', 'error', 'seconds'))
    job_status = JobStatus(value=status)
    job_result = JobResult()
    job_result.status = job_status
    job_result.result = result
    job_result.error = error
    job_result.seconds = seconds
    return job_result


@app.post('/result/store', response_model=JobResult)
def post_job_store(job_id: Optional[JobId] = None) -> JobResult:
    """
    Store a job result for later retrieval
    """
    pass
