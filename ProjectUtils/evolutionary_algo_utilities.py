import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from ax.core.base_trial import TrialStatus
from ax.core.data import Data
from ax.core.experiment import Experiment
from ax.core.parameter import RangeParameter
from ax.core.types import TParameterization
from ax.modelbridge.external_generation_node import ExternalGenerationNode
from ax.modelbridge.generation_node import GenerationNode
from ax.modelbridge.generation_strategy import GenerationStrategy
from ax.modelbridge.model_spec import ModelSpec
from ax.modelbridge.registry import Models
from ax.modelbridge.transition_criterion import MaxTrials
from ax.plot.trace import plot_objective_value_vs_trial_index
from ax.service.ax_client import AxClient, ObjectiveProperties
from ax.service.utils.report_utils import exp_to_df
from ax.utils.common.typeutils import checked_cast
from ax.utils.measurement.synthetic_functions import hartmann6
from sklearn.ensemble import RandomForestRegressor

from pymoo.core.problem import Problem
from pymoo.core.population import Population
from pymoo.core.individual import Individual
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

# Subclassing Ax 'ExternalGenerationNode' based on tutorial at
# https://ax.dev/tutorials/external_generation_node.html
class NSGA2GenerationNode(ExternalGenerationNode):
    def __init__(self, pop_size, transition_criteria=None, algo_options: Dict[str, Any] = None) -> None:
        t_init_start = time.monotonic()
        super().__init__(node_name="NSGA2",transition_criteria=transition_criteria)
        self.algorithm = NSGA2(pop_size=pop_size)
        
        self.parameters: Optional[List[RangeParameter]] = None
        self.minimize: Optional[bool] = None
        self.fit_time_since_gen: float = time.monotonic() - t_init_start
        
    def update_generator_state(self, experiment: Experiment, data: Data) -> None:
        search_space = experiment.search_space
        parameter_names = list(search_space.parameters.keys())
        metric_names = list(experiment.optimization_config.metrics.keys())

        # Get the data for the completed trials, fill population
        population = Population()        
        num_completed_trials = len(experiment.trials_by_status[TrialStatus.COMPLETED])
        for t_idx, trial in experiment.trials.items():
            if trial.status == "COMPLETED":                
                trial_parameters = trial.arm.parameters
                x = np.array([trial_parameters[p] for p in parameter_names])
                trial_df = data.df[data.df["trial_index"] == t_idx]
                y = trial_df[trial_df["metric_name"] == metric_names[0]][
                    "mean"
                ].item()
                # Individual for population 
                ind = Individual(X=x, F=[y])
                population.append(ind)
        # Train the regressor.

        # assuming all range parameters
        upper_bounds = []
        lower_bounds = []
        for p in parameter_names:
            upper_bounds.append(search_space.parameters[p].upper)
            lower_bounds.append(search_space.parameters[p].lower)
            
        
        class MyProblem(Problem):
            
            def __init__(self):
                super().__init__(n_var=len(parameter_names),
                                 n_obj=1,
                                 xl=np.array(lower_bounds),
                                 xu=np.array(upper_bounds))                
                def _evaluate(self, x, out, *args, **kwargs):
                    out["F"] = np.zeros(x.shape[0])
                    
        self.algo_result = minimize(problem=MyProblem(),
                               algorithm=self.algorithm,
                               termination=('n_gen',1), #Produce 1 generation here
                               verbose=False,
                               pop=population
                               )
        # Update the attributes not set in __init__.
        self.parameters = search_space.parameters
        self.minimize = experiment.optimization_config.objective.minimize
        self.candidate_num = 0
    def get_next_candidate(
        self, pending_parameters: List[TParameterization]
    ) -> TParameterization:
        x = self.algo_result.pop.get("X")[self.candidate_num]
        candidate = {
            p_name: x[i]
            for i, p_name in enumerate(self.parameters.keys())
        }
        self.candidate_num += 1
        return candidate
