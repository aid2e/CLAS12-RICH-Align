# CLAS12-RICH-Align
Application of Bayesian optimization to the alignment of the CLAS12 RICH. The code contained here provides tools for selecting an alignment dataset and using Trust Region Bayesian Optimization (TuRBO, arXiv:1910.01739) to determine global and optical component alignment parameters. This implementation requires a SLURM computing environment and the CLAS12 software environment (pre-installed or in a container). 

## Repository layout
```text
CLAS12-RICH-Align/
├── ProjectUtils/                              # shared Python classes and slurm monitoring utilities
├── Clas12RichUtils/                           # C++ and bash scripts using CLAS12 software (C++ scripts must be built)
├── generateTopologySelectionConfigs.py        # script generating config files for event selection
├── turbo_slurm_ax_1.0.py                      # full alignment procedure script
├── parameters_*.config                        # alignment parameter search space definition
└── optimize.config                            # user-edited settings for the alignment procedure
```
## Requirements and build
The C++ scripts in ```Clas12RichUtils/``` require the HIPO and ROOT libraries. These should be straightforward to build with ```make``` on ifarm if you have loaded the CLAS12 environment. They can also be built within the ```analysis``` singularity container from [container-forge](https://code.jlab.org/hallb/clas12/container-forge).

A python environment with the following packages is also required: 
* [Ax](https://ax.dev) version 1.0
* uncertainties,
* uproot

## Selecting the dataset
Currently, the hipo bank ```RICH::Ring```, which includes photon-by-photon reconstructed Cherenkov angle information, is not kept by default in CLAS12 DSTs. To use this repository and alignment approach, it is then assumed that you have already re-cooked some amount of data and kept this bank. 

The script ```Clas12RichUtils/RICH-skim-onetop``` is used to select events with the desired photon reflection topologies for alignment. This script takes a text file containing a list of hipo files as an argument, as well as a config file defining the topology to skim for. In the curent workflow, the topologies are selected one-by-one in individual slurm jobs prior to starting the full optimization procedure.

Following the selection of each topology, two merged hipo files must be created (using ```hipo-utils --merge```):
* One containing the two skims produced for track-cluster matching (for global alignment),
* One containing all selected photon topologies (for optical parameter alignment).

The notebook ```notebooks/generateTopologySelectionConfigs.ipynb``` can be used to generate the needed topology config files to pass to ```RICH-skim-onetop```.

## Configuration
Two configuration files are used to define the alignment parameter search space and general optimization hyperparameters/setup. The comments at the top of ```optimize.config``` provide some further guidance for setup. 
* ```optimize.config```: steering information (initial alignment parameters file, target HIPO file, output directories, slurm configuration, optimization hyperparameters). This file must be edited to reflect your environment and the desired number of trials. 
* ```parameters.config```: definition of alignment parameter search space (```parameters_global.config```: global alignment only, ```parameters_planarALL_sphALL.config```: all optical component parameters). These files should not need to be edited for use unless changes to the search space are needed, e.g. expanding/tightening parameter bounds. 

## Workflow
### 1. Event selection
Event selection is carried out with the C++ script defined in ```Clas12RichUtils/RICH-skim-onetop.cpp```. To generate the .json files passed to this script and a corresponding list of commands passed to slurm, run

``` source setup.sh```

``` python generate_topology_selection_configs.py --input-file [.txt list of hipo files to skim] --run-string [run number/chosen suffix] --datadir [directory to store resulting hipo files]```,

which will then save the skim json files in the directory ```$AIDE_HOME/skim_files```. The file ```$AIDE_HOME/skim_files/skim_topology_commands.slurm``` will contain a list of commands executing ```RICH-skim-onetop``` for each json file, which can be run in individual slurm jobs via

```
#SBATCH --array=1-118
cmd=$(sed -n "${SLURM_ARRAY_TASK_ID}p" skim_files/skim_topology_commands.slurm)
srun bash -lc "$cmd"
```
TODO: add some automatic merger script here...

### 2. Edit configuration file
The following are descriptions of fields to edit for your own slurm and alignment configuration.

#### Paths (output path information)
* ```"LOG_DIR"```: location for slurm out/error files,
* ```"CSV_DIR"```: location for final CSV storing all trial information (small, one per alignment run),
* ```"OUTPUT_DIR"```: where per-trial CCDB tables, CCDB copies, HIPO and ROOT files will be stored (recommend setting this to a temporary storage location e.g. /volatile/),
* ```"OUTPUT_NAME```: base name used for outputs for this alignment run, e.g. "rgk_spring2024_runone"

#### Scripts (must be edited for global vs optical component alignment)
* ```"RECO_SCRIPT_NAME"```: "runContainerReconstructionConfig.sh" if reconstruction done in container, runReconstructionConfig.sh if not in container.
* ```"ANA_SCRIPT_NAME"```: "runObjectiveCalcMchi2.py" for global alignment, "runObjectiveCalcPionMatchingSeparated.py" for all optical component alignment.

#### Calibration (information on dataset and RICH module/sector)
* ```"SECTOR"```: RICH sector (1 or 4, int),
* ```"MODULE"```: RICH module number (1 or 2, int),
* ```"HIPO_FILE"```: merged hipo file containing dataset to be used for this alignment step

#### Reco (information for coatjava and CCDB)
* ```"VARIATION"```: ccdb variation (corresponds with dataset e.g. rgk_spring2024).
* ```"CCDB_USERNAME"```: username for adding to ccdb copy.
* ```"CCDB_FILE"```: starting CCDB sqlite file (should be pre-filled with RICH time calibration and defaults for all other RICH tables).
* ```"YAML_FILE"```: yaml file passed to ```recon-util``` for reconstruction.
* ```"INIT_ALIGN_FILE"```: initial alignment parameters table used for this step. When runnning optical component alignment, this should have global alignment parameters already filled.

#### Optimization (information for the optimizer)
* ```"METRIC_NAME"```: only used internally and in final csv.
* ```"load_previous_trials"```: 0 if starting from scratch, 1 if resuming an alignment run. See below for instructions on resuming alignment.
* ```"n_sobol"```: number of initial space-filling trials generated with Sobol sequence.
* ```"n_mobo"```: total number of TuRBO trials to carry out.
* ```"n_batch_sobol"```: batch size for initial Sobol trials (evaluated in parallel)
* ```"n_batch_mobo"```: batch size for TuRBO trials (evaluated in parallel)

#### Jobs (information for slurm jobs)
* ```"ACCOUNT"```: slurm account,
* ```"PARTITION"```: slurm partition,
* ```"TIME_LIMIT"```: job time limit (on DCC, recommended "04:00:00" for optical component alignment, "00:30:00" for global alignment), 
* ```"MEMORY"```: memory request per slurm job, recommended "6G"

### 3. Run alignment
Once configured, run optimization in a long-running slurm job via:

```source setup.sh```

```python turbo_slurm_ax_1.0.py -c optimization.config -d parameters.config```.

The CSV file containing information on each trial will then be stored at "CSV_DIR". TODO: Automatically identify the best trial and store it somewhere, and produce 1-2 validation plots. 

