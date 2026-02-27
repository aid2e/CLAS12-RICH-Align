#!/hpc/group/vossenlab/software/miniconda3/envs/mobo-env-0.3.6//bin/python3
import sys
import os
import sqlalchemy

if __name__ == "__main__":
    import ccdb
    ccdb.init_ccdb_console()
