# BTVNanoCommissioning
Repository for Commissioning studies in the BTV POG based on (custom) nanoAOD samples


## Structure
Example worfkflow for ttbar is included. 

Each workflow can be a separete "processor" file, creating the mapping from NanoAOD to
the histograms we need. Workflow processors can be passed to the `runner.py` script 
along with the fileset these should run over. Multiple executors can be chosen 
(for now iterative - one by one, uproot/futures - multiprocessing and dask-slurm). 

To run the example, run:
```
python runner.py --workflow ttcom
```

Example plots can be found in ` make_some_plots.ipynb` though we might want to make
that more automatic in the end.

## Requirements
### Coffea installation with Miniconda
For installing Miniconda, see also https://hackmd.io/GkiNxag0TUmHnnCiqdND1Q#Local-or-remote
```
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
# Run and follow instructions on screen
bash Miniconda3-latest-Linux-x86_64.sh
```
NOTE: always make sure that conda, python, and pip point to local Miniconda installation (`which conda` etc.).

You can either use the default environment`base` or create a new one:
```
# create new environment with python 3.7, e.g. environment of name `coffea`
conda create --name coffea python=3.7
# activate environment `coffea`
conda activate coffea
```
Install coffea and xrootd:
```
pip install git+https://github.com/CoffeaTeam/coffea.git #latest published release with `pip install coffea`
conda install -c conda-forge xrootd
```
### Other installation options for coffea
See https://coffeateam.github.io/coffea/installation.html
### Running jupyter remotely
See also https://hackmd.io/GkiNxag0TUmHnnCiqdND1Q#Remote-jupyter

1. On your local machine, edit `.ssh/config`:
```
Host lxplus*
  HostName lxplus7.cern.ch
  User <your-user-name>
  ForwardX11 yes
  ForwardAgent yes
  ForwardX11Trusted yes
Host *_f
  LocalForward localhost:8800 localhost:8800
  ExitOnForwardFailure yes
```
2. Connect to remote with `ssh lxplus_f`
3. Start a jupyter notebook:
```
jupyter notebook --ip=127.0.0.1 --port 8800 --no-browser
```
4. URL for notebook will be printed, copy and open in local browser

## To be debugged currently
Running the following command on the t3:
```
python runner.py --workflow bbtag --executor futures --samples proxy_samples_reduced.json --workers 10
```
gives the following error message:
```
ImportError: Install XRootD python bindings with:
    conda install -c conda-forge xrootd
```

Running the following command on the t3:
```
python runner.py --workflow bbtag --executor dask/slurm --samples proxy_samples_reduced.json --workers 10
```
gives the following error message:
```
AttributeError: module 'yaml' has no attribute '__with_libyaml__'
```
