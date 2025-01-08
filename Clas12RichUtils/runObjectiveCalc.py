import numpy as np
import os, sys
import uproot

def retrieveResults(job_id):
    # when results finished, retrieve analysis script outputs
    # and calculate objectives
    rootfile = uproot.open(str(os.environ["AIDE_HOME"])+"/rich/log/root_files/output_{}.root".format(job_id))
    tree = rootfile[rootfile.keys()[0]]
    mchi2 = tree["mchi2"].array(library='np')
    pmt = tree["pmt"].array(library='np')

    # get list of unique pmts, and get mean mchi2 for each pmt
    unique_pmts, indices = np.unique(pmt, return_inverse=True)
    mean_mchi2_perpmt = np.array([mchi2[indices == i].mean() for i in range(len(unique_pmts))])

    # take quadrature mean
    mean_mchi2 = np.sqrt(np.mean(mean_mchi2_perpmt**2))

    return mean_mchi2

jobid = sys.argv[1]

meanchi2 = np.array(retrieveResults(jobid))
np.savetxt(os.environ["AIDE_HOME"]+"/log/results/" + "rich-align-mobo-out_{}.txt".format(jobid),[meanchi2])
