import os
import sys
#print(sys.path)
PATH_TO_MODULE = "/home/anovak/BTVNanoCommissioning/PocketCoffea"
if not PATH_TO_MODULE in sys.path:
    sys.path.append(PATH_TO_MODULE)

import tarfile
import json

import numpy as np
import awkward as ak

import coffea
from coffea import processor, lookup_tools, hist
from coffea.util import load
from coffea.processor import dict_accumulator, defaultdict_accumulator
from coffea.lumi_tools import LumiMask #, LumiData
from coffea.analysis_tools import PackedSelection, Weights

import correctionlib

from PocketCoffea.lib.triggers import get_trigger_mask
from PocketCoffea.lib.objects import jet_correction, lepton_selection, lepton_selection_noniso, jet_selection, btagging, get_dilepton
from PocketCoffea.lib.pileup import sf_pileup_reweight
from PocketCoffea.lib.scale_factors import sf_ele_reco, sf_ele_id, sf_mu
from PocketCoffea.lib.fill import fill_histograms_object_with_flavor
from PocketCoffea.parameters.triggers import triggers
from PocketCoffea.parameters.btag import btag
from PocketCoffea.parameters.jec import JECversions, JERversions
from PocketCoffea.parameters.event_flags import event_flags, event_flags_data
from PocketCoffea.parameters.lumi import lumi, goldenJSON
from PocketCoffea.parameters.samples import samples_info
from PocketCoffea.parameters.allhistograms import histogram_settings

from lib.sv import get_nsv, get_sv_in_jet

class fatjetBaseProcessor(processor.ProcessorABC):
    def __init__(self, cfg) -> None:
        # Read required cuts and histograms from config file
        self.cfg = cfg

        # Save histogram settings of the required histograms
        self._variables = self.cfg.variables
        self._variables2d = self.cfg.variables2d

        ### Cuts
        # The definition of the cuts in the analysis is hierarchical.
        # 1) a list of *skim* functions is applied on bare NanoAOD, with no object preselection or correction.
        #   Triggers are also applied there. 
        # 2) Objects are corrected and selected and a list of *preselection* cuts are applied to skim the dataset.
        # 3) A list of cut function is applied and the masks are kept in memory to defined later "categories"
        self._skim = self.cfg.skim
        self._preselections  = self.cfg.preselections
        self._cuts = self.cfg.cut_functions
        self._categories = self.cfg.categories
        self.define_pt_reweighting_maps()
        ### Define PackedSelector to save per-event cuts and dictionary of selections
        # The skim mask is applied on baseline nanoaod before any object is corrected
        self._skim_masks = PackedSelection()
        # The preselection mask is applied after the objects have been corrected
        self._preselection_masks = PackedSelection()
        # After the preselections more cuts are defined and combined in categories.
        # These cuts are applied only for outputs, so they cohexists in the form of masks
        self._cuts_masks = PackedSelection()

        # Pt reweighting
        self._pt_reweighting = True
        
        # Accumulators for the output
        self._accum_dict = {}
        self._hist_dict = {}
        self._hist2d_dict = {}
        self._sumw_dict = {
            "sum_genweights": defaultdict_accumulator(float),
        }
        self._accum_dict.update(self._sumw_dict)
        # Accumulator with number of events passing each category for each sample
        self._cutflow_dict =   {cat: defaultdict_accumulator(int) for cat in self._categories}
        self._cutflow_dict["initial"] = defaultdict_accumulator(int)
        self._cutflow_dict["skim"] = defaultdict_accumulator(int)
        self._cutflow_dict["presel"] = defaultdict_accumulator(int)
        self._accum_dict["cutflow"] = dict_accumulator(self._cutflow_dict)
        
        # Accumulator with sum of weights of the events passing each category for each sample
        self._sumw_weighted_dict =   {cat: defaultdict_accumulator(float) for cat in self._categories}
        self._accum_dict["sumw"] = dict_accumulator(self._sumw_weighted_dict)

        # Accumulator with seed number used for the stochastic smearing, for each processed chunk
        self._seed_dict = {"seed_chunk" : processor.defaultdict_accumulator(int)}
        self._seed_fatjet_dict = {"seed_fatjet_chunk" : processor.defaultdict_accumulator(int)}
        self._accum_dict.update(self._seed_dict)
        self._accum_dict.update(self._seed_fatjet_dict)

        #for var in self._vars_to_plot.keys():
        #       self._accumulator.add(processor.dict_accumulator({var : processor.column_accumulator(np.array([]))}))

        # Define axes
        self._sample_axis = hist.Cat("sample", "Sample")
        self._cat_axis    = hist.Cat("cat", "Cat")
        self._year_axis   = hist.Cat("year", "Year")
        self._flavor_axis   = hist.Cat("flavor", "Flavor")

        # Create histogram accumulators
        for var_name in self._variables.keys():
            if var_name.startswith('n'):
                field = var_name
            else:
                obj, field = (var_name.split('_')[0], '_'.join(var_name.split('_')[1:]))
            variable_axis = hist.Bin( field, self._variables[var_name]['xlabel'],
                                      **self._variables[var_name]['binning'] )
            self._hist_dict[f'hist_{var_name}'] = hist.Hist("$N_{events}$", self._sample_axis,
                                                            self._cat_axis, self._year_axis, self._flavor_axis, variable_axis)
        for hist2d_name in self._variables2d.keys():
            print("AAA", hist2d_name)
            varname_x = list(self._variables2d[hist2d_name].keys())[0]
            varname_y = list(self._variables2d[hist2d_name].keys())[1]
            variable_x_axis = hist.Bin(varname_x, self._variables2d[hist2d_name][varname_x]['xlabel'],
                                       **self._variables2d[hist2d_name][varname_x]['binning'] )
            variable_y_axis = hist.Bin(varname_y, self._variables2d[hist2d_name][varname_y]['ylabel'],
                                       **self._variables2d[hist2d_name][varname_y]['binning'] )
            self._hist2d_dict[f'hist2d_{hist2d_name}'] = hist.Hist("$N_{events}$", self._sample_axis, self._cat_axis,
                                                                   self._year_axis, self._flavor_axis, variable_x_axis, variable_y_axis)
            
        self._accum_dict.update(self._hist_dict)
        self._accum_dict.update(self._hist2d_dict)

        self.nobj_hists = [histname for histname in self._hist_dict.keys() if histname.lstrip('hist_').startswith('n') and not 'nevts' in histname]
        self.muon_hists = [histname for histname in self._hist_dict.keys() if 'muon' in histname and not histname in self.nobj_hists]
        self.electron_hists = [histname for histname in self._hist_dict.keys() if 'electron' in histname and not histname in self.nobj_hists]
        self.jet_hists = [histname for histname in self._hist_dict.keys() if 'jet' in histname and not 'fatjet' in histname and not histname in self.nobj_hists]
        self.fatjet_hists = [histname for histname in self._hist_dict.keys() if 'fatjet' in histname and not histname in self.nobj_hists]
        self.sv_hists = [histname for histname in self._hist_dict.keys() if 'sv' in histname and not histname in self.nobj_hists]
        self.nd_hists = [histname for histname in self._hist2d_dict.keys()]
        # The final accumulator dictionary is built when the accumulator() property is called for the first time.
        # Doing so, subclasses can add additional context to the self._accum_dict. 
        # self._accumulator = dict_accumulator(self._accum_dict)
        self._accumulator = None
        
    @property
    def accumulator(self):
        ''' The accumulator instance of the processor is not built in the constructor directly because sub-classes
        can add more accumulators to the self._accum_dict definition.
        When the accumulator() property if then accessed the dict_accumulator is built.'''
        if not self._accumulator:
            self._accumulator = dict_accumulator(self._accum_dict)
        return self._accumulator

    def define_pt_reweighting_maps(self):
        self._pt_reweighting_map = {}
        for category in self._categories.keys():
            if 'msd40' in category:
                self._pt_reweighting_map[category] = 'pt350msd40'
            elif 'msd60' in category:
                self._pt_reweighting_map[category] = 'pt350msd60'
            elif 'msd80' in category:
                self._pt_reweighting_map[category] = 'pt350msd80'
            elif 'msd100' in category:
                self._pt_reweighting_map[category] = 'pt350msd100'
            elif category == 'inclusive':
                self._pt_reweighting_map[category] = 'inclusive'
            else:
                sys.exit(f"The association of the category '{category}' to a pt reweighting key is ambiguous")

    def add_additional_histograms(self, histograms_dict):
        '''Helper function to add additional histograms to the dict_accumulator.
        Usually useful for derived classes to include the definition of custom histograms '''
        for k,h in histograms_dict.items():
            if k in self._accum_dict:
                raise Exception(f"You are trying to overwrite an already defined histogram {k}!")
            else:
                self._accum_dict[k] = h
        
    @property
    def nevents(self):
        '''The current number of events in the chunk is computed with a property'''
        return ak.count(self.events.event, axis=0)

    def get_histogram(self, name):
        if name in self.output:
            return self.output[name]
        else:
            raise Exception("Missing histogram: ", name)
    
    # Function to load year-dependent parameters
    def load_metadata(self):
        self._dataset = self.events.metadata["dataset"]
        self._sample = self.events.metadata["sample"]
        self._year = self.events.metadata["year"]
        self._triggers = triggers[self.cfg.finalstate][self._year]
        self._btag = btag[self._year]
        self._isMC = 'genWeight' in self.events.fields
        # JEC
        self._JECversion = JECversions[self._year]['MC' if self._isMC else 'Data']
        self._JERversion = JERversions[self._year]['MC' if self._isMC else 'Data']
        self._goldenJSON = goldenJSON[self._year]

    # Function that computes the trigger masks and save it in the PackedSelector
    def apply_triggers(self):
        # Trigger logic is included in the preselection mask
        mask = get_trigger_mask(self.events, self._triggers, self.cfg.finalstate)
        self._skim_masks.add('trigger', get_trigger_mask(self.events, self._triggers, self.cfg.finalstate))


    # Function to apply flags and lumi mask
    def skim_events(self):
        # In the initial skimming we apply METfilters, PV requirement, lumimask(for DATA), the trigger,
        # and user-defined skimming function.
        # BE CAREFUL: the skimming is done before any object preselection and cleaning
        mask_flags = np.ones(self.nEvents_initial, dtype=np.bool)
        flags = event_flags[self._year]
        if not self._isMC:
            flags += event_flags_data[self._year]
        for flag in flags:
            mask_flags = getattr(self.events.Flag, flag)
        self._skim_masks.add("event_flags", mask_flags)
        
        # Primary vertex requirement
        self._skim_masks.add("PVgood", self.events.PV.npvsGood > 0)

        # In case of data: check if event is in golden lumi file
        if not self._isMC:
            #mask_lumi = lumimask(self.events.run, self.events.luminosityBlock)
            mask_lumi = LumiMask(self._goldenJSON)(self.events.run, self.events.luminosityBlock)
            self._skim_masks.add("lumi_golden", mask_lumi)

        for skim_func in self._skim:
            # Apply the skim function and add it to the mask
            mask = skim_func.get_mask(self.events, year=self._year, sample=self._sample, btag=self._btag, isMC=self._isMC)
            self._skim_masks.add(skim_func.id, mask)
            
        # Finally we skim the events and count them
        self.events = self.events[self._skim_masks.all(*self._skim_masks.names)]
        self.nEvents_after_skim = self.nevents
        self.output['cutflow']['skim'][self._sample] += self.nEvents_after_skim
        self.has_events = self.nEvents_after_skim > 0
        
    def apply_JERC(self, JER=True, verbose=False, *args, **kwargs):
        if not self._isMC: return
        if int(self._year) > 2018:
            sys.exit("Warning: Run 3 JEC are not implemented yet.")
        if JER:
            self.events.Jet, seed_dict = jet_correction(self.events, "Jet", "AK4PFchs", self._year, self._JECversion, self._JERversion, verbose=verbose)
            self.events.FatJet, seed_fatjet_dict = jet_correction(self.events, "FatJet", "AK8PFPuppi", self._year, self._JECversion, self._JERversion, verbose=verbose)
            self.output['seed_chunk'].update(seed_dict)
            self.output['seed_fatjet_chunk'].update(seed_fatjet_dict)
        else:
            self.events.Jet = jet_correction(self.events, "Jet", "AK4PFchs", self._year, self._JECversion, verbose=verbose)
            self.events.FatJet = jet_correction(self.events, "FatJet", "AK8PFPuppi", self._year, self._JECversion, verbose=verbose)

    # Function to compute masks to preselect objects and save them as attributes of `events`
    def apply_object_preselection(self):
        # Include the supercluster pseudorapidity variable
        electron_etaSC = self.events.Electron.eta + self.events.Electron.deltaEtaSC
        self.events["Electron"] = ak.with_field(self.events.Electron, electron_etaSC, "etaSC")
        # Build masks for selection of muons, electrons, jets, fatjets
        self.events["MuonGood"]     = lepton_selection_noniso(self.events, "Muon", self.cfg.finalstate)
        self.events["ElectronGood"] = lepton_selection(self.events, "Electron", self.cfg.finalstate)
        leptons = ak.with_name( ak.concatenate( (self.events.MuonGood, self.events.ElectronGood), axis=1 ), name='PtEtaPhiMCandidate' )
        self.events["LeptonGood"]   = leptons[ak.argsort(leptons.pt, ascending=False)]
        self.events["JetGood"], self.jetGoodMask = jet_selection(self.events, "Jet", self.cfg.finalstate)
        #self.events["BJetGood"] = btagging(self.events["JetGood"], self._btag)
        self.events["FatJetGood"], self.fatjetGoodMask = jet_selection(self.events, "FatJet", self.cfg.finalstate)

        if self.cfg.finalstate == 'dilepton':
            self.events["ll"] = get_dilepton(self.events.ElectronGood, self.events.MuonGood)

    def build_fatjet_observables(self):
        if self.cfg.finalstate == 'mutag':
            self.events["FatJetLeading"] = ak.firsts(self.events.FatJetGood)
            Xbb = self.events.FatJetLeading.particleNetMD_Xbb
            Xcc = self.events.FatJetLeading.particleNetMD_Xcc
            QCD = self.events.FatJetLeading.particleNetMD_QCD
            fatjet_leading_fields = {
                "tau21"   : self.events.FatJetLeading.tau2 / self.events.FatJetLeading.tau1,
                "subjet1" : ak.pad_none(self.events.FatJetLeading.subjets, 2)[:, 0],
                "subjet2" : ak.pad_none(self.events.FatJetLeading.subjets, 2)[:, 1],
                "particleNetMD_Xbb_QCD" : Xbb / (Xbb + QCD),
                "particleNetMD_Xcc_QCD" : Xcc / (Xcc + QCD),
            }

            for field, value in fatjet_leading_fields.items():
                self.events["FatJetLeading"] = ak.with_field(self.events.FatJetLeading, value, field)

            fatjet_subjet_fields = {
                "nsv1"    : get_nsv(self.events.FatJetLeading.subjet1, self.events.SV),
                "nsv2"    : get_nsv(self.events.FatJetLeading.subjet2, self.events.SV),
                "nmusj1"  : ak.sum(self.events.FatJetLeading.subjet1.delta_r(self.events.MuonGood) < 0.4, axis=1),
                "nmusj2"  : ak.sum(self.events.FatJetLeading.subjet2.delta_r(self.events.MuonGood) < 0.4, axis=1),
            }

            for field, value in fatjet_subjet_fields.items():
                self.events["FatJetLeading"] = ak.with_field(self.events.FatJetLeading, value, field)

            self.events.FatJetLeading.subjet1 = ak.with_field(self.events.FatJetLeading.subjet1, self.events.FatJetLeading.subjet1.nearest(self.events.MuonGood, threshold=0.4)[:, 0], "MuonLeading")
            self.events.FatJetLeading.subjet2 = ak.with_field(self.events.FatJetLeading.subjet2, self.events.FatJetLeading.subjet2.nearest(self.events.MuonGood, threshold=0.4)[:, 0], "MuonLeading")
            self.events = ak.with_field(self.events, ak.pad_none(self.events.MuonGood, 2)[:, 0] + ak.pad_none(self.events.MuonGood, 2)[:, 1], "dimuon")
            self.events.dimuon = ak.with_field(self.events.dimuon, self.events.dimuon.mass, "mass")
        else:
            raise NotImplementedError

    def build_sv_observables(self):
        
        def project(a, b):
            return a.dot(b)/b.dot(b) * b

        self.events.SV = self.events.SV[get_sv_in_jet(self.events.FatJetLeading, self.events.SV)]
        i_maxPt     = ak.argsort(self.events.SV.pt, ascending=False)
        i_maxdxySig = ak.argsort(self.events.SV.dxySig, ascending=False)
        sv_pt_sorted = self.events.SV[i_maxPt]
        leadsv = ak.firsts(sv_pt_sorted)
        self.events["SVLeading"] = leadsv
        
        sv_fields = {
            "summass" : sv_pt_sorted.p4.sum().mass,
            "logsummass" : np.log(sv_pt_sorted.p4.sum().mass),
            "projmass" : project(sv_pt_sorted.p4.sum(), self.events.FatJetLeading).mass,
            "logprojmass" : np.log(project(sv_pt_sorted.p4.sum(), self.events.FatJetLeading).mass),
            "sv1mass" : leadsv.mass,
            "logsv1mass" : np.log(leadsv.mass),
        }

        corrmass = np.sqrt(sv_pt_sorted.p4.mass**2 + sv_pt_sorted.p4.pt**2 * np.sin(sv_pt_sorted.pAngle)**2) + sv_pt_sorted.p4.pt * np.sin(sv_pt_sorted.pAngle)
        sv_pt_sorted['mass'] = corrmass

        sv_corrmass_fields = {
            "sumcorrmass" : sv_pt_sorted.p4.sum().mass,
            "logsumcorrmass" : np.log(sv_pt_sorted.p4.sum().mass),
        }
        sv_fields.update(sv_corrmass_fields)

        for field, value in sv_fields.items():
            self.events["SVLeading"] = ak.with_field(self.events.SVLeading, value, field)

    # Function that counts the preselected objects and save the counts as attributes of `events`
    def count_objects(self):
        self.events["nmuon"]     = ak.num(self.events.MuonGood)
        self.events["nelectron"] = ak.num(self.events.ElectronGood)
        self.events["nlep"]      = self.events["nmuon"] + self.events["nelectron"]
        self.events["njet"]      = ak.num(self.events.JetGood)
        #self.events["nbjet"]     = ak.num(self.events.BJetGood)
        self.events["nfatjet"]   = ak.num(self.events.FatJetGood)
        self.events["nsv"]       = ak.num(self.events.SV)


    def apply_preselections(self):
        ''' The function computes all the masks from the preselection cuts
        and filter out the events to speed up the later computations.
        N.B.: Preselection happens after the objects correction and cleaning'''
        for cut in self._preselections:
            # Apply the cut function and add it to the mask
            mask = cut.get_mask(self.events, year=self._year, sample=self._sample, isMC=self._isMC)
            self._preselection_masks.add(cut.id, mask)
        # Now that the preselection mask is complete we can apply it to events
        self.events = self.events[self._preselection_masks.all(*self._preselection_masks.names)]
        self.nEvents_after_presel = self.nevents
        self.output['cutflow']['presel'][self._sample] += self.nEvents_after_presel
        self.has_events = self.nEvents_after_presel > 0

    def assign_flavor(self):
        #The function assigns a flavor to the fatjets depending on the hadron flavor, and the number of B and C hadrons
        self._flavors = {}
        if self._isMC:
            self._flavors['b'] = (self.events.FatJetLeading.hadronFlavour == 5)
            self._flavors['c'] = (self.events.FatJetLeading.hadronFlavour == 4)
            self._flavors['l'] = (self.events.FatJetLeading.hadronFlavour < 4)
            self._flavors['bb'] = abs(self.events.FatJetLeading.hadronFlavour == 5) & (self.events.FatJetLeading.nBHadrons >= 2) #& (self.events.FatJetLeading.nCHadrons == 0)
            self._flavors['cc'] = abs(self.events.FatJetLeading.hadronFlavour == 4) & (self.events.FatJetLeading.nBHadrons == 0) & (self.events.FatJetLeading.nCHadrons >= 2)
            #self._flavors['ll'] = abs(self.events.FatJetLeading.hadronFlavour < 4) & (self.events.FatJetLeading.nBHadrons == 0) & (self.events.FatJetLeading.nCHadrons == 0)
            self._flavors['b'] = self._flavors['b'] & ~self._flavors['bb']
            self._flavors['c'] = self._flavors['c'] & ~self._flavors['cc']
            self._flavors['l'] = self._flavors['l'] & ~self._flavors['bb'] & ~self._flavors['cc'] & ~self._flavors['b'] & ~self._flavors['c']
            #self._flavors['others'] = ~self._flavors['l'] & ~self._flavors['bb'] & ~self._flavors['cc'] & ~self._flavors['b'] & ~self._flavors['c']
        else:
            self._flavors['Data'] = np.ones(self.nEvents_after_presel, dtype='bool')
            
    def define_categories(self):
        for cut in self._cuts:
            mask = cut.get_mask(self.events, year=self._year, sample=self._sample)
            self._cuts_masks.add(cut.id, mask)
        # We make sure that for each category the list of cuts is unique in the Configurator validation

    def compute_weights(self):
        self.weights = Weights(self.nEvents_after_presel)
        if self._isMC:
            self.weights.add('genWeight', self.events.genWeight)
            self.weights.add('lumi', ak.full_like(self.events.genWeight, lumi[self._year]))
            self.weights.add('XS', ak.full_like(self.events.genWeight, samples_info[self._sample]["XS"]))
            # Pileup reweighting with nominal, up and down variations
            self.weights.add('pileup', *sf_pileup_reweight(self.events, self._year))
            # Electron reco and id SF with nominal, up and down variations
            #self.weights.add('sf_ele_reco', *sf_ele_reco(self.events, self._year))
            #self.weights.add('sf_ele_id',   *sf_ele_id(self.events, self._year))
            # Muon id and iso SF with nominal, up and down variations
            #self.weights.add('sf_mu_id',  *sf_mu(self.events, self._year, 'id'))
            #self.weights.add('sf_mu_iso', *sf_mu(self.events, self._year, 'iso'))

    def apply_pt_reweighting(self):
        if self.cfg.pt_reweighting != None:
            dict_corrPt = load(self.cfg.pt_reweighting)
            self.pt_weights = {cat : Weights(self.nEvents_after_presel) for cat in dict_corrPt.keys()}
            for cat, corrPt in dict_corrPt.items():
                if self._isMC:
                    self.pt_weights[cat].add( 'ptcorr', corrPt(ak.fill_none(self.events.FatJetLeading.pt, 0)) )
                else:
                    print(self.events.FatJetLeading.pt)
                    print(ak.ones_like(ak.fill_none(self.events.FatJetLeading.pt, 0)))
                    self.pt_weights[cat].add( 'ptcorr', ak.ones_like(ak.fill_none(self.events.FatJetLeading.pt, 0)) )

    def fill_histograms(self):
        for (obj, obj_hists) in zip([self.events, self.events.FatJetLeading, self.events.SVLeading], [self.nobj_hists, self.fatjet_hists, self.sv_hists]):
            fill_histograms_object_with_flavor(self, obj, obj_hists, event_var=True, pt_reweighting=self._pt_reweighting)
        for (obj, obj_hists) in zip([self.events.MuonGood, self.events.ElectronGood, self.events.JetGood], [self.muon_hists, self.electron_hists, self.jet_hists]):
            fill_histograms_object_with_flavor(self, obj, obj_hists, pt_reweighting=self._pt_reweighting)
        fill_histograms_object_with_flavor(self, self.events.SVLeading, self.sv_hists, event_var=True, pt_reweighting=self._pt_reweighting)
        

    def count_events(self):
        # Fill the output with the number of events and the sum of their weights in each category for each sample
        for category, cuts in self._categories.items():
            mask = self._cuts_masks.all(*cuts)
            self.output["cutflow"][category][self._sample] = ak.sum(mask)
            if self._isMC:
                w = self.weights.weight()
                self.output["sumw"][category][self._sample] = ak.sum(w*mask)

    def process_extra_before_skim(self):
        pass
    
    def process_extra_before_presel(self):
        pass
    
    def process_extra_after_presel(self):
        pass

    def fill_histograms_extra(self):
        pass
    
    def process(self, events):
        self.events = events

        ###################
        # At the beginning of the processing the initial number of events
        # and the sum of the genweights is stored for later use
        #################
        self.load_metadata()
        # Define the accumulator instance for this chunk
        self.output = self.accumulator.identity()
        #if len(events)==0: return output
        self.nEvents_initial = self.nevents
        self.output['cutflow']['initial'][self._sample] += self.nEvents_initial
        if self._isMC:
            # This is computed before any preselection
            self.output['sum_genweights'][self._sample] += sum(self.events.genWeight)

        ########################
        # Then the first skimming happens. 
        # Events that are for sure useless are removed, and trigger are applied.
        # The user can specify in the configuration a function to apply for the skiming.
        # BE CAREFUL: objects are not corrected and cleaned at this stage, the skimming
        # selections MUST be loose and inclusive w.r.t the final selections. 
        #########################
        # Trigger are applied at the beginning since they do not change 
        self.apply_triggers()
        # Customization point for derived workflows before skimming
        self.process_extra_before_skim()
        # MET filter, lumimask, + custom skimming function
        self.skim_events()
        if not self.has_events: return self.output

        #########################
        # After the skimming we apply the object corrections and preselection
        # Doing so we avoid to compute them on the full NanoAOD dataset
        #########################
        # Apply JEC + JER
        self.apply_JERC(JER=False, typeJet='AK8PFPuppi')
        #self.apply_JEC()

        # Apply preselections
        self.apply_object_preselection()
        self.build_fatjet_observables()
        self.build_sv_observables()
        self.count_objects()
        # Customization point for derived workflows after preselection cuts
        self.process_extra_before_presel()
        # This will remove all the events not passing preselection from further processing
        self.apply_preselections()
       
        # If not events remains after the preselection we skip the chunk
        if not self.has_events: return self.output

        # A quark flavor is assigned to the leading fatjets
        self.assign_flavor()

        ##########################
        # After the preselection cuts has been applied more processing is performwend 
        ##########################
        # Customization point for derived workflows after preselection cuts
        self.process_extra_after_presel()
        
        # This function applies all the cut functions in the cfg file
        # Each category is an AND of some cuts. 
        self.define_categories()

        # Weights
        self.compute_weights()

        # Per-event Pt reweighting
        self.apply_pt_reweighting()
        
        # Fill histograms
        self.fill_histograms()
        self.fill_histograms_extra()
        self.count_events()
        
        return self.output

    def postprocess(self, accumulator):
        # Rescale MC histograms by the total sum of the genweights
        scale_genweight = {}
        h = accumulator[list(self._hist_dict.keys())[0]]
        for sample in h.identifiers('sample'):
            sample = str(sample)
            scale_genweight[sample] = 1 if sample.startswith('DATA') else 1./accumulator['sum_genweights'][sample]

        for histname in accumulator:
            if (histname in self._hist_dict) | (histname in self._hist2d_dict):
                accumulator[histname].scale(scale_genweight, axis='sample')

        accumulator["scale_genweight"] = scale_genweight

        return accumulator
