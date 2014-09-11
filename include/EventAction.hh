//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
/// \file electromagnetic/TestEm1/include/EventAction.hh
/// \brief Definition of the EventAction class
//
// $Id: EventAction.hh 76293 2013-11-08 13:11:23Z gcosmo $
// 

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#ifndef EventAction_h
#define EventAction_h 1

#include "G4UserEventAction.hh"
#include "globals.hh"

#include <set>

// Maximum number of pixels to allocate memory for.
// Ideally we could just receive this information from
// the config file and dynamically allocate,
// but it's a big pain in the ass to get the
// DetectorConstruction to communicate with this object :(
#define MAX_PIX 1000

class EventMessenger;

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

class EventAction : public G4UserEventAction
{
  public:
    EventAction();
   ~EventAction();

  public:
    virtual void BeginOfEventAction(const G4Event*);
    virtual void   EndOfEventAction(const G4Event*);
    
    void AddEdep(G4double Edep)    {fTotalEnergyDeposit += Edep;};      
    G4double GetEnergyDeposit()    {return fTotalEnergyDeposit;};    
    void AddPixHit(G4double Edep, int x, int y);

    void SetMinPixOut(G4double newval) { fMinPixOut = newval; };
    void SetMinPixEvent(G4double newval) { fMinPixEvent = newval; };
    void SetNPixEvent(G4int newval) { fNPixEvent = newval; };
    
  private:
    G4double fTotalEnergyDeposit;   
    G4double pix_hits[MAX_PIX][MAX_PIX];

    bool fHasHit;

    std::set<std::pair<int, int> > fPixAboveThreshold;

    G4double fMinPixOut;
    G4double fMinPixEvent;
    G4int    fNPixEvent;

    EventMessenger* fEventMessenger;
};

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#endif

    
