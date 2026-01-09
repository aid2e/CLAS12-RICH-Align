from collections import defaultdict
from typing import Any, Mapping

from ax.api.protocols.metric import IMetric
from ax.api.protocols.runner import IRunner, TrialStatus
from ax.api.types import TParameterization

from .slurm_utilities_global import get_slurm_queue_client

# could probably condense this with SlurmQueueClient at this point
class SlurmJobRunner(IRunner):  # Deploys trials to external system.
    def __init__(self, metrics, scriptname, config, output_dir, first_trial_number, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # list of objectives (to pass to SlurmQueueClient)
        self.metrics = metrics
        self.scriptname = scriptname
        self.config = config
        self.output_dir = output_dir
        slurm_job_queue = get_slurm_queue_client()
        slurm_job_queue.output_dir = output_dir
        slurm_job_queue.totaljobs += first_trial_number
        
    def run_trial(self, trial_index: int, parameterization: TParameterization):
        slurm_job_queue = get_slurm_queue_client()
        slurm_job_queue.output_dir = self.output_dir
        # supply objective names if not already set for SlurmQueueClient
        if slurm_job_queue.metrics == None:
            slurm_job_queue.metrics = self.metrics

        # store slurm job ID
        job_id = slurm_job_queue.schedule_job_with_parameters(
            parameters=parameterization,
            scriptname=self.scriptname,
            config=self.config
            
        )

        return {"job_id": job_id}
    def poll_trial(self, trial_index: int, trial_metadata: Mapping[str, Any]):
        slurm_job_queue = get_slurm_queue_client()
        status = slurm_job_queue.get_job_status(
            trial_metadata["job_id"]
        )
        return status
