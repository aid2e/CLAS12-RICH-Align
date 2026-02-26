from ProjectUtils.config_editor import *
from ProjectUtils.genstrategy_utilities import construct_generation_strategy, construct_turbo_generation_strategy
import os, argparse, shutil

import pandas as pd
import numpy as np
import json
from dataclasses import asdict

# Ax imports
from ax import *
from ax.api.client import Client
from ax.api.configs import RangeParameterConfig
from ax.service.utils.report_utils import exp_to_df

# Scheduler/runner imports
from ProjectUtils.runner_utilities import SlurmJobRunner
from ProjectUtils.metric_utilities import SlurmJobMetric
from ProjectUtils.turbo_utilities import TuRBOGenerationNode, TurboState


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
    
    config = ReadJsonFile(args.config) # optimization parameters
    detconfig = ReadJsonFile(args.detparameters) # geometry parameters

    csvdir = config["paths"]["CSV_DIR"]    
    outdir = config["paths"]["OUTPUT_DIR"]    
    outname = config["paths"]["OUTPUT_NAME"]
    logdir = config["paths"]["LOG_DIR"]    
    
    metric_name = config["optimization"]["METRIC_NAME"]
    job_script_name = config["scripts"]["RECO_SCRIPT_NAME"]
    
    # create specified output directory if it doesn't exist
    if(not os.path.exists(csvdir)):
        os.makedirs(csvdir)
    ensure_output_dirs(outdir) # create output directory and its needed subdirectories
    
    search_space = [RangeParameterConfig(name=i,
                                         bounds=(float(detconfig["parameters"][i]["lower"]), float(detconfig["parameters"][i]["upper"])), 
                                         parameter_type="float")
                    for i in detconfig["parameters"]
                    ]
    
    names = [metric_name
             ]

    metrics = []
    for name in names:
        metrics.append(
            SlurmJobMetric(
                name=name,
                output_dir=outdir
            )
        )
            
    client = Client()
    client.configure_experiment(
        parameters=search_space,
        # The following arguments are only necessary when saving to the DB
        name="outname",
        description="RICH alignment"
    )
    client.configure_optimization(objective=f"-{names[0]}")

    # load data from old trials
    first_trial_number = 0
    load_previous_trials = config["optimization"]["load_previous_trials"]
    if load_previous_trials:
        previous_csv = config["optimization"]["previous_csv"]
        previous_results_dir = config["optimization"]["previous_results_dir"]

        prev_df = pd.read_csv(previous_csv)
        first_trial_number = len(prev_df)
        for i in range(len(prev_df)):
            trial_status = prev_df["trial_status"][i]
            trial_par = {}
            for par in detconfig["parameters"]:
                trial_par[par] = prev_df[par][i]
            trial_results = {}
            trial_index = client.attach_trial(parameters=trial_par)

            if trial_status == "FAILED":
                client.mark_trial_failed(trial_index)            
            else:
                results_txt = np.loadtxt(previous_results_dir+f"/rich-align-mobo-out_{i}.txt")
                trial_results = {names[0]:(results_txt[0], results_txt[1])}
                client.complete_trial(
                    trial_index=trial_index, raw_data=trial_results
                )

    client.configure_runner(SlurmJobRunner(metrics=names,
                                           scriptname=job_script_name,
                                           config=args.config,
                                           output_dir=outdir,
                                           first_trial_number=first_trial_number                                           
                                           ))
    client.configure_metrics(metrics=metrics)
    
    # now run fixed N points
    BATCH_SIZE_SOBOL = config["optimization"]["n_batch_sobol"]
    BATCH_SIZE_MOBO = config["optimization"]["n_batch_mobo"]
    N_SOBOL = config["optimization"]["n_sobol"]
    N_MOBO = config["optimization"]["n_mobo"]
    N_TOTAL = N_SOBOL + N_MOBO
    print("Scheduling ", N_TOTAL, " trials")

    if not load_previous_trials:
        generation_strategy = construct_generation_strategy(N_SOBOL, N_MOBO, BATCH_SIZE_SOBOL, BATCH_SIZE_MOBO)
    else:
        # assuming that if we are re-starting, sobol trials are already done
        previous_state_file = config["previous_turbo_state"]
        with open(previous_state_file, "r") as f:
            data = json.load(f)
            previous_state = TurboState(**data)
        generation_strategy = construct_turbo_generation_strategy(N_MOBO, BATCH_SIZE_MOBO, previous_state)

    client.set_generation_strategy(
        generation_strategy=generation_strategy
    )
    if N_SOBOL > 0:
        for i in range(int(N_SOBOL/BATCH_SIZE_SOBOL)):
            client.run_trials(max_trials=BATCH_SIZE_SOBOL,
                              parallelism=BATCH_SIZE_SOBOL,
                              tolerated_trial_failure_rate=0.25,
                              initial_seconds_between_polls=10
                              )
            print(f"Done batch {i}")
    for i in range(int(N_MOBO/BATCH_SIZE_MOBO)):
        # TODO: when restarting, need to pass something to the runner so that it knows what trial number it is starting at...
        client.run_trials(max_trials=BATCH_SIZE_MOBO,
                          parallelism=BATCH_SIZE_MOBO,
                          tolerated_trial_failure_rate=0.25,
                          initial_seconds_between_polls=10
                          )
        exp_df = client.summarize()
        exp_df.to_csv(csvdir+"/"+outname+".csv")

        current_turbo_state = generation_strategy.nodes_dict['TuRBONode'].state
        with open(csvdir+"/"+outname+"_turbo_state.json", "w") as f:
            json.dump(asdict(current_turbo_state), f)
        
        if generation_strategy.nodes_dict['TuRBONode'].state.restart_triggered: #if converged, end
            break
    # save trial results to csv
    exp_df = client.summarize()
    exp_df.to_csv(csvdir+"/"+outname+".csv")
    # save trust regions
    trust_regions = pd.DataFrame(generation_strategy.nodes_dict['TuRBONode'].state.trust_regions)
    trust_regions.to_csv(csvdir+"/"+outname+"_trustregions.csv")

    # save turbo state when trials completed
    final_turbo_state = generation_strategy.nodes_dict['TuRBONode'].state
    with open(csvdir+"/"+outname+"_turbo_state.json", "w") as f:
        json.dump(asdict(final_turbo_state), f)
    
    # save old results files
    results_dir = str(logdir+"/results/")
    copy_dir = str(logdir+f"/results_{outname}/")
    os.makedirs(logdir+f"/results_{outname}/",exist_ok=True)
    for filename in os.listdir(results_dir):
        src_path = os.path.join(results_dir, filename)
        dst_path = os.path.join(copy_dir, filename)
        if os.path.isfile(src_path):  # skip subdirectories
            shutil.copy2(src_path, dst_path)  # copy2 keeps metadata
            
