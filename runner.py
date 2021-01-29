import os
import sys
import json
import argparse

import numpy as np

import uproot4 as uproot
from coffea import hist
from coffea.nanoevents import NanoEventsFactory
from coffea.util import load, save
from coffea import processor

def validate(file):
    try:
        fin = uproot.open(file)
        return fin['Events'].num_entries
    except:
        print("Corrupted file: {}".format(file))
        return 


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run analysis on baconbits files using processor coffea files')
    parser.add_argument( '--wf', '--workflow', dest='workflow', choices=['ttcom', 'bbtag'], help='Which processor to run', required=True)
    parser.add_argument('-o', '--output', default=r'hists.coffea', help='Output histogram filename (default: %(default)s)')
    parser.add_argument('--samples', '--json', dest='samplejson', default='dummy_samples.json', help='JSON file containing dataset and file locations (default: %(default)s)')

    parser.add_argument('--executor', choices=['iterative', 'futures', 'parsl', 'dask/condor', 'dask/slurm'], default='futures', help='The type of executor to use (default: %(default)s)')
    parser.add_argument('-j', '--workers', type=int, default=12, help='Number of workers to use for multi-worker executors (e.g. futures or condor) (default: %(default)s)')

    parser.add_argument('--validate', action='store_true', help='Do not process, just check all files are accessible')
    parser.add_argument('--only', type=str, default=None, help='Only process specific dataset or file')
    parser.add_argument('--limit', type=int, default=None, metavar='N', help='Limit to the first N files of each dataset in sample JSON')
    parser.add_argument('--chunk', type=int, default=250000, metavar='N', help='Number of events per process chunk')
    parser.add_argument('--max', type=int, default=None, metavar='N', help='Max number of chunks to run in total')
    args = parser.parse_args()
    if args.output == parser.get_default('output'):
        args.output = f'hists_{args.workflow}_{(args.samplejson).rstrip(".json")}.coffea'


    # load dataset
    with open(args.samplejson) as f:
        sample_dict = json.load(f)
    
    for key in sample_dict.keys():
        sample_dict[key] = sample_dict[key][:args.limit]

    # For debugging
    if args.only is not None:
        if args.only in sample_dict.keys():  # is dataset
            sample_dict = dict([(args.only, sample_dict[args.only])])
        if "*" in args.only: # wildcard for datasets
            _new_dict = {}
            print("Will only proces the following datasets:")
            for k, v in sample_dict.items():
                if k.lstrip("/").startswith(args.only.rstrip("*")):
                    print("    ", k)
                    _new_dict[k] = v
            sample_dict = _new_dict
        else:  # is file
            for key in sample_dict.keys():
                if args.only in sample_dict[key]:
                    sample_dict = dict([(key, [args.only])]) 


    # Scan if files can be opened
    if args.validate:
        # Run locally, but with multiprocessing
        import dask
        from dask.distributed import Client
        client = Client(n_workers=4)
        for sample in sample_dict.keys():
            results = []
            for x in sample_dict[sample]:
                y = dask.delayed(validate)(x)
                results.append(y)

            results = dask.compute(*results)
            print(sample)
            print("    Events:", np.sum(list(results)))
        sys.exit(0)
    
    # load workflow
    # Maybe this can be done better
    if args.workflow == "ttcom":
        from workflows.ttbar_validation import NanoProcessor
        processor_instance = NanoProcessor()
    elif args.workflow == "bbtag":
        from workflows.bbtag_scalefactors import NanoProcessor
        processor_instance = NanoProcessor()
    else:
        raise NotImplemented

    #########
    # Execute
    if args.executor in ['futures', 'iterative']:
        if args.executor == 'iterative':
            _exec = processor.iterative_executor
        else:
            _exec = processor.futures_executor
        uproot.open.defaults["xrootd_handler"] = uproot.source.xrootd.MultithreadedXRootDSource
        output = processor.run_uproot_job(sample_dict,
                                    treename='Events',
                                    processor_instance=processor_instance,
                                    executor=_exec,
                                    executor_args={
                                        'skipbadfiles':True,
                                        'schema': processor.NanoAODSchema, 
                                        'flatten':True, 
                                        'workers': args.workers},
                                        #'workers': 4},
                                    chunksize=args.chunk, maxchunks=args.max
                                    )
    elif args.executor == 'parsl':
        raise NotImplemented
        
    elif 'dask' in args.executor:
        from dask_jobqueue import SLURMCluster, HTCondorCluster
        from distributed import Client
        from dask.distributed import performance_report

        if 'slurm' in args.executor:
            cluster = SLURMCluster(
                queue='wn',
                cores=16,
                processes=16,
                memory="32 GB",
                walltime='05:00:00',
                env_extra=['ulimit -u 32768'],
            )
        elif 'condor' in args.executor:
             cluster = HTCondorCluster(
                 cores=1, 
                 memory='2GB', 
                 disk='2GB', 
            )
        cluster.scale(jobs=args.workers)

        print(cluster.job_script())
        client = Client(cluster)
        with performance_report(filename="dask-report.html"):
            output = processor.run_uproot_job(sample_dict,
                                        treename='Events',
                                        processor_instance=processor_instance,
                                        executor=processor.dask_executor,
                                        executor_args={
                                            'client': client,
                                            'skipbadfiles':True,
                                            'schema': processor.NanoAODSchema, 
                                            'flatten':True, 
                                        },
                                        chunksize=args.chunk, maxchunks=args.max
                            )
    save(output, args.output)
  
    print(output)
    print(f"Saving output to {args.output}")