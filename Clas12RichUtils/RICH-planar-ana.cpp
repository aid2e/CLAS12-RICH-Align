
#include "RICH-planar-ana.h"
#include "RICH-reflection-tools.h"
void fillTree(const char* file, RICHOutput& outobj){
  
  hipo::reader  reader;
  reader.open(file);
  hipo::dictionary factory;
  reader.readDictionary(factory);
  
  hipo::bank particles(factory.getSchema("REC::Particle"));
  hipo::bank RICHring(factory.getSchema("RICH::Ring"));
  hipo::bank RICHpart(factory.getSchema("RICH::Particle"));
  
  hipo::event event;
  
  int nev = 0;
  int nNoRich = 0;
  while(reader.next()==true){
    reader.read(event);
    
    nev++;
    event.getStructure(particles);
    event.getStructure(RICHring);    
    event.getStructure(RICHpart);
    
    if(particles.getRows()==0) continue; // no reconstructed particles    
    
    // loop over RICH hadrons
    for(int ir = 0; ir < RICHpart.getRows(); ir++){
      int pindex = RICHpart.getInt("pindex",ir);
      int ebpid = particles.getInt("pid",pindex);
      
      if(ebpid!=11) continue; // using only electrons for now
      // TODO: apply better improved electron PID cuts
      
      double px = particles.getFloat("px",pindex);
      double py = particles.getFloat("py",pindex);
      double pz = particles.getFloat("pz",pindex);
      double p = sqrt(px*px+py*py+pz*pz);
      
      double mass = getMass(ebpid); // assume mass from ebpid
      double beta = p/(sqrt(p*p+mass*mass));
      
      int aerolayer = RICHpart.getInt("emilay",ir);
      int aerocomp = RICHpart.getInt("emico",ir);
      
      double nAero = getnAero(aerolayer,aerocomp);
      
      double chExpected = acos(1/(nAero*beta))*1000;
      // loop over photons
      for(int ip = 0; ip < RICHring.getRows(); ip++){
	// if photon from same track as current RICHpart
	if( RICHring.getInt("pindex",ip) == pindex){
	  double chRec = RICHring.getFloat("etaC",ip)*1000; // to mrad
	  double dtheta = abs(chRec-chExpected);
	  if(chRec != 0){
	    int ringlayers = RICHring.getInt("layers",ip);
	    int ringcompos = RICHring.getInt("compos",ip);
	    std::tuple<int,int,int> path = DecodePhotonPath(ringlayers,ringcompos);	    
	    if (std::get<0>(path) == 1){
	      //cout << "mirror num: " << std::get<1>(path) << endl;
	      //cout << "chExpected: " << chExpected << " chReco: " << chRec << endl;
	      outobj.Fill(std::get<1>(path),dtheta);
	    }
	  }
	}
      }
      
    }
  }
}

int main(int argc, char* argv[]){
  if(argc < 2){
    cout << "usage: RICH-ana [output file name] [list of hipo files]\n";
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
