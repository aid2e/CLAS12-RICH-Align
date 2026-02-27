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
  
public:

  RICHOutput(const std::string& treeName = "eleProtTree") {
    tree = new TTree(treeName.c_str(), "");
    // integers
    tree->Branch("aerolayer",   &aerolayer,   "aerolayer/I");
    tree->Branch("aerocomp",     &aerocomp,     "aerocomp/I");
    tree->Branch("ebpid",        &ebpid,        "ebpid/I");
    tree->Branch("pmt",        &pmt,        "pmt/I");
    tree->Branch("sector",        &sector,        "sector/I");
    tree->Branch("mchi2",     &mchi2,     "mchi2/D");
    tree->Branch("beta",        &beta,        "beta/D");
    tree->Branch("p",           &p,           "p/D");
    tree->Branch("theta",           &theta,           "theta/D");
    tree->Branch("phi",           &phi,           "phi/D");
  }

  void Fill(int aerolayer_,
	    int aerocomp_,
	    int ebpid_,
	    int pmt_,
	    int sector_,
	    double mchi2_,
	    double beta_,
	    double p_,
	    double theta_,
	    double phi_	    
	    )
  {
    aerolayer   = aerolayer_;
    aerocomp    = aerocomp_;
    ebpid       = ebpid_;
    pmt       = pmt_;
    sector       = sector_;
    mchi2    = mchi2_;
    beta        = beta_;
    p           = p_;
    theta       = theta_;
    phi         = phi_;        
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
  int                   aerolayer    = 0;
  int                   aerocomp     = 0;
  int                   ebpid        = 0;
  int                   pmt        = 0;
  int                   sector        = 0;
  double                beta         = 0.;
  double                mchi2         = 0.;
  double                p            = 0.;
  double                theta            = 0.;
  double                phi            = 0.;  
};

