import json
import os
import sys
from pathlib import Path

def ensure_output_dirs(output_dir: str):
    """
    Ensure OUTPUT_DIR and all required subdirectories exist.
    Equivalent to `mkdir -p` in bash.
    """
    output_dir = Path(output_dir)

    dirs = [
        output_dir,
        output_dir / "rich/log/hipo_files",
        output_dir / "rich/log/root_files",
        output_dir / "log/results",
        output_dir / "log/job_output",
        output_dir / "ccdb_copies",
        output_dir / "rich/tables",
        output_dir / "rich/yaml",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def ReadJsonFile(jsonFile):
    if(os.path.isfile(jsonFile) == False):
        print ("ERROR: the json file you specified does not exist")
        sys.exit(1)
    with open(jsonFile) as f:
        data = json.loads(f.read())
    return data

def GetDesignParamNames(dataDict, rangeDict):
    designParams = {}
    for key, value in dataDict.items():
        for i in range(1, value[0] + 1):
            key1 = key.replace("_fill_", f"{i}")
            if(rangeDict.get(key1)):
                designParams[key1] = rangeDict[key1]
            else:
                designParams[key1] = rangeDict[key]
    return designParams
