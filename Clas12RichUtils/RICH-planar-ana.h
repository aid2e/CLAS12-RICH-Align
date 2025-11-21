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

double nAero_module1[102][3] = {
    {0, 0, 1.05054},
    {0, 1, 1.05164},
    {0, 2, 1.05227},
    {0, 3, 1.05175},
    {0, 4, 1.05214},
    {0, 5, 1.05208},
    {0, 6, 1.05096},
    {0, 7, 1.05110},
    {0, 8, 1.05158},
    {0, 9, 1.05189},
    {0, 10, 1.04943},
    {0, 11, 1.05200},
    {0, 12, 1.04998},
    {0, 13, 1.05114},
    {0, 14, 1.05100},
    {0, 15, 1.05220},

    {1, 0, 1.04879},
    {1, 1, 1.05137},
    {1, 2, 1.05116},
    {1, 3, 1.05164},
    {1, 4, 1.05154},
    {1, 5, 1.04920},
    {1, 6, 1.04943},
    {1, 7, 1.05081},
    {1, 8, 1.05081},
    {1, 9, 1.05058},
    {1, 10, 1.05168},
    {1, 11, 1.05071},
    {1, 12, 1.05002},
    {1, 13, 1.05125},
    {1, 14, 1.05206},
    {1, 15, 1.05162},
    {1, 16, 1.05154},
    {1, 17, 1.05052},
    {1, 18, 1.05164},
    {1, 19, 1.05154},
    {1, 20, 1.04977},
    {1, 21, 1.05121},

    {2, 0, 1.04960},
    {2, 1, 1.04960},
    {2, 2, 1.04808},
    {2, 3, 1.04899},
    {2, 4, 1.05229},
    {2, 5, 1.05208},
    {2, 6, 1.05108},
    {2, 7, 1.04947},
    {2, 8, 1.04964},
    {2, 9, 1.0053},
    {2, 10, 1.05208},
    {2, 11, 1.05064},
    {2, 12, 1.05062},
    {2, 13, 1.04906},
    {2, 14, 1.05020},
    {2, 15, 1.05093},
    {2, 16, 1.05098},
    {2, 17, 1.04870},
    {2, 18, 1.05050},
    {2, 19, 1.05004},
    {2, 20, 1.05210},
    {2, 21, 1.05000},
    {2, 22, 1.05058},
    {2, 23, 1.04854},
    {2, 24, 1.05104},
    {2, 25, 1.04937},
    {2, 26, 1.04987},
    {2, 27, 1.04822},
    {2, 28, 1.04899},
    {2, 29, 1.04958},
    {2, 30, 1.05187},
    {2, 31, 0.0},

    {3, 0, 1.05210},
    {3, 1, 1.04935},
    {3, 2, 1.04791},
    {3, 3, 1.04995},
    {3, 4, 1.05208},
    {3, 5, 1.05208},
    {3, 6, 1.05166},
    {3, 7, 1.04906},
    {3, 8, 1.05014},
    {3, 9, 1.05146},
    {3, 10, 1.05137},
    {3, 11, 1.05060},
    {3, 12, 1.05104},
    {3, 13, 1.04950},
    {3, 14, 1.04983},
    {3, 15, 1.05208},
    {3, 16, 1.05208},
    {3, 17, 1.04941},
    {3, 18, 1.05050},
    {3, 19, 1.04801},
    {3, 20, 1.05206},
    {3, 21, 1.05062},
    {3, 22, 1.05041},
    {3, 23, 1.04778},
    {3, 24, 1.05083},
    {3, 25, 1.05000},
    {3, 26, 1.05083},
    {3, 27, 1.04831},
    {3, 28, 1.04910},
    {3, 29, 1.05000},
    {3, 30, 1.05175},
    {3, 31, 0.0}
};

// need passport info...
double getnAero(int layer, int comp){
  // for test: hard code passport info
  for (int i = 0; i < 102; i++) {
    // Compare the stored layer and comp values (cast to int for comparison)
    if (int(nAero_module1[i][0]) == layer && int(nAero_module1[i][1]) == comp) {
      return nAero_module1[i][2];
    }
  }
  return 1;
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

class RICHOutput{
public:
  // 7 planar mirrors
  TH1F *hDThetaPlanar[7];
  
  RICHOutput(){
    int nbins = 150;
    double min = 0;
    double max = 45;
    hDThetaPlanar[0] = new TH1F("hDThetaPlanar0", "Mirror A3", nbins, min, max);
    hDThetaPlanar[1] = new TH1F("hDThetaPlanar1", "Mirror B1", nbins, min, max);
    hDThetaPlanar[2] = new TH1F("hDThetaPlanar2", "Mirror B2", nbins, min, max);
    hDThetaPlanar[3] = new TH1F("hDThetaPlanar3", "Mirror A2R", nbins, min, max);
    hDThetaPlanar[4] = new TH1F("hDThetaPlanar4", "Mirror A1R", nbins, min, max);
    hDThetaPlanar[5] = new TH1F("hDThetaPlanar5", "Mirror A2L", nbins, min, max);
    hDThetaPlanar[6] = new TH1F("hDThetaPlanar6", "Mirror A1L", nbins, min, max);
  } 
  void Fill(int mirrornum, double dtheta){
    hDThetaPlanar[mirrornum-11]->Fill(dtheta);
    return;
  }
  
  void Write(const char* outname){
    // test with writing out histos for now
    TFile* outfile = new TFile(TString(outname)+TString(".root"),"recreate");
    for(int i = 0; i < 7; i++){
      hDThetaPlanar[i]->Write();
    }
    outfile->Close();
    return;
  }

};
