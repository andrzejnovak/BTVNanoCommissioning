import argparse
import numpy as np
from coffea.util import load
from coffea.hist import plot
import coffea.hist as hist
import itertools
import os
import pickle
#from lib.luminosity import rescale
from parameters import histogram_settings, xsecs, FinalMask, PtBinning, AK8TaggerWP, lumi

parser = argparse.ArgumentParser(description='Plot histograms from coffea file')
parser.add_argument('-i', '--input', type=str, help='Input histogram filename', required=True)
parser.add_argument('-o', '--output', type=str, default='', help='Output file')
parser.add_argument('--outputDir', type=str, default=None, help='Output directory')
parser.add_argument('--campaign', type=str, choices={'EOY', 'UL'}, help='Dataset campaign.', required=True)
parser.add_argument('--year', type=str, choices=['2016', '2017', '2018'], help='Year of data/MC samples', required=True)
parser.add_argument('--vfp', type=str, default=None, choices=['pre', 'post'], help='Year of data/MC samples', required=False)
parser.add_argument('--data', type=str, default='BTagMu', help='Data sample name')
#parser.add_argument('--pt', type=int, default=500, help='Pt cut.')
parser.add_argument('--lumiscale', type=float, default=None, help='Scale MC by x-section times luminoisity.', required=False)
parser.add_argument('--scaleFail', type=float, default=None, help='Artificial scaling factor for distributions in the fail region.', required=False)
parser.add_argument('--mergebbcc', action='store_true', default=False, help='Merge bb+cc')

args = parser.parse_args()
print("Running with options:")
print("    ", args)

if (args.campaign == 'UL') & (args.year == '2016'):
    if args.vfp == parser.get_default('vfp'):
        sys.exit("For 2016UL, specify if 'pre' or 'post' VFP.")
    else:
        vfp_label = {'pre' : '-PreVFP', 'post' : '-PostVFP'}[args.vfp]
        totalLumi = lumi[args.campaign][f"{args.year}{vfp_label}"]
else:
    totalLumi = lumi[args.campaign][args.year]

if os.path.isfile( args.input ): accumulator = load(args.input)
else:
    files_list = [ifile for ifile in os.listdir(args.input) if ifile != args.output]
    accumulator = load(args.input + files_list[0])
    histograms = accumulator.keys()
    for ifile in files_list[1:]:
        output = load(args.input + ifile)
        for histname in histograms:
            accumulator[histname].add(output[histname])

scaleXS = {}
for isam in accumulator[next(iter(accumulator))].identifiers('dataset'):
    isam = str(isam)
    if args.lumiscale:
        scaleXS[isam] = 1 if isam.startswith('BTag') else xsecs[isam]/accumulator['sumw'][isam] * 1000 * totalLumi
    else:
        scaleXS[isam] = 1 if isam.startswith('BTag') else xsecs[isam]/accumulator['sumw'][isam]

print(accumulator.keys())

outputDict = {}
#for ivar in [ 'fatjet_jetproba', 'sv_logsv1mass', 'sv_logsv1mass_maxdxySig' ]:
for ivar in [ 'sv_logsv1mass', 'sv_logsv1mass_maxdxySig' ]:
    for isel in FinalMask:
        for tagger in AK8TaggerWP[args.campaign][args.year].keys():
            for wp in [ 'L', 'M', 'H' ]:
                for wpt in ['Inclusive'] + list(PtBinning[args.campaign][args.year].keys()):
                #for (pt_low, pt_high) in [('', ''), (350, args.pt), (args.pt, 'Inf')]:
                    if wpt == 'Inclusive':
                        pt_low, pt_high = ('', '')
                    else:
                        pt_low, pt_high = PtBinning[args.campaign][args.year][wpt]
                    for passfail in ['pass', 'fail']:

                        if pt_low == '':
                            histname=f'{ivar}_{isel}{tagger}{passfail}{wp}wp'
                        else:
                            histname=f'{ivar}_{isel}{tagger}{passfail}{wp}wpPt-{pt_low}to{pt_high}'
                        histname_coffea = histname
                        if histname_coffea not in accumulator.keys():
                            if args.campaign == 'EOY':
                                histname_coffea = histname_coffea.replace(f'{isel}', f'{isel}ggHcc')
                        if histname_coffea not in accumulator.keys():
                            print("not in accumulator:", histname_coffea)
                            continue
                            raise NotImplementedError
                        else:
                            h          = accumulator[histname_coffea]
                            #h_fail     = accumulator[histname_coffea.replace(f'{isel}{tagger}pass', f'{isel}{tagger}fail')].copy()
                            #h_passfail = accumulator[f'{ivar}_{isel}'].copy()
                        h.scale( scaleXS, axis='dataset' )
                        #h_fail.scale( scaleXS, axis='dataset' )
                        #h_passfail.scale( scaleXS, axis='dataset' )
                        if (args.scaleFail != None) & (passfail == 'fail'):
                            print(f"Scaling fail distributions by a factor {args.scaleFail}")
                            #h.scale( args.scaleFail, axis='dataset' )
                            h.scale( args.scaleFail )
                            #h_fail.scale( args.scaleFail )
                            #h_passfail.scale( args.scaleFail )
                        h          = h.rebin(h.fields[-1], hist.Bin(h.fields[-1], h.axis(h.fields[-1]).label, **histogram_settings[args.campaign]['variables'][ivar]['binning']))
                        #h_fail     = h_fail.rebin(h.fields[-1], hist.Bin(h.fields[-1], h.axis(h.fields[-1]).label, **histogram_settings[args.campaign]['variables'][ivar]['binning']))
                        #h_passfail = h_passfail.rebin(h.fields[-1], hist.Bin(h.fields[-1], h.axis(h.fields[-1]).label, **histogram_settings[args.campaign]['variables'][ivar]['binning']))

                        ##### grouping flavor
                        flavors = [str(s) for s in h.axis('flavor').identifiers() if str(s) != 'flavor']
                        mapping_flavor = {f : [f] for f in flavors}
                        flavors_to_merge = ['bb', 'b', 'cc', 'c']
                        for flav in flavors_to_merge:
                            mapping_flavor.pop(flav)
                        if args.mergebbcc:
                            mapping_flavor['bb_cc'] = ['b', 'bb', 'c', 'cc']
                        else:
                            mapping_flavor['b_bb'] = ['b', 'bb']
                            mapping_flavor['c_cc'] = ['c', 'cc']
                        h          = h.group("flavor", hist.Cat("flavor", "Flavor"), mapping_flavor)
                        #h_fail     = h_fail.group("flavor", hist.Cat("flavor", "Flavor"), mapping_flavor)
                        #h_passfail = h_passfail.group("flavor", hist.Cat("flavor", "Flavor"), mapping_flavor)

                        ##### grouping data and QCD histos
                        datasets = [str(s) for s in h.axis('dataset').identifiers() if str(s) != 'dataset']
                        mapping = {
                            r'QCD ($\mu$ enriched)' : [dataset for dataset in datasets if 'QCD_Pt' in dataset],
                            r'BTagMu': [ idata for idata in datasets if args.data in idata ],
                        }
                        datasets = mapping.keys()
                        datasets_data  = [dataset for dataset in datasets if args.data in dataset]
                        datasets_QCD = [dataset for dataset in datasets if ((args.data not in dataset) & ('GluGlu' not in dataset))]
                        
                        h          = h.group("dataset", hist.Cat("dataset", "Dataset"), mapping)
                        #h_fail     = h_fail.group("dataset", hist.Cat("dataset", "Dataset"), mapping)
                        #h_passfail = h_passfail.group("dataset", hist.Cat("dataset", "Dataset"), mapping)

                        #### rescaling QCD to data
                        if not args.scalelumi:
                            #print(h_passfail.values())
                            dataSum = np.sum( h_fail[args.data].sum('flavor').values()[('BTagMu',)] )
                            QCDSum = np.sum( h_fail[datasets_QCD].sum('dataset', 'flavor').values()[()] )
                            QCD = h[datasets_QCD].sum('dataset')
                            QCD.scale( dataSum/QCDSum )

                            #wrong_factor = np.sum( h[args.data].sum('flavor').values()[('BTagMu',)] ) / np.sum( h[datasets_QCD].sum('dataset', 'flavor').values()[()] )
                            #print(histname_coffea)
                            #print("correct =", dataSum/QCDSum, "wrong =", wrong_factor, "ratio =", dataSum/QCDSum/wrong_factor)
                        else:
                            QCD = h[datasets_QCD].sum('dataset')

                        #### storing into dict
                        for iflav in QCD.values():
                            tmpValue, sumw2 = QCD[iflav].sum('flavor').values(sumw2=True)[()]
                            #tmpValue, sumw2 = QCD_rescaled[iflav].sum('flavor').values(sumw2=True)[()]
                            outputDict[ histname+'_QCD_'+iflav[0] ] = [ tmpValue, sumw2  ]
                        tmpValue, sumw2 = h[args.data].sum('flavor').values(sumw2=True)[('BTagMu',)]
                        outputDict[ histname+'_BtagMu' ] = [ tmpValue, sumw2 ]

#### Saving into pickle
output_dir = args.outputDir if args.outputDir else os.getcwd()+"/histograms/"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
#outputFileName = output_dir + ( args.output if args.output else args.input.split('/')[-1].replace('coffea7', 'pkl')  )
outputFileName = output_dir + ( args.output if args.output else args.input.split('/')[-1].replace(args.input.split('.')[-1], 'pkl')  )
outputFile = open( outputFileName, 'wb'  )
pickle.dump( outputDict, outputFile, protocol=2 )
outputFile.close()

