#include "RICH-skim-dst-modular-onetop.h"
#include "RICH-reflection-tools.h"
#include "TCanvas.h"
#include "TVector3.h"
#include "TLorentzVector.h"
#include <sstream>
#include <iostream>
#include <cstring>
#include <fstream>
#include <nlohmann/json.hpp>
using json = nlohmann::json;
//using namespace std;

TH1F* hAvgCher;
SkimConfig loadConfig(const std::string& path) {
    SkimConfig cfg;
    std::ifstream in(path);
    if(!in.is_open()) {
        std::cerr << "Error opening config file: " << path << std::endl;
        return cfg;
    }
    json j;
    in >> j;
    if(j.contains("applyDISCut"))      cfg.applyDISCut       = j["applyDISCut"].get<bool>();
    if(j.contains("applyRichOneCut"))  cfg.applyRichOneCut   = j["applyRichOneCut"].get<bool>();
    if(j.contains("topologyType"))  cfg.topologyType   = j["topologyType"].get<int>(); // 0: direct, 1: planar, 2: spherical
    if(j.contains("aerolayer"))  cfg.aerolayer   = j["aerolayer"].get<int>();
    if(j.contains("planarMirror"))  cfg.planarMirror   = j["planarMirror"].get<int>();
    if(j.contains("planarMirror1"))  cfg.planarMirror1   = j["planarMirror1"].get<int>();
    if(j.contains("planarMirror2"))  cfg.planarMirror2   = j["planarMirror2"].get<int>();
    if(j.contains("sphericalMirror"))  cfg.sphericalMirror   = j["sphericalMirror"].get<int>();
    if(j.contains("minPhotons"))  cfg.minPhotons   = j["minPhotons"].get<int>();
    if(j.contains("maxev"))  cfg.maxev   = j["maxev"].get<int>();
    if(j.contains("validPIDs"))        cfg.validPIDs         = j["validPIDs"].get<std::vector<int>>();
    return cfg;
}

// -- unchanged helper implementations here --
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
bool oneInRICH(hipo::bank RICHparticles, hipo::bank particles, const std::vector<int>& validPIDs, double mchi2cut){
  //int hadm1 = 0;
  //int hadm2 = 0;
  // for rgc and later, check both modules
  if(RICHparticles.getRows() != 1){ return false;}
  int pindex = RICHparticles.getInt("pindex",0);
  float mchi2 = RICHparticles.getFloat("mchi2",0);
  int ebpid = particles.getInt("pid",pindex);
  double px = particles.getFloat("px",pindex);
  double py = particles.getFloat("py",pindex);
  double pz = particles.getFloat("pz",pindex);
  double p = sqrt(px*px+py*py+pz*pz);

  if(p > 5) return false;
  
  if (mchi2 <= mchi2cut) {
    return false;
  }
  
  for (int pid : validPIDs) {
    if (ebpid == pid) {
      return true;
    }
  }
  return false;
}
// check if PMT hit by cluster matched to track
// is within some list of PMTs.
bool PMTSelection(int clusterpmt){

  std::vector<int> edgepmts = {
    17,27,34,55,73,80,117,125,143,153,172,180,
    191,203,213,220,233,246,258,266,281,307,314,320,
    325,331,349,351
  };
  if(std::count(edgepmts.begin(), edgepmts.end(), clusterpmt) > 0){
    return true;
  }
  else return false;
}

int strToInt(const char* s) {
  std::stringstream ss; ss << s; int x; ss >> x; return x;
}

bool isGoodDirectEvent(hipo::bank RICHring, hipo::bank RICHpart, hipo::bank particles, SkimConfig cfg){
  int ndirect = 0;
    
  for(int jp = 0; jp < RICHpart.getRows(); jp++){
    int layer = RICHpart.getInt("emilay", jp) + 201;
    int compo = RICHpart.getInt("emico", jp);
    int pindex = RICHpart.getInt("pindex", jp);
    double avgetaC_part = RICHpart.getFloat("best_ch",jp);

    int nphotons = 0; double avgetaC = 0;
    for(int ip=0; ip<RICHring.getRows(); ++ip) {
      if(RICHring.getInt("pindex",ip) != pindex) continue;
      float etaC = RICHring.getFloat("etaC",ip);
      int use = int(RICHring.getByte("use",ip));
      if(etaC == 0 || use != 111) continue; // use!=111                                                                                                             
      
      avgetaC += etaC;
      nphotons++;
      auto [nref,_r1,top,refl] = DecodePhotonPath(
						  RICHring.getInt("layers",ip),
						  RICHring.getInt("compos", ip)
						  );
      
      if(nref == 0 && layer == cfg.aerolayer) ++ndirect;
    }
  }
  if(ndirect >= cfg.minPhotons) return true;
  return false;
  
}
bool isGoodPlanarEvent(hipo::bank RICHring, hipo::bank RICHpart, hipo::bank particles, SkimConfig cfg){
  int nplanar = 0;
  bool hit15 = 0;
  for(int jp = 0; jp < RICHpart.getRows(); jp++){
    int layer = RICHpart.getInt("emilay", jp) + 201;
    int compo = RICHpart.getInt("emico", jp);
    int pindex = RICHpart.getInt("pindex", jp);
    double avgetaC_part = RICHpart.getFloat("best_ch",jp);

    for(int ip=0; ip<RICHring.getRows(); ++ip) {
      if(RICHring.getInt("pindex",ip) != pindex) continue;
      float etaC = RICHring.getFloat("etaC",ip);
      int use = int(RICHring.getByte("use",ip));
      if(etaC == 0 || use != 111) continue; // use!=111
      
      auto [nref,mirr1,top,refl] = DecodePhotonPath(
						    RICHring.getInt("layers",ip),
						    RICHring.getInt("compos", ip)
						    );
      if(nref == 1 && layer == cfg.aerolayer){
	if(mirr1 == cfg.planarMirror){
	  ++nplanar;
	}
      }
    }
  }

  if(nplanar >= cfg.minPhotons) return true;
  return false;
  
}

bool isGoodSphericalEvent(hipo::bank RICHring, hipo::bank RICHpart, hipo::bank particles, SkimConfig cfg){
  int nphotons = 0;
  
  for(int jp = 0; jp < RICHpart.getRows(); jp++){
    int layer = RICHpart.getInt("emilay", jp) + 201;
    int compo = RICHpart.getInt("emico", jp);
    int pindex = RICHpart.getInt("pindex", jp);
    double avgetaC_part = RICHpart.getFloat("best_ch",jp);
    //if(layer != cfg.aerolayer) continue;
    
    for(int ip=0; ip<RICHring.getRows(); ++ip) {
      if(RICHring.getInt("pindex",ip) != pindex) continue;
      float etaC = RICHring.getFloat("etaC",ip);
      int use = int(RICHring.getByte("use",ip));
      //if(etaC == 0 || use < 10) continue; // use!=111                                                                                                             
      if(etaC == 0 || use!=111) continue;
      
      auto [nref,mirr1,top,refl] = DecodePhotonPath(
						    RICHring.getInt("layers",ip),
						    RICHring.getInt("compos", ip)
						    );
      
      if(nref == 2){
	int sphmirror = -1;
	int planmirror = -1;
	for(int ir = 0; ir < refl.size(); ir++){
	  //std::cout << "ir " << ir << " refl[ir]: " << refl[ir] << std::endl;
	  if(refl[ir] > 20){
	    sphmirror = refl[ir];
	  }
	  else if(refl[ir] <= 20){
	    planmirror = refl[ir];
	  }
	}
	//if(sphmirror != -1) std::cout << "Photon " << ip << " Sph: " << sphmirror << " Plan: " << planmirror << std::endl;
	if(sphmirror == cfg.sphericalMirror && planmirror == cfg.planarMirror && layer == cfg.aerolayer){
	  nphotons++;
	}
      }
    }
  }
  if(nphotons >= cfg.minPhotons) return true;
  return false;
  
}

bool isGoodThreeReflEvent(hipo::bank RICHring, hipo::bank RICHpart, hipo::bank particles, SkimConfig cfg){
  int nphotons = 0;
  
  for(int jp = 0; jp < RICHpart.getRows(); jp++){
    int layer = RICHpart.getInt("emilay", jp) + 201;
    int compo = RICHpart.getInt("emico", jp);
    int pindex = RICHpart.getInt("pindex", jp);
    double avgetaC_part = RICHpart.getFloat("best_ch",jp);
    //if(layer != cfg.aerolayer) continue;
    
    for(int ip=0; ip<RICHring.getRows(); ++ip) {
      if(RICHring.getInt("pindex",ip) != pindex) continue;
      float etaC = RICHring.getFloat("etaC",ip);
      int use = int(RICHring.getByte("use",ip));
      //if(etaC == 0 || use < 10) continue; // use!=111                                                                                                             
      if(etaC == 0 || use!=111) continue;
      
      auto [nref,mirr1,top,refl] = DecodePhotonPath(
						    RICHring.getInt("layers",ip),
						    RICHring.getInt("compos", ip)
						    );
      
      if(nref == 3){
	int sphmirror = -1;
	int planmirror1 = -1;
	int planmirror2 = -1;
	int nplanar = 0;
	for(int ir = 0; ir < refl.size(); ir++){
	  //std::cout << "ir " << ir << " refl[ir]: " << refl[ir] << std::endl;
	  if(refl[ir] > 20){
	    sphmirror = refl[ir];
	  }
	  else if(refl[ir] <= 20 && nplanar==0){
	    planmirror1 = refl[ir];
	    nplanar++;
	  }
	  else if(refl[ir] <= 20 && nplanar==1){
	    planmirror2 = refl[ir];
	  }
	}
	//if(sphmirror != -1) std::cout << "Photon " << ip << " Sph: " << sphmirror << " Plan: " << planmirror << std::endl;
	if(sphmirror == cfg.sphericalMirror && planmirror1 == cfg.planarMirror1 && planmirror2 == cfg.planarMirror2 && layer == cfg.aerolayer){
	  nphotons++;
	}
      }
    }
  }
  if(nphotons >= cfg.minPhotons) return true;
  return false;
  
}
bool isGoodTwoPlanarReflEvent(hipo::bank RICHring, hipo::bank RICHpart, hipo::bank particles, SkimConfig cfg){
  int nphotons = 0;
  
  for(int jp = 0; jp < RICHpart.getRows(); jp++){
    int layer = RICHpart.getInt("emilay", jp) + 201;
    int compo = RICHpart.getInt("emico", jp);
    int pindex = RICHpart.getInt("pindex", jp);
    double avgetaC_part = RICHpart.getFloat("best_ch",jp);
    //if(layer != cfg.aerolayer) continue;
    
    for(int ip=0; ip<RICHring.getRows(); ++ip) {
      if(RICHring.getInt("pindex",ip) != pindex) continue;
      float etaC = RICHring.getFloat("etaC",ip);
      int use = int(RICHring.getByte("use",ip));
      //if(etaC == 0 || use < 10) continue; // use!=111                                                                                                             
      if(etaC == 0 || use!=111) continue;
      
      auto [nref,mirr1,top,refl] = DecodePhotonPath(
						    RICHring.getInt("layers",ip),
						    RICHring.getInt("compos", ip)
						    );
      
      if(nref == 2){
	int planmirror1 = -1;
	int planmirror2 = -1;
	int nplanar = 0;
	for(int ir = 0; ir < refl.size(); ir++){
	  //std::cout << "ir " << ir << " refl[ir]: " << refl[ir] << std::endl;
	  if(refl[ir] <= 20 && nplanar==0){
	    planmirror1 = refl[ir];
	    nplanar++;
	  }
	  else if(refl[ir] <= 20 && nplanar==1){
	    planmirror2 = refl[ir];
	  }
	}
	//if(sphmirror != -1) std::cout << "Photon " << ip << " Sph: " << sphmirror << " Plan: " << planmirror << std::endl;
	if(planmirror1 == cfg.planarMirror1 && planmirror2 == cfg.planarMirror2 && layer == cfg.aerolayer){
	  nphotons++;
	}
      }
    }
  }
  if(nphotons >= cfg.minPhotons) return true;
  return false;
  
}

bool isGoodClusterEvent(hipo::bank RICHcluster, hipo::bank RICHpart, hipo::bank particles, SkimConfig cfg){
  // should only be used with 1 hadron in the rich
  int nphotons = 0;  
  int layer = RICHpart.getInt("emilay", 0) + 201;
  int compo = RICHpart.getInt("emico", 0);
  int pindex = RICHpart.getInt("pindex", 0);
  int hindex = RICHpart.getInt("hindex", 0);
  
  if(hindex >= 0){
    int pmt = RICHcluster.getShort("pmt",hindex);
    float mchi2 = RICHpart.getFloat("mchi2",0);
    if(PMTSelection(pmt) && (mchi2>0)){
      return true;
    }
  }
  return false;
  
}

void skimDST(const char* file,
             hipo::writer& outWriter,
             const SkimConfig& cfg,
	     CounterStats& stats) {
    int evnum = 0;
    hipo::reader reader;
    reader.open(file);
    hipo::dictionary dict;
    reader.readDictionary(dict);
    double lastAvCh = 0.0;
    int lastebid = -1;
    // Setup banks
    hipo::bank RECevent(dict.getSchema("REC::Event"));
    hipo::bank track(dict.getSchema("REC::Track"));
    hipo::bank traj(dict.getSchema("REC::Traj"));
    hipo::bank particles(dict.getSchema("REC::Particle"));
    hipo::bank RICHpart(dict.getSchema("RICH::Particle"));
    hipo::bank RICHtdc(dict.getSchema("RICH::tdc"));
    hipo::bank RICHring(dict.getSchema("RICH::Ring"));
    hipo::bank RICHhadron(dict.getSchema("RICH::Hadron"));
    hipo::bank RICHcluster(dict.getSchema("RICH::Cluster"));
    hipo::bank RUNconfig(dict.getSchema("RUN::config"));
    hipo::event event;
    std::cout << "Selected topo: " << cfg.topologyType << " Max ev: " << cfg.maxev << " Aero layer: " << cfg.aerolayer <<std::endl;
    std::cout << "Planar: " << cfg.planarMirror << " Sph mirror: " << cfg.sphericalMirror << std::endl;
    std::cout << "Planar1: " << cfg.planarMirror1 << " Planar2: " << cfg.planarMirror2 << std::endl;
    while(reader.next()) {
      //std::cout << "Evnum: " << evnum << std::endl;
        evnum++;
        reader.read(event);
        event.getStructure(particles);
        event.getStructure(track);
        event.getStructure(traj);
        event.getStructure(RUNconfig);
        event.getStructure(RECevent);
        event.getStructure(RICHpart);
        event.getStructure(RICHtdc);
        event.getStructure(RICHring);
        event.getStructure(RICHhadron);
        event.getStructure(RICHcluster);
	
        // Apply optional cuts
        if(cfg.applyDISCut && !isGoodDISEvent(particles)) continue; //{std::cout << "Cut for DIS\n"; continue;}
        if(cfg.applyRichOneCut && !oneInRICH(RICHpart, particles,
					     cfg.validPIDs, -1)) continue; //{stats.nOneInRICHCut++; std::cout << "Cut for one in RICH\n"; continue;}
        
	// count reflections
	// replace this with a function that checks for the exact topology we want
	if(cfg.topologyType == 0 && !isGoodDirectEvent(RICHring,RICHpart,particles,cfg)) continue; //{std::cout << "Cut for direct\n";continue;}
	if(cfg.topologyType == 1 && !isGoodPlanarEvent(RICHring,RICHpart,particles,cfg)) continue; //{std::cout << "Cut for planar\n";continue;}
	if(cfg.topologyType == 2 && !isGoodSphericalEvent(RICHring,RICHpart,particles,cfg)) continue; //{std::cout << "Cut for spherical\n";continue;}
	if(cfg.topologyType == 3 && !isGoodThreeReflEvent(RICHring,RICHpart,particles,cfg)) continue; //{std::cout << "Cut for spherical\n";continue;}
	if(cfg.topologyType == 4 && !isGoodTwoPlanarReflEvent(RICHring,RICHpart,particles,cfg)) continue; //{std::cout << "Cut for spherical\n";continue;}
	if(cfg.topologyType == 5 && !isGoodClusterEvent(RICHcluster,RICHpart,particles,cfg)) continue; //{std::cout << "Cut for spherical\n";continue;}
	if(stats.nAccepted > cfg.maxev) continue;
        ++stats.nAccepted;
        hipo::event outE;
        outE.addStructure(RECevent);
        outE.addStructure(track);
        outE.addStructure(traj);
        outE.addStructure(particles);
        outE.addStructure(RICHpart);
        outE.addStructure(RICHtdc);
        outE.addStructure(RICHring);
        outE.addStructure(RICHhadron);
        outE.addStructure(RICHcluster);
        outE.addStructure(RUNconfig);
        outWriter.addEvent(outE);
    }    
}

int main(int argc, char* argv[]) {
  if(argc < 3) {
        std::cout << "usage: RICH-ana [output file] [input hipo files...] [--config config.json]" << std::endl;
        return 1;
    }
    SkimConfig cfg;
    int argi = 3;
    for(; argi < argc; ++argi) {
      if(std::strcmp(argv[argi], "--config") == 0 && argi+1 < argc) {
	  cfg = loadConfig(argv[++argi]);
      }
      // add other simple flags here if needed
    }
    // before main loop over argv inputs:
    std::vector<std::string> inputs;
    for (int i = 2; i < argc; ++i) {
      std::string a = argv[i];
      if (!a.empty() && a[0] == '@') {
	std::ifstream fin(a.substr(1));
	std::string line;
	while (std::getline(fin, line)) {
	  if (!line.empty()) inputs.push_back(line);
	}
      } else if (a.rfind("--",0) == 0) {
	break;
	// flags — handle as you do now
      } else {
	inputs.push_back(a);
      }
    }
    // then open each from `inputs`
    hipo::reader dum;
    dum.open(inputs[0].c_str());
    hipo::dictionary dict;
    dum.readDictionary(dict);
    hipo::writer writer;
    for(auto name: {"REC::Event","REC::Particle","REC::Track","REC::Traj",
                    "RICH::Particle","RICH::Ring","RICH::Hadron","RICH::tdc","RUN::config",
		    "RICH::Cluster"
      }){
        writer.getDictionary().addSchema(dict.getSchema(name));
    }
    writer.open(argv[1]);
    hAvgCher = new TH1F(
			"hAvgCher",
			"Average Cherenkov Angle;#theta_{C} [rad];Counts",
			100, 0.2, 0.4
			);

    CounterStats stats(cfg);
    //for(int i=2; i<argc; ++i) {
    for(int i=0; i<inputs.size(); ++i) {
      std::string arg = inputs[i];
      //if(arg.rfind("--",0) == 0) break; // stop at options
      if(stats.nAccepted >= cfg.maxev) {std::cout<< "Skipping file, already full\n"; continue;}
      
      if(i > 10 && stats.nAccepted == 0){
	std::cout << "Already read 10 files and no events kept, something probably wrong. Ending \n"; break;
      }
      std::cout << "Processing: "<< arg << std::endl;
      skimDST(arg.c_str(), writer, cfg, stats);
    }

    std::cout << "Total events accepted:      " << stats.nAccepted       << "\n"
         << "Total direct events cut:    " << stats.nCutDirect      << "\n"
         << "Total oneInRICH cuts:       " << stats.nOneInRICHCut  << "\n"
         << "Total DIS layer cuts:       " << stats.nLayerCut      << "\n"
	 << "Total Mean angle cuts:       " << stats.nCherCut      << "\n"
         << "Total per‑tile cuts:        " << stats.nLayerCountCut << "\n"
         << "Total mirror count cuts:    " << stats.nMirrorCut     << "\n"
         << "Total photon‑count cuts:    " << stats.nPhotonCountCut<< std::endl;
    std::cout << "final mirror counts: " << std::endl;
    for(int i = 0; i < stats.planarCounters.size(); i++){
      std::cout << i+1 << ": " << stats.planarCounters[i] << std::endl;
    }
    std::cout << "final spherical mirror counts: " << std::endl;
    for(int i = 0; i < stats.sphericalCounters.size(); i++){
      std::cout << i+1 << ": " << stats.sphericalCounters[i] << std::endl;
    }
    writer.close();

    TCanvas c("c","c",800,600);
    hAvgCher->Draw();
    c.SaveAs("log/plots/avgCherAngle.pdf");

    return 0;
}




