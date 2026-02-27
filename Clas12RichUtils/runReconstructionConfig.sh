#!/bin/bash

if [ "$#" != 2 ]; then
    echo "Usage: $0 [job id] [config file]"
    exit 1
fi

# Assuming that $1 is the trial number,and
# $2 points to the json file used
# to define arguments for the alignment
CONFIG=$2
INPUT_HIPO=$(jq -er '.calibration.HIPO_FILE' "$CONFIG")
SECTOR=$(jq -er '.calibration.SECTOR' "$CONFIG")
MODULE=$(jq -er '.calibration.MODULE' "$CONFIG")
YAML_FILE=$(jq -er '.reco.YAML_FILE' "$CONFIG")
CCDB_FILE=$(jq -er '.reco.CCDB_FILE' "$CONFIG") # initial ccdb file
VARIATION=$(jq -er '.reco.VARIATION' "$CONFIG")
CCDB_USERNAME=$(jq -er '.reco.CCDB_USERNAME' "$CONFIG")
OUTPUT_DIR=$(jq -er '.paths.OUTPUT_DIR' "$CONFIG")
ANA_SCRIPT_NAME=$(jq -er '.scripts.ANA_SCRIPT_NAME' "$CONFIG")

# set up ccdb
cp ${CCDB_FILE} ${OUTPUT_DIR}/ccdb_copies/ccdb_copy_$1.sqlite
export CCDB_CONNECTION=sqlite:///${OUTPUT_DIR}/ccdb_copies/ccdb_copy_$1.sqlite
export CCDB_USER=$CCDB_USERNAME
if [ -f "${OUTPUT_DIR}/rich/log/hipo_files/output_$1.hipo" ]; then
    rm "${OUTPUT_DIR}/rich/log/hipo_files/output_$1.hipo"
fi

# Assumes that ccdb was already set up with all correct tables except alignment for this trial (e.g. statuses, aerogel table, ...)
ccdb add /geometry/rich/module${MODULE}/alignment -v ${VARIATION} ${OUTPUT_DIR}/rich/tables/rich_m1_alignment_$1.dat

recon-util -y ${YAML_FILE} -i ${INPUT_HIPO} -o ${OUTPUT_DIR}/rich/log/hipo_files/output_$1.hipo
${AIDE_HOME}/Clas12RichUtils/RICH-hipo-to-tree ${OUTPUT_DIR}/rich/log/root_files/output_$1.root ${OUTPUT_DIR}/rich/log/hipo_files/output_$1.hipo

python "${AIDE_HOME}/Clas12RichUtils/${ANA_SCRIPT_NAME}" $1 $SECTOR $OUTPUT_DIR

# clean up large files (but keep root file for analysis)
rm ${OUTPUT_DIR}/rich/log/hipo_files/output_$1.hipo
rm ${OUTPUT_DIR}/ccdb_copies/ccdb_copy_$1.sqlite
