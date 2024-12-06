import numpy as np
import os, sys
import uproot

def retrieveResults(job_id):
    # when results finished, retrieve analysis script outputs
    # and calculate objectives
    rootfile = uproot.open(str(os.environ["AIDE_HOME"])+"/rich/log/root_files/output_{}.root".format(job_id))
    tree = rootfile[rootfile.keys()[0]]
    mchi2 = tree["mchi2"].array(library='np')    
    return np.mean(mchi2[mchi2!=0])

jobid = sys.argv[1]

meanchi2 = np.array(retrieveResults(jobid))
np.savetxt(os.environ["AIDE_HOME"]+"/log/results/" + "rich-align-mobo-out_{}.txt".format(jobid),[meanchi2])
