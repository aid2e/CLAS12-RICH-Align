#!/bin/bash

if [ "$#" != 1 ]; then
    echo "Usage: $0 [job id] "
    exit 1
fi


# REMEMBER TO BIND AIDE_HOME...
cat << EOF | $AIDE_HOME/clas12_shell.sh
export PATH=/opt/apps/rhel8/root-6.24/bin/:/hpc/group/vossenlab/software/miniconda3/envs/mobo-env/bin:/opt/coatjava/bin/:$PATH
export LD_LIBRARY_PATH=/opt/apps/rhel8/root-6.24/lib:/usr/local/lib/:$LD_LIBRARY_PATH

# set up ccdb
cp ${AIDE_HOME}/ccdb_copy_2025-03-09.sqlite ${OUTPUT_DIR}/ccdb_copies/ccdb_copy_2025-03-09_$1.sqlite
export CCDB_CONNECTION=sqlite:///${OUTPUT_DIR}/ccdb_copies/ccdb_copy_2025-03-09_$1.sqlite
export CCDB_USER=cpecar
if [ -f "${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1.hipo" ]; then
    rm "${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1.hipo"
fi
if [ -f "${OUTPUT_DIR}/rich/log/hipo_files/output_mchi2_$1.hipo" ]; then
    rm "${OUTPUT_DIR}/rich/log/hipo_files/output_mchi2_$1.hipo"
fi

cd ${AIDE_HOME}

${AIDE_HOME}/ccdb_test_script.py add /geometry/rich/module1/alignment -v rga_fall2018 ${AIDE_HOME}/rich/tables/rich_m1_alignment_$1.dat
${AIDE_HOME}/ccdb_test_script.py add /calibration/rich/module1/status_aerogel -v rga_fall2018 ${AIDE_HOME}/aerogel_status_allok_module1.txt
${AIDE_HOME}/ccdb_test_script.py add /calibration/rich/module1/status_mirror -v rga_fall2018 ${AIDE_HOME}/mirror_status_allok_module1.txt
${AIDE_HOME}/ccdb_test_script.py add /geometry/rich/module1/aerogel -v rga_fall2018 ${AIDE_HOME}/aerogel_module1_passports.txt

recon-util -y ${AIDE_HOME}/rich/yaml/rich.yaml -i ${AIDE_HOME}/rich_skim_ele_alltopo.hipo -o ${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1.hipo
recon-util -y ${AIDE_HOME}/rich/yaml/rich.yaml -i ${AIDE_HOME}/rich_skim_ele_mchi2.hipo -o ${OUTPUT_DIR}/rich/log/hipo_files/output_mchi2_$1.hipo

${AIDE_HOME}/Clas12RichUtils/RICH-direct-and-planar ${OUTPUT_DIR}/rich/log/root_files/output_spherical_$1.root ${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1.hipo
${AIDE_HOME}/Clas12RichUtils/RICH-track-matching-tree ${OUTPUT_DIR}/rich/log/root_files/output_mchi2_$1 ${OUTPUT_DIR}/rich/log/hipo_files/output_mchi2_$1.hipo

EOF
python ${AIDE_HOME}/Clas12RichUtils/runObjectiveCalc_sphericalAndDirect_ele_resid_withmchi2.py $1
