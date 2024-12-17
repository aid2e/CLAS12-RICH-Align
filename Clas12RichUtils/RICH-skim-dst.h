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
using namespace std;

int getCharge(int pid){
  if(pid > 12){
    return 1;
  }
  else{
    return -1;
  }
}
// shift angle difference, account for wrap-around                                                                                
double angleDiff(double ang1, double ang2){
  double diff = ang1-ang2;
  if(diff > M_PI){
    diff-=M_PI;
  }
  if(diff < -M_PI){
    diff+=M_PI;
  }
  return abs(diff);
}

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

// check that there is ONE hadron in (either) rich
bool oneInRICH(hipo::bank RICHparticles, hipo::bank particles){
  //int hadm1 = 0;
  //int hadm2 = 0;
  // for rgc and later, check both modules
  if(RICHparticles.getRows() != 1){ return false;}
  int pindex = RICHparticles.getInt("pindex",0);
  float mchi2 = RICHparticles.getFloat("mchi2",0);
  int ebpid = particles.getInt("pid",pindex);
  if((ebpid == 211 || ebpid == -211) && (mchi2>0)){
    return true;
  }  
  else{ return false; }
  
}

// check if PMT hit by cluster matched to track
// is within some list of PMTs. 
bool PMTSelection(int hindex, hipo::bank clusters){
  int clusterpmt = clusters.getShort("pmt", hindex);
  std::vector<int> edgepmts = { // within 3 of edge
    1,   2,   3,   4,   5,   6,   7,   8,   9,  11,  12,  13,  14,
        15,  16,  19,  20,  21,  22,  23,  24,  28,  29,  30,  31,  32,
        33,  38,  39,  40,  41,  42,  43,  49,  50,  51,  52,  53,  54,
        61,  62,  63,  64,  65,  66,  74,  75,  76,  77,  78,  79,  88,
        89,  90,  91,  92,  93, 103, 104, 105, 106, 107, 108, 119, 120,
       121, 122, 123, 124, 136, 137, 138, 139, 140, 141, 154, 155, 156,
       157, 158, 159, 173, 174, 175, 176, 177, 178, 193, 194, 195, 196,
       197, 198, 214, 215, 216, 217, 218, 219, 236, 237, 238, 239, 240,
       241, 259, 260, 261, 262, 263, 264, 283, 284, 285, 286, 287, 288,
       308, 309, 310, 311, 312, 313, 334, 335, 336, 337, 338, 339, 361,
       362, 363, 364, 365, 366, 389, 390, 391
  };
  if(std::count(edgepmts.begin(), edgepmts.end(), clusterpmt) > 0){
    return true;
  }
  else return false;

}
// ADAPTED DIRECTLY from RICH calibration suite
// RICH::ring layers, compos to photon path information

int GetTopology(int nrefl, int refl1)
{
  /* topology id                                                                                                                                                              
     1 -> direct
     2 -> 1 reflection on the lateral mirrors
     12 -> more than 1 reflections, the first on a lateral mirror
     3 -> 2 reflections, the first on a spherical mirror
     13 -> more than 2 reflections, the first on a spherical mirror

     mirror flags
     planar mirrors: r1,r2=11-17
     spherical mirrors: r1,r2=21-30
  */

  int Topology = -1;
  int *refl;
  if (nrefl == 0) Topology = 1;
  else {
    if ( (10 < refl1) && (refl1 < 20) ) {
      if (nrefl == 1) Topology = 2;
      else Topology = 12;
    }
    else if ( (20 < refl1) && (refl1 <= 30) ) {
      if (nrefl == 2) Topology = 3;
      else Topology = 13;
    }


  }

  return Topology;
}

// ADAPTED DIRECTLY from RICH calibration suite
// RICH::ring layers, compos to photon path information
std::tuple<int,int,int> DecodePhotonPath(int layers, int compos)
{
  /* calculating number of reflections, refractions, first reflection and topology from the traced path flags */
  /* Mirror flag                                                                                                                                                              
     10 + 2 -> B1
     10 + 3 -> B2
     10 + 6 -> A2L
     10 + 7 -> A1L
     10 + 4 -> A2R
     10 + 5 -> A1R
     10 + 1 -> A3                                                                                                                                                                              
     20 + ID -> spherical mirror ID from 1 to 10
  */
  std::vector<int> refl;
  /* Checking the values of the flags */
  if ( (layers < 0) || (compos < 0) ) {
    return std::make_tuple(-1,-1,-1);
  }


  int nReflections = -1;
  int firstReflMirror = -1;
  int secondReflMirror = -1;

  //if (layers==1 && compos==0) printf(" Hit: -->layers=%d  compos=%d\n", layers, compos);                                                                                    
  int c = compos;
  int l = layers;
  int currentLayer = -1;
  int currentComp = -1;
  nReflections = 0;
  firstReflMirror = 0;
  secondReflMirror = 0;
  //while (l && c) {                                                                                                                                                          
  while (l) {
    nReflections++;
    currentLayer = l%10;
    currentComp = 1 + c%10 + 10*currentLayer;

    refl.push_back(currentComp);

    c = c/10;
    l = l/10;
  }

  int r1 = -1;
  if (nReflections > 0) r1 = refl[0];
  int top = GetTopology(nReflections, r1);
  

  
  return std::make_tuple(nReflections,r1,top);
}
