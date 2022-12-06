from pocket_coffea.parameters.cuts.preselection_cuts import *
from workflows.fatjet_base import fatjetBaseProcessor
from pocket_coffea.lib.cut_functions import get_nObj_min
from pocket_coffea.parameters.histograms import *
from pocket_coffea.parameters.btag import btag_variations
from pocket_coffea.lib.weights_manager import WeightCustom
from config.fatjet_base.custom.cuts import mutag_presel, get_ptbin, get_ptmsd, get_nObj_minmsd, get_flavor
from config.fatjet_base.custom.functions import get_inclusive_wp, get_HLTsel
import numpy as np

from parameters import PtBinning, AK8TaggerWP
PtBinning = PtBinning['UL']['2018']
wps = AK8TaggerWP['UL']['2018']

tagger = "btagDDBvLV2"

categories = {
    "inclusive" : [passthrough],
    "pt350msd40" : [get_ptmsd(350., 40.)],
    "pt350msd40_ptreweight" : [get_ptmsd(350., 40.)],
}

for wp in ["L", "M", "H"]:
    for pt_low, pt_high in PtBinning.values():
        cat = f"msd40Pt-{pt_low}to{pt_high}"
        categories.update({ cat : [
                                        get_ptmsd(350., 40.),
                                        get_ptbin(pt_low, pt_high),
                                        ]
                                })
        for region in ["pass", "fail"]:
            cat = f"msd40{tagger}{region}{wp}wpPt-{pt_low}to{pt_high}"
            categories.update({ cat : [
                                        get_ptmsd(350., 40.),
                                        get_ptbin(pt_low, pt_high),
                                        get_inclusive_wp(tagger, wps[tagger][wp], region)
                                        ]
                                })

categories_to_reweight = { cat : v for cat, v in categories.items() if cat not in ["inclusive", "pt350msd40"]}

samples = ["QCD_Pt-170to300",
           "QCD_Pt-300to470",
           "QCD_Pt-470to600",
           "QCD_Pt-600to800",
           "QCD_Pt-800to1000",
           "QCD_Pt-1000toInf",
           "DATA"]
subsamples = {}
for s in filter(lambda x: 'DATA' not in x, samples):
    subsamples[s] = {f"{s}_{f}" : [get_flavor(f)] for f in ['l', 'c', 'b', 'cc', 'bb']}

cfg =  {
    "dataset" : {
        "jsons": ["datasets/MC_QCD_MuEnriched_RunIISummer20UL_local.json",
                  "datasets/DATA_BTagMu_RunIISummer20UL_local.json"],
        "filter" : {
            "samples": samples,
            "samples_exclude" : [],
            "year": ['2018']
        },
        "subsamples": subsamples
    },
    

    # Input and output files
    "workflow" : fatjetBaseProcessor,
    "output"   : "output/pocket_coffea/testB/test_shapes",
    "workflow_options" : {},

    # "run_options" : {
    #     "executor"       : "parsl/slurm",
    #     # "workers"        : 16,
    #     "scaleout"       : 5,
    #     "queue"          : "standard",
    #     "walltime"       : "8:00:00",
    #     "mem_per_worker" : None,# GB
    #     "exclusive"      : True,
    #     "chunk"          : 100000,
    #     "retries"        : 10,
    #     # "treereduction"  : 10,
    #     "max"            : None,
    #     "skipbadfiles"   : None,
    #     "voms"           : None,
    #     "limit"          : None,
    #     "adapt"          : False,
    # },
    "run_options" : {
        "executor"       : "parsl/slurm",
        "queue"          : None,
        "scaleout"       : 6,
        "partition"      : None,
        "walltime"       : "12:00:00",
        "mem_per_worker" : None, # GB
        "exclusive"      : False,
        "chunk"          : 200000,
        "retries"        : 10,
        # "treereduction"  : 10,
        "max"            : None,
        "skipbadfiles"   : True,
        "voms"           : None,
        "limit"          : 5,
    },

    # Cuts and plots settings
    "finalstate" : "mutag",
    "skim": [get_nObj_min(1, 200., "FatJet"),
             # TO BE CHECKED
             get_nObj_minmsd(1, 30., "FatJet"),
             get_nObj_min(2, 3., "Muon"),
             get_HLTsel("mutag")],
    "preselections" : [mutag_presel],
    "categories": categories,

    "weights": {
        "common": {
            "inclusive": ["genWeight","lumi","XS",
                          "pileup"#, "sf_L1prefiring"
                          ],
            "bycategory" : { cat : ["pt_reweighting"] for cat in categories_to_reweight.keys()}
        },
        "bysample": {
        }
    },

    "variations": {
        "weights": {
            "common": {
                "inclusive": [ "pileup" ],#, "sf_L1prefiring" ],
                "bycategory" : {
                }
            },
        "bysample": {
        }    
        },
        "shape": {
            "common":{
                "inclusive": [ "JES_Total" ]
            }
        }
    },

   "variables":
    {
        **muon_hists(coll="MuonGood"),
        **muon_hists(coll="MuonGood", pos=0),
        **jet_hists(coll="JetGood"),
        **jet_hists(coll="JetGood", pos=0),
        **fatjet_hists(coll="FatJetGood"),
        **fatjet_hists(coll="FatJetGood", pos=0),
        **sv_hists(coll="events"),
        **sv_hists(coll="events", pos=0),
        **count_hist(name="nElectronGood", coll="ElectronGood",bins=10, start=0, stop=10),
        **count_hist(name="nMuonGood", coll="MuonGood",bins=10, start=0, stop=10),
        **count_hist(name="nJets", coll="JetGood",bins=10, start=0, stop=10),
        **count_hist(name="nFatJets", coll="FatJetGood",bins=10, start=0, stop=10),
        **count_hist(name="nSV", coll="SV",bins=10, start=0, stop=10),
        "nmusj_fatjet1": HistConf(
            [ Axis(coll="events", field="nmusj_fatjet1", label=r"$N_{\mu, J1}$", bins=10, start=0, stop=10) ]
        ),
        "nmusj_fatjet2": HistConf(
            [ Axis(coll="events", field="nmusj_fatjet2", label=r"$N_{\mu, J2}$", bins=10, start=0, stop=10) ]
        ),
        # "logsumcorrmass_btagDDBvLV2": HistConf(
        #     [
        #         Axis(
        #             coll="events",
        #             field="logsumcorrmass",
        #             bins=60,
        #             start=-2.5,
        #             stop=6,
        #             lim=(-2.5, 6),
        #             label="logsumcorrmass",
        #             pos=0,
        #         ),
        #         Axis(
        #             coll="FatJetGood",
        #             field="btagDDBvLV2",
        #             bins=50,
        #             start=0,
        #             stop=1,
        #             lim=(0, 1),
        #             label="btagDDBvLV2",
        #             pos=0,
        #         ),
        #     ],
        #     variations=False,
        #     no_weights=True,
        # ),
        "logsumcorrmass_btagDDBvLV2": HistConf(
            [
                Axis(
                    coll="FatJetGood",
                    field="btagDDBvLV2",
                    bins=100,
                    start=0,
                    stop=1,
                    label="DDBvLV2",
                    pos=0,
                ),
                Axis(
                    coll="FatJetGood",
                    field="logsumcorrmass",
                    bins=100,
                    start=-2.5,
                    stop=6,
                    label="logsumcorrmass",
                    pos=0
                ),
            ],
            variations=False,
            no_weights=False,
        ),
    },

    "columns" : {}

}
