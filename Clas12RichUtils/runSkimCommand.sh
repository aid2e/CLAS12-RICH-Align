#!/bin/bash

# helper for running hipo skim commands inside a singularity container
CMD_ESCAPED=$(printf "%q " "$@")

cat << EOF | $AIDE_HOME/clas12_shell.sh
export PATH=/opt/apps/rhel8/root-6.24/bin/:/hpc/group/vossenlab/software/miniconda3/envs/mobo-env/bin:/opt/coatjava/bin/:$PATH
export LD_LIBRARY_PATH=/opt/apps/rhel8/root-6.24/lib:/usr/local/lib/:$LD_LIBRARY_PATH

echo "CMD => $CMD_ESCAPED"
bash -lc "$CMD_ESCAPED"
EOF


