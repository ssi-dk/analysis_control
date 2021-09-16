from __future__ import annotations

import asyncio
from uuid import uuid4
from datetime import datetime, timedelta
import os
import pathlib
import json
import subprocess
import yaml
from datetime import datetime

from fastapi import FastAPI
import redis
import pandas as pd
from grapetree.module import MSTrees


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

data = dict()

with open('config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)
for k, v in config['species'].items():
    chewie_workdir = pathlib.Path(v['chewie_workdir'])

    distance_matrix_path = chewie_workdir.joinpath('output/cgmlst/distance_matrix.tsv')
    start = datetime.now()
    data[k] = dict()
    print(f"Start loading distance matrix for {k} at {start}")
    data[k]['distance_matrix'] = pd.read_csv(distance_matrix_path, sep=' ', index_col=0, header=None)
    finish = datetime.now()
    print(f"Finished loading distance matrix for {k} in {finish - start}")

    allele_profile_path = chewie_workdir.joinpath('output/cgmlst/allele_profiles.tsv')
    start = datetime.now()
    print(f"Start loading allele profiles for {k} at {start}")
    with open(allele_profile_path) as f:
        data[k]['allele_profiles'] = f.readlines()
    finish = datetime.now()
    print(f"Finished loading allele profiles for {k} in {finish - start}")

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


def find_nearest_neighbors(input_sequence: str, matrix: pd.DataFrame, cutoff: int):
    result = set()
    row: pd.Series = matrix.loc[input_sequence , :]
    # print("Row:")
    # print(row)
    # Run through the columns in the row and see if they are less than or equal to cutoff.
    for item in row.iteritems():
        print(f"Item within row: {item}")
        idx = item[0]
        distance = item[1]
        # What is the name of the sample in ROW <index> (assuming that rows and columns use the same order)?
        found_sequence: pd.Series = matrix.index[idx - 1]
        print(f"Found sequence name: {found_sequence}")
        if distance <= cutoff:
            print(f"Distance {distance} is smaller than cutoff {cutoff}.")
            if found_sequence == input_sequence:
                print(f"However, {found_sequence} is our input sequence, so it's not a match!")
            else:
                print(f"{found_sequence} is not {input_sequence}, so this is in fact a match!")
                result.add(found_sequence)
    return result


@app.post('/comparative/nearest_neighbors/from_dm', response_model=NearestNeighbors)
async def init_nearest_neighbors(job: NearestNeighbors) -> NearestNeighbors:
    """
    Nearest neighbors from distance matrix.
    """
    job.job_id = str(uuid4())
    job.status = JobStatus.Accepted
    species = job.species.replace(' ', '_')
    matrix = data[species]['distance_matrix']
    result_seq_set = set()
    for input_sequence in job.sequences:
        print()
        print(f"***** Now looking at this input sequence: {input_sequence}.")
        result_sequences = find_nearest_neighbors(input_sequence, matrix, job.cutoff)
        for s in result_sequences:
            # If it's already in the set it will not be added
            result_seq_set.add(str(s))
        job.result = list(result_seq_set)
    return job


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
    # Todo: use job.species.replace(' ', '_')
    all_allele_profiles: list = data['Salmonella_enterica']['allele_profiles']
    profiles_for_tree = lookup_allele_profiles(job.sequences, all_allele_profiles)
    job.result = MSTrees.backend(profile=profiles_for_tree)
    return job

def lookup_allele_profiles(sequences: list[str], all_allele_profiles: list[str]):
    found = list()
    for prospect in all_allele_profiles:
        if prospect.startswith('#'):  # header line
            continue
        for wanted in sequences:
            i = prospect.index('\t')
            if prospect[:i] == wanted:
                found.append(prospect)
    return '\n'.join(found)


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


