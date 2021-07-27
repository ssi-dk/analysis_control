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
import bifrostapi
import yaml


from models import (
    BifrostAnalysisList,
    BifrostAnalysis,
    BifrostRun,
    CgMLST,
    NearestNeighbors,
    JobResponse,
    JobId,
    JobStatus,
)

from hpc import create_bifrost_job

app = FastAPI(
    title='Analysis Control',
    version='0.6',
    description='API for controlling analysis jobs on the SOFI platform',
    contact={'name': 'ssi.dk'},
)

r = redis.Redis(charset="utf-8", decode_responses=True)

BIFROST_DB_KEY = os.getenv("BIFROST_DB_KEY", "mongodb://localhost/test_bifrost")
mongo = MongoClient(BIFROST_DB_KEY)
db = mongo.get_database()
bifrostapi.add_URI(BIFROST_DB_KEY)


with open('config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)


@app.get('/bifrost/list_analyses', response_model=BifrostAnalysisList)
def list_hpc_analysis() -> BifrostAnalysisList:
    """
    Get the list of configured Bifrost analyses from application config.
    """
    response = BifrostAnalysisList()
    analysis_dict = config['bifrost_analyses']
    for identifier in analysis_dict:
        version = analysis_dict[identifier]['version']
        response.analyses.append(BifrostAnalysis(
            identifier=identifier,
            version=version))
    return response


@app.post('/bifrost/init', response_model=BifrostRun)
def init_bifrost_run(run: BifrostRun = None) -> BifrostRun:
    """
    Initiate a Bifrost run with one or more sequences and one or more Bifrost analyses.
    """
    # Return an error if analysis list is empty
    if hasattr(run, 'analyses') and (run.analyses is None or len(run.analyses) == 0):
        run.status = JobStatus.Rejected
        return run

    # Todo: Find sequence in MongoDB and return with error if not found

    # For each analysis, make sure that analysis is present in config
    for analysis in run.analyses:
        try:
            assert analysis in config['bifrost_analyses']
            run.status = JobStatus.Accepted
        except AssertionError:
            run.status = JobStatus.Rejected
            run.error = f"Could not find a Bifrost analysis with the identifier '{analysis}'."
            return run
    
    response = create_bifrost_job(run)
    return response


@app.get('/bifrost/status', response_model=BifrostRun)
def status_bifrost(job_id: str) -> BifrostRun:
    response = BifrostRun(identifier=job_id)
    return response


@app.post('/comparative/nearest_neighbors/init', response_model=NearestNeighbors)
async def init_nearest_neighbors(job: NearestNeighbors) -> NearestNeighbors:
    """
    Initiate a "nearest neighbors" comparative analysis job.
    """
    job.job_id = str(uuid4())
    # r.hmset(job_id, {'status': 'Running'})
    # asyncio.create_task(do_nearest_neighbors(job_id, body))
    return job


async def do_nearest_neighbors(job: NearestNeighbors):
    start_time = datetime.now()
    # For now, we just return the first 10 sample ID's
    try:
        sample_ids_cursor = db.samples.find({}, {"_id": 1}, limit=10)
        sample_ids = [ str(element['_id']) for element in sample_ids_cursor ]
        end_time = datetime.now()
        processing_time = end_time - start_time
        r.hmset(job.job_id, {'result': json.dumps(sample_ids), 'status': 'Succeeded', 'seconds': processing_time.seconds})
    except Exception as e:
        end_time = datetime.now()
        processing_time = end_time - start_time
        r.hmset(job.job_id, {'error': str(e), 'status': 'Failed', 'seconds': processing_time.seconds})


@app.get('/comparative/nearest_neighbors/status', response_model=NearestNeighbors)
def status_nearest_neighbors(job_id: str) -> NearestNeighbors:
    """
    Get the current status of a "nearest neighbors" job.
    """

    """status, result, error, seconds = r.hmget(job_id, ('status', 'result', 'error', 'seconds'))
    job_status = JobStatus(value=status)
    job_result = Job()
    job_result.status = job_status
    job_result.result = result
    job_result.error = error
    job_result.seconds = seconds """

    response = NearestNeighbors(job_id=job_id)
    return response


@app.post('/comparative/nearest_neighbors/store', response_model=NearestNeighbors)
async def store_nearest_neighbors(job_id: JobId) -> NearestNeighbors:
    """
    Store a "nearest neighbors" comparative analysis job.
    """
    # r.hmset(job_id, {'status': 'Running'})
    # asyncio.create_task(do_nearest_neighbors(job_id, body))
    response = NearestNeighbors(job_id=job_id.__root__)
    return response


@app.post('/comparative/cgmlst/init', response_model=CgMLST)
async def init_cgmlst(body: CgMLST = None) -> CgMLST:
    """
    Initiate a cgMLST comparative analysis job
    """
    job_id = str(uuid4()) + '.internal'
    r.hmset(job_id, {'status': 'Running'})
    asyncio.create_task(do_cgmlst(job_id, body))
    response = CgMLST(job_id=job_id)
    return response

async def do_cgmlst(job_id: str, body:CgMLST):
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


@app.get('/comparative/cgmlst/status', response_model=CgMLST)
def status_cgmlst(job_id: str) -> CgMLST:
    """
    Get the current status of a "nearest neighbors" job.
    """

    """status, result, error, seconds = r.hmget(job_id, ('status', 'result', 'error', 'seconds'))
    job_status = JobStatus(value=status)
    job_result = Job()
    job_result.status = job_status
    job_result.result = result
    job_result.error = error
    job_result.seconds = seconds """

    response = CgMLST(job_id=job_id)
    return response


@app.post('/comparative/cgmlst/store', response_model=CgMLST)
async def init_cgmlst(job_id: JobId) -> CgMLST:
    """
    Initiate a CgMLST comparative analysis job.
    """
    # r.hmset(job_id, {'status': 'Running'})
    # asyncio.create_task(do_nearest_neighbors(job_id, body))
    response = CgMLST(job_id=job_id.__root__)
    return response


