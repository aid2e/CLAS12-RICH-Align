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
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.optimize import minimize
from pymoo.core.evaluator import Evaluator
from pymoo.problems.static import StaticProblem

# Subclassing Ax 'ExternalGenerationNode' based on tutorial at
# https://ax.dev/tutorials/external_generation_node.html
class PymooGenerationNode(ExternalGenerationNode):
    def __init__(self, algo, problem, pop_size, name, gen_num, transition_criteria=None, algo_options: Dict[str, Any] = None) -> None:
        t_init_start = time.monotonic()
        super().__init__(node_name=name,transition_criteria=transition_criteria)
        self.algo = algo
        self.problem = problem
        self.pop_size = pop_size        
        self.gen_num = gen_num
        self.parameters: Optional[List[RangeParameter]] = None        
        self.minimize: Optional[bool] = None
        self.fit_time_since_gen: float = time.monotonic() - t_init_start
        self.candidate_num = 0
        self.n_generations = 0
        print("initialized node ", name)
    @property
    def model_to_gen_from_name(self) -> str | None:
        # Override definition in GenerationNode
        # If no model name, error raised during assertion in MaxGenerationParallelism
        return "pymoo"
    def update_generator_state(self, experiment: Experiment, data: Data) -> None:
        print("checking if time to update generator state, n_generations: ", self.n_generations, " node name: ", self.node_name)
        # We generate a population of size 'pop_size',
        # evaluate all of these candidates, then
        # only produce a new generation when candidate_num == pop_size

        # if already produced a generation in this instance, skip update.
        if self.n_generations > 0:
            if self.candidate_num < self.pop_size:
                return
        print("generating new population")
        search_space = experiment.search_space
        parameter_names = list(search_space.parameters.keys())
        metric_names = list(experiment.optimization_config.metrics.keys())

        # for first generation, just 'ask'.
        # if not first generation, read in results from last
        if self.gen_num != 0:
            # Get the data for the completed trials, fill population
            num_completed_trials = len(experiment.trials_by_status[TrialStatus.COMPLETED])
            
            # last population should be [num_completed_trials - pop_size:num_completed_trials]
            X = []
            Y = []

            # first: get all completed trials
            for t_idx, trial in experiment.trials.items():                
                if trial.status == TrialStatus.COMPLETED:
                    trial_parameters = trial.arm.parameters
                    x = np.array([trial_parameters[p] for p in parameter_names])
                    trial_df = data.df[data.df["trial_index"] == t_idx]
                    y = trial_df[trial_df["metric_name"] == metric_names[0]][
                        "mean"
                    ].item()
                    # Individual for population
                    X.append(x)
                    Y.append(y)
            Y = np.array(Y)
            X = np.array(X)
            # TODO: instead, select only trials where name matches the
            # last generation node
            ind_arr = []

            if len(Y)-self.pop_size < 0:
                trialmin = 0
            else:
                trialmin = len(Y)-self.pop_size
            trialmax = len(Y)
            last_population = Population.new("X", X[trialmin:trialmax])
            #print("y shape before: ", Y.shape)    
            Y = Y[trialmin:trialmax]
            #print("y shape after: ", Y.shape)
            
            static = StaticProblem(self.problem, F=Y)
            Evaluator().eval(static, last_population)
            self.algo.tell(infills=last_population)

        self.pop = self.algo.ask()
        self.current_pop_size = len(self.pop)
        # Update the attributes not set in __init__.
        self.parameters = search_space.parameters
        self.minimize = experiment.optimization_config.objective.minimize
        self.candidate_num = 0
        self.n_generations += 1
    def get_next_candidate(
        self, pending_parameters: List[TParameterization]
    ) -> TParameterization:
        x = self.pop.get("X")[self.candidate_num]
        candidate = {
            p_name: x[i]
            for i, p_name in enumerate(self.parameters.keys())
        }
        self.candidate_num += 1
        return candidate
