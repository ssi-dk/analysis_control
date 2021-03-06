from __future__ import annotations

from datetime import datetime
import os
import pathlib
import subprocess
from pydantic.typing import all_literal_values
import yaml
from datetime import datetime
from collections import Set

from fastapi import FastAPI, BackgroundTasks
import pandas as pd
from paramiko.client import SSHClient
from paramiko import AutoAddPolicy
from pymongo import MongoClient

import MSTrees


from models import (
    BifrostAnalysisList,
    BifrostAnalysis,
    BifrostJob,
    ComparativeAnalysis,
    NearestNeighbors,
    JobStatus,
)

app = FastAPI(
    title='Analysis Control',
    version='0.6',
    description='API for controlling analysis jobs on the SOFI platform',
    contact={'name': 'Finn Gruwier Larsen', 'email': 'figl@ssi.dk'},
)

data = dict()

with open('./config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

mongo = MongoClient(os.getenv('MONGO_CONN'))
db = mongo.get_database()

for k, v in config['species'].items():  # For each configured species
    cgmlst_dir = pathlib.Path(os.getenv('CHEWIE_DATA'), v['cgmlst'])
    print(f"cgmlst_dir: {cgmlst_dir}")
    data[k] = dict()

    start = datetime.now()
    print(f"Start loading distance matrix for {k} at {start}")
    distance_matrix_path = cgmlst_dir.joinpath('distance_matrix.tsv')
    try:
        data[k]['distance_matrix'] = pd.read_csv(distance_matrix_path, sep=' ', index_col=0, header=None)
        finish = datetime.now()
        print(f"Finished loading distance matrix for {k} in {finish - start}")
    except FileNotFoundError:
        print(f"Distance matrix file not found: {distance_matrix_path}")

    start = datetime.now()
    print(f"Start loading allele profiles for {k} at {start}")
    try:
        allele_profile_path = cgmlst_dir.joinpath('allele_profiles.tsv')
        data[k]['allele_profiles'] = pd.read_csv(allele_profile_path, sep='\t', index_col=0, header=0)
        finish = datetime.now()
        print(f"Finished loading allele profiles for {k} in {finish - start}")
    except FileNotFoundError:
        print(f"Allele profile file file not found: {allele_profile_path}")

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

def get_hpc_conn():
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    hostname = os.getenv('HPC_HOSTNAME')
    port = int(os.getenv('HPC_PORT'))
    print(f"Connect to {hostname} on port {str(port)}")
    username = os.getenv('HPC_USERNAME')
    password = os.getenv('HPC_PASSWORD')
    ssh_client.connect(
        hostname=hostname,
        port=port,
        username=username,
        password=password
        )
    return ssh_client

@app.post('/bifrost/init', response_model=BifrostJob)
def init_bifrost_job(job: BifrostJob = None) -> BifrostJob:
    """
    Initiate a Bifrost job with one or more sequences and one or more Bifrost analyses.
    """

    # For each analysis, make sure that analysis is present in config
    for analysis in job.analyses:
        try:
            assert analysis in config['bifrost_analyses']
            job.status = JobStatus.Accepted
        except AssertionError:
            job.status = JobStatus.Rejected
            job.error = f"Could not find a Bifrost analysis with the identifier '{analysis}'."
            return job

    command_prefix = os.getenv('HPC_COMMAND_PREFIX')
    script_dir = os.getenv('BIFROST_SCRIPT_DIR')
    script_name = os.getenv('BIFROST_SCRIPT_NAME')
    launch_script = pathlib.Path(script_dir, script_name)
    raw_command = f"{launch_script} -s {' '.join(job.sequences)} -co {' '.join(job.analyses)}"
    command = f"{command_prefix} {raw_command}"
    print(f"HPC command: {command}")
    with get_hpc_conn() as  hpc:
        stdin, stdout, stderr = hpc.exec_command(command)
        job.process_out = str(stdout.readlines())
        job.process_error = str(stderr.readlines())
    if 'error' in job.process_out:
        job.status = JobStatus.Failed
    else:
        job.status = JobStatus.Accepted
    return job


@app.get('/bifrost/status', response_model=BifrostJob)
def status_bifrost(job_id: str) -> BifrostJob:
    job = BifrostJob(job_id=job_id)
    command = f"checkjob {job_id}"
    with get_hpc_conn() as  hpc:
        stdin, stdout, stderr = hpc.exec_command(command)
        job.process_out = str(stdout.readlines())
        job.process_error = str(stderr.readlines())
    if 'error' in job.process_out or len(job.process_error) > 0:
        job.status = JobStatus.Failed
    else:
        job.status = JobStatus.Accepted
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


@app.post('/comparative/cgmlst/nearest_neighbors', response_model=NearestNeighbors)
async def generate_nearest_neighbors(job: NearestNeighbors) -> NearestNeighbors:
    """
    Nearest neighbors from distance matrix.
    """
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


def generate_tree(_id, species: str, profiles: list[pd.Series]):
    # profile_str is a string in the format MSTrees.backend needs for input.
    # First add header by looking it up directly from 'data'.
    col_names: list = data[species]['allele_profiles'].columns.tolist()
    profile_str = '\t'.join(col_names) + '\n'
    for profile in profiles:
        p_list = profile.to_list()
        p_str = '\t'.join([str(v) for v in p_list])
        profile_str = profile_str + p_str + '\n'
    tree = MSTrees.backend(profile=profile_str)
    return db.trees.find_one_and_update(
        {'_id': _id}, {'$set': {'tree': tree, 'finished': datetime.now()}})


@app.post('/comparative/cgmlst/tree', response_model=ComparativeAnalysis)
async def cgmlst_tree(job: ComparativeAnalysis, background_tasks: BackgroundTasks) -> ComparativeAnalysis:
    """
    Generate minimum spanning tree for selected sequences based on cgMLST data.
    Trees are saved in MongoDB.
    'type' can be 'S' (samples) or 'P' (allele profiles).
    If type == 'S' we use sample names as 'elements'.
    If type == 'P' we use allele profile hash id's as 'elements'.
    """
    job.started_at = datetime.now()
    _id = db.trees.insert_one({
            'initialized': job.started_at,
            'type': 'S',
            'elements': job.sequences,
            'species': job.species.replace('_', ' ')
        }).inserted_id
    job.job_id = str(_id)
    job.status = JobStatus.Accepted
    all_allele_profiles: pd.DataFrame = data[job.species]['allele_profiles']
    profiles: list[pd.Series] = [all_allele_profiles.loc[sequence_id] for sequence_id in job.sequences]
    background_tasks.add_task(generate_tree, _id, job.species, profiles)
    return job


@app.post('/comparative/cgmlst/profile_diffs', response_model=ComparativeAnalysis)
async def profile_diffs(job: ComparativeAnalysis = None) -> ComparativeAnalysis:
    """
    Show differences between requested allele profiles.
    """
    df: pd.DataFrame = data[job.species]['allele_profiles']
    filtered_df: pd.DataFrame = df.loc[job.sequences]
    columns_to_show = list()
    for label, content in filtered_df.items():
        previous_value = None
        for value in content:
            if value == "#FILE":
                continue
            if value == "-":
                columns_to_show.append(label)
                break
            if value == previous_value:
                continue
            columns_to_show.append(label)
            break

    result_df: pd.DataFrame = filtered_df[columns_to_show]
    job.result = result_df.to_dict()
    return job
