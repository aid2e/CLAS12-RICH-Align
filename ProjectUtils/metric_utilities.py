import pandas as pd
from typing import Any, Mapping

from ax.api.protocols.metric import IMetric
from ax.core.data import Data
from .slurm_utilities import get_slurm_queue_client

class SlurmJobMetric(IMetric):  # Pulls data for trial from external system.                                                     
    def fetch(self, trial_index: int, trial_metadata: Mapping[str, Any]):
        slurm_job_queue = get_slurm_queue_client()
        metric_data = slurm_job_queue.get_outcome_value_for_completed_job(
            trial_metadata["job_id"]
        )
        mean = metric_data.get(self.name)[0]
        sem = metric_data.get(self.name)[1]
        if sem == None:
            return (trial_index, mean)
        else:
            return (trial_index, (mean, sem))
