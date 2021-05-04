from typing import List
import bifrostapi

from .models import (JobResponse, BifrostAnalysis, SequenceId)

def build_snakemake_command(sing_args, sing_prefix, component_path, sample_id, component_id, extra_arg=''):
    return_str = f'snakemake --use-singularity  --singularity-args \"{sing_args}\" '
    + f'--singularity-prefix \"{sing_prefix}\" --restart-times 2 '
    + f"--cores 4 -s {component_path} "
    + f"--config sample_id={sample_id} component_id={component_id} {extra_arg}; "

def create_and_execute_bifrost_run(analysis: BifrostAnalysis, sequence_ids: List[SequenceId]):
    """
    Create a Bifrost run with one sample and one or more analyses.
    """
    """
    First step: create a run in Bifrost.
    For this we'll probably need:
    - The input folder (which is the folder containing the sample data)
    - The output folder (which we create here)
    - The tools list (which we have as a function argument)
    """
    # run = bifrostapi.create_virtual_run(name, ip, samples)

    # Build command
    # command = (f'if [ -d \"{analysis}\" ]; then rm -r {analysis}; fi; ')  # Delete component folder beneath sequence folder
    # command += build_snakemake_command(sing_args, sing_prefix, component_path, sample_id, component_id, "--unlock")
    # command += build_snakemake_command(sing_args, sing_prefix, component_path, sample_id, component_id)
    # command += (f"#PBS -V -d . -w . -l mem={memory}gb,nodes=1:"
    #     + f"ppn={threads},walltime={walltime}{advres} -N "
    #     + f"'bifrost_{sample_name}' -W group_list={group}"
    #     + f" -A {group} \n")

    # Put script file on filesystem (maybe also function as a log of what has been done?)
    # script_path = os.path.join(sample_path, "manual_rerun.sh")
    # with open(script_path, "w") as script:
    #     script.write(command)

    # Tell qsub to execute script
    # process = subprocess.Popen(
    #     'qsub {}'.format(script_path),
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.STDOUT,
    #     shell=True,
    #     env=os.environ,
    #     cwd=sample_path
    # )
    # process_out, process_err = process.communicate()

    # Get job id from process out
    job_response = JobResponse()
    return job_response