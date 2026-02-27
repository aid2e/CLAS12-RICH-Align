
#include "RICH-hipo-to-tree-mchi2.h"
#include "RICH-reflection-tools.h"


// Produce tree from hipo files for further analysis with
// track kinematics and track-cluster matching chi2 (mchi2)

void fillTree(const char* file, RICHOutput& outobj){

  
  hipo::reader  reader;
  reader.open(file);
  hipo::dictionary factory;
  reader.readDictionary(factory);
  
  hipo::bank particles(factory.getSchema("REC::Particle"));
  hipo::bank RICHring(factory.getSchema("RICH::Ring"));
  hipo::bank RICHhadron(factory.getSchema("RICH::Hadron"));
  hipo::bank RICHpart(factory.getSchema("RICH::Particle")); 
  hipo::bank RICHcluster(factory.getSchema("RICH::Cluster")); 
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
    event.getStructure(RICHcluster);
    event.getStructure(traj);
    
    if(particles.getRows()==0) continue; // no reconstructed particles    
    
    // loop over RICH hadrons
    for(int ir = 0; ir < RICHpart.getRows(); ir++){
      int pindex = RICHpart.getInt("pindex",ir);
      int ebpid = particles.getInt("pid",pindex);
      
      double px = particles.getFloat("px",pindex);
      double py = particles.getFloat("py",pindex);
      double pz = particles.getFloat("pz",pindex);
      double p = sqrt(px*px+py*py+pz*pz);

      TVector3 vec(px,py,pz);
      double theta = vec.Theta();
      double phi = vec.Phi();

      double mass = getMass(ebpid); // assume mass from ebpid
      double beta = p/(sqrt(p*p+mass*mass));

      double mchi2 = RICHpart.getFloat("mchi2",ir);
      int clusterindex = RICHpart.getShort("hindex", ir);
      int clusterpmt = RICHcluster.getShort("pmt", clusterindex);
      int sector = RICHcluster.getShort("sector", clusterindex);
      
      int aerolayer = RICHpart.getInt("emilay",ir); // check indexing of these
      int aerocomp = RICHpart.getInt("emico",ir);
      outobj.Fill(aerolayer,aerocomp,ebpid,clusterpmt,sector,mchi2,
		  beta, p, theta, phi
		  );
      
      
    }
  }
}

int main(int argc, char* argv[]){
  if(argc < 2){
    cout << "usage: RICH-hipo-to-tree-mchi2 [output file name] [list of hipo files]\n";
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
