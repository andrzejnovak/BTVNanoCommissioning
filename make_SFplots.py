import os
import sys
import argparse
from copy import deepcopy

import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText

import uproot
import mplhep as hep

from coffea.util import load
from coffea.hist import plot
from coffea.hist.plot import poisson_interval
import coffea.hist as hist

from lib.luminosity import rescale
from parameters import histogram_settings, flavors_color, flavor_opts, lumi, xsecs, PtBinning, AK8TaggerWP

fontsize = 12

parser = argparse.ArgumentParser(description='Plot histograms from FitDiagnostic file')
parser.add_argument('-i', '--input', type=str, help='Input histogram filename', required=True)
parser.add_argument('-o', '--outputDir', type=str, default='', help='Output directory', required=False)
#parser.add_argument('-s', '--scale', type=str, default='linear', help='Plot y-axis scale', required=False)
#parser.add_argument('-d', '--dense', action='store_true', default=False, help='Normalized plots')
parser.add_argument('--campaign', type=str, choices={'EOY', 'UL'}, help='Dataset campaign.', required=True)
parser.add_argument('--year', type=str, choices=['2016', '2017', '2018'], help='Year of data/MC samples', required=True)
parser.add_argument('--vfp', type=str, default=None, choices=['pre', 'post'], help='Year of data/MC samples', required=False)
parser.add_argument('--var', type=str, default='sv_logsv1mass', help='Variable used in the template fit.', required=False)
#parser.add_argument('--wpt', type=str, choices={'', 'M', 'H'}, default='', help='Pt bin')
parser.add_argument('--data', type=str, default='BTagMu', help='Data sample name')
#parser.add_argument('--selection', type=str, default='all', help='Plot only plots with this selection. ("all" to plot all the selections in file)', required=True)
parser.add_argument('--selection', type=str, default='msd100tau06', help='Selection to compute SF.', required=True)
parser.add_argument('--tagger', type=str, help='Tagger to calibrate.', required=False)
#parser.add_argument('--pt', type=int, default=500, help='Pt cut.', required=True)
#parser.add_argument('--MwpDDB', type=float, default=0.7, help='Medium working point for DDB.', required=True)
parser.add_argument('--passonly', action='store_true', default=False, help='Fit pass region only')
parser.add_argument('--debug', action='store_true', default=False, help='Activate debug printout', required=False)
parser.add_argument('--crop', action='store_true', default=False, help='Produce cropped plots in dedicated sub-directories', required=False)
parser.add_argument('--mergebbcc', action='store_true', default=False, help='Merge bb+cc')

args = parser.parse_args()
pt_interval = PtBinning[args.campaign][args.year]
if args.campaign == 'EOY':
    pt_interval['Inclusive'] = (pt_interval['M'][0], 'Inf')
else:
    pt_interval['Inclusive'] = (pt_interval['L'][0], 'Inf')

if (args.campaign == 'UL') & (args.year == '2016'):
    if args.vfp == parser.get_default('vfp'):
        sys.exit("For 2016UL, specify if 'pre' or 'post' VFP.")
    else:
        vfp_label = {'pre' : '-PreVFP', 'post' : '-PostVFP'}[args.vfp]
        totalLumi = lumi[args.campaign][f"{args.year}{vfp_label}"]
else:
    totalLumi = lumi[args.campaign][args.year]

if args.tagger in AK8TaggerWP[args.campaign][args.year].keys():
    taggers = [args.tagger]
else:
    taggers = AK8TaggerWP[args.campaign][args.year].keys()
ptbins = ['Inclusive', 'L', 'M', 'H', 'M+H']

inputDir = None
if os.path.isdir(args.input):
    inputDir = args.input
    if not inputDir.endswith('/'):
        inputDir = inputDir + '/'
    #if args.selection:
    #    if any([tagger in args.selection for tagger in taggers]):
    #        taggers = [tagger for tagger in taggers if tagger in inputDir]

elif os.path.isfile(args.input):
    inputDir = '/'.join(args.input.split('/')[:-2]) + '/'
    if not args.input.endswith('.root'):
        sys.exit("Only ROOT files are accepted as an input")
    else:
        if not args.selection:
            sys.exit("Specify the selection")
        else:
            if not args.tagger:
                sys.exit("Specify the tagger")
            taggers = [tagger for tagger in taggers if tagger == args.tagger]
            ptbins = [ptbin for ptbin in ptbins if ptbin in args.input.split('/')[-1]]
else:
    print(args.input)
    raise NotImplementedError

regions = ['sfpass', 'sffail']
if args.passonly:
    regions = ['sfpass']

data_err_opts = {
    'linestyle': 'none',
    'marker': '.',
    'markersize': 10.,
    'color': 'k',
    'elinewidth': 1,
}

qcd_opts = {
    'facecolor': 'yellow',
    'edgecolor': 'black',
    'alpha': 1.0
}

flavor_normed_opts = {
    'facecolor': 'None',
    'edgecolor': 'green',
    'linestyle': '-',
    'linewidth': 2,
    'alpha': 0.7
}

err_opts = {
    'linestyle': '-',
    'marker': '.',
    'markersize': 10,
    'color': 'k',
    'elinewidth': 0,
}

MC_opts = {
    'facecolor': (0, 0, 0, 0),
}

selection = {}
"""
selection = {
    'basic' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 250 GeV$"+"\n"+
                  r"$m_{SD} > 20 GeV$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
    'pt350msd50' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 350 GeV$"+"\n"+
                  r"$m_{SD} > 50 GeV$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
    'msd100tau06' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 350 GeV$"+"\n"+
                  r"$m_{SD} > 100 GeV$"+"\n"+
                  r"$\tau_{21} < 0.6$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
    'pt400msd100tau06' : (r"$\geq$1 AK8 jets"+"\n"+
                  r"$p_T > 400 GeV$"+"\n"+
                  r"$m_{SD} > 100 GeV$"+"\n"+
                  r"$\tau_{21} < 0.6$"+"\n"+
                  r"$\geq$2 $\mu$-tagged AK4 subjets"+"\n"),
}
"""

#_final_mask = ['msd100tau06', 'pt400msd100tau06']
_final_mask = ['msd100tau06', 'msd100tau06ggHcc']

_mask_DDX = AK8TaggerWP[args.campaign][args.year]

xlabel = {
    'fatjet_jetproba' : r"jet Probability",
    'sv_logsv1mass'   : r"lead. FatJet log($m_{SV,1}$/GeV)",
}

for mask_f in _final_mask:
    for DDX in _mask_DDX.keys():
        for wp, cut in _mask_DDX[DDX].items():
            selection['{}{}pass{}wp'.format(mask_f, DDX, wp)] = r"{} $\in$ {}".format(DDX, cut)+"\n"
            selection['{}{}fail{}wp'.format(mask_f, DDX, wp)] = r"{} $\notin$ {}".format(DDX, cut)+"\n"

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

plt.style.use([hep.style.ROOT, {'font.size': 16}])

print("taggers:", taggers)
for tagger in taggers:
    for wp in [ 'L', 'M', 'H' ]:
        selDir = '{}{}{}wp/'.format(args.selection, tagger, wp)
        plot_dir = args.outputDir if args.outputDir else inputDir + selDir
        if not os.path.exists(plot_dir):
            print("Directory {} does not exist".format(plot_dir))
            continue
        if not plot_dir.endswith('/'):
            plot_dir = plot_dir + '/'
        for wpt in ptbins:
            filename = 'fitDiagnostics{}wp{}Pt.root'.format(wp, wpt)
            filepath = inputDir + selDir + filename
            if not os.path.exists(filepath):
                print(f"File {filepath} does not exist.")
                continue

            if args.mergebbcc:
                flavors = ['l', 'bb_cc']
            else:
                if (('DDB' in tagger) | ('Xbb' in tagger)):
                    flavors = ['l', 'c_cc', 'b_bb']
                elif (('DDC' in tagger) | ('Xcc' in tagger)):
                    flavors = ['l', 'b_bb', 'c_cc']
                else:
                    raise NotImplementedError
            flavor_opts['facecolor'] = [flavors_color[f.split('_')[-1]] for f in flavors]
            flavor_axis  = hist.Cat("flavor",   "Flavor")
            varname = args.var.split('_')[1]
            observable_axis  = hist.Bin(varname,  xlabel[args.var], **histogram_settings[args.campaign]['postfit'][args.var]['binning'])
            output = {}

            for region in ['sfpass', 'sffail']:
                for fit in ['prefit', 'fit_s']:
                    output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)] = hist.Hist("entries", flavor_axis, observable_axis)

            line = ''.join((8 + len(filepath))*['-'])
            print(line)
            print(f"Opening {filepath}")
            f = uproot.open(filepath)
            failedFit = False
            if 'shapes_fit_s;1' not in f.keys():
                failedFit = True
                print("Fit failed.")
                continue
            for region in regions:
                fig, axes = plt.subplots(2, 2, figsize=(12,7), gridspec_kw={"height_ratios": (2.5, 1)}, sharex=True)
                fig_normed, axes_normed = plt.subplots(2, 2, figsize=(12,7), gridspec_kw={"height_ratios": (2.5, 1)}, sharex=True)
                #flavors_to_remove = []
                for i, fit in enumerate(['prefit', 'fit_s']):
                #for i, fit in enumerate(['prefit']):
                    #ax = axes[i]
                    covar, binsX, binsY = f['shapes_{}/{}/total_covar;1'.format(fit, region)].to_numpy()
                    flavors_to_remove = []
                    max_weights_normed = []
                    for (j, flavor) in enumerate(flavors):
                        histname = 'shapes_{}/{}/{};1'.format(fit, region, flavor)
                        if histname not in f.keys():
                            flavors_to_remove.append(flavor)
                            continue
                        h = f[histname]
                        weights, bins = h.to_numpy()
                        binwidth = np.diff(bins)
                        weights = weights*binwidth                        
                        values = (bins[1:] - 0.5*binwidth)
                        if args.debug:
                            print(values)
                            print(flavor, region, fit, weights)
                        
                        values_to_fill = np.concatenate(np.array([values[i]*np.ones(math.ceil(abs(w))) for i,w in enumerate(weights)], dtype=object))
                        weights_to_fill = np.concatenate(np.array([w/math.ceil(abs(w))*np.ones(math.ceil(abs(w))) for i,w in enumerate(weights)], dtype=object))
                        if args.debug:
                            print(flavor, region, fit, values_to_fill)
                            print(flavor, region, fit, weights_to_fill)
                        #output[f'shape_{fit}_{region}{tagger}{args.year}'].fill(flavor=flavor, jetproba=values, weight=weights)
                        #output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)].fill(flavor=flavor, logsv1mass=values, weight=weights)
                        #output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)].fill(flavor=flavor, logsv1mass=values_to_fill, weight=weights_to_fill)
                        output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)].fill(flavor=flavor, logsv1mass=np.array(values_to_fill, dtype='float64'), weight=np.array(weights_to_fill, dtype='float64'))
                        if args.debug:
                            print(flavor_opts)
                        weights_normed, bins, patches = axes_normed[0][i].hist(values, bins, weights=weights, edgecolor=flavor_opts['facecolor'][j], histtype='step', density=True, stacked=False, label=flavor)
                        max_weights_normed.append(max(weights_normed))

                    flavors_to_plot = flavors[:]
                    flavor_opts_to_plot = deepcopy(flavor_opts)
                    #print(flavors_to_remove)
                    for flavor in flavors:
                        if flavor in flavors_to_remove:
                            flavor_opts_to_plot['facecolor'].pop(flavors.index(flavor))
                            #flavor_opts['facecolor'].pop(flavors.index(flavor))
                            flavors_to_plot.remove(flavor)
                            #flavors.remove(flavor)

                    plot.plot1d(output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][flavors_to_plot], ax=axes[0][i], legend_opts={'loc':1}, fill_opts=flavor_opts_to_plot, order=flavors_to_plot, stack=True)
                    MC_sum = output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][flavors_to_plot].sum('flavor')
                    MC_var = np.diag(covar)
                    MC_values = MC_sum.values()[()]
                    print(MC_values)
                    edges = MC_sum.axis(varname).edges(overflow='none')
                    print(edges)
                    print(len(MC_var))
                    MC_unc = np.diff(edges) * np.concatenate( (np.zeros(len(MC_values) - len(MC_var)), np.sqrt(MC_var)) )
                    lo = MC_values - MC_unc
                    hi = MC_values + MC_unc
                    MC_unc_band = np.array([lo, hi])
                    hatch_density = 4
                    MC_unc_opts = {"step": "post", "color": (0, 0, 0, 0.4), "facecolor": (0, 0, 0, 0.0), "linewidth": 0, "hatch": '/'*hatch_density, "zorder": 2}
                    axes[0][i].fill_between(edges, np.r_[MC_unc_band[0], MC_unc_band[0, -1]], np.r_[MC_unc_band[1], MC_unc_band[1, -1]], **MC_unc_opts, label='MC unc.')
                    #for (j, flavor) in enumerate(flavors):
                        #flavor_normed_opts['facecolor'] = flavor_opts['facecolor'][j]
                        #flavor_normed_opts['edgecolor'] = flavor_opts['facecolor'][j]
                        #err_opts['color'] = flavor_opts['facecolor'][j]
                        #plot.plot1d(output[f'shape_{fit}_{region}{tagger}{args.year}'][flavor], ax=axes_normed[0][i], density=True, legend_opts={'loc':1}, fill_opts=flavor_normed_opts, error_opts=err_opts, stack=False, clear=False)
                        #plot.plot1d(output[f'shape_{fit}_{region}{tagger}{args.year}'][flavor], ax=axes_normed[0][i], density=True, legend_opts={'loc':1}, error_opts=err_opts, stack=False, clear=False)
                    data = f['shapes_{}/{}/data;1'.format(fit, region)]
                    data_values = data.values()[0]
                    data_weights = data.values()[1]*binwidth
                    data_values_to_fill = np.concatenate(np.array([data_values[i]*np.ones(math.ceil(w)) for i,w in enumerate(data_weights)], dtype=object))
                    data_sum = np.sum(data_weights*binwidth)
                    data_weights_normed = data.values()[1]*binwidth/data_sum
                    errors = data.errors('mean')[1]*binwidth
                    errors_normed = data.errors('mean')[1]*binwidth/data_sum
                    #output[f'shape_{fit}_{region}{tagger}{args.year}'].fill(flavor=args.data, jetproba=data.values()[0], weight=data_weights)
                    #output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)].fill(flavor=args.data, logsv1mass=data_values, weight=data_weights)
                    #output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)].fill(flavor=args.data, logsv1mass=data_values_to_fill)
                    output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)].fill(flavor=args.data, logsv1mass=np.array(data_values_to_fill, dtype='float64'))
                    axes[0][i].errorbar(data_values, data_weights, yerr=errors, marker='.', linestyle='', markersize=10, elinewidth=1, color='black', label=args.data)
                    axes_normed[0][i].errorbar(data_values, data_weights_normed, yerr=errors_normed, marker='.', linestyle='', markersize=10, elinewidth=1, color='black', label=args.data)
                    #plot.plot1d(output[f'shape_{fit}_{region}{tagger}{args.year}'][args.data], ax=ax'es[0][i], legend_opts={'loc':1}, error_opts=data_err_opts, clear=False)
                    #axes[0][i].set_title('shapes_{} '.format(fit) + region + ' ({}, {})'.format(tagger, args.year))
                    #axes_normed[0][i].set_title('shapes_{} '.format(fit) + region + ' ({}, {})'.format(tagger, args.year))
                    resize = 1.8
                    if i == 0:
                        axes[0][i].set_ylim(0.0, resize*max(data_weights))
                        axes_normed[0][i].set_ylim(0.0, resize*max(max(data_weights_normed), max(max_weights_normed)))
                    elif i == 1:
                        axes[0][i].set_ylim(axes[0][0].get_ylim())
                        axes_normed[0][i].set_ylim(axes_normed[0][0].get_ylim())
                    handles, labels = axes[0][i].get_legend_handles_labels()
                    for (l, label) in enumerate(labels):
                        if '_' in label:
                            labels[l] = label.replace('_', ' + ')
                        if label == 'l':
                            labels[l] = 'light'
                        if label == args.data:
                            labels[l] = 'data'
                    axes[0][i].legend(handles, labels, loc='upper right')
                    handles.pop(-2)
                    labels.pop(-2)
                    axes_normed[0][i].legend(handles, labels, loc='upper right')
                    hep.cms.text("Preliminary", ax=axes[0][i], fontsize=fontsize)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=fontsize, ax=axes[0][i])
                    hep.cms.text("Preliminary", ax=axes_normed[0][i], fontsize=fontsize)
                    hep.cms.lumitext(text=f'{totalLumi}' + r' fb$^{-1}$, 13 TeV,' + f' {args.year}', fontsize=fontsize, ax=axes_normed[0][i])
                    pt_low, pt_high = pt_interval[wpt]
                    if pt_high == 'Inf':
                        pt_high = r'$\infty$'
                    text = selection[f'{args.selection}{tagger}{region[2:]}{wp}wp'] + r"$p_T$:" + f" ({pt_low}, {pt_high}) [GeV]"+"\n"
                    at = AnchoredText(text, loc='upper left', prop={'fontsize' : fontsize}, frameon=False)
                    at_normed = AnchoredText(text, loc='upper left', prop={'fontsize' : fontsize}, frameon=False)
                    axes[0][i].add_artist(at)
                    axes_normed[0][i].add_artist(at_normed)
                    num = output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][args.data].sum('flavor')
                    if fit == 'prefit':
                        plot.plotratio(num=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][args.data].sum('flavor'),
                                       denom=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][flavors].sum('flavor'),
                                       ax=axes[1][i],
                                       error_opts=data_err_opts, denom_fill_opts=None, guide_opts={},
                                       unc='num')
                        plot.plotratio(num=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][args.data].sum('flavor'),
                                       denom=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][flavors].sum('flavor'),
                                       ax=axes_normed[1][i],
                                       error_opts=data_err_opts, denom_fill_opts=None, guide_opts={},
                                       unc='num')
                    elif fit == 'fit_s':
                        plot.plotratio(num=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][args.data].sum('flavor'),
                                       denom=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][flavors].sum('flavor'),
                                       ax=axes[1][i],
                                       error_opts=data_err_opts, denom_fill_opts=None, guide_opts={},
                                       #error_opts=data_err_opts, denom_fill_opts=MC_opts, guide_opts={},
                                       unc='num')
                        plot.plotratio(num=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][args.data].sum('flavor'),
                                       denom=output['shape_{}_{}{}{}'.format(fit, region, tagger, args.year)][flavors].sum('flavor'),
                                       ax=axes_normed[1][i],
                                       error_opts=data_err_opts, denom_fill_opts=None, guide_opts={},
                                       #error_opts=data_err_opts, denom_fill_opts=MC_opts, guide_opts={},
                                       unc='num')
                    unity = np.ones_like(MC_values)
                    denom_unc = poisson_interval(unity, MC_unc**2 / MC_values ** 2)
                    axes[1][i].fill_between(edges, np.r_[denom_unc[0], denom_unc[0, -1]], np.r_[denom_unc[1], denom_unc[1, -1]], **MC_unc_opts, label='MC unc.')
                    axes[1][i].set_xlim(**histogram_settings[args.campaign]['postfit']['sv_logsv1mass']['xlim'])
                    axes_normed[1][i].set_xlim(**histogram_settings[args.campaign]['postfit']['sv_logsv1mass']['xlim'])
                    axes[1][i].set_ylim(0.0, 2.0)
                    axes_normed[1][i].set_ylim(0.0, 2.0)
                    axes[1][i].set_yticks([0.5, 1.0, 1.5])
                    axes_normed[1][i].set_yticks([0.5, 1.0, 1.5])
                    axes[1][i].hlines([0.5, 1.5], **histogram_settings[args.campaign]['postfit']['sv_logsv1mass']['xlim'], colors='grey', linestyles='dashed', linewidth=1)
                    axes_normed[1][i].hlines([0.5, 1.5], **histogram_settings[args.campaign]['postfit']['sv_logsv1mass']['xlim'], colors='grey', linestyles='dashed', linewidth=1)
                histname = 'shapes_{}{}{}Pt_{}.png'.format(region, tagger, wpt, args.year)
                fig.savefig(plot_dir + histname, dpi=300, format="png")
                fig_normed.savefig(plot_dir + histname.replace('.png', '_normed.png'), dpi=300, format="png")
            f.close()

            if args.crop:
                for region in regions:
                    length = histogram_settings[args.campaign]['crop'][region]['length']
                    height = histogram_settings[args.campaign]['crop'][region]['height']
                    cropCommand = f"convert -crop {length}x{height} {plot_dir}shapes_{region}{tagger}{wpt}Pt_{args.year}.png {plot_dir}shapes_{region}{tagger}{wpt}Pt_{args.year}_%d.png"
                    rmCommand = f"rm {plot_dir}*_2.png"
                    for command in [cropCommand, rmCommand]:
                        os.system( command )
                    for (i, fit) in enumerate(['prefit', 'postfit']):
                        sub_dir = plot_dir + fit + '/'
                        if not os.path.exists(sub_dir):
                            os.makedirs(sub_dir)
                        moveCommand = f"mv {plot_dir}*_{i}.png {sub_dir}/."
                        trimCommand = f"convert -trim {sub_dir}shapes_{region}{tagger}{wpt}Pt_{args.year}_{i}.png {sub_dir}shapes_{region}{tagger}{wpt}Pt_{args.year}_{fit}.png"
                        rmCommand = f"rm {sub_dir}*_{i}.png"
                        for command in [moveCommand, trimCommand, rmCommand]:
                            os.system( command )



                    
