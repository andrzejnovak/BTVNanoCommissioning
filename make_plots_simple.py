import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import mplhep as hep
from coffea.util import load
from coffea.hist import plot
import coffea.hist as hist
import itertools
import os
import time
from multiprocessing import Pool
from parameters import histogram_settings, flavors_color, flavor_opts, flavors_order, lumi, xsecs, AK8Taggers

parser = argparse.ArgumentParser(description='Plot histograms from coffea file')
parser.add_argument('-i', '--input', type=str, help='Input histogram filename', required=True)
parser.add_argument('-o', '--output', type=str, default='', help='Output directory')
parser.add_argument('--outputDir', type=str, default=None, help='Output directory')
parser.add_argument('-s', '--scale', type=str, default='linear', help='Plot y-axis scale', required=False)
parser.add_argument('-d', '--dense', action='store_true', default=False, help='Normalized plots')
parser.add_argument('--campaign', type=str, choices={'EOY', 'UL'}, help='Dataset campaign.', required=True)
parser.add_argument('--year', type=str, choices=['2016', '2017', '2018'], help='Year of data/MC samples', required=True)
parser.add_argument('--hist2d', action='store_true', default=False, help='Plot only 2D histograms')
parser.add_argument('--proxy', action='store_true', help='Plot proxy and signal comparison')
parser.add_argument('--only', action='store', default='', help='Plot only one histogram')
parser.add_argument('--test', action='store_true', default=False, help='Test with lower stats.')
parser.add_argument('--data', type=str, default='BTagMu', help='Data sample name')
parser.add_argument('--selection', type=str, default='all', help='Plot only plots with this selection. ("all" to plot all the selections in file)')
parser.add_argument('--passfail', action='store_true', default=False, help='Plots in pass + fail regions')
parser.add_argument('-n', '--normed', action='store_true', default=False, help='Normalized overlayed plots')
parser.add_argument('-j', '--workers', type=int, default=12, help='Number of workers (cores/threads) to use for multi-worker execution (default: %(default)s)')

args = parser.parse_args()

print("Starting ", end='')
print(time.ctime())
start = time.time()
print("Running with options:")
print("    ", args)

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
    scaleXS[isam] = 1 if isam.startswith('BTag') else xsecs[isam]/accumulator['sumw'][isam]

data_err_opts = {
    'linestyle': 'none',
    'marker': '.',
    'markersize': 10.,
    'color': 'k',
    'elinewidth': 1,
}

qcd_opts = {
    'facecolor': 'None',
    'edgecolor': 'blue',
    'linestyle': '-',
    'linewidth': 2,
    'alpha': 0.7
}

signal_opts = {
    'facecolor': 'None',
    'edgecolor': ['green', 'red'],
    'linestyle': ['--', '-'],
    'linewidth': 2,
    'alpha': 0.7
}

ggH_opts = {
    'bb' : {
        'facecolor': 'None',
        'edgecolor': 'green',
        'linestyle': '--',
        'linewidth': 2,
        'alpha': 0.7
    },
    'cc': {
        'facecolor': 'None',
        'edgecolor': 'red',
        'linestyle': '--',
        'linewidth': 2,
        'alpha': 0.7
    }
}

selection = {
    'basic' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 250 GeV$"+"\n"+
                  r"$m_{SD} > 20 GeV$"+"\n"),
    'pt350msd50' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 350 GeV$"+"\n"+
                  r"$m_{SD} > 50 GeV$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
    'msd100tau06' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 350 GeV$"+"\n"+
                  r"$m_{SD} > 100 GeV$"+"\n"+
                  r"$\tau_{21} < 0.6$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
    'msd100tau03' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 350 GeV$"+"\n"+
                  r"$m_{SD} > 100 GeV$"+"\n"+
                  r"$\tau_{21} < 0.3$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
    'pt400msd100tau06' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 400 GeV$"+"\n"+
                  r"$m_{SD} > 100 GeV$"+"\n"+
                  r"$\tau_{21} < 0.6$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
}

#_final_mask = ['msd100tau06', 'pt400msd100tau06']
_final_mask = ['msd100tau06', 'msd100tau03']
_mask_DDX = {
            'DDB' : {
                #'L' : XX,
                'M' : 0.7
            },
            'DDC' : {
                #'L' : XX,
                'M' : 0.45
            },
}
for mask_f in _final_mask:
    for DDX in _mask_DDX.keys():
        for wp, cut in _mask_DDX[DDX].items():
            selection[f'{mask_f}{DDX}pass{wp}wp'] = selection[mask_f]
            selection[f'{mask_f}{DDX}pass{wp}wp'] += f"{DDX}vLV2 > {str(cut)}"+"\n"
            selection[f'{mask_f}{DDX}fail{wp}wp'] = selection[mask_f]
            selection[f'{mask_f}{DDX}fail{wp}wp'] += f"{DDX}vLV2 < {str(cut)}"+"\n"
"""
selection_basic = (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 250 GeV$"+"\n"+
                  r"$m_{SD} > 20 GeV$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n")

selection_msd100tau06 = (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 250 GeV$"+"\n"+
                  r"$m_{SD} > 100 GeV$"+"\n"+
                  r"$\tau_{21} < 0.6$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n")
"""

totalLumi = 'TEST' if args.test else lumi[args.campaign][args.year]

plt.style.use([hep.style.ROOT, {'font.size': 16}])
plot_dir = args.outputDir if args.outputDir else os.getcwd()+"/plots/" + args.output + "/"
if not os.path.exists(plot_dir):
    os.makedirs(plot_dir)

def make_plots(entrystart, entrystop):
    _accumulator = dict(list(accumulator.items())[entrystart:entrystop])
    for histname in _accumulator:
        if args.only and not (args.only in histname): continue
        if not args.selection.startswith('all') and not ( args.selection in histname  ): continue
        if not args.passfail and (any(r in histname for r in ['pass', 'fail'])): continue
        if histname in ["sumw", "nbtagmu", "nbtagmu_event_level", "nfatjet"]: continue

        if any([histname.startswith('cutflow')]): break
        sel = [s for s in selection.keys() if s in histname][0]
        selection_text = selection[sel]
        h = _accumulator[histname]
        varname = h.fields[-1]
        varlabel = h.axis(varname).label
        if histname.startswith( tuple(histogram_settings[args.campaign]['variables'].keys()) ):
            h = h.rebin(varname, hist.Bin(varname, varlabel, **histogram_settings[args.campaign]['variables']['_'.join(histname.split('_')[:2])]['binning']))
        h.scale( scaleXS, axis='dataset' )
        
        ##### grouping flavor
        flavors = [str(s) for s in h.axis('flavor').identifiers() if str(s) != 'flavor']
        mapping_flavor = {f : [f] for f in flavors}
        flavors_to_merge = ['bb', 'b', 'cc', 'c']
        for flav in flavors_to_merge:
            mapping_flavor.pop(flav)
        mapping_flavor['b_bb'] = ['b', 'bb']
        mapping_flavor['c_cc'] = ['c', 'cc']
        
        h = h.group("flavor", hist.Cat("flavor", "Flavor"), mapping_flavor)        
        flavors = [item for item in list(mapping_flavor.keys()) if 'Data' not in item]
        #flavors = ['b_bb', 'c_cc', 'l']
        order = flavors_order['btagDDBvLV2']
        if ('btagDDCvLV2' in histname) | ('particleNetMD_Xcc' in histname):
            order = flavors_order['btagDDCvLV2']

        flavor_opts['facecolor'] = [flavors_color[f.split('_')[-1]] for f in order if 'Data' not in f]

        ##### grouping data and QCD datasets
        datasets = [str(s) for s in h.axis('dataset').identifiers() if str(s) != 'dataset']
        mapping = {
            r'QCD ($\mu$ enriched)' : [dataset for dataset in datasets if 'QCD_Pt' in dataset],
            r'BTagMu': [ idata for idata in datasets if args.data in idata ],
        }
        for dataset in datasets:
            if 'QCD' in dataset: continue
            if args.data in dataset: continue
            mapping[dataset] = [dataset]
        datasets = mapping.keys()
        datasets_data  = [dataset for dataset in datasets if args.data in dataset]
        datasets_QCD = [dataset for dataset in datasets if ((args.data not in dataset) & ('GluGlu' not in dataset))]
        datasets_ggH = [dataset for dataset in datasets if 'GluGlu' in dataset]
        h = h.group("dataset", hist.Cat("dataset", "Dataset"), mapping)

        if (not 'hist2d' in histname) & (not args.hist2d):

            print("Plotting", histname)
            dataSum = np.sum( h[args.data].sum('flavor').values()[('BTagMu',)] )
            QCDSum = np.sum( h[datasets_QCD].sum('dataset', 'flavor').values()[()] )
            QCD_rescaled = h[datasets_QCD].sum('dataset')
            QCD_rescaled.scale( dataSum/QCDSum )
            QCDALL_rescaled = h[datasets_QCD].sum('dataset', 'flavor')
            QCDALL_rescaled.scale( dataSum/QCDSum )

            ggH_rescaled = h[datasets_ggH].sum('flavor')
            scale_ggH = 100
            ggH_rescaled.scale(scale_ggH)
            maxY = 1.2 *max( [ max(h[args.data].sum('flavor').values()[('BTagMu',)]),  max(QCDALL_rescaled.values()[()]) ] )

            fig, (ax, rax) = plt.subplots(2, 1, figsize=(12,12), gridspec_kw={"height_ratios": (3, 1)}, sharex=True)
            #fig_normed, (ax_normed, rax_normed) = plt.subplots(2, 1, figsize=(12,12), gridspec_kw={"height_ratios": (3, 1)}, sharex=True)
            fig.subplots_adjust(hspace=.07)
            plot.plot1d(QCD_rescaled, ax=ax, legend_opts={'loc':1}, fill_opts=flavor_opts, order=order, stack=True)
            plot.plot1d(h[args.data].sum('flavor'), ax=ax, legend_opts={'loc':1}, error_opts=data_err_opts, clear=False)
            #plot.plot1d(ggH_rescaled, ax=ax, legend_opts={'loc':1}, fill_opts=signal_opts, stack=False, clear=False)
            plot.plotratio(num=h[datasets_data].sum('dataset', 'flavor'), denom=QCDALL_rescaled, ax=rax,
                           error_opts=data_err_opts, denom_fill_opts={}, guide_opts={}, unc='num')
            handles, labels = ax.get_legend_handles_labels()
            for (i, label) in enumerate(labels):
                if "GluGlu" in label:
                    if "BB" in label:
                        labels[i] = r"ggH$\rightarrow$bb $\times$" + str(scale_ggH)
                    if "CC" in label:
                        labels[i] = r"ggH$\rightarrow$cc $\times$" + str(scale_ggH)
            hep.cms.text("Preliminary", ax=ax)
            hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax)
            ax.legend(handles, labels)
            rax.set_ylabel('Data/MC')
            rax.set_ylim(0.0,2.0)
            rax.set_yticks([0.5, 1.0, 1.5])
            if histname.startswith( tuple(histogram_settings[args.campaign]['variables'].keys()) ):
                ax.set_xlim(**histogram_settings[args.campaign]['variables']['_'.join(histname.split('_')[:2])]['xlim'])
                rax.set_xlim(**histogram_settings[args.campaign]['variables']['_'.join(histname.split('_')[:2])]['xlim'])
            x_low, x_high = rax.get_xlim()
            rax.hlines([0.5, 1.5], x_low, x_high, colors='grey', linestyles='dashed', linewidth=1)
            if ('Pt-' in histname.split('_')[-1]):
                pt_low, pt_high = [pt for pt in histname.split('_')[-1].split('Pt-')[-1].split('to')]
                if pt_high == 'Inf':
                    pt_high = r'$\infty$'
                selection_text = selection[sel] + r"$p_T$ bin:" + f" ({pt_low}, {pt_high}) [GeV]"+"\n"
            at = AnchoredText(selection_text, loc=2, frameon=False)
            ax.add_artist(at)
            if histname.startswith("btag"):
                ax.semilogy()
            if (not args.dense) & (args.scale == "log"):
                ax.semilogy()                
                ax.set_ylim(0.1, 10**7)
            else: ax.set_ylim(0,maxY)
            #hep.mpl_magic(ax)
            filepath = f"{plot_dir}{histname}.png"
            if args.scale != parser.get_default('scale'):
                #rax.set_ylim(0.1,10)
                filepath = filepath.replace(".png", "_" + args.scale + ".png")
            print("Saving", filepath)
            plt.savefig(filepath, dpi=300, format="png")
            plt.close(fig)

            if args.proxy & (any(tagger in histname for tagger in AK8Taggers) | ('logsv1mass' in histname)):
                if any(r in histname for r in ['pass', 'fail']): continue
                QCD = {}
                ggH = {}
                for dataset in datasets:
                    if 'QCD' in dataset:
                        histo_QCD = h[dataset]
                        QCD['bb'] = h[(dataset, 'bb')]
                        QCD['cc'] = h[(dataset, 'cc')]
                    if 'GluGluHToBB' in dataset:
                        histo_BB  = h[dataset]
                        ggH['bb'] = h[(dataset, 'bb')]
                    if 'GluGluHToCC' in dataset:
                        histo_CC  = h[dataset]
                        ggH['cc'] = h[(dataset, 'cc')]

                for xx in QCD.keys():
                    for scale in ['linear', 'log']:
                        fig, ax = plt.subplots(1, 1, figsize=(9,9))
                        plot.plot1d(QCD[xx].sum('flavor'), ax=ax, legend_opts={'loc':1}, density=True, fill_opts=qcd_opts, stack=True)
                        plot.plot1d(ggH[xx].sum('flavor'), ax=ax, legend_opts={'loc':1}, density=True, fill_opts=ggH_opts[xx], stack=False, clear=False)
                        hep.cms.text("Simulation", ax=ax)
                        hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax)
                        ax.set_yscale(scale)
                        if scale == 'log':
                            ax.set_ylim(10**(-3), 10**3)
                        ax.set_ylabel('a.u.')
                        handles, labels = ax.get_legend_handles_labels()
                        for (i, label) in enumerate(labels):
                            if "QCD" in label:
                                labels[i] = rf"g$\rightarrow${xx}"
                            if "GluGlu" in label:
                                #labels[i] = r"ggH$\rightarrow${xx} ({xx} component)"
                                labels[i] = rf"ggH$\rightarrow${xx}"
                        ax.legend(handles, labels)

                        at = AnchoredText(selection_text, loc=2, frameon=False)
                        ax.add_artist(at)
                        filepath = f"{plot_dir}{histname}_ggH{xx}_{scale}.png"
                        print("Saving", filepath)
                        plt.savefig(filepath, dpi=300, format="png")
                        plt.close(fig)

        if args.hist2d:
            if (not 'btag' in histname) & (not 'sv' in histname):
                continue
            if not 'hist2d' in histname:
                continue
            print("Plotting", histname)

            if 'sv' in histname:
                fig, ax = plt.subplots(1, 1, figsize=(9,9))
                plot.plot2d(h.sum('dataset', 'flavor'), xaxis='logsv1mass', ax=ax)
                hep.cms.text("Preliminary", ax=ax)
                hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax)
                hep.cms.text("Preliminary", ax=ax)
                hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax)
                filepath = plot_dir + histname + ".png"
                print("Saving", filepath)
                plt.savefig(filepath, dpi=300, format="png")
                plt.close(fig)
            elif 'btag' in histname:
                for dataset in datasets:
                    if 'QCD' in dataset:
                        #histo_QCD = h[dataset].sum('dataset')
                        #histo_QCD_bb = h[dataset].sum('dataset')['bb']
                        #histo_QCD_cc = h[dataset].sum('dataset')['cc']
                        histo_QCD = h[dataset]
                        histo_QCD_bb = h[(dataset, '_bb')]
                        histo_QCD_cc = h[(dataset, '_cc')]
                    if 'GluGluHToBB' in dataset:
                        #histo_BB    = h[dataset].sum('dataset')
                        #histo_BB_bb = h[dataset].sum('dataset')['bb']
                        histo_BB    = h[dataset]
                        histo_BB_bb = h[(dataset, '_bb')]
                    if 'GluGluHToCC' in dataset:
                        #histo_CC    = h[dataset].sum('dataset')
                        #histo_CC_cc = h[dataset].sum('dataset')['cc']
                        histo_CC    = h[dataset]
                        histo_CC_cc = h[(dataset, '_cc')]
                xaxis = [axis.name for axis in histo_QCD.axes() if 'btag' in axis.name][0]

                for histo_GluGlu, dataset_GluGlu in zip([histo_BB, histo_CC], ['GluGluHToBB', 'GluGluHToCC']):
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24,9))
                    plot.plot2d(histo_QCD.sum('dataset', 'flavor'), xaxis=xaxis, ax=ax1)
                    plot.plot2d(histo_GluGlu.sum('dataset', 'flavor'), xaxis=xaxis, ax=ax2)
                    hep.cms.text("Preliminary", ax=ax1)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax1)
                    hep.cms.text("Preliminary", ax=ax2)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax2)
                    ax1.set_title('QCD')
                    ax2.set_title(dataset_GluGlu)
                    filepath = plot_dir + histname + "_" + dataset_GluGlu + ".png"
                    print("Saving", filepath)
                    plt.savefig(filepath, dpi=300, format="png")
                    plt.close(fig)

                for histo_GluGlu_xx, dataset_GluGlu_xx in zip([histo_BB_bb, histo_CC_cc], ['GluGluHToBB (bb)', 'GluGluHToCC (cc)']):
                    if dataset_GluGlu_xx == 'GluGluHToBB (bb)':
                        histo_QCD_xx = histo_QCD_bb
                        qcd_label = 'QCD (bb)'
                    elif dataset_GluGlu_xx == 'GluGluHToCC (cc)':
                        histo_QCD_xx = histo_QCD_cc
                        qcd_label = 'QCD (cc)'
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24,9))
                    plot.plot2d(histo_QCD_xx.sum('dataset', 'flavor'), xaxis=xaxis, ax=ax1)
                    plot.plot2d(histo_GluGlu_xx.sum('dataset', 'flavor'), xaxis=xaxis, ax=ax2)
                    hep.cms.text("Preliminary", ax=ax1)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax1)
                    hep.cms.text("Preliminary", ax=ax2)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax2)
                    ax1.set_title(qcd_label)
                    ax2.set_title(dataset_GluGlu_xx)
                    filepath = plot_dir + histname + "_" + '_'.join(dataset_GluGlu_xx.strip(')').split(' (')) + ".png"
                    print("Saving", filepath)
                    plt.savefig(filepath, dpi=300, format="png")
                    plt.close(fig)

                for flavor in flavors:
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24,9))
                    plot.plot2d(h.sum('dataset')['_l'].sum('flavor'), xaxis=xaxis, ax=ax1)
                    plot.plot2d(h.sum('dataset')[flavor].sum('flavor'), xaxis=xaxis, ax=ax2)
                    hep.cms.text("Preliminary", ax=ax1)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax1)
                    hep.cms.text("Preliminary", ax=ax2)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=18, ax=ax2)
                    ax1.set_title('light')
                    ax2.set_title(flavor)
                    filepath = plot_dir + histname + "_" + flavor + ".png"
                    print("Saving", filepath)
                    plt.savefig(filepath, dpi=300, format="png")
                    plt.close(fig)
    return

NtotHists = len(accumulator.keys())
NHistsToPlot = len([key for key in accumulator.keys() if args.only in key])
print("# tot histograms = ", NtotHists)
print("# histograms to plot = ", NHistsToPlot)
delimiters = np.linspace(0, NtotHists, args.workers + 1).astype(int)
chunks = [(delimiters[i], delimiters[i+1]) for i in range(len(delimiters[:-1]))]
pool = Pool()
pool.starmap(make_plots, chunks)
pool.close()

end = time.time()
runTime = round(end-start)
print("Finishing ", end='')
print(time.ctime())
print(f"Drawn {NHistsToPlot} plots in {runTime} s")