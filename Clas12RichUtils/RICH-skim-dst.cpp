#include "RICH-skim-dst.h"
using namespace std;

int strToInt(const char* string){
  stringstream sstream;
  sstream << string;
  int sint;
  sstream >> sint;
  return sint;
}

// skim for: Good DIS electron && 1 hadron in either RICH
void skimDST(const char* file, hipo::writer &outWriter, int clustercut){

  
  hipo::reader  reader;
  reader.open(file);
  hipo::dictionary factory;
  reader.readDictionary(factory);
  
  hipo::bank RECevent(factory.getSchema("REC::Event"));
  hipo::bank track(factory.getSchema("REC::Track"));
  hipo::bank traj(factory.getSchema("REC::Traj"));
  hipo::bank particles(factory.getSchema("REC::Particle"));
  hipo::bank RICHpart(factory.getSchema("RICH::Particle"));
  hipo::bank RICHtdc(factory.getSchema("RICH::tdc"));
  hipo::bank RICHcluster(factory.getSchema("RICH::Cluster"));
  hipo::bank RICHring(factory.getSchema("RICH::Ring"));
  hipo::bank RUNconfig(factory.getSchema("RUN::config"));
  
  hipo::event event;
  
  int nev = 0;
  int nNoRich = 0;
  int nAccepted = 0;
  int nMax = 100000000;
  while(reader.next()){
    if(nAccepted >= nMax) break;
    reader.read(event);
    
    nev++;
    event.getStructure(particles);
    event.getStructure(track);
    event.getStructure(traj);
    event.getStructure(RUNconfig);
    event.getStructure(RECevent);
    
    event.getStructure(RICHpart);
    event.getStructure(RICHtdc);
    event.getStructure(RICHcluster);
    event.getStructure(RICHring);
    
    if(particles.getRows()==0) continue; // no reconstructed particles    
    if(!isGoodDISEvent(particles)) continue; // no good reconstructed electron
    if(!oneInRICH(RICHpart,particles,{11},-1)) continue; // add some check for PID?
    if(clustercut){
      if(!PMTSelection(RICHpart.getShort("hindex",0), RICHcluster)) continue;
    }
    //if(!nPlanarPhotonCut(RICHring,3)) continue;
    nAccepted++;
    hipo::event outEvent;
    outEvent.addStructure(RECevent);
    outEvent.addStructure(track);
    outEvent.addStructure(traj);
    outEvent.addStructure(particles);
    outEvent.addStructure(RICHpart);
    outEvent.addStructure(RICHtdc);
    outEvent.addStructure(RICHcluster);
    outEvent.addStructure(RICHring);
    outEvent.addStructure(RUNconfig);
    outWriter.addEvent(outEvent);        
  }
  return;
}

int main(int argc, char* argv[]){
  if(argc < 2){
    cout << "usage: RICH-ana [output file name] [1: place cluster cut; 0: no cluster cut] [list of hipo files]\n";
    return 1;
  }
  int clustercut = strToInt(argv[2]);
  hipo::reader  dummy_reader;
  dummy_reader.open(argv[3]);
  hipo::dictionary factory;
  dummy_reader.readDictionary(factory);

  hipo::writer writer;
  cout << "adding scheam to writer" << endl;
  writer.getDictionary().addSchema(factory.getSchema("REC::Event"));
  writer.getDictionary().addSchema(factory.getSchema("REC::Particle"));
  writer.getDictionary().addSchema(factory.getSchema("REC::Track"));
  writer.getDictionary().addSchema(factory.getSchema("REC::Traj"));
  writer.getDictionary().addSchema(factory.getSchema("RICH::Cluster"));
  writer.getDictionary().addSchema(factory.getSchema("RICH::Particle"));
  writer.getDictionary().addSchema(factory.getSchema("RICH::tdc"));
  writer.getDictionary().addSchema(factory.getSchema("RUN::config"));
  writer.open(argv[1]);

  //hipo::writer  writer;
  //cout << "opening file: " << argv[1] << endl;
  //writer.open(argv[1]);
  
  for(int i = 3; i < argc; i++){
    cout << "reading file " << argv[i] << endl;
    skimDST(argv[i], writer, clustercut);
    
  }
  writer.close();
  return 0;
}
