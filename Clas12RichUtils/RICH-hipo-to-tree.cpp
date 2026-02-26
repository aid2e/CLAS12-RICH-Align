
#include "RICH-hipo-to-tree.h"
#include "RICH-reflection-tools.h"


// Produce tree from hipo files for further analysis with
// track kinematics, aerogel layer/tile information,
// individual photon reconstructed Cherenkov angle,
// event builder PID, other relevant quantities.

void fillTree(const char* file, RICHOutput& outobj){

  
  hipo::reader  reader;
  reader.open(file);
  hipo::dictionary factory;
  reader.readDictionary(factory);
  
  hipo::bank particles(factory.getSchema("REC::Particle"));
  hipo::bank RICHring(factory.getSchema("RICH::Ring"));
  hipo::bank RICHhadron(factory.getSchema("RICH::Hadron"));
  hipo::bank RICHpart(factory.getSchema("RICH::Particle")); 
  hipo::bank traj(factory.getSchema("REC::Traj"));
 
  hipo::event event;
  
  int nev = 0;
  int nNoRich = 0;
  while(reader.next()==true){
    reader.read(event);

    nev++;
    if(nev%100000 == 0) {cout << "on event " << nev << endl;}
    event.getStructure(particles);
    event.getStructure(RICHring);    
    event.getStructure(RICHhadron);    
    event.getStructure(RICHpart);
    event.getStructure(traj);
    
    if(particles.getRows()==0) continue; // no reconstructed particles    
    
    // loop over RICH hadrons
    for(int ir = 0; ir < RICHpart.getRows(); ir++){
      int pindex = RICHpart.getInt("pindex",ir);
      int ebpid = particles.getInt("pid",pindex);
      int RICHid = RICHpart.getInt("best_PID",ir);
      
      double px = particles.getFloat("px",pindex);
      double py = particles.getFloat("py",pindex);
      double pz = particles.getFloat("pz",pindex);
      double p = sqrt(px*px+py*py+pz*pz);

      TVector3 vec(px,py,pz);
      double theta = vec.Theta();
      double phi = vec.Phi();

      double mass = getMass(ebpid); // assume mass from ebpid
      double beta = p/(sqrt(p*p+mass*mass));
      
      int aerolayer = RICHpart.getInt("emilay",ir); // check indexing of these
      int aerocomp = RICHpart.getInt("emico",ir);
      int sector = -1; // set later in photon loop, when we get access to sector info...
      
      std::vector<double> chRecVec;
      std::vector<int> topologyVec;
      std::vector<int> sphericalVec;
      std::vector<int> planarVec;
      std::vector<int> nRefVec;
      // loop over photons
      for(int ip = 0; ip < RICHring.getRows(); ip++){
	// if photon from same track as current RICHpart
	if( RICHring.getInt("pindex",ip) == pindex){
	  if(sector == -1) sector = RICHring.getByte("sector",ip);
	  
	  double chRec = RICHring.getFloat("etaC",ip);
	  int use = int(RICHring.getByte("use",ip));
	  
	  if(chRec != 0 && use == 111){ // TODO: 110 or 111? 111 applies some (loose) theta_cher cuts
	    int ringlayers = RICHring.getInt("layers",ip);
	    int ringcompos = RICHring.getInt("compos",ip);
	    auto [nref,_r1,top,refl] = DecodePhotonPath(ringlayers,ringcompos);
	    
	    if (nref <= 2){ // max one spherical + one planar (for now)
	      chRecVec.push_back(chRec);
	      topologyVec.push_back(_r1);
	      nRefVec.push_back(nref);
	      if(nref == 0){
		planarVec.push_back(-1); // none
		sphericalVec.push_back(-1); // none
	      }
	      if(nref == 1){
		planarVec.push_back(refl[0]);
		sphericalVec.push_back(-1); // none
	      }
	      if(nref == 2){
		planarVec.push_back(refl[1]); // from topology
		sphericalVec.push_back(refl[0]);
	      }
	    }
	  }
	}
      }
      double emix = 0;
      double emiy = 0;
      double emiz = 0;
      for(int ih = 0; ih < RICHhadron.getRows(); ih++){
	int hpindex = RICHhadron.getInt("pindex",ih);
	if(hpindex == pindex){
	  emix = RICHhadron.getFloat("traced_emix",ih);
	  emiy = RICHhadron.getFloat("traced_emiy",ih);
	  emiz = RICHhadron.getFloat("traced_emiz",ih);
	}
      }
      double trackx, tracky, trackz; // unit vector of track projection at RICH 
      for(int ij = 0; ij < traj.getRows(); ij++){
	if(traj.getShort("pindex",ij)==pindex){
	  if(traj.getByte("detector",ij)==18){ //RICH
	    if(traj.getByte("layer",ij)==2 || traj.getByte("layer",ij)==3 || traj.getByte("layer",ij)==4){ //aerogel
	      trackx = traj.getFloat("cx",ij);
	      tracky = traj.getFloat("cy",ij);
	      trackz = traj.getFloat("cz",ij);
	    }
	  }
	}
      }
      
      outobj.Fill(sector,aerolayer,aerocomp,ebpid,chRecVec,topologyVec,
		  beta, p, theta, phi, emix, emiy, emiz,
		  trackx, tracky, trackz, RICHid,
		  planarVec, sphericalVec, nRefVec
		  );
      
      
    }
  }
}

int main(int argc, char* argv[]){
  if(argc < 2){
    cout << "usage: RICH-hipo-to-tree [output file name] [list of hipo files]\n";
    return 1;
  }
  
  RICHOutput output;
  cout << "starting" << endl;
  
  for(int i = 2; i < argc; i++){
    cout << "reading file " << argv[i] << endl;
    fillTree(argv[i], output);
    
  }
  
  output.Write(argv[1]);
  return 0;
}
