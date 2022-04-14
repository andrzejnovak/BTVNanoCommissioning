cfg =  {
    # Dataset parameters
    "dataset"  : "datasets/DAS/datasets_btag2016EOY.txt",
    "json"     : "datasets/RunIISummer16EOY16.json",
    "storage_prefix" : "/pnfs/psi.ch/cms/trivcat/store/user/mmarcheg/BTVNanoCommissioning",
    "campaign" : "EOY",
    "year"     : "2016",

    # PU files
    "puFile"   : "correction_files/PileupHistogram-goldenJSON-13tev-2016-69200ub-99bins.root",
    "nTrueFile": "correction_files/nTrueInt_RunIISummer16EOY16_local_2016.coffea",

    # JEC
    "JECfolder": "correction_files/tmp",

    # Input and output files
    "workflow" : "fatjet_tagger_ggHcc",
    "input"    : "datasets/RunIISummer16EOY16_local.json",
    "output"   : "histograms/RunIISummer16EOY16.coffea",
    "plots"    : "plots/RunIISummer16EOY16",

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
