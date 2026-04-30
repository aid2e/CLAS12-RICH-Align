# CLAS12-RICH-Align
Repository for applying Bayesian optimization to the alignment of the CLAS12 RICH.

## Setup
The C++ scripts in ```Clas12RichUtils/``` require the HIPO and ROOT libraries. These should be straightforward to build with ```make``` on ifarm if you have loaded the CLAS12 environment. They can also be built within the ```analysis``` singularity container from [container-forge](https://code.jlab.org/hallb/clas12/container-forge). These scripts are used for event selection and in analysis.

To run the optimization itself via the script ```turbo_slurm_ax_1.0.py```, a python environment with the packages
* [Ax](https://ax.dev) version 1.0
* uncertainties,
* uproot

## Dataset for alignment
Currently, the hipo bank ```RICH::Ring```, which includes photon-by-photon reconstructed Cherenkov angle information, is not kept by default in CLAS12 DSTs. To use this repository and alignment approach, it is then assumed that you have already re-cooked some amount of data and kept this bank. 

The script ```Clas12RichUtils/RICH-skim-onetop``` is used to select events with the desired photon reflection topologies for alignment. This script takes a file with a list of hipo files as an argument, as well as a config file defining the topology to skim for. In the curent workflow, the topologies are selected one-by-one in individual slurm jobs prior to starting the full optimization procedure.

Following the selection of each topology, two merged hipo files must be created (using ```hipo-utils --merge```):
* One containing the two skims produced for track-cluster matching (for global alignment),
* One containing all selected photon topologies (for optical parameter alignment).

The notebook ```notebooks/generateTopologySelectionConfigs.ipynb``` can be used to generate the needed topology config files to pass to ```RICH-skim-onetop```.  

## Output and alignment configuration
Two configuration files are used to define the alignment parameter search space and general optimization hyperparameters/setup. The comments at the top of ```optimize.config``` provide some further guidance for setup. 
* ```optimize.config```: steering information (initial alignment parameters file, target HIPO file, output directories, slurm configuration, optimization hyperparameters)
* ```parameters.config```: definition of alignment parameter search space (```parameters_global.config```: global alignment only, ```parameters_planarALL_sphALL.config```: all optical component parameters)

If the alignment will be run on ifarm, with the CLAS12 software pre-installed, the reconstruction shell script used should be ```runReconstructionConfig.sh```. If the reconstruction and analysis will be run in a container, the shell script ```runContainerReconstructionConfig.sh``` is used.

## Running the alignment
