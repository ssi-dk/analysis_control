from __future__ import annotations

from datetime import datetime
import os
import pathlib
import subprocess
import yaml
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks
import pandas as pd

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

with open('config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

mongo = MongoClient(config['mongo_key'])
db = mongo.get_database()

for k, v in config['species'].items():
    cgmlst_dir = pathlib.Path(v['cgmlst'])

    distance_matrix_path = cgmlst_dir.joinpath('distance_matrix.tsv')
    start = datetime.now()
    data[k] = dict()
    print(f"Start loading distance matrix for {k} at {start}")
    data[k]['distance_matrix'] = pd.read_csv(distance_matrix_path, sep=' ', index_col=0, header=None)
    finish = datetime.now()
    print(f"Finished loading distance matrix for {k} in {finish - start}")

    allele_profile_path = cgmlst_dir.joinpath('allele_profiles.tsv')
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
        pathlib.Path(__file__).parent.joinpath('fake_cluster_commands')
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


def lookup_allele_profiles(sequences: list[str], all_allele_profiles: list[str]):
    found = list()
    found.append(all_allele_profiles[0])  # Append header line to result
    for prospect in all_allele_profiles:
        for wanted in sequences:
            i = prospect.index('\t')
            if prospect[:i] == wanted:
                found.append(prospect)
    assert len(found) == len(sequences) + 1
    return '\n'.join(found) + '\n'


def generate_tree(_id, profiles: str):
    return db.trees.find_one_and_update(
        {'_id': _id}, {'$set': {'tree': MSTrees.backend(profile=profiles)}})


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
            'created': job.started_at,
            'type': 'S',
            'elements': job.sequences,
            'species': job.species.replace('_', ' ')
        }).inserted_id
    job.job_id = str(_id)
    job.status = JobStatus.Accepted
    profiles = lookup_allele_profiles(job.sequences, data[job.species]['allele_profiles'])
    background_tasks.add_task(generate_tree, _id, profiles)
    return job


@app.post('/comparative/cgmlst/profile_diffs', response_model=ComparativeAnalysis)
async def profile_diffs(job: ComparativeAnalysis = None) -> ComparativeAnalysis:
    """
    Show differences between requested allele profiles.
    """
    profiles = lookup_allele_profiles(job.sequences, data[job.species]['allele_profiles'])
    job.result = 'Hej'
    return job



