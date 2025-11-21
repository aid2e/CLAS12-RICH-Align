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
Script for producing alignment metric from a single root file,
corresponding to one dataset (inbending or outbending).
'''

jobid = sys.argv[1]

tiles_by_layer = {201:range(1,17),202:range(1,23),
                 203:range(1,33)
                 }

def calc_cher_residual_generic(
    filename,
    sellayer,
    tiles,
    mode="direct",                 # "direct", "planar", or "spherical"
    planar_mirror=None,            # required when mode == "planar" or "spherical"
    spherical_mirror=None,         # required when mode == "spherical"
    topology_select=-1,
    ebpid_select=11,
    scale_angle=False,
):
    """
    Produces dict of vectors of Cherenkov angle distributions for selected EB pid.
    """

    file = uproot.open(filename)
    tree = file[file.keys()[0]]

    # reconstructed cherenkov angle info
    aerolayer   = tree['aerolayer'].array(library='np')
    aerocomp    = tree['aerocomp'].array(library='np')
    ebpid       = tree['ebpid'].array(library='np')
    nphotons    = tree['nphotons'].array(library='np')
    chRecScaled = tree['chRecScaled'].array(library='ak')
    topology    = tree['topology'].array(library='ak')

    # Only needed for planar/spherical selection
    if mode in ("planar", "spherical"):
        nRefl        = tree['nRefVec'].array(library='ak')
        planarVec    = tree['planarVec'].array(library='ak')
        sphericalVec = tree['sphericalVec'].array(library='ak')

    # track kinematics
    beta  = tree['beta'].array(library='np')
    p     = tree['p'].array(library='np')
    theta = tree['theta'].array(library='np')
    phi   = tree['phi'].array(library='np')

    dict_resid = defaultdict(dict)
    total_ev = 0  # printed for planar/spherical, consistent with your originals

    for c in tiles:
        mask = (
            ((aerolayer + 201) == sellayer)
            & ((aerocomp + 1) == c)
            & (ebpid == ebpid_select)
            & (nphotons > 2)
            & (p < 5)
        )
        # photon-level selection based on topology
        if mode == "direct":
            top_photons = ak.flatten(topology[mask])
            ele_photons = ak.flatten(chRecScaled[mask])[top_photons == topology_select]
            cut = (top_photons == topology_select)

        elif mode == "planar":
            nrefl_photons = ak.flatten(nRefl[mask])
            plan_photons  = ak.flatten(planarVec[mask])
            # nrefl==1 & planar mirror match
            cut = (nrefl_photons == 1) & (plan_photons == planar_mirror)
            ele_photons = ak.flatten(chRecScaled[mask])[cut]
            total_ev += np.sum(cut)

        elif mode == "spherical":
            nrefl_photons = ak.flatten(nRefl[mask])
            plan_photons  = ak.flatten(planarVec[mask])
            spher_photons = ak.flatten(sphericalVec[mask])
            # nrefl==2 & both spherical and planar mirrors match
            cut = (nrefl_photons == 2) & (spher_photons == spherical_mirror) & (plan_photons == planar_mirror)
            ele_photons = ak.flatten(chRecScaled[mask])[cut]
            total_ev += np.sum(cut)

        else:
            raise ValueError(f"Unknown mode '{mode}'. Use 'direct', 'planar', or 'spherical'.")

        # per-photon beta
        p_evt   = p[mask]
        mass    = 0.13957039  # TODO: RICH PID if/when you add it; kept exactly as your original
        beta_evt  = p_evt / np.sqrt(p_evt * p_evt + mass * mass)
        counts    = ak.num(chRecScaled[mask], axis=1)
        beta_phot = np.repeat(beta_evt, counts)[cut]

        ele_np = np.asarray(ele_photons)
        ok     = np.isfinite(ele_np)

        if scale_angle:
            ele_np = np.acos(beta_phot * np.cos(ele_np))

        resid = 1000.0 * ele_np[ok]        
        dict_resid[sellayer][c] = resid

    if mode in ("planar", "spherical"):
        print("Layer:", sellayer, "Total N photons:", total_ev)

    return dict(dict_resid)

def calc_cher_residual_layers_generic(
    filename,
    tiles_by_layer,
    mode="direct",
    planar_mirror=None,
    spherical_mirror=None,
    topology_select=-1,
    ebpid_select=11,
    scale_angle=False,
):
    # loops over all tiles in a layer, collects photons for selected topology + EB pid
    all_resid = defaultdict(dict)
    for sellayer, tiles in tiles_by_layer.items():
        single = calc_cher_residual_generic(
            filename=filename,
            sellayer=sellayer,
            tiles=tiles,
            mode=mode,
            planar_mirror=planar_mirror,
            spherical_mirror=spherical_mirror,
            topology_select=topology_select,
            ebpid_select=ebpid_select,
            scale_angle=scale_angle,
        )
        all_resid[sellayer] = single[sellayer]
    return dict(all_resid)

# Collect single-photons cherenkov angle distributions separated by layer/tile/topology
file_ele = os.environ["OUTPUT_DIR"]+f"/rich/log/root_files/output_spherical_{jobid}.root"
print("starting direct")
cher_dist_direct    = calc_cher_residual_layers_generic(file_ele, tiles_by_layer, scale_angle=False,
                                                                mode="direct",
                                                                ebpid_select=11)
# and for your mirror‐by‐mirror splits:
mirrors_row1 = [21,25,22]
mirrors_row2 = [28,29,30,23,26,27,24]

cher_dist_spher_row1  = defaultdict(dict)
cher_dist_spher_row2  = defaultdict(dict)

mirrors_planar = [11,14,15,16,17] # 1 reflection topology planar mirrors
cher_dist_planar  = defaultdict(dict)

for m in mirrors_planar:
    print(m)
    print("ele")
    cher_dist_planar[m] = calc_cher_residual_layers_generic(
            file_ele, tiles_by_layer, planar_mirror=m, ebpid_select=11, scale_angle=False,
            mode="planar"
        )

for m in mirrors_row1:
    for p in [12,13]:
        print(m,p)
        cher_dist_spher_row1[m][p] = calc_cher_residual_layers_generic(
            file_ele, tiles_by_layer, planar_mirror=p, spherical_mirror=m,
            ebpid_select=11, scale_angle=False,
            mode="spherical"
        )

for m in mirrors_row2:
    for p in [13]:
        print(m,p)
        cher_dist_spher_row2[m][p] = calc_cher_residual_layers_generic(
            file_ele, tiles_by_layer, planar_mirror=p, spherical_mirror=m,
            ebpid_select=11, scale_angle=False,
            mode="spherical"
        )

cher_dist_spher_row1 = dict(cher_dist_spher_row1)
cher_dist_spher_row2 = dict(cher_dist_spher_row2)

##############################
# Helper functions for spread
# amongst topologies metric.
##############################

# interquartile range for width of distribution
def iqr(arr):
    if arr.size == 0: return 0.0
    q75, q25 = np.percentile(arr, [75, 25])
    return float((q75 - q25)/1.349) # scale to be equivalent to a gaussian sigma

# peak of distribution from weighted mean within +/- 5 bins of peak
def mean_from_histo_peak(data, bins=80, data_range=None):
    arr = np.asarray(data)
    arr = arr[np.isfinite(arr)]
    if arr.size <= 25:
        return ufloat(0.0, 0.0)    
    
    counts, edges = np.histogram(arr, bins=bins, range=data_range)
    if counts.sum() == 0:
        return 0.0
    centers = 0.5 * (edges[:-1] + edges[1:])
    
    # weighted avg within 5 bins of the peak
    peak_idx = int(np.argmax(counts))
    lo = max(0, peak_idx - 5)
    hi = min(len(counts) - 1, peak_idx + 5)
    w = counts[lo:hi+1]
    x = centers[lo:hi+1]
    if w.sum() == 0:
        return 0.0
    return float(np.average(x, weights=w))

def spread_metric(means, widths):
    mean_bar = float(np.mean(means)) # average of peak position of topologies 
    diff_term = float(np.sum((means - mean_bar)**2) / len(means))
    width_bar  = float(np.mean(widths**2)) # average width of topologies
    return diff_term / (width_bar + 1e-9)

def bootstrap_spread_metric(data_topos, # dict containing all topologies to be used,
                          n_boot: int = 300
                    ):
    rng = np.random.default_rng()
    print("topos: ", data_topos.keys())
    
    scores = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        means, widths = [], []
        for k in data_topos.keys():
            # bootstrapping for every topology 
            vals = data_topos[k]
            samp = vals[rng.integers(0, vals.size, size=vals.size)]  # sample with replacement
            means.append(mean_from_histo_peak(samp))
            widths.append(iqr(samp))
        means  = np.asarray(means,  float)
        #if b == 0:
        #    print(means)
        widths = np.asarray(widths, float)
        scores[b] = spread_metric(means, widths)

    return ufloat(float(scores.mean()), float(scores.std(ddof=1)))

def getSpreadMetric(
    dict_direct, dict_planar, dict_spher, dict_spher_row2,
    layer: int, tile: int, min_counts: int = 1000, # min counts to consider a topology/tile combination
    *,
    bounds = (280.0, 350.0), # theta_cher range in which we'll accept single photons
    n_boot = 300, # number of bootstrap calls
    spherical_shift = 1.59, # expected difference in mean cherenkov angle btw 2 refl and 0 refl
    spherical_shift_203 = 1.45, # expected difference in mean cherenkov angle btw 2 refl and 0 refl, 6cm aero. layer
):

    lo, hi = bounds[0], bounds[1]
    # Create dict containing all topologies that have counts > min_counts 
    # for this layer and tile (inbending and outbending)
    data_topos = {}

    # direct
    a = np.asarray(dict_direct[layer][tile], float)
    a = a[(a >= lo) & (a <= hi)]
    if a.size >= min_counts:
        data_topos["direct"] = a
        
    # planar
    for key in dict_planar.keys():
        a = np.asarray(dict_planar[key][layer][tile], float)
        a = a[(a >= lo) & (a <= hi)]
        if a.size >= min_counts:
            data_topos[f"planar_{key}"] = a        

    # spherical (lower row only)
    for k1 in dict_spher.keys():
        for k2 in dict_spher[k1].keys():
            if layer < 203:
                a = np.asarray(dict_spher[k1][k2][layer][tile], float) + spherical_shift
            else:
                a = np.asarray(dict_spher[k1][k2][layer][tile], float) + spherical_shift_203
            a = a[(a >= lo) & (a <= hi)]
            if a.size >= min_counts:
                data_topos[f"spher_{k1}_{k2}"] = a
            
    # spherical (upper 2 rows of mirrors)
    for k1 in dict_spher_row2.keys():
        for k2 in dict_spher_row2[k1].keys():
            if layer < 203:
                a = np.asarray(dict_spher_row2[k1][k2][layer][tile], float) + spherical_shift
            else:
                a = np.asarray(dict_spher_row2[k1][k2][layer][tile], float) + spherical_shift_203
            a = a[(a >= lo) & (a <= hi)]
            if a.size >= min_counts:
                data_topos[f"spher_{k1}_{k2}"] = a            

    # If fewer than 2 usable topologies, return 0
    if len(data_topos) <= 1:
        return ufloat(0.0, 0.0)
        
    return bootstrap_spread_metric(data_topos, n_boot)


distance_sum = {201:0, 202:0, 203:0}
total_terms = {201:0, 202:0, 203:0}
terms = {}
layer_avg = ufloat(0.0,0.0)
for layer in tiles_by_layer.keys():
    for tile in tiles_by_layer[layer]:
        print(layer,tile)            
        spread_together = getSpreadMetric(
            cher_dist_direct,cher_dist_planar,cher_dist_spher_row1,cher_dist_spher_row2,
            layer=layer, tile=tile,
            bounds=(280, 350),
            min_counts=500,
        )

        if spread_together>0:
            distance_sum[layer] += spread_together
            total_terms[layer] += 1
            layer_avg += spread_together
    terms[f'topo_mismatch_layer{layer}'] = layer_avg/total_terms[layer]

# calculate spread for a given topology (data_dict), looping over ALL
# tiles with counts > min_counts for that topology
def get_width_sum_alltiles(
    data_dict,
    *,
    min_counts = 500,
    bounds=(280.0, 350.0),  # range of single photon cherenkov angles accepted
    fallback_width=20.0, # when not enough data
    bootstrap=True,
    n_bootstraps=100,
    random_state=None
):
    lo, hi = bounds
    rng = np.random.default_rng(random_state)
    
    total = ufloat(0.0, 0.0)
    
    total_tiles = 0
    for ln in tiles_by_layer:
        for tn in tiles_by_layer[ln]:
            vals = np.asarray(data_dict[ln][tn], dtype=float)
            
            # should we punish if N outside of the range > min_counts?
            good_photons = vals[(vals >= lo) & (vals <= hi)]
            N = good_photons.size
            # number of photons cut, where do we want to place this?
            if N < min_counts:
                continue

            # sample with replacement 
            boot_spreads = np.empty(n_bootstraps, dtype=float)
            for b in range(n_bootstraps):
                samp = rng.choice(good_photons, size=N, replace=True)
                boot_spreads[b] = iqr(samp)
            tile_mean = float(np.mean(boot_spreads))
            tile_std  = float(np.std(boot_spreads, ddof=1))
            total += (ufloat(tile_mean, tile_std)/(4))**2
            total_tiles += 1
    if total_tiles == 0:
        return 0
    else:
        return total/total_tiles
iqr_sum = ufloat(0,0)
n_topos = 0

for i in [21,25,22]:
    iqr_sum += get_width_sum_alltiles(cher_dist_spher_row1[i][13])
    n_topos += 1
    iqr_sum += get_width_sum_alltiles(cher_dist_spher_row1[i][12])
    terms[f'iqr_sph_{i}_12'] = get_width_sum_alltiles(cher_dist_spher_row1[i][12])
    terms[f'iqr_sph_{i}_13'] = get_width_sum_alltiles(cher_dist_spher_row1[i][13])
    n_topos += 1
for i in mirrors_row2:
    iqr_sum += get_width_sum_alltiles(cher_dist_spher_row2[i][13])
    terms[f'iqr_sph_{i}_13'] = get_width_sum_alltiles(cher_dist_spher_row2[i][13])
    n_topos += 1
for i in [11,14,16]:
    iqr_sum += get_width_sum_alltiles(cher_dist_planar[i])
    terms[f'iqr_planar_{i}'] = get_width_sum_alltiles(cher_dist_planar[i])
    n_topos += 1
print("direct")
iqr_sum += get_width_sum_alltiles(cher_dist_direct)
n_topos+=1
terms[f'iqr_direct'] = get_width_sum_alltiles(cher_dist_direct)

combined_metric = (distance_sum[201] + distance_sum[202] +
                  distance_sum[203] + 
                  iqr_sum)
np.savetxt(os.environ["AIDE_HOME"]+"/log/results/" + "rich-align-mobo-out_{}.txt".format(jobid),np.array([combined_result.n,combined_result.s]))

import pandas as pd
# Flatten into {name_value: n, name_uncertainty: s}
data = {}
for name, val in terms.items():
    data[f"{name}_value"] = val.n  # nominal value
    data[f"{name}_uncertainty"] = val.s  # std dev


df = pd.DataFrame([data])
# Save csv of all terms in metric
df.to_csv(os.environ["AIDE_HOME"]+"/log/results/"+f"results_allterms_{jobid}.csv", index=False)

if math.isnan(combined_metric.n):
    print("metric returned NaN or 0, flag failure")
    sys.exit(1)
