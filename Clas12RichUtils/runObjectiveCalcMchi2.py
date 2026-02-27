import os, sys
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import uproot
import awkward as ak
import math
from uncertainties import ufloat
from uncertainties.umath import sqrt as usqrt
from collections import defaultdict
from typing import Callable, Tuple, Optional

'''
Script for producing GLOBAL alignment metric from a single root file,
corresponding to one dataset (inbending or outbending).
'''

jobid = sys.argv[1]
align_sector = int(sys.argv[2])
output_dir = sys.argv[3]
tiles_by_layer = {201:range(1,17),202:range(1,23),
                 203:range(1,33)
                 }
def getHistoPeakBootstrap(
    x,
    bins=60,
    half_window_bins=5,
    n_boot=500,
    histrange=None,
    min_count_in_window=10,
    random_state=None,
):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return ufloat(np.nan, np.nan)
    
    rng = np.random.default_rng(random_state)
    
    # Choose a reasonable default histogram range (robust to tails)
    if histrange is None:
        lo, hi = np.percentile(x, [0.5, 99.5])
        if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
            lo, hi = np.min(x), np.max(x)
        if lo == hi:
            return ufloat(float(lo), 0.0)
        histrange = (float(lo), float(hi))

    counts, edges = np.histogram(x, bins=bins, range=histrange)
    if counts.size == 0 or np.all(counts == 0):
        return ufloat(np.mean(x), 0.0)

    peak_idx = int(np.argmax(counts))

    # Window around the peak bin, in bin-index space
    i0 = max(0, peak_idx - int(half_window_bins))
    i1 = min(len(edges) - 2, peak_idx + int(half_window_bins))  # last bin index is len(edges)-2

    # Convert bin indices to value window
    lo_edge = edges[i0]
    hi_edge = edges[i1 + 1]

    in_window = (x >= lo_edge) & (x < hi_edge)
    xw = x[in_window]

    # If the peak window is too sparse, relax (fallback to using the peak bin only, then expand)
    if xw.size < min_count_in_window:
        # try peak bin only
        lo_edge2 = edges[peak_idx]
        hi_edge2 = edges[peak_idx + 1]
        in_peak_bin = (x >= lo_edge2) & (x < hi_edge2)
        xw2 = x[in_peak_bin]

        if xw2.size >= min_count_in_window:
            xw = xw2
            lo_edge, hi_edge = lo_edge2, hi_edge2
        else:
            # last resort: just use all points (and bootstrap the global mean)
            xw = x

    peak_mean = float(np.mean(xw))

    # Bootstrap uncertainty on that mean
    if xw.size <= 1 or n_boot <= 1:
        return ufloat(peak_mean, 0.0)

    boots = np.empty(int(n_boot), dtype=float)
    n = xw.size
    for i in range(int(n_boot)):
        sample = xw[rng.integers(0, n, size=n)]
        boots[i] = np.mean(sample)

    # Use sample std (ddof=1) for bootstrap distribution
    peak_sigma = float(np.std(boots, ddof=1)) if boots.size > 1 else 0.0
    return ufloat(peak_mean, peak_sigma)


selected_pmts = [17,27,34,55,73,80,117,125,143,153,172,180,
                 191,203,213,220,233,246,258,266,281,307,314,320,
                 325,331,349,351]

file_ele = uproot.open(output_dir+f"/rich/log/root_files/output_global_{jobid}.root")
tree = file_ele[file_ele.keys()[0]]

min_tracks = 100
ebpid = tree['ebpid'].array(library='np')
mchi2 = tree['mchi2'].array(library='np')
pmt = tree['pmt'].array(library='np')
sector = tree['sector'].array(library='np')
combined_metric = ufloat(0.0,0.0)
print("N in sector: ", np.sum(sector==align_sector))
# separate pi+ and pi-, only use pmts with > 100 tracks
for p in selected_pmts:
    if np.sum((pmt==p)*(ebpid==211)*(sector==align_sector)) > min_tracks:
        combined_metric += (getHistoPeakBootstrap(mchi2[(pmt==p)*(ebpid==211)*(sector==align_sector)]))
    if np.sum((pmt==p)*(ebpid==-211)*(sector==align_sector)) > min_tracks:
        combined_metric += (getHistoPeakBootstrap(mchi2[(pmt==p)*(ebpid==-211)*(sector==align_sector)]))

#combined_metric /= len(selected_pmts)
print(combined_metric)
np.savetxt(output_dir+"/log/results/" + "rich-align-mobo-out_{}.txt".format(jobid),np.array([combined_metric.n,combined_metric.s]))

# Flatten into {name_value: n, name_uncertainty: s}
if math.isnan(combined_metric.n):
    print("metric returned NaN or 0, flag failure")
    sys.exit(1)
