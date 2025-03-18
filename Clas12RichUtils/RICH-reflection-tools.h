using namespace std;

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
