from ProjectUtils.config_editor import *
from ProjectUtils.mobo_utilities import *
from ProjectUtils.evolutionary_algo_utilities import *
from ProjectUtils.cma_node import CMAESGenerationNode

import os, pickle, torch, argparse, datetime, sys
import time

import pandas as pd
from ax import *

import numpy as np

from ax.metrics.noisy_function import GenericNoisyFunctionMetric
from ax.service.utils.report_utils import exp_to_df

# Model registry for creating multi-objective optimization models.
from ax.modelbridge.registry import Models

# Scheduler imports
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions

from ax.core.metric import Metric
from botorch.utils.multi_objective.box_decompositions.dominated import (
    DominatedPartitioning,
)

import matplotlib.pyplot as plt

from ax.modelbridge.registry import Models
from ProjectUtils.runner_utilities import SlurmJobRunner
from ProjectUtils.metric_utilities import SlurmJobMetric

from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.modelbridge.modelbridge_utils import observed_hypervolume
from ax.models.torch.botorch_modular.surrogate import Surrogate
from ax.models.torch.botorch_modular.model import BoTorchModel
from ax.modelbridge.torch import TorchModelBridge
from botorch.acquisition.monte_carlo import (
    qNoisyExpectedImprovement,
)
from botorch.acquisition.logei import (
    qLogExpectedImprovement,
)
#transition criteria (for GenerationNodes)
from ax.modelbridge.transition_criterion import MaxTrials, MinTrials
from ax.modelbridge.transition_criterion import MaxGenerationParallelism
from ax.core.base_trial import TrialStatus

# for sql storage of experiment
from ax.storage.metric_registry import register_metrics
from ax.storage.runner_registry import register_runner

from ax.storage.registry_bundle import RegistryBundle
from ax.storage.sqa_store.db import (
    create_all_tables,
    get_engine,
    init_engine_and_session_factory,
)
from ax.storage.sqa_store.decoder import Decoder
from ax.storage.sqa_store.encoder import Encoder
from ax.storage.sqa_store.sqa_config import SQAConfig
from ax.storage.sqa_store.structs import DBSettings

# pymoo imports
from pymoo.core.problem import Problem
from pymoo.core.termination import NoTermination
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.algorithms.soo.nonconvex.cmaes import CMAES
from pymoo.algorithms.soo.nonconvex.de import DE

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description= "Optimization, dRICH")
    parser.add_argument('-c', '--config', 
                        help='Optimization configuration file', 
                        type = str, required = True)
    parser.add_argument('-d', '--detparameters', 
                        help='Detector parameter configuration file', 
                        type = str, required = True)
    parser.add_argument('-j', '--json_file', 
                        help = "The json file to load and continue optimization", 
                        type = str, required=False)
    args = parser.parse_args()
    
    # READ SOME INFO 
    config = ReadJsonFile(args.config)
    detconfig = ReadJsonFile(args.detparameters)
    
    outdir = config["OUTPUT_DIR"]    
    if(not os.path.exists(outdir)):
        os.makedirs(outdir)

    isGPU = torch.cuda.is_available()
    tkwargs = {
        "dtype": torch.double, 
        "device": torch.device("cuda" if isGPU else "cpu"),
    }
    
    print(detconfig["parameters"])

    # creates linear constraint to pass to ax SearchSpace
    # based on list of parameters with weights given in --detparameters.
    # constraints pass if output < 0
    def constraint_ax(constraints,parameters):
        # constraint_dict: Dict[str,float], bound: float
        constraint_list = []
        for c in constraints:
            param_dict = {}
            param_list = constraints[c]["parameters"]
            for param in parameters:
                if param in param_list:
                    param_dict[param] = constraints[c]["weights"][param_list.index(param)]
                else:
                    param_dict[param] = 0
            print("param dict: ", param_dict, " param_list: ", param_list)
            constraint_list.append( ParameterConstraint(param_dict,constraints[c]["bound"]) )
        return constraint_list
    
    parameters = list(detconfig["parameters"].keys())
    
    # create search space with linear constraints
    search_space = SearchSpace(
        parameters=[
            RangeParameter(name=i,
                           lower=float(detconfig["parameters"][i]["lower"]), upper=float(detconfig["parameters"][i]["upper"]), 
                           parameter_type=ParameterType.FLOAT)
            for i in detconfig["parameters"]]
    )

    names = ["mean_mchi2" #RICH track-cluster matching
             ]  
    metrics = []
    
    for name in names:
        metrics.append(
            SlurmJobMetric(
                name=name, lower_is_better=True
            )
        )
    objective = Objective(metrics[0])
    
    optimization_config = OptimizationConfig(objective=objective)

    #TODO: implement check of dominated HV convergence instead of
    #fixed N points
    BATCH_SIZE_SOBOL = config["n_batch_sobol"]
    N_SOBOL = config["n_sobol"]
    pop_size = config["pop_size"]
    n_evolutions = config["n_generations"]
    BATCH_SIZE_EVO = config["n_batch_evo"]
    #N_TOTAL = N_SOBOL + pop_size*n_evolutions 
    N_TOTAL = pop_size*n_evolutions 
    print("running ", N_TOTAL, " trials")
    outname = config["OUTPUT_NAME"]
            
    #experiment with custom slurm runner
    experiment = build_experiment_slurm(search_space,optimization_config, SlurmJobRunner())
    
    lower_bounds = np.array([ float(detconfig["parameters"][i]["lower"]) for i in detconfig["parameters"] ])
    upper_bounds = np.array([ float(detconfig["parameters"][i]["upper"]) for i in detconfig["parameters"] ])

    problem = Problem(n_var=len(parameters), n_obj=1, n_constr=0, xl=lower_bounds, xu=upper_bounds)
    algorithm = GA(pop_size=pop_size,eliminate_duplicates=True)
    
    termination = NoTermination()
    algorithm.setup(problem, termination=termination)
    
    nodes = []
    #algo, problem, name, name_lastnode, gen_num
    # create n_evolutions generation nodes (each node producing one generation through
    # pymoo ask-tell interface)
    for i in range(0,n_evolutions):
        nodes.append(PymooGenerationNode(algorithm,problem,"pymoo_"+str(i),
                                         "pymoo_"+str(i-1),i,
                                         transition_criteria=[
                                             MaxGenerationParallelism(pop_size),
                                             MinTrials(threshold=pop_size,block_transition_if_unmet=True,only_in_statuses=[TrialStatus.COMPLETED],
                                                       transition_to="pymoo_"+str(i+1))
                                         ]
                                         ))
    nodes.append(PymooGenerationNode(algorithm,problem,"pymoo_"+str(n_evolutions),
				     "pymoo_"+str(n_evolutions-1),n_evolutions,
                                     transition_criteria=[
                                         MaxGenerationParallelism(BATCH_SIZE_EVO)
                                    ]))
    gen_strategy = GenerationStrategy(
        nodes=nodes
    )

    scheduler = Scheduler(experiment=experiment,
                          generation_strategy=gen_strategy,
                          options=SchedulerOptions(init_seconds_between_polls=10,
                                                   seconds_between_polls_backoff_factor=1,
                                                   min_failed_trials_for_failure_rate_check=2)                          
                          )
    
    scheduler.run_n_trials(max_trials=N_TOTAL)    
    
    # TODO: check for HV convergence
    #hv = observed_hypervolume(modelbridge=model_obj)
    
    exp_df = exp_to_df(experiment)    
    exp_df.to_csv(outname+".csv")
    
