#!/bin/bash

if [ "$#" != 1 ]; then
    echo "Usage: $0 [job id] "
    exit 1
fi

export CCDB_CONNECTION=sqlite:///${AIDE_HOME}/ccdb_copy.sqlite
if [ -f "${AIDE_HOME}/rich/log/hipo_files/output_$1.hipo" ]; then
    rm "${AIDE_HOME}/rich/log/hipo_files/output_$1.hipo"
fi
ccdb mkvar variation_$1
ccdb add /geometry/rich/module1/alignment -v variation_$1 ${AIDE_HOME}/rich/tables/rich_m1_alignment_$1.dat
recon-util -y ${AIDE_HOME}/rich/yaml/rich_$1.yaml -i ${AIDE_HOME}/rich_skim.hipo -o ${AIDE_HOME}/rich/log/hipo_files/output_$1.hipo
${AIDE_HOME}/Clas12RichUtils/RICH-track-matching-tree ${AIDE_HOME}/rich/log/root_files/output_$1 ${AIDE_HOME}/rich/log/hipo_files/output_$1.hipo
python ${AIDE_HOME}/Clas12RichUtils/runObjectiveCalc.py $1
