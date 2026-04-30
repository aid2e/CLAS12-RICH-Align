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
