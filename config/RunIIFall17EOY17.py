cfg =  {
    # Dataset parameters
    "dataset"  : "datasets/DAS/datasets_btag2017EOY.txt",
    "json"     : "datasets/RunIIFall17EOY17.json",
    "storage_prefix" : "/pnfs/psi.ch/cms/trivcat/store/user/mmarcheg/BTVNanoCommissioning",
    "campaign" : "EOY",
    "year"     : "2017",

    # PU files
    "puFile"   : "correction_files/PileupHistogram-goldenJSON-13tev-2017-69200ub-99bins.root",
    "nTrueFile": "correction_files/nTrueInt_RunIIFall17EOY17_local_2017.coffea",

    # JEC
    "JECfolder": "correction_files/tmp",

    # Input and output files
    "workflow" : "fatjet_tagger_ggHcc",
    "input"    : "datasets/RunIIFall17EOY17_max.json",
    "output"   : "histograms/RunIIFall17EOY17.coffea",
    "plots"    : "plots/RunIIFall17EOY17",

    # Executor parameters
    "run_options" : {
        "executor"       : "parsl/slurm",
        # "executor"       : "iterative",
        "workers"        : None,
        "scaleout"       : 4,
        "partition"      : None,
        "walltime"       : "4:00:00",
        "mem_per_worker" : None, # GB
        "exclusive"      : True,
        "chunk"          : 200000,
        "max"            : None,
        "skipbadfiles"   : True,
        "voms"           : None,
        # "limit"          : None,
        # "limit"          : 1,
    },

    # Processor parameters
    "checkOverlap" : False,
    "hist2d"       : False,
    "mupt"         : 5,
}
