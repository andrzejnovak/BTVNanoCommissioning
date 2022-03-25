import os
import sys
import json
import importlib.util

import parsl
from parsl import python_app
from parsl.config import Config
from parsl.executors.threads import ThreadPoolExecutor

class Sample():
    def __init__(self, path, prefix):
        self.prefix = prefix
        self.path = path
        self.sample_dict = {}
        self.load_attributes()
        self.get_filelist()
        self.build_sample_dict()

    # Function to get sample name and year from dataset name on DAS
    def load_attributes(self):
        self.sample = self.path.split('/')[1].split('_')[0]
        self.year = '20' + self.path.split('/')[2].split('UL')[1][:2]
        if self.year not in ['2016', '2017', '2018']:
            self.year = self.path.split('/')[2].split('UL')[1][:4]
        if self.year not in ['2016', '2017', '2018']:
            sys.exit(f"No dataset available for year '{self.year}'")
        self.name = self.sample + '_' + self.year

    # Function to get the dataset filelist from DAS
    def get_filelist(self):
        command = f'dasgoclient -query="file dataset={self.path} instance=prod/phys03"'
        self.filelist = os.popen(command).read().split('\n')
        self.filelist = [os.path.join(self.prefix, *file.split('/')) for file in self.filelist if file != '']

    # Function to build the sample dictionary
    def build_sample_dict(self):
        self.sample_dict[self.name] = {}
        self.sample_dict[self.name]['metadata'] = {'sample' : self.sample, 'year' : self.year, 'path' : self.path}
        self.sample_dict[self.name]['files']    = self.filelist

    def Print(self):
        print(f"path: {self.path}, sample: {self.sample}, year: {self.year}")

class Dataset():
    def __init__(self, file, prefix, outfile):
        self.prefix = prefix
        self.outfile = outfile
        self.sample_dict = {}
        self.sample_dict_local = {}
        with open(file, 'r') as f:
            self.samples = f.read().splitlines()
        self.get_samples()

    # Function to build the dataset dictionary
    def get_samples(self):
        for name in self.samples:
            sample = Sample(name, "root://xrootd-cms.infn.it//")
            sample_local = Sample(name, self.prefix)
            self.sample_dict.update(sample.sample_dict)
            self.sample_dict_local.update(sample_local.sample_dict)

    # Function to save the dataset dictionary with xrootd and local prefixes
    def save(self, local=True):
        for outfile, sample_dict in zip([self.outfile, self.outfile.replace('.json', '_local.json')], [self.sample_dict, self.sample_dict_local]):
            print(f"Saving datasets to {outfile}")
            with open(outfile, 'w') as fp:
                json.dump(sample_dict, fp, indent=4)
                fp.close()

    @python_app
    def down_file(fname, out, ith=None):
        if ith is not None:
            print(ith)
        os.system("xrdcp -P " + fname + " " + out)
        return 0

    def download(self):
        # Setup multithreading
        config_parsl = Config(executors=[ThreadPoolExecutor(max_threads=8)])
        parsl.load(config_parsl)

        # Write futures
        out_dict = {} # Output filename list
        run_futures = [] # Future list
        for key in sorted(self.sample_dict.keys()):
            new_list = [] 
            #print(key)
            if isinstance(self.sample_dict[key], dict):
                filelist = self.sample_dict[key]['files']
            elif isinstance(self.sample_dict[key], list):
                filelist = self.sample_dict[key]
            else:
                raise NotImplemented
            for i, fname in enumerate(filelist):
                if i%5 == 0: 
                    # print some progress info
                    ith = f'{key}: {i}/{len(filelist)}'
                else:
                    ith = None
                out = os.path.join(os.path.abspath(self.prefix), fname.split("//")[-1].lstrip("/"))
                new_list.append(out)
                if os.path.isfile(out):
                    'File found'
                else:
                    x = self.down_file(fname, out, ith)
                    run_futures.append(x)
            if isinstance(self.sample_dict[key], dict):
                out_dict[key] = {}
                out_dict[key]['files'] = new_list
                out_dict[key]['metadata'] = self.sample_dict[key]['metadata']
            elif isinstance(self.sample_dict[key], list):
                out_dict[key] = new_list
            else:
                raise NotImplemented

        for i, r in enumerate(run_futures):
            r.result()

        outfile = self.outfile.replace('.json', '_download.json')
        print(f"Writing files to {outfile}")
        with open(outfile, 'w') as fp:
            json.dump(out_dict, fp, indent=4)


