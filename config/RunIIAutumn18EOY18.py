cfg =  {
    # Dataset parameters
    "dataset"  : "datasets/DAS/datasets_btag2018EOY.txt",
    "json"     : "datasets/RunIIAutumn18EOY18.json",
    "storage_prefix" : "/pnfs/psi.ch/cms/trivcat/store/user/mmarcheg/BTVNanoCommissioning",
    "campaign" : "EOY",
    "year"     : "2018",

    # PU files
    "puFile"   : "correction_files/PileupHistogram-goldenJSON-13tev-2018-69200ub-99bins.root",
    "nTrueFile": "correction_files/nTrueInt_RunIIAutumn18EOY18_local_2018.coffea",

    # JEC
    "JECfolder": "correction_files/tmp",

    # Input and output files
    "workflow" : "fatjet_tagger_ggHcc",
    "input"    : "datasets/RunIIAutumn18EOY18_local.json",
    "output"   : "histograms/RunIIAutumn18EOY18.coffea",
    "plots"    : "plots/RunIIAutumn18EOY18_local",

    # Executor parameters
    "run_options" : {
        "executor"       : "parsl/slurm",
        # "executor"       : "iterative",
        # "workers"        : 10,
        "workers"        : None,
        "scaleout"       : 4,
        "partition"      : None,
        "walltime"       : "4:00:00",
        "mem_per_worker" : None, # GB
        "exclusive"      : True,
        "chunk"          : 250000,
        "max"            : None,
        "skipbadfiles"   : None,
        "voms"           : None,
        "limit"          : None,
        # "limit"          : 1,
    },

    # Processor parameters
    "checkOverlap" : False,
    "hist2d"       : False,
    "mupt"         : 5,
}