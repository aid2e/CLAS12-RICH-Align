// RICH-skim-dst-modular.h (modularized)
#ifndef RICH_SKIM_DST_MODULAR_ONETOP_H
#define RICH_SKIM_DST_MODULAR_ONETOP_H

#include "TFile.h"
#include "TString.h"
#include "TH1F.h"
#include "TH2F.h"
#include "TF1.h"
#include "TTree.h"
#include "TGraph.h"
#include "TCanvas.h"
#include "TVector3.h"
#include "TLorentzVector.h"
#include "hipo4/reader.h"
#include "hipo4/writer.h"
#include "hipo4/event.h"
#include "hipo4/bank.h"
#include <vector>
#include <initializer_list>


static constexpr int MAX_LAYER = 4;
static constexpr int MAX_COMPO_PER_LAYER[4] = {16, 22, 32, 32};

// Configuration struct to toggle cuts and set thresholds
struct SkimConfig {
  bool applyDISCut       = false;
  bool applyRichOneCut   = true;
  int topologyType = 0;
  int aerolayer = 201;
  int planarMirror = 0;
  int planarMirror1 = 0;
  int planarMirror2 = 0;
  int sphericalMirror = 0;
  int minPhotons = 2;
  int maxev = 100000;
  int maxPerTile = 5000;
  int sector = 4;
  double minP = 1.25;
  std::vector<int> validPIDs = {11};
};

struct CounterStats {
  std::vector<int> layerCounters[3];   // [layer][compo]
  std::vector<int>               planarCounters;  // per–mirror planar counts
  std::vector<int> directLayerCounters;   // [layer], direct only
  std::vector<int> planarCountersMultiRefl; // per planar mirror, >1 refl
  std::vector<int> sphericalCounters; // per spherical mirror (first refl, >1 total)


  int nOneInRICHCut   = 0;
  int nLayerCut       = 0;
  int nCherCut       = 0;
  int nLayerCountCut  = 0;
  int nMirrorCut      = 0;
  int nPhotonCountCut = 0;
  int nDirectEv       = 0;
  int nCutDirect      = 0;
  int nAccepted       = 0;
  
  CounterStats(const SkimConfig& cfg) {
    for(int i = 0; i < 16; i++){
      layerCounters[0].push_back(0);
    }
    for(int i = 0; i < 22; i++){
      layerCounters[1].push_back(0);
    }
    for(int i = 0; i < 32; i++){
      layerCounters[2].push_back(0);
    }
  }
};


// Original helpers
int   getCharge(int pid);
double angleDiff(double ang1, double ang2);
double getMass(int pid);
bool  isGoodDISEvent(hipo::bank particles);
bool  oneInRICH(hipo::bank RICHparticles, hipo::bank particles,
                 const std::vector<int>& validPIDs, double mchi2cut);
bool  PMTSelection(int hindex, hipo::bank clusters);
int   GetTopology(int nrefl, int refl1);
bool  nPlanarPhotonCut(hipo::bank RICHring, int nphotons);

// Modular skim function
void skimDST(const char* file,
             hipo::writer& outWriter,
             const SkimConfig& cfg,
	     CounterStats& stats);

#endif // RICH_SKIM_DST_MODULAR_H
