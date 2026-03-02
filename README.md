# CLAS12-RICH-Align
Repository for applying Bayesian optimization to the alignment of the CLAS12 RICH.

## Setup
The C++ scripts in ```Clas12RichUtils/``` require the HIPO and ROOT libraries. These should be straightforward to build with ```make``` on ifarm if you have loaded the CLAS12 environment. They can also be built within the ```analysis``` singularity container from [container-forge](https://code.jlab.org/hallb/clas12/container-forge). These scripts are used for event selection and in analysis

To run the optimization itself via the script ```turbo_slurm_ax_1.0.py```, a python environment with the packages
* [Ax](https://ax.dev) version 1.0
* uncertainties,
* uproot

## Dataset for alignment
Currently, the hipo bank ```RICH::Ring```, which includes photon-by-photon reconstructed Cherenkov angle information, is not kept by default in CLAS12 DSTs. To use this repository and alignment approach, it is then assumed that you have already re-cooked some amount of data and kept this bank. 

The script ```Clas12RichUtils/RICH-skim-onetop``` is used to select events with the desired photon reflection topologies for alignment. This script takes a file with a list of hipo files as an argument, as well as a config file defining the topology to skim for. In the curent workflow, the topologies are selected one-by-one, requiring that you run this over the hipo files for each topology. 

The notebook ```notebooks/generateTopologySelectionConfigs.ipynb``` can be used to generate the needed topology config files to pass to ```RICH-skim-onetop```.  

## Alignment configuration
