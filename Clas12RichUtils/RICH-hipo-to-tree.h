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
#include "hipo4/event.h"
using namespace std;

double getMass(int pid){
  double mass;
  switch (abs(pid)){
  case 321:
    mass = .493677;
    break;
  case 211:
    mass = .13957039;
    break;
  case 2212:
    mass = .93827208816;
    break;
  case 11:
    mass = 0.00051099895000;
    break;
  default:
    mass = .13957039;
    break;
  }
  return mass;
}

int pidToIndex(int pid){
  int index = -1;
  switch (abs(pid)){
  case 321:
    index = 2;
    break;
  case 211:
    index = 1;
    break;
  case 2212:
    index = 3;
    break;
  case 11:
    index = 0;
    break;
  default:
    index = -1; 
    break;
  }
  return index;  
}

class RICHOutput{
  // store analysis for each [aerogel tile][particle PID]
  // number of aerogel tiles depends on layer #.
  // could store both and analyze separately later
  
public:
  /// ctor: creates the TTree and its branches
  RICHOutput(const std::string& treeName = "eleProtTree") {
    tree = new TTree(treeName.c_str(), "");
    // integers
    tree->Branch("sector",   &sector,   "sector/I");
    tree->Branch("aerolayer",   &aerolayer,   "aerolayer/I");
    tree->Branch("aerocomp",     &aerocomp,     "aerocomp/I");
    tree->Branch("ebpid",        &ebpid,        "ebpid/I");
    tree->Branch("nphotons",     &nphotons,     "nphotons/I");
    // vector of doubles: ROOT will detect the STL vector type automatically
    tree->Branch("chRecScaled", &chRecScaled);
    tree->Branch("topology", &topology);
    tree->Branch("planarVec", &planarVec);
    tree->Branch("sphericalVec", &sphericalVec);
    tree->Branch("nRefVec", &nRefVec);
    // doubles
    tree->Branch("beta",        &beta,        "beta/D");
    tree->Branch("p",           &p,           "p/D");
    tree->Branch("theta",           &theta,           "theta/D");
    tree->Branch("phi",           &phi,           "phi/D");
    tree->Branch("emix",           &emix,           "emix/D");
    tree->Branch("emiy",           &emiy,           "emiy/D");
    tree->Branch("emiz",           &emiz,           "emiz/D");
    tree->Branch("cx",           &cx,           "cx/D");
    tree->Branch("cy",           &cy,           "cy/D");
    tree->Branch("cz",           &cz,           "cz/D");
    tree->Branch("RICHid",           &RICHid,           "RICHid/I");
  }

  /// Fill one “event” (you can call this repeatedly)
  void Fill(int sector_,
	    int aerolayer_,
	    int aerocomp_,
	    int ebpid_,
	    const std::vector<double>& chRecScaled_,
	    const std::vector<int>& topology_,
	    double beta_,
	    double p_,
	    double theta_,
	    double phi_,
	    double emix_,
	    double emiy_,
	    double emiz_,
	    double cx_,
	    double cy_,
	    double cz_,
	    int RICHid_,
	    const std::vector<int>& planarVec_,
	    const std::vector<int>& sphericalVec_,
	    const std::vector<int>& nRefVec_)
  {
    sector      = sector_;
    aerolayer   = aerolayer_;
    aerocomp    = aerocomp_;
    ebpid       = ebpid_;
    chRecScaled = chRecScaled_;
    topology    = topology_;
    nphotons    = static_cast<int>(chRecScaled.size());
    beta        = beta_;
    p           = p_;
    theta       = theta_;
    phi         = phi_;
    emix        = emix_;
    emiy        = emiy_;
    emiz        = emiz_;
    cx        = cx_;
    cy        = cy_;
    cz        = cz_;
    RICHid        = RICHid_;
    planarVec = planarVec_;
    sphericalVec = sphericalVec_;
    nRefVec = nRefVec_;
    tree->Fill();
  }
  
  /// Write the tree to a ROOT file
  void Write(const std::string& filename) {
    TFile f(filename.c_str(), "RECREATE");
    tree->Write();
    f.Close();
  }

private:
  TTree*                tree         = nullptr;
  int                   sector       = 0;
  int                   aerolayer    = 0;
  int                   aerocomp     = 0;
  int                   ebpid        = 0;
  int                   nphotons     = 0;
  std::vector<double>   chRecScaled;
  std::vector<int>      topology;
  std::vector<int>      planarVec;
  std::vector<int>      sphericalVec;
  std::vector<int>      nRefVec;
  double                beta         = 0.;
  double                p            = 0.;
  double                theta            = 0.;
  double                phi            = 0.;
  double                emix         = 0.;
  double                emiy         = 0.;
  double                emiz         = 0.;
  double                cx         = 0.;
  double                cy         = 0.;
  double                cz         = 0.;
  int                   RICHid         = 0.;
};

