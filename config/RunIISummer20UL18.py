cfg =  {
    # Dataset parameters
    "dataset"  : "datasets/DAS/datasets_btag2018UL.txt",
    "json"     : "datasets/RunIISummer20UL18.json",
    "storage_prefix" : "/pnfs/psi.ch/cms/trivcat/store/user/mmarcheg/BTVNanoCommissioning",
    "campaign" : "UL",
    "year"     : "2018",

    # PU files
    "puFile"   : "correction_files/UltraLegacy/PileupHistogram-goldenJSON-13tev-2018-69200ub-99bins.root",
    "nTrueFile": "correction_files/nTrueInt_RunIISummer20UL18_FIXED_SV_local_2018.coffea",

    # JEC
    "JECfolder": "correction_files/tmp",

    # Input and output files
    "workflow" : "fatjet_tagger",
    "input"    : "datasets/RunIISummer20UL18_local.json",
    "output"   : "histograms/RunIISummer20UL18_FIXED_SV.coffea",
    "plots"    : "plots/RunIISummer20UL18_FIXED_SV",

    # Executor parameters
    "run_options" : {
        "executor"       : "parsl/slurm",
        "workers"        : 12,
        "scaleout"       : 10,
        "partition"      : "standard",
        "walltime"       : "12:00:00",
        "mem_per_worker" : None, # GB
        "exclusive"      : True,
        "chunk"          : 50000,
        "max"            : None,
        "skipbadfiles"   : None,
        "voms"           : None,
        "limit"          : None,
    },

    # Processor parameters
    "checkOverlap" : False,
    "hist2d"       : False,
    "mupt"         : 5,
}