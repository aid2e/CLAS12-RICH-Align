#!/usr/bin/env bash

set -euo pipefail
MODE="$1"   # inb | outb
IDX="$2"

# Pick inputs/outputs
if [[ "$MODE" == "inb" ]]; then
  IN_HIPO="${AIDE_HOME}/skim_5232_ele_mergedLower_andMergedUpper_ANDupperPlanar.hipo"
  OUT_HIPO="${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_${IDX}_inb.hipo"
  LOG_RECON="${OUTPUT_DIR}/rich/log/recon/recon_inb_${IDX}.log"
elif [[ "$MODE" == "outb" ]]; then
  IN_HIPO="${AIDE_HOME}/skim_outb_mergedLowerAndUpper.hipo"
  OUT_HIPO="${OUTPUT_DIR}/rich/log/hipo_files/output_spherical_${IDX}_outb.hipo"
  LOG_RECON="${OUTPUT_DIR}/rich/log/recon/recon_outb_${IDX}.log"
else
  echo "Unknown MODE: $MODE" >&2; exit 2
fi

mkdir -p "${OUTPUT_DIR}/rich/log/recon" "${OUTPUT_DIR}/rich/log/hipo_files"

cat <<EOF | "$AIDE_HOME/clas12_shell.sh" 
export PATH=/opt/apps/rhel8/root-6.24/bin/:/hpc/group/vossenlab/software/miniconda3/envs/mobo-env/bin:/opt/coatjava/bin/:\$PATH
export LD_LIBRARY_PATH=/opt/apps/rhel8/root-6.24/lib:/usr/local/lib/:\$LD_LIBRARY_PATH

export CCDB_CONNECTION=sqlite:///${OUTPUT_DIR}/ccdb_copies/ccdb_copy_2025-03-09_${IDX}.sqlite
export CCDB_USER=cpecar

cd "${AIDE_HOME}"
[[ -f "${OUT_HIPO}" ]] && rm -f "${OUT_HIPO}"
# obey threads if set
[[ -n "\${OMP_NUM_THREADS:-}" ]] && export OMP_NUM_THREADS
recon-util -y "${AIDE_HOME}/rich/yaml/rich.yaml" -i "${IN_HIPO}" -o "${OUT_HIPO}"
EOF
