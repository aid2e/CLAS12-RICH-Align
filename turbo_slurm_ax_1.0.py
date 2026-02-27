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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Optimization, dRICH")
    parser.add_argument(
        "-c",
        "--config",
        help="Optimization configuration file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-d",
        "--detparameters",
        help="Detector parameter configuration file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-j",
        "--json_file",
        help="The json file to load and continue optimization",
        type=str,
        required=False,
    )
    return parser.parse_args()


def ensure_dirs(csvdir: str, outdir: str) -> None:
    """Create output directories if needed."""
    if not os.path.exists(csvdir):
        os.makedirs(csvdir)
    ensure_output_dirs(outdir)  # create output directory and its needed subdirectories


def build_search_space(detconfig: dict) -> list[RangeParameterConfig]:
    """Construct Ax search space from detector-parameter config."""
    return [
        RangeParameterConfig(
            name=par,
            bounds=(
                float(detconfig["parameters"][par]["lower"]),
                float(detconfig["parameters"][par]["upper"]),
            ),
            parameter_type="float",
        )
        for par in detconfig["parameters"]
    ]


def build_metrics(metric_names: list[str], outdir: str) -> list[SlurmJobMetric]:
    """Create Ax metrics that read results from the Slurm output directory."""
    metrics: list[SlurmJobMetric] = []
    for name in metric_names:
        metrics.append(
            SlurmJobMetric(
                name=name,
                output_dir=outdir,
            )
        )
    return metrics


def configure_client(search_space: list[RangeParameterConfig], metric_name: str) -> Client:
    """Create and configure the Ax client."""
    client = Client()
    client.configure_experiment(
        parameters=search_space,
        # The following arguments are only necessary when saving to the DB
        name="outname",
        description="RICH alignment",
    )
    client.configure_optimization(objective=f"-{metric_name}")
    return client


def attach_previous_trials(
    client: Client,
    config: dict,
    detconfig: dict,
    metric_name: str,
) -> int:
    """Optionally load and attach trials from a previous CSV.

    Returns the first trial number (i.e., number of prior trials).
    """
    first_trial_number = 0
    load_previous_trials = config["optimization"]["load_previous_trials"]
    if not load_previous_trials:
        return first_trial_number

    previous_csv = config["optimization"]["previous_csv"]
    previous_results_dir = config["optimization"]["previous_results_dir"]

    prev_df = pd.read_csv(previous_csv)
    first_trial_number = len(prev_df)

    for i in range(len(prev_df)):
        trial_status = prev_df["trial_status"][i]

        trial_par = {}
        for par in detconfig["parameters"]:
            trial_par[par] = prev_df[par][i]

        trial_index = client.attach_trial(parameters=trial_par)

        if trial_status == "FAILED":
            client.mark_trial_failed(trial_index)
        else:
            results_txt = np.loadtxt(previous_results_dir + f"/rich-align-mobo-out_{i}.txt")
            trial_results = {metric_name: (results_txt[0], results_txt[1])}
            client.complete_trial(trial_index=trial_index, raw_data=trial_results)

    return first_trial_number


def build_generation_strategy(config: dict, load_previous_trials: bool) -> object:
    """Construct generation strategy (Sobol+MOBO or TuRBO restart)."""
    BATCH_SIZE_SOBOL = config["optimization"]["n_batch_sobol"]
    BATCH_SIZE_MOBO = config["optimization"]["n_batch_mobo"]
    N_SOBOL = config["optimization"]["n_sobol"]
    N_MOBO = config["optimization"]["n_mobo"]

    if not load_previous_trials:
        return construct_generation_strategy(N_SOBOL, N_MOBO, BATCH_SIZE_SOBOL, BATCH_SIZE_MOBO)

    # assuming that if we are re-starting, sobol trials are already done
    previous_state_file = config["previous_turbo_state"]
    with open(previous_state_file, "r") as f:
        data = json.load(f)
        previous_state = TurboState(**data)
    return construct_turbo_generation_strategy(N_MOBO, BATCH_SIZE_MOBO, previous_state)


def run_batches(
    client: Client,
    generation_strategy: object,
    csvdir: str,
    outname: str,
    load_previous_trials: bool,
    config: dict,
) -> None:
    """Run Sobol then MOBO batches, periodically saving the experiment summary and TuRBO state."""
    BATCH_SIZE_SOBOL = config["optimization"]["n_batch_sobol"]
    BATCH_SIZE_MOBO = config["optimization"]["n_batch_mobo"]
    N_SOBOL = config["optimization"]["n_sobol"]
    N_MOBO = config["optimization"]["n_mobo"]

    client.set_generation_strategy(generation_strategy=generation_strategy)

    # Sobol phase (only if not restarting)
    if N_SOBOL > 0:
        for i in range(int(N_SOBOL / BATCH_SIZE_SOBOL)):
            client.run_trials(
                max_trials=BATCH_SIZE_SOBOL,
                parallelism=BATCH_SIZE_SOBOL,
                tolerated_trial_failure_rate=0.25,
                initial_seconds_between_polls=10,
            )
            print(f"Done batch {i}")

    # MOBO / TuRBO phase
    for i in range(int(N_MOBO / BATCH_SIZE_MOBO)):
        # TODO: when restarting, need to pass something to the runner so that it knows what trial number it is starting at...
        client.run_trials(
            max_trials=BATCH_SIZE_MOBO,
            parallelism=BATCH_SIZE_MOBO,
            tolerated_trial_failure_rate=0.25,
            initial_seconds_between_polls=10,
        )

        exp_df = client.summarize()
        exp_df.to_csv(csvdir + "/" + outname + ".csv")

        current_turbo_state = generation_strategy.nodes_dict["TuRBONode"].state
        with open(csvdir + "/" + outname + "_turbo_state.json", "w") as f:
            json.dump(asdict(current_turbo_state), f)

        if generation_strategy.nodes_dict["TuRBONode"].state.restart_triggered:  # if converged, end
            break


def save_final_outputs(
    client: Client,
    generation_strategy: object,
    csvdir: str,
    outname: str,
) -> None:
    """Save final experiment summary, trust regions, and TuRBO state."""
    exp_df = client.summarize()
    exp_df.to_csv(csvdir + "/" + outname + ".csv")

    trust_regions = pd.DataFrame(generation_strategy.nodes_dict["TuRBONode"].state.trust_regions)
    trust_regions.to_csv(csvdir + "/" + outname + "_trustregions.csv")

    final_turbo_state = generation_strategy.nodes_dict["TuRBONode"].state
    with open(csvdir + "/" + outname + "_turbo_state.json", "w") as f:
        json.dump(asdict(final_turbo_state), f)


def copy_results(logdir: str, outname: str) -> None:
    """Copy results files into a run-specific subdirectory."""
    results_dir = str(logdir + "/results/")
    copy_dir = str(logdir + f"/results_{outname}/")
    os.makedirs(logdir + f"/results_{outname}/", exist_ok=True)

    for filename in os.listdir(results_dir):
        src_path = os.path.join(results_dir, filename)
        dst_path = os.path.join(copy_dir, filename)
        if os.path.isfile(src_path):  # skip subdirectories
            shutil.copy2(src_path, dst_path)  # copy2 keeps metadata


def main() -> None:
    args = parse_args()

    # Load optimization and detector parameter configs
    config = ReadJsonFile(args.config)  # optimization parameters
    detconfig = ReadJsonFile(args.detparameters)  # geometry parameters

    # Pull commonly used config values
    csvdir = config["paths"]["CSV_DIR"]
    outdir = config["paths"]["OUTPUT_DIR"]
    outname = config["paths"]["OUTPUT_NAME"]
    logdir = config["paths"]["LOG_DIR"]

    metric_name = config["optimization"]["METRIC_NAME"]
    job_script_name = config["scripts"]["RECO_SCRIPT_NAME"]

    # Directory setup
    ensure_dirs(csvdir, outdir)

    # Ax setup
    search_space = build_search_space(detconfig)
    metric_names = [metric_name]
    metrics = build_metrics(metric_names, outdir)

    client = configure_client(search_space, metric_name)

    # load data from old trials
    first_trial_number = attach_previous_trials(client, config, detconfig, metric_name)
    load_previous_trials = config["optimization"]["load_previous_trials"]

    # Runner + metrics configuration
    client.configure_runner(
        SlurmJobRunner(
            metrics=metric_names,
            scriptname=job_script_name,
            config=args.config,
            output_dir=outdir,
            first_trial_number=first_trial_number,
        )
    )
    client.configure_metrics(metrics=metrics)

    # now run fixed N points
    BATCH_SIZE_SOBOL = config["optimization"]["n_batch_sobol"]
    BATCH_SIZE_MOBO = config["optimization"]["n_batch_mobo"]
    N_SOBOL = config["optimization"]["n_sobol"]
    N_MOBO = config["optimization"]["n_mobo"]
    N_TOTAL = N_SOBOL + N_MOBO
    print("Scheduling ", N_TOTAL, " trials")

    generation_strategy = build_generation_strategy(config, load_previous_trials)

    run_batches(
        client=client,
        generation_strategy=generation_strategy,
        csvdir=csvdir,
        outname=outname,
        load_previous_trials=load_previous_trials,
        config=config,
    )

    save_final_outputs(client, generation_strategy, csvdir, outname)
    copy_results(logdir, outname)


if __name__ == "__main__":
    main()
