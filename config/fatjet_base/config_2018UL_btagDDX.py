import sys
from PocketCoffea.parameters.cuts.baseline_cuts import passthrough
# from PocketCoffea.parameters.cuts.baseline_cuts import passthrough
from config.fatjet_base.custom_cuts import mutag_presel, get_ptbin, get_ptmsd
# from PocketCoffea.PocketCoffea.lib.cut_functions import get_nObj
from PocketCoffea.lib.cut_functions import get_nObj
from config.fatjet_base.functions import get_tagger_passfail, get_exclusive_wp
from workflows.fatjet_base import fatjetBaseProcessor
from math import pi
import numpy as np

from parameters import PtBinning, AK8TaggerWP
PtBinning = PtBinning['UL']['2018']
wp = AK8TaggerWP['UL']['2018']

cfg =  {

    "dataset" : {
        "jsons": ["datasets/MC_QCD_MuEnriched_locald.json", "datasets/DATA_BTagMu_locald.json", ],
        # "jsons": ["datasets/RunIISummer20UL18_local.json"],
        "filter" : {
            "samples": ["QCD_Pt-170to300", "QCD_Pt-300to470", "QCD_Pt-470to600", "QCD_Pt-600to800", "QCD_Pt-800to1000", "QCD_Pt-1000toInf", "DATA"],
            "samples_exclude" : [],
            "year": ["2018"]
        }
    },

    # Input and output files
    "workflow" : fatjetBaseProcessor,
    "output"   : "output/fatjet_base/fatjet_base_2018UL_btagDDX",
    # pT reweighting
    "pt_reweighting": "correction_files/pt_reweighting/pt_reweighting_2018UL_pt350/pt_corr.coffea",

    # Executor parameters
    "run_options" : {
        "executor"       : "parsl/slurm",
        # "executor"       : "iterative",
        # "workers"        : 1,
        "scaleout"       : 6,
        "partition"      : None,
        "walltime"       : "12:00:00",
        "mem_per_worker" : None, # GB
        "exclusive"      : False,
        "chunk"          : 200000,
        "retries"        : 10,
        # "treereduction"  : 10,
        "max"            : None,
        "skipbadfiles"   : None,
        "voms"           : None,
        "limit"          : 2,
    },

    # Cuts and plots settings
    "finalstate" : "mutag",
    "skim" : [ get_nObj(1, minpt=200., coll="FatJet"), get_nObj(1, minmsd=30., coll="FatJet"), get_nObj(2, minpt=3., coll="Muon")],
    "preselections" : [mutag_presel],
    "categories": {
        "inclusive" : [passthrough],
        "pt350msd40" : [get_ptmsd(350., 40.)],
        "pt350msd60" : [get_ptmsd(350., 60.)],
        "pt350msd100" : [get_ptmsd(350., 100.)],

        ## Inclusive pt categories
        # btagDDCvLV2
        "msd40btagDDCvLV2passLwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'pass')],
        "msd40btagDDCvLV2passMwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'pass')],
        "msd40btagDDCvLV2passHwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'pass')],

        "msd40btagDDCvLV2failLwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'fail')],
        "msd40btagDDCvLV2failMwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'fail')],
        "msd40btagDDCvLV2failHwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'fail')],

        # btagDDBvLV2
        "msd40btagDDBvLV2passLwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'pass')],
        "msd40btagDDBvLV2passMwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'pass')],
        "msd40btagDDBvLV2passHwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'pass')],

        "msd40btagDDBvLV2failLwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'fail')],
        "msd40btagDDBvLV2failMwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'fail')],
        "msd40btagDDBvLV2failHwpPt-400toInf" : [get_ptmsd(350., 40.), get_ptbin(400, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'fail')],

        ## Pt binning split + WPs + pass/fail
        # btagDDCvLV2
        "msd40btagDDCvLV2passLwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'pass')],
        "msd40btagDDCvLV2passLwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'pass')],
        "msd40btagDDCvLV2passLwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'pass')],
        "msd40btagDDCvLV2passLwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'pass')],

        "msd40btagDDCvLV2failLwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'fail')],
        "msd40btagDDCvLV2failLwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'fail')],
        "msd40btagDDCvLV2failLwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'fail')],
        "msd40btagDDCvLV2failLwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['L'], 'fail')],

        "msd40btagDDCvLV2passMwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'pass')],
        "msd40btagDDCvLV2passMwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'pass')],
        "msd40btagDDCvLV2passMwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'pass')],
        "msd40btagDDCvLV2passMwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'pass')],

        "msd40btagDDCvLV2failMwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'fail')],
        "msd40btagDDCvLV2failMwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'fail')],
        "msd40btagDDCvLV2failMwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'fail')],
        "msd40btagDDCvLV2failMwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['M'], 'fail')],

        "msd40btagDDCvLV2passHwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'pass')],
        "msd40btagDDCvLV2passHwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'pass')],
        "msd40btagDDCvLV2passHwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'pass')],
        "msd40btagDDCvLV2passHwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'pass')],

        "msd40btagDDCvLV2failHwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'fail')],
        "msd40btagDDCvLV2failHwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'fail')],
        "msd40btagDDCvLV2failHwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'fail')],
        "msd40btagDDCvLV2failHwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDCvLV2", wp["btagDDCvLV2"]['H'], 'fail')],

        # btagDDBvLV2
        "msd40btagDDBvLV2passLwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'pass')],
        "msd40btagDDBvLV2passLwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'pass')],
        "msd40btagDDBvLV2passLwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'pass')],
        "msd40btagDDBvLV2passLwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'pass')],

        "msd40btagDDBvLV2failLwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'fail')],
        "msd40btagDDBvLV2failLwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'fail')],
        "msd40btagDDBvLV2failLwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'fail')],
        "msd40btagDDBvLV2failLwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['L'], 'fail')],

        "msd40btagDDBvLV2passMwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'pass')],
        "msd40btagDDBvLV2passMwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'pass')],
        "msd40btagDDBvLV2passMwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'pass')],
        "msd40btagDDBvLV2passMwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'pass')],

        "msd40btagDDBvLV2failMwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'fail')],
        "msd40btagDDBvLV2failMwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'fail')],
        "msd40btagDDBvLV2failMwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'fail')],
        "msd40btagDDBvLV2failMwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['M'], 'fail')],

        "msd40btagDDBvLV2passHwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'pass')],
        "msd40btagDDBvLV2passHwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'pass')],
        "msd40btagDDBvLV2passHwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'pass')],
        "msd40btagDDBvLV2passHwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'pass')],

        "msd40btagDDBvLV2failHwpPt-400to600" : [get_ptmsd(350., 40.), get_ptbin(400, 600), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'fail')],
        "msd40btagDDBvLV2failHwpPt-600to800" : [get_ptmsd(350., 40.), get_ptbin(600, 800), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'fail')],
        "msd40btagDDBvLV2failHwpPt-600toInf" : [get_ptmsd(350., 40.), get_ptbin(600, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'fail')],
        "msd40btagDDBvLV2failHwpPt-800toInf" : [get_ptmsd(350., 40.), get_ptbin(800, 'Inf'), get_exclusive_wp("btagDDBvLV2", wp["btagDDBvLV2"]['H'], 'fail')],
    },

    "variables" : {
        "muon_pt" : None,
        "muon_eta" : None,
        "muon_phi" : None,
        "leadfatjet_pt" : None,
        "leadfatjet_eta" : None,
        "leadfatjet_phi" : None,
        "leadfatjet_msoftdrop" : None,
        "leadfatjet_tau21" : None,
        "leadfatjet_btagDDBvLV2" : None,
        "leadfatjet_btagDDCvLV2" : None,
        "leadfatjet_btagDDCvBV2" : None,
        "leadfatjet_particleNetMD_Xbb" : None,
        "leadfatjet_particleNetMD_Xcc" : None,
        "leadfatjet_particleNetMD_Xbb_QCD" : None,
        "leadfatjet_particleNetMD_Xcc_QCD" : None,
        "sv_summass" : None,
        "sv_logsummass" : None,
        "sv_projmass" : None,
        "sv_logprojmass" : None,
        "sv_sv1mass" : None,
        "sv_logsv1mass" : None,
        "sv_sumcorrmass" : None,
        "sv_logsumcorrmass" : None,
        "nmuon" : None,
        "nelectron" : None,
        "nlep" : None,
        "njet" : None,
        "nfatjet" : None,
        "nsv" : {'binning' : {'n_or_arr' : 20, 'lo' : 0, 'hi' : 20},    'xlim' : (0,20),   'xlabel' : "$N_{SV}$"},
    },
    "variables2d": {
        'nd_logsumcorrmass_DDBvL': {
            'sv_logsumcorrmass': {
                'binning': {'n_or_arr' : 50, 'lo' : -1.2, 'hi' : 4.8},   
                'xlim' : (-1.2,4.8),
                'xlabel': "Electron $p_{T}$ [GeV]",
                # 'xticks': [20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500]
                },
            'leadfatjet_btagDDBvLV2': {
                'binning': {'n_or_arr' : 50, 'lo' : 0, 'hi' : 1},
                'ylim': (0, 1), 
                'ylabel': "DDBvLV2"
                },
        },
        
    },
    "plot_options" : {
        #"sum_over" : ['cat', 'year', 'flavor'],
        "sum_over" : ['cat', 'year', 'sample'],
        "only" : None,
        "workers" : 8,
        "scale" : None,
        "fontsize" : 18,
        "fontsize_map" : 10,
        "dpi" : 150,
        "rebin" : {
            'leadfatjet_pt'        : {'binning' : {'n_or_arr' : 20, 'lo' : 0, 'hi' : 1000}, 'xlim' : (0,1000), 'xlabel' : "FatJet $p_T$"},
            'leading_fatjet_tau21' : {'binning' : {'n_or_arr' : 40, 'lo' : 0, 'hi' : 1},    'xlim' : (0,1),    'xlabel' : r'FatJet $\tau_{21}$'},
            'sv_logsummass'        : {'binning' : {'n_or_arr' : 60, 'lo' : -6, 'hi' : 6},   'xlim' : (-2.5,6), 'xlabel' : r"FatJet log($\sum({m_{SV}})$) [GeV]"},
            'sv_logsv1mass'        : {'binning' : {'n_or_arr' : 60, 'lo' : -6, 'hi' : 6},   'xlim' : (-4,4),   'xlabel' : r"FatJet log($m_{SV,1}$/GeV)"},
            'sv_logprojmass'       : {'binning' : {'n_or_arr' : 60, 'lo' : -6, 'hi' : 6},   'xlim' : (-2.5,6), 'xlabel' : r"FatJet log($m_{SV}^{proj}$) [GeV]"},
            'sv_logsumcorrmass'    : {'binning' : {'n_or_arr' : 60, 'lo' : -6, 'hi' : 6},   'xlim' : (-2.5,6), 'xlabel' : r"FatJet log($\sum({m^{corr}_{SV}})$) [GeV]"},
        }
    },
    "sf_options" : {
        "parameters" : None,
        "merge_x_xx" : True,
        "categories" : {"filter" : ["msd40btagDDCvLV2"]},
        "rebin" : {
            'sv_logsummass'        : {'binning' : {'n_or_arr' : 30, 'lo' : -6, 'hi' : 6},   'xlim' : (-2.5,6), 'xlabel' : r"FatJet log($\sum({m_{SV}})$) [GeV]"},
            'sv_logsv1mass'        : {'binning' : {'n_or_arr' : 30, 'lo' : -6, 'hi' : 6},   'xlim' : (-4,4),   'xlabel' : r"FatJet log($m_{SV,1}$/GeV)"},
            'sv_logprojmass'       : {'binning' : {'n_or_arr' : 30, 'lo' : -6, 'hi' : 6},   'xlim' : (-2.5,6), 'xlabel' : r"FatJet log($m_{SV}^{proj}$) [GeV]"},
            'sv_logsumcorrmass'    : {'binning' : {'n_or_arr' : 30, 'lo' : -6, 'hi' : 6},   'xlim' : (-1.2,4.8), 'xlabel' : r"FatJet log($\sum({m^{corr}_{SV}})$) [GeV]"},
        }
    }
}
