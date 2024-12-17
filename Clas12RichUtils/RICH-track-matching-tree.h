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


class RICHTree{
public:
  TTree *tree;

  //Int_t mcp;
  Float_t trkx, trky, trkz, clx, cly, clz;
  Float_t deltaR;
  Float_t mchi2;
  Int_t ebpid, pmt;
  
  RICHTree(){
    tree = new TTree("RICHtree", "");
    //tree->Branch("mcp", &mcp, "mcp/I");
    tree->Branch("trkx", &trkx, "trkx/F");                                                                                      
    tree->Branch("trky", &trky, "trky/F");                                                                                      
    tree->Branch("trkz", &trkz, "trkz/F");                                                                                      
    tree->Branch("clx", &clx, "clx/F");                                                                                         
    tree->Branch("cly", &cly, "cly/F");                                                                                         
    tree->Branch("clz", &clz, "clz/F");
    tree->Branch("deltaR", &deltaR, "deltaR/F");
    tree->Branch("mchi2", &mchi2, "mchi2/F");
    tree->Branch("ebpid", &ebpid, "ebpid/I");
    tree->Branch("pmt", &pmt, "pmt/I");
    //tree->Branch("traced_mchi2", &traced_mchi2, "traced_mchi2/F");
  }

  /*void setTrackInfo(double track_x, double track_y, double track_z){
    trkx = track_x;
    trky = track_y;
    trkz = track_z;
    return;
  }
  
  void setClusterInfo(double cluster_x, double cluster_y, double cluster_z){
    clx = cluster_x;
    cly = cluster_y;
    clz = cluster_z;
    return;
  }

  void CalcDeltaR(TVector3 vec_track, TVector3 vec_cluster){
    deltaR = (vec_track - vec_cluster).Mag();
    return;
    }*/

  void setmchi2(double mchi2_val){
    mchi2 = mchi2_val;
    return;
  }
  void setEBpid(int pid){
    ebpid = pid;
    return;
  }
  void setPMT(int clpmt){
    pmt = clpmt;
    return;
  }
    
  void Fill(){
    tree->Fill();
    return;
  }

  void Write(const char* outname){
    TFile* outfile = new TFile(TString(outname)+TString(".root"),"recreate");
    tree->Write();
    outfile->Close();
    return;
  }

};


// check if there is a reconstructed electron in the event
bool isGoodDISEvent(hipo::bank particles){

  double eleP = 0;
  int eleInd = -1;
  std::vector<int> indexhad;
  for(int i = 0; i < particles.getRows(); i++){
    int pid = particles.getInt("pid",i);
    double px = particles.getFloat("px",i);
    double py = particles.getFloat("py",i);
    double pz = particles.getFloat("pz",i);
    int status = particles.getShort("status",i);
    TVector3 p(px,py,pz);

    if(pid == 11 && p.Mag() > 2. && (status > -4000 && status <= 2000)){
      if(p.Mag() > eleP){
        eleInd = i; eleP = p.Mag();
      }

    }
    if( (abs(pid) == 321 || abs(pid) == 211 ) && p.Theta() < (35.*M_PI/180.) && p.Theta() > (5.*M_PI/180.)  ){
      if(p.Mag() > 1.){
        indexhad.push_back(i);
      }
    }
  }
  if (eleInd == -1) return false;
  if( indexhad.size() == 0) return false;

  return true;


}

