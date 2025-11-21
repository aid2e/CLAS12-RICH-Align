#!/bin/bash

if [ "$#" != 1 ]; then
    echo "Usage: $0 [job id] "
    exit 1
fi


# REMEMBER TO BIND AIDE_HOME...
cat << EOF | $AIDE_HOME/clas12_shell.sh

#TODO: Generalize this (with new container from Chris might not need this path workaround)

export PATH=/opt/apps/rhel8/root-6.24/bin/:/hpc/group/vossenlab/software/miniconda3/envs/mobo-env/bin:/opt/coatjava/bin/:$PATH
export LD_LIBRARY_PATH=/opt/apps/rhel8/root-6.24/lib:/usr/local/lib/:$LD_LIBRARY_PATH

# set up ccdb
cp ${AIDE_HOME}/ccdb_copy_2025-03-09.sqlite ${OUTPUT_DIR}/ccdb_copies/ccdb_copy_2025-03-09_$1.sqlite
export CCDB_CONNECTION=sqlite:///${OUTPUT_DIR}/ccdb_copies/ccdb_copy_2025-03-09_$1.sqlite
export CCDB_USER=cpecar
if [ -f "${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1_inb.hipo" ]; then
    rm "${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1_inb.hipo"
fi

if [ -f "${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1_outb.hipo" ]; then
    rm "${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1_outb.hipo"
fi

cd ${AIDE_HOME}
${AIDE_HOME}/ccdb_test_script.py add /geometry/rich/module1/alignment -v rga_fall2018 ${AIDE_HOME}/rich/tables/rich_m1_alignment_$1.dat
${AIDE_HOME}/ccdb_test_script.py add /calibration/rich/module1/status_aerogel -v rga_fall2018 ${AIDE_HOME}/aerogel_status_allok_module1.txt
${AIDE_HOME}/ccdb_test_script.py add /calibration/rich/module1/status_mirror -v rga_fall2018 ${AIDE_HOME}/mirror_status_allok_module1.txt
${AIDE_HOME}/ccdb_test_script.py add /geometry/rich/module1/aerogel -v rga_fall2018 ${AIDE_HOME}/aerogel_module1_passports.txt
EOF

srun --overlap -n1 -c 1 \
     --export=ALL \
     "$AIDE_HOME/Clas12RichUtils/run_reco_torus.sh" inb "$1" & pid_inb=$!

srun --overlap -n1 -c 1 \
     --export=ALL \
     "$AIDE_HOME/Clas12RichUtils/run_reco_torus.sh" outb "$1" & pid_outb=$!

wait $pid_inb; status_inb=$?
wait $pid_outb; status_outb=$?
if [[ $status_inb -ne 0 || $status_outb -ne 0 ]]; then
  echo "recon-util failed: inb=$status_inb, outb=$status_outb"
  echo "logs: ${OUTPUT_DIR}/rich/log/recon/"
  exit 1
fi

cat << EOF | $AIDE_HOME/clas12_shell.sh
export PATH=/opt/apps/rhel8/root-6.24/bin/:/hpc/group/vossenlab/software/miniconda3/envs/mobo-env/bin:/opt/coatjava/bin/:$PATH
export LD_LIBRARY_PATH=/opt/apps/rhel8/root-6.24/lib:/usr/local/lib/:$LD_LIBRARY_PATH

export CCDB_CONNECTION=sqlite:///${OUTPUT_DIR}/ccdb_copies/ccdb_copy_2025-03-09_$1.sqlite
export CCDB_USER=cpecar

${AIDE_HOME}/Clas12RichUtils/RICH-hipo-to-tree ${OUTPUT_DIR}/rich/log/root_files/output_spherical_$1_inb.root ${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1_inb.hipo
${AIDE_HOME}/Clas12RichUtils/RICH-hipo-to-tree ${OUTPUT_DIR}/rich/log/root_files/output_spherical_$1_outb.root ${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_$1_outb.hipo
EOF
python ${AIDE_HOME}/Clas12RichUtils/runObjectiveCalcEleMatchingBothTorus.py  $1
