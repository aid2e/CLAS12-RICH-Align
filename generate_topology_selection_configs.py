#!/usr/bin/env python3
"""Generate RICH topology skim JSON configs and a commands file.

This script writes one JSON configuration file per skim topology and a text file
containing the commands that can be submitted as individual SLURM jobs.

Example:
    python generate_topology_selection_configs.py \
        --input-file /path/to/inputs_19706_19765_combined.txt \
        --run-string RGK_19706_19765 \
        --datadir /cwork/cmp115/AIDE/CLAS12-RICH-Align/dataset

By default, output files are written to:
    $AIDE_HOME/skim_files
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


# topologyType is the topology to skim for.
# 0: direct photons,
# 1: one planar refl. (selected by planarMirror)
# 2: one sph + one planar (selected by planarMirror and sphericalMirror)
# 3: one sph + two planar reflections (selected by planarMirror{1,2} and sphericalMirror)
# 4: two planar reflections (selected by planarMirror{1,2})
# 5: select tracks with a matching cluster for global alignment

BASE_CONFIG: dict[str, Any] = {
    "applyDISCut": True,        # good electron + hadron
    "applyRichOneCut": True,    # one track in the RICH
    "topologyType": 2,          # overwritten for each generated config, 0: direct, 1: planar, 2: 1 sph + 1 planar, 3:
    "aerolayer": 203,
    "planarMirror": 12,
    "planarMirror1": 0,
    "planarMirror2": 0,
    "sphericalMirror": 25,
    "minPhotons": 2,
    "maxev": 50000,
    "validPIDs": [-211],
    "maxPerTile": 1000,
    "sector": 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate topology-selection skim configs and a commands file."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to the text file containing the list of input HIPO files.",
    )
    parser.add_argument(
        "--run-string",
        required=True,
        help="String used in output skim filenames, e.g. RGK_19706_19765_combined.",
    )
    parser.add_argument(
        "--datadir",
        required=True,
        help="Directory where skim output HIPO files should be written.",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Directory for generated JSON files and commands file. Default: $AIDE_HOME/skim_files.",
    )
    parser.add_argument(
        "--commands-file",
        default=None,
        help="Name or path of commands file. Default: <outdir>/skim_topology_commands.slurm.",
    )
    parser.add_argument("--maxev", type=int, default=20000)
    parser.add_argument("--max-pref", type=int, default=20)
    parser.add_argument("--max-per-tile", type=int, default=1000)
    parser.add_argument("--sector", type=int, default=4)
    parser.add_argument(
        "--aide-home",
        default=os.environ.get("AIDE_HOME"),
        help="AIDE installation directory. Default: environment variable AIDE_HOME.",
    )
    return parser.parse_args()


def make_config(
    *,
    topo: int,
    layer: int,
    planar: int,
    spherical: int,
    photons: int,
    maxev: int,
    pids: list[int],
    planar1: int,
    planar2: int,
    max_per_tile: int,
    sector: int,
    min_p: float,
) -> dict[str, Any]:
    config = BASE_CONFIG.copy()
    config.update(
        {
            "topologyType": topo,
            "aerolayer": layer,
            "planarMirror": planar,
            "planarMirror1": planar1,
            "planarMirror2": planar2,
            "sphericalMirror": spherical,
            "minPhotons": photons,
            "maxev": maxev,
            "validPIDs": pids,
            "maxPerTile": max_per_tile,
            "sector": sector,
            "minP": min_p,
        }
    )
    return config


def write_config(path: Path, config: dict[str, Any]) -> None:
    with path.open("w") as f:
        json.dump(config, f, indent=4)
        f.write("\n")


def add_job(
    *,
    commands: list[str],
    outdir: Path,
    aide_home_for_job: str,
    datadir: Path,
    input_file: Path,
    run_string: str,
    json_name: str,
    output_name: str,
) -> None:
    """Append one skim command to the command list.

    The commands intentionally use ${AIDE_HOME} by default, so the generated
    command file remains portable as long as AIDE_HOME is set inside the SLURM job.
    """
    config_path = outdir / json_name
    output_path = datadir / output_name
    command = (
        f"{aide_home_for_job}/Clas12RichUtils/runSkimCommand.sh "
        f"{aide_home_for_job}/Clas12RichUtils/RICH-skim-onetop "
        f"{output_path} @{input_file} --config {config_path}"
    )
    commands.append(command)


def main() -> None:
    args = parse_args()

    if args.aide_home is None:
        raise SystemExit("Error: set AIDE_HOME or pass --aide-home.")

    # create needed directories
    aide_home = Path(args.aide_home).expanduser().resolve()
    outdir = Path(args.outdir).expanduser() if args.outdir else aide_home / "skim_files"
    outdir.mkdir(parents=True, exist_ok=True)

    input_file = Path(args.input_file).expanduser().resolve()
    datadir = Path(args.datadir).expanduser().resolve()
    datadir.mkdir(parents=True, exist_ok=True)

    skim_clusters_dir = datadir / "skim_clusters"
    skim_cherenkov_dir = datadir / "skim_cherenkov"
    
    skim_clusters_dir.mkdir(parents=True, exist_ok=True)
    skim_cherenkov_dir.mkdir(parents=True, exist_ok=True)


    commands_file = Path(args.commands_file).expanduser() if args.commands_file else outdir / "skim_topology_commands.slurm"
    if not commands_file.is_absolute():
        commands_file = outdir / commands_file

    # Use the already set AIDE_HOME environment variable in the generated SLURM commands
    aide_home_for_job = "${AIDE_HOME}"

    min_p_by_layer = {201: 3.0, 202: 2.0, 203: 1.5}
    mirrors_row1 = [21, 25, 22]
    mirrors_row2 = [28, 29, 30, 23, 26, 27, 24]
    mirrors_planar = [11, 14, 15, 16, 17]

    commands: list[str] = []
    n_configs = 0

    for pid, pidname in zip([211, -211], ["PIP", "PIM"]):
        # Spherical + planar reflected topologies.
        for spherical in mirrors_row1 + mirrors_row2:
            for planar in [12, 13]:
                for layer in [202, 203]:
                    min_p = min_p_by_layer[layer]
                    json_name = (
                        f"skim_for_sector{args.sector}_{args.max_pref}k_l{layer}_"
                        f"s{spherical}_p{planar}_{pidname}_minp.json"
                    )
                    config = make_config(
                        topo=2,
                        layer=layer,
                        planar=planar,
                        spherical=spherical,
                        photons=2,
                        maxev=args.maxev,
                        pids=[pid],
                        planar1=0,
                        planar2=0,
                        max_per_tile=args.max_per_tile,
                        sector=args.sector,
                        min_p=min_p,
                    )
                    write_config(outdir / json_name, config)
                    n_configs += 1

                    output_name = (
                        f"skim_sector{args.sector}_{args.run_string}_{pidname}_"
                        f"{args.max_pref}k_l{layer}_s{spherical}_p{planar}_minp{min_p}.hipo"
                    )
                    add_job(
                        commands=commands,
                        outdir=outdir,
                        aide_home_for_job=aide_home_for_job,
                        datadir=skim_cherenkov_dir,
                        input_file=input_file,
                        run_string=args.run_string,
                        json_name=json_name,
                        output_name=output_name,
                    )

        # Direct photons.
        for layer in [201, 202]:
            min_p = min_p_by_layer[layer]
            json_name = f"skim_for_sector{args.sector}_{args.max_pref}k_l{layer}_direct_{pidname}_minp.json"
            config = make_config(
                topo=0,
                layer=layer,
                planar=-1,
                spherical=-1,
                photons=3,
                maxev=args.maxev,
                pids=[pid],
                planar1=0,
                planar2=0,
                max_per_tile=args.max_per_tile,
                sector=args.sector,
                min_p=min_p,
            )
            write_config(outdir / json_name, config)
            n_configs += 1

            output_name = (
                f"skim_sector{args.sector}_{args.run_string}_{pidname}_"
                f"{args.max_pref}k_l{layer}_direct_minp{min_p}.hipo"
            )
            add_job(
                commands=commands,
                outdir=outdir,
                aide_home_for_job=aide_home_for_job,
                datadir=skim_cherenkov_dir,
                input_file=input_file,
                run_string=args.run_string,
                json_name=json_name,
                output_name=output_name,
            )

        # Planar reflected topologies only.
        for planar in mirrors_planar:
            for layer in [201, 202, 203]:
                min_p = min_p_by_layer[layer]
                json_name = (
                    f"skim_for_sector{args.sector}_{args.max_pref}k_l{layer}_"
                    f"s0_p{planar}_{pidname}_minp.json"
                )
                config = make_config(
                    topo=1,
                    layer=layer,
                    planar=planar,
                    spherical=0,
                    photons=2,
                    maxev=args.maxev,
                    pids=[pid],
                    planar1=0,
                    planar2=0,
                    max_per_tile=args.max_per_tile,
                    sector=args.sector,
                    min_p=min_p,
                )
                write_config(outdir / json_name, config)
                n_configs += 1

                output_name = (
                    f"skim_sector{args.sector}_{args.run_string}_{pidname}_"
                    f"{args.max_pref}k_l{layer}_s0_p{planar}_minp{min_p}.hipo"
                )
                add_job(
                    commands=commands,
                    outdir=outdir,
                    aide_home_for_job=aide_home_for_job,
                    datadir=skim_cherenkov_dir,
                    input_file=input_file,
                    run_string=args.run_string,
                    json_name=json_name,
                    output_name=output_name,
                )
        # events with PMT clusters for global alignment
        for layer in [201, 202]:            
            json_name = (
                    f"skim_for_sector{args.sector}_{args.max_pref}k_clusters_l{layer}_"
                    f"{pidname}.json"
                )
            config = make_config(
                topo=5,
                layer=layer,
                planar=0,
                spherical=0,
                photons=0,
                maxev=args.maxev,
                pids=[pid],
                planar1=0,
                planar2=0,
                max_per_tile=args.max_per_tile,
                sector=args.sector,
                min_p=0,
            )
            write_config(outdir / json_name, config)
            n_configs += 1
            
            output_name = (
                f"skim_sector{args.sector}_{args.run_string}_{pidname}_"
                f"{args.max_pref}k_l{layer}_clusters.hipo"
            )
            add_job(
                commands=commands,
                outdir=outdir,
                aide_home_for_job=aide_home_for_job,
                datadir=skim_clusters_dir,
                input_file=input_file,
                run_string=args.run_string,
                json_name=json_name,
                output_name=output_name,
            )
        
    with commands_file.open("w") as f:
        f.write("\n".join(commands))
        f.write("\n")

    print(f"Wrote {n_configs} JSON configs to {outdir}")
    print(f"Wrote {len(commands)} commands to {commands_file}")


if __name__ == "__main__":
    main()
