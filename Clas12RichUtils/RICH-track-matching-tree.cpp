
#include "RICH-track-matching-tree.h"

void fillTree(const char* file, RICHTree& tree){
  
  hipo::reader  reader;
  reader.open(file);
  hipo::dictionary factory;
  reader.readDictionary(factory);
  
  hipo::bank particles(factory.getSchema("REC::Particle"));
  hipo::bank RICHcluster(factory.getSchema("RICH::Cluster"));
  hipo::bank RICHhadron(factory.getSchema("RICH::Hadron"));
  hipo::bank RICHpart(factory.getSchema("RICH::Particle"));
  
  hipo::event event;
  
  int nev = 0;
  int nNoRich = 0;
  while(reader.next()==true){
    reader.read(event);

    nev++;
    event.getStructure(particles);
    event.getStructure(RICHcluster);
    event.getStructure(RICHhadron);
    event.getStructure(RICHpart);
    
    if(particles.getRows()==0) continue; // no reconstructed particles    
    if(!isGoodDISEvent(particles)) continue; // no reconstructed electron

    // loop over RICH hadrons
    for(int ir = 0; ir < RICHpart.getRows(); ir++){
      //if(RICHhadron.getRows() == 0){    
      double mchi2_val = RICHpart.getFloat("mchi2", ir);      
      tree.setmchi2(mchi2_val);      
      tree.Fill();      
    }
  }
}

int main(int argc, char* argv[]){
  if(argc < 2){
    cout << "usage: RICH-ana [output file name] [list of hipo files]\n";
    return 1;
  }  
  
  RICHTree treeobj;
  cout << "starting" << endl;
  
  for(int i = 2; i < argc; i++){
    cout << "reading file " << argv[i] << endl;
    fillTree(argv[i], treeobj);
    
  }
  
  treeobj.Write(argv[1]);
  return 0;
}
