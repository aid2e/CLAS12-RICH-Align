import os, sys, subprocess
import numpy as np
from ax.core.base_trial import TrialStatus
from time import time
from ProjectUtils.edit_text_file import *
from ProjectUtils.config_editor import *
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
    metrics = None
    output_dir = None
    
    def submit_slurm_job(self, jobnum, scriptname, config):
        config_data = ReadJsonFile(config)        
        account = config_data["jobs"]["ACCOUNT"]
        partition = config_data["jobs"]["PARTITION"]
        time_limit = config_data["jobs"]["TIME_LIMIT"]
        memory = config_data["jobs"]["MEMORY"]
        # assuming we have one bash script to run per job
        with open(self.output_dir+"/jobconfig_{}.slurm".format(jobnum),"w") as file:
            file.write("#!/bin/bash\n")
            file.write("#SBATCH --job-name=rich-align-bo\n")
            file.write(f"#SBATCH --account={account}\n")
            file.write(f"#SBATCH --partition={partition}\n")
            file.write(f"#SBATCH --mem={memory}\n")
            file.write("#SBATCH --cpus-per-task=1\n")
            file.write(f"#SBATCH --time={time_limit}\n") 
            file.write("#SBATCH --output="+self.output_dir+f"/log/job_output/drich-mobo_{jobnum}.out\n")
            file.write("#SBATCH --error="+self.output_dir+f"/log/job_output/drich-mobo_{jobnum}.err\n")
            file.write(f'{os.environ["AIDE_HOME"]}/Clas12RichUtils/{scriptname} {jobnum} {config}\n')
        print("starting slurm job ", jobnum)
        shellcommand = ["sbatch","--export=ALL",self.output_dir+"/jobconfig_{}.slurm".format(jobnum)]
        
        commandout = subprocess.run(shellcommand,stdout=subprocess.PIPE)
        
        output = commandout.stdout.decode('utf-8')
        line_split = output.split()
        if len(line_split) == 4:
            return int(line_split[3])
        else:
            return -1
        return
        
    def schedule_job_with_parameters(self, parameters, scriptname, config):
        ### HERE: schedule the slurm job, retrieve the jobid from command line output        
        ### totaljobs/jobid defines the suffix of the files we will use
        jobid = self.totaljobs

        config_data = ReadJsonFile(config)
        init_file = config_data["reco"]["INIT_ALIGN_FILE"]
        sector = config_data["calibration"]["SECTOR"]
        create_dat_general(parameters, jobid, self.output_dir, init_file, sector)
        
        slurmjobnum = self.submit_slurm_job(jobid, scriptname, config)        
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
        ### HERE: load results from text file, formatted based on job id
        results = np.loadtxt(self.output_dir+"/log/results/" + "rich-align-mobo-out_{}.txt".format(jobid))        
        results_dict = {}
        if len(self.metrics) > 1:
            for idx, obj in enumerate(self.metrics):
                mean = results[2*idx]
                sem = results[2*idx+1]
                if sem == 0:
                    sem = None
                results_dict[obj] = [mean,sem]
        else:
            results_dict = {self.metrics[0]:results}
        return results_dict

SLURM_QUEUE_CLIENT = SlurmQueueClient()

def get_slurm_queue_client():
    return SLURM_QUEUE_CLIENT
