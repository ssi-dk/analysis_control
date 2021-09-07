from __future__ import annotations

import asyncio
from uuid import uuid4
from datetime import datetime
import os
import pathlib
import json
import subprocess
import yaml

from fastapi import FastAPI
import redis
import bifrostapi
from grapetree import module


from models import (
    BifrostAnalysisList,
    BifrostAnalysis,
    BifrostJob,
    CgMLST,
    NearestNeighbors,
    JobId,
    JobStatus,
)

app = FastAPI(
    title='Analysis Control',
    version='0.6',
    description='API for controlling analysis jobs on the SOFI platform',
    contact={'name': 'ssi.dk'},
)

r = redis.Redis(charset="utf-8", decode_responses=True)

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


@app.post('/bifrost/init', response_model=BifrostJob)
def init_bifrost_job(job: BifrostJob = None) -> BifrostJob:
    """
    Initiate a Bifrost job with one or more sequences and one or more Bifrost analyses.
    """

    # Todo: Find sequence in MongoDB and return with error if not found

    # For each analysis, make sure that analysis is present in config
    for analysis in job.analyses:
        try:
            assert analysis in config['bifrost_analyses']
            job.status = JobStatus.Accepted
        except AssertionError:
            job.status = JobStatus.Rejected
            job.error = f"Could not find a Bifrost analysis with the identifier '{analysis}'."
            return job
    
    command_prefix = config['hpc_command_prefix']
    launch_script = config['bifrost_launch_script']
    work_dir = config['bifrost_work_dir'] if config['production'] else \
        pathlib.Path(__file__).parent.parent.joinpath('fake_cluster_commands')
    raw_command = f"{launch_script} -s {' '.join(job.sequences)} -a {' '.join(job.analyses)}"
    command = f"{command_prefix} {raw_command}" if config['bifrost_use_hpc'] else raw_command
    print(command)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=os.environ,
        cwd=work_dir
    )
    process_out, process_error = process.communicate()
    if process_out:
        job.job_id = (str(process_out, 'utf-8')).rstrip()
        job.status = JobStatus.Queued
    if process_error:
        job.error = (str(process_error, 'utf-8')).rstrip()
        job.status = JobStatus.Failed
    return job


@app.get('/bifrost/status', response_model=BifrostJob)
def status_bifrost(job_id: str) -> BifrostJob:
    job = BifrostJob(job_id=job_id)
    process = subprocess.Popen(
        f"checkjob {job_id}",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=os.environ,
    )
    process_out, process_error = process.communicate()
    if process_out:
        # Todo: set job.status after parsing process_out
        job.status = JobStatus.Running
    if process_error:
        job.error = (str(process_error, 'utf-8')).rstrip()
        job.status = JobStatus.Failed
    return job


@app.post('/comparative/nearest_neighbors/from_dm', response_model=NearestNeighbors)
async def init_nearest_neighbors(job: NearestNeighbors) -> NearestNeighbors:
    """
    Initiate a "nearest neighbors" comparative analysis job.
    """
    job.job_id = str(uuid4())
    job.status = JobStatus.Accepted
    r.set(job.job_id, job.json())
    asyncio.create_task(do_nearest_neighbors(job))
    return job


async def do_nearest_neighbors(job: NearestNeighbors):
    start_time = datetime.now()
    # job.result = [ str(element['_id']) for element in sample_ids_cursor ]
    end_time = datetime.now()
    processing_time = end_time - start_time
    job.finished_at = end_time
    job.seconds = processing_time
    r.set(job.job_id, job.json())


@app.get('/comparative/nearest_neighbors/status', response_model=NearestNeighbors)
def status_nearest_neighbors(job_id: str) -> NearestNeighbors:
    """
    Get the current status of a "nearest neighbors" job.
    """
    response = NearestNeighbors(**json.loads(r.get(job_id)))
    return response


@app.post('/comparative/nearest_neighbors/store', response_model=NearestNeighbors)
async def store_nearest_neighbors(job_id: JobId) -> NearestNeighbors:
    """Store the list of sequence ids permanently (in MongoDB or Postgres) together with
    meta information (owner, date, description, etc.). After this, the Redis entry should
    be deleted.
    """
    job_id = job_id.__root__
    response = NearestNeighbors(**json.loads(r.get(job_id)))
    return response


@app.post('/comparative/cgmlst/init', response_model=CgMLST)
async def init_cgmlst(job: CgMLST = None) -> CgMLST:
    """
    Initiate a cgMLST comparative analysis job
    """
    job.job_id = str(uuid4())
    job.status = JobStatus.Accepted
    r.set(job.job_id, job.json())
    asyncio.create_task(do_cgmlst(job))
    return job

def lookup_allele_profile(hash_id: str, identified_species: str):
    key = f"allele_profile_{identified_species}:{hash_id}"
    ret = list()
    ret.append(hash_id)
    ret.extend(r.lrange(key, 0, -1))
    return ret

async def do_cgmlst(job:CgMLST):
    job.status = JobStatus.Running
    start_time = datetime.now()
    # Currently we assume that input is given as allele hash ids, not as sequence names.
    # Look up the actual allele profiles from hash ids.
    allele_profiles = [ lookup_allele_profile(hash_id, job.identified_species) for hash_id in job.allele_hash_ids ]
    # Turn each element in allele_profiles into a tab-separated string
    allele_profiles_as_text_lines = list()
    for allele_profile in allele_profiles:
        line = "\t".join(allele_profile) + "\n"
        allele_profiles_as_text_lines.append(line)
    # The following lines are not beautiful - only for prototype...
    temp_path = pathlib.Path(__file__).parent.parent.joinpath('tmp')
    temp_path.mkdir(exist_ok=True)
    profile_file = temp_path.joinpath('grapetree_input.tsv')
    with open(profile_file, 'w') as profile_file_writer:
        header_names = [ str(i) for i in range(1, 3001) ]
        profile_file_writer.write("#Hash ID\t" + "\t".join(header_names) + "\n")
        profile_file_writer.writelines(allele_profiles_as_text_lines)
    script_path = pathlib.Path(__file__).parent.parent.joinpath('commands').joinpath('generate_newick.py')
    cmd = f"python {script_path} {profile_file}"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    end_time = datetime.now()
    processing_time = end_time - start_time
    if proc.returncode == 0:
        job.status = JobStatus.Succeeded
        job.result = stdout
        job.finished_at = end_time
        job.seconds = processing_time
    else:
        job.status = JobStatus.Failed
        job.error = stderr
    r.set(job.job_id, job.json())


@app.get('/comparative/cgmlst/status', response_model=CgMLST)
def status_cgmlst(job_id: str) -> CgMLST:
    """
    Get the current status of a "nearest neighbors" job.
    """
    response = CgMLST(**json.loads(r.get(job_id)))
    return response


@app.post('/comparative/cgmlst/store', response_model=CgMLST)
async def init_cgmlst(job_id: JobId) -> CgMLST:
    """Store the the phylogenetic tree permanently (in MongoDB or Postgres) together with
    meta information (owner, date, description, etc.). After this, the Redis entry should
    be deleted.
    """
    job_id = job_id.__root__
    response = CgMLST(**json.loads(r.get(job_id)))
    return response


