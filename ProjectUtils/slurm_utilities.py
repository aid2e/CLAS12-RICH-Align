import os, sys, subprocess
import numpy as np
from ax.core.base_trial import TrialStatus
from time import time
from ProjectUtils.edit_text_file import *

from typing import Any, Dict, NamedTuple, Union

class SlurmJob(NamedTuple):
    id: int
    slurmid: int
    parameters: Dict[str, Union[str, float, int, bool]]
    
class SlurmQueueClient:
    """ Class to queue and query slurm jobs,
    based on https://ax.dev/tutorials/scheduler.html
    """
    jobs = {}
    totaljobs = 0
    objectives = ["mean_mchi2"
                  ]
    
    def submit_slurm_job(self, jobnum):
        with open("jobconfig_{}.slurm".format(jobnum),"w") as file:
            file.write("#!/bin/bash\n")
            file.write("#SBATCH --job-name=rich-align-mobo\n")
            file.write("#SBATCH --account=clas12\n")
            file.write("#SBATCH --partition=production\n")
            file.write("#SBATCH --mem=2G\n")
            file.write("#SBATCH --time=00:03:00\n") 
            file.write("#SBATCH --output="+str(os.environ["AIDE_HOME"])+"/log/job_output/drich-mobo_%j.out\n")
            file.write("#SBATCH --error="+str(os.environ["AIDE_HOME"])+"/log/job_output/drich-mobo_%j.err\n")
            file.write(str(os.environ["AIDE_HOME"])+'/Clas12RichUtils/runReconstruction.sh {}'.format(jobnum))
        print("starting slurm job ", jobnum)
        shellcommand = ["sbatch","--export=ALL","jobconfig_{}.slurm".format(jobnum)]        
        commandout = subprocess.run(shellcommand,stdout=subprocess.PIPE)
        
        output = commandout.stdout.decode('utf-8')
        line_split = output.split()
        if len(line_split) == 4:
            return int(line_split[3])
        else:
            return -1
        return
    
    def schedule_job_with_parameters(self, parameters):
        ### HERE: schedule the slurm job, retrieve the jobid from command line output        
        ### totaljobs/jobid defines the suffix of the files we will use
        jobid = self.totaljobs
        create_dat(parameters, jobid)
        create_yaml(jobid)
        
        slurmjobnum = self.submit_slurm_job(jobid)
        
        self.jobs[jobid] = SlurmJob(jobid, slurmjobnum, parameters) 
        self.totaljobs += 1
        return jobid
    
    def get_job_status(self, jobid):
        job = self.jobs[jobid]
        
        if job.slurmid == -1:
            # something failed in job submission
            return TrialStatus.FAILED

        ### HERE: run bash command to retrieve status, exit code
        shellcommand = [str(os.environ["AIDE_HOME"])+"/ProjectUtils/"+"checkSlurmStatus.sh", str(job.slurmid)]
        commandout = subprocess.run(shellcommand,stdout=subprocess.PIPE)
        
        output = commandout.stdout.decode('utf-8')
        line_split = output.split()

        if len(line_split) == 1:
            status = line_split[0]
        else:
            #something wrong, try again
            print("Error in checking slurm status, assuming still running")
            return TrialStatus.RUNNING

        if status == "0":
            return TrialStatus.RUNNING
        elif status == "1":
            return TrialStatus.COMPLETED
        elif status == "-2":
            return TrialStatus.EARLY_STOPPED
        elif status == "-1":
            return TrialStatus.FAILED
        
        return TrialStatus.RUNNING
    
    def get_outcome_value_for_completed_job(self, jobid):
        job = self.jobs[jobid]
        ### HERE: load results from text file, formatted based on job id
        results = np.loadtxt(str(os.environ["AIDE_HOME"])+"/log/results/" + "rich-align-mobo-out_{}.txt".format(jobid))
        results_dict = {"mean_mchi2":results}
        return results_dict

SLURM_QUEUE_CLIENT = SlurmQueueClient()

def get_slurm_queue_client():
    return SLURM_QUEUE_CLIENT
