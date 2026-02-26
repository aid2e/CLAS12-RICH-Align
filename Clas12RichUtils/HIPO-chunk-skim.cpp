// HIPO-chunk-skim.cpp
#include "HIPO-chunk-skim.h"
#include <iostream>
#include <vector>
#include <string>


int main(int argc, char* argv[]) {
    if (argc < 5) {
        std::cerr << "Usage: " << argv[0]
                  << " <output_prefix> <max_events> <chunk_size> <in1.hipo> [in2.hipo ...]\n";
        return 1;
    }

    // parse arguments
    std::string outputPrefix = argv[1];
    size_t      maxEvents     = std::stoul(argv[2]);   // e.g. 500000
    size_t      chunkSize     = std::stoul(argv[3]);   // e.g. 50000

    std::vector<std::string> inputFiles;
    for (int i = 4; i < argc; ++i) {
        inputFiles.push_back(argv[i]);
    }

    // open first input to grab the dictionary
    hipo::reader reader;
    reader.open(inputFiles[0].c_str());
    hipo::dictionary dict;
    reader.readDictionary(dict);

    // set up writer with the same schemas
    hipo::writer writer;
    for (auto const& name : {
         "REC::Event", "REC::Particle", "REC::Track", "REC::Traj",
         "RICH::Particle",// "RICH::Ring",
	 //"RICH::Hadron",
	 "RICH::tdc",
         "RUN::config"
    }) {
        writer.getDictionary().addSchema(dict.getSchema(name));
    }

    // prepare banks once
    hipo::bank RECevent (dict.getSchema("REC::Event"));
    hipo::bank track    (dict.getSchema("REC::Track"));
    hipo::bank traj     (dict.getSchema("REC::Traj"));
    hipo::bank particles(dict.getSchema("REC::Particle"));
    hipo::bank RICHpart (dict.getSchema("RICH::Particle"));
    hipo::bank RICHtdc  (dict.getSchema("RICH::tdc"));
    //hipo::bank RICHring (dict.getSchema("RICH::Ring"));
    //hipo::bank RICHhad  (dict.getSchema("RICH::Hadron"));
    hipo::bank RUNcfg   (dict.getSchema("RUN::config"));
    hipo::event event;

    // chunk bookkeeping
    size_t totalEvents   = 0;
    size_t eventsInChunk = 0;
    int    chunkIndex    = 1;

    // lambda to open (and on rollover close) chunk files
    auto openNewChunk = [&]() {
        if (chunkIndex > 1) {
            writer.close();
        }
        std::string fname = outputPrefix + "_" + std::to_string(chunkIndex) + ".hipo";
        std::cout << "[chunk] open ➔ " << fname << "\n";
        writer.open(fname.c_str());
    };

    // open the very first chunk
    openNewChunk();

    // loop over all input files
    for (auto const& file : inputFiles) {
        // reopen reader on each file (reuses same dict/banks)
        reader.open(file.c_str());

        while (reader.next() && (totalEvents < maxEvents || maxEvents == 0)) {
            reader.read(event);

            // grab the structures you care about
            event.getStructure(RECevent);
            event.getStructure(track);
            event.getStructure(traj);
            event.getStructure(particles);
            event.getStructure(RICHpart);
            event.getStructure(RICHtdc);
            //event.getStructure(RICHring);
            //event.getStructure(RICHhad);
            event.getStructure(RUNcfg);

            // build a new event containing only those
            hipo::event outE;
            outE.addStructure(RECevent);
            outE.addStructure(track);
            outE.addStructure(traj);
            outE.addStructure(particles);
            outE.addStructure(RICHpart);
            outE.addStructure(RICHtdc);
            //outE.addStructure(RICHring);
            //outE.addStructure(RICHhad);
            outE.addStructure(RUNcfg);
            writer.addEvent(outE);

            ++totalEvents;
            ++eventsInChunk;

            // when chunk is full, start the next one
            if (eventsInChunk >= chunkSize && (totalEvents < maxEvents || maxEvents == 0)) {
                eventsInChunk = 0;
                ++chunkIndex;
                openNewChunk();
            }
        }
        if (totalEvents >= maxEvents) break;
    }

    // final close
    writer.close();
    std::cout << "Finished: wrote " << totalEvents
              << " events into " << chunkIndex << " files.\n";
    return 0;
}
