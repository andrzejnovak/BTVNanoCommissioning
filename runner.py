import os
import sys
import json
import argparse
import time
import gc
import tempfile

import numpy as np

import uproot
from coffea import hist
from coffea.nanoevents import NanoEventsFactory
from coffea.util import load, save
from coffea import processor

from utils.Configurator import Configurator
from lib.luminosity import rescale
from parameters import lumi, xsecs


wrk_init = '''
export X509_USER_PROXY=/afs/cern.ch/user/a/algomez/x509up_u15148
source /afs/cern.ch/work/a/algomez/miniconda3/etc/profile.d/conda.sh
export PATH=/afs/cern.ch/work/a/algomez/miniconda3/bin:$PATH
source activate btv
cd /afs/cern.ch/work/a/algomez/DoubleXTagger/BTVNanoCommissioning/
'''
condor_cfg = '''
getenv      =  True
+JobFlavour =  "nextweek"
'''

def validate(file):
    try:
        fin = uproot.open(file)
        return fin['Events'].num_entries
    except:
        print("Corrupted file: {}".format(file))
        return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run analysis on baconbits files using processor coffea files')
    # Inputs
    parser.add_argument('--cfg', default=os.getcwd() + "/config/test.py", help='Config file with parameters specific to the current run', required=True)

    args = parser.parse_args()
    config = Configurator(args.cfg)

    if config.run_options['executor'] not in ['futures', 'iterative']:
        # dask/parsl needs to export x509 to read over xrootd
        if config.run_options['voms'] is not None:
            _x509_path = config.run_options['voms']
        else:
            _x509_localpath = [l for l in os.popen('voms-proxy-info').read().split("\n") if l.startswith('path')][0].split(":")[-1].strip()
            _x509_path = os.environ['HOME'] + f'/.{_x509_localpath.split("/")[-1]}'
            os.system(f'cp {_x509_localpath} {_x509_path}')

        env_extra = [
            'export XRD_RUNFORKHANDLER=1',
            f'export X509_USER_PROXY={_x509_path}',
            f'export X509_CERT_DIR={os.environ["X509_CERT_DIR"]}',
            'ulimit -u 32768',
        ]

        wrk_init = [
            f'export X509_USER_PROXY={_x509_path}',
            f'export X509_CERT_DIR={os.environ["X509_CERT_DIR"]}',
            # 'source /etc/profile.d/conda.sh',
            # 'export PATH=$CONDA_PREFIX/bin:$PATH',
            'conda activate coffea',
            # 'cd /afs/cern.ch/work/m/mmarcheg/BTVNanoCommissioning/',
        ]

        condor_cfg = '''
        getenv      =  True
        +JobFlavour =  "nextweek"
        '''
        #process_worker_pool = os.environ['CONDA_PREFIX'] + "/bin/process_worker_pool.py"

    #########
    # Execute
    output_split = []
    if config.run_options['executor'] in ['futures', 'iterative']:
        if config.run_options['executor'] == 'iterative':
            _exec = processor.iterative_executor
        else:
            _exec = processor.futures_executor
        output = processor.run_uproot_job(config.fileset,
                                    treename='Events',
                                    processor_instance=config.processor_instance,
                                    executor=_exec,
                                    executor_args={
                                        'skipbadfiles':config.run_options['skipbadfiles'],
                                        'schema': processor.NanoAODSchema,
                                        'workers': config.run_options['workers']},
                                    chunksize=config.run_options['chunk'], maxchunks=config.run_options['max']
                                    )
    #elif config.run_options['executor'] == 'parsl/slurm':
    elif 'parsl' in config.run_options['executor']:
        import parsl
        from parsl.providers import LocalProvider, CondorProvider, SlurmProvider
        from parsl.channels import LocalChannel
        from parsl.config import Config
        from parsl.executors import HighThroughputExecutor
        from parsl.launchers import SrunLauncher, SingleNodeLauncher
        from parsl.addresses import address_by_hostname

        if 'slurm' in config.run_options['executor']:
            slurm_htex = Config(
                executors=[
                    HighThroughputExecutor(
                        label="coffea_parsl_slurm",
                        address=address_by_hostname(),
                        prefetch_capacity=0,
                        mem_per_worker=config.run_options['mem_per_worker'],
                        provider=SlurmProvider(
                            channel=LocalChannel(script_dir='logs_parsl'),
                            launcher=SrunLauncher(),
                            #launcher=SingleNodeLauncher(),
                            max_blocks=(config.run_options['scaleout'])+2,
                            init_blocks=config.run_options['scaleout'],
                            #partition='long',
                            partition=config.run_options['partition'],
                            worker_init="\n".join(env_extra) + "\nexport PYTHONPATH=$PYTHONPATH:$PWD",
                            walltime=config.run_options['walltime'],
                            exclusive=config.run_options['exclusive'],
                        ),
                    )
                ],
                retries=20,
            )
            dfk = parsl.load(slurm_htex)

            output = processor.run_uproot_job(config.fileset,
                                        treename='Events',
                                        processor_instance=config.processor_instance,
                                        executor=processor.parsl_executor,
                                        executor_args={
                                            'skipbadfiles':True,
                                            'schema': processor.NanoAODSchema,
                                            'config': None,
                                        },
                                        chunksize=config.run_options['chunk'], maxchunks=config.run_options['max']
                                        )
        elif 'condor' in config.run_options['executor']:
            #xfer_files = [process_worker_pool, _x509_path]
            #print(xfer_files)

            condor_htex = Config(
                executors=[
                    HighThroughputExecutor(
                        label="coffea_parsl_slurm",
                        #address=address_by_hostname(),
                        worker_ports=(8786,8785),
                        prefetch_capacity=0,
                        provider=CondorProvider(
                            channel=LocalChannel(script_dir='logs_parsl'),
                            launcher=SingleNodeLauncher(),
                            max_blocks=(config.run_options['scaleout'])+2,
                            init_blocks=config.run_options['scaleout'],
                            worker_init="\n".join(wrk_init),
                            #transfer_input_files=xfer_files,
                            scheduler_options=condor_cfg,
                            walltime=config.run_options['walltime']
                        ),
                    )
                ],
                #retries=20,
            )
            dfk = parsl.load(condor_htex)

            output = processor.run_uproot_job(sample_dict,
                                        treename='Events',
                                        processor_instance=processor_instance,
                                        executor=processor.parsl_executor,
                                        executor_args={
                                            'skipbadfiles':True,
                                            'schema': processor.NanoAODSchema,
                                            'config': None,
                                        },
                                        chunksize=config.run_options['chunk'], maxchunks=config.run_options['max']
                                        )
    elif 'dask' in config.run_options['executor']:
        from dask_jobqueue import SLURMCluster, HTCondorCluster
        from distributed import Client
        from dask.distributed import performance_report

        if 'slurm' in config.run_options['executor']:
            cluster = SLURMCluster(
                queue='all',
                cores=config.run_options['workers'],
                processes=config.run_options['workers'],
                memory="200 GB",
                retries=10,
                walltime=config.run_options['walltime'],
                env_extra=env_extra,
            )
        elif 'condor' in config.run_options['executor']:
            cluster = HTCondorCluster(
                 cores=config.run_options['workers'],
                 memory='2GB',
                 disk='2GB',
                 env_extra=env_extra,
            )
        cluster.scale(jobs=config.run_options['scaleout'])

        client = Client(cluster)
        with performance_report(filename="dask-report.html"):
            output = processor.run_uproot_job(config.fileset,
                                        treename='Events',
                                        processor_instance=config.processor_instance,
                                        executor=processor.dask_executor,
                                        executor_args={
                                            'client': client,
                                            'skipbadfiles':config.run_options['skipbadfiles'],
                                            'schema': processor.NanoAODSchema,
                                        },
                                        chunksize=config.run_options['chunk'], maxchunks=config.run_options['max']
                            )

    #if len(sample_dict.keys()) > 1:     ##################### needs fix.
    #   output = rescale(output, xsecs, lumi[args.year])
    #   #output = rescale(output, xsecs, lumi[args.year], "JetHT")
    save(output, config.output)
    print(output)
    print(f"Saving output to {config.output}")
