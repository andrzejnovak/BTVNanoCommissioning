from __future__ import print_function, division
import sys
import os
import rhalphalib as rl
import numpy as np
import pandas as pd
import scipy.stats
import pickle
import uproot
import ROOT
from parameters import histogram_settings, sample_baseline_names, sample_merged_names, sample_splitflavor_names, fit_parameters, fit_extra_args, PtBinning

nPtBins = 3

def exec_me(command, dryRun=False, folder=False):
    
    print(command)
    if not dryRun:
        if folder: os.chdir(folder)
        os.system(command)

def rebin(h_vals, h_sumw2, bins, lo, hi):

    binwidth = bins[1] - bins[0]
    bin_centers = (bins + 0.5*binwidth)[:-1]
    mask = (bin_centers >= lo) & (bin_centers <= hi)
    idx = np.argwhere(mask)[0][0]
    mask_bins = np.concatenate((mask[:idx],[True],mask[idx:]))      # Add an extra True value for `bins` array
    h_vals = h_vals[mask]
    h_sumw2 = h_sumw2[mask]
    bins = bins[mask_bins]

    return h_vals, h_sumw2, bins

def get_templ(f, sample, obs, lo, hi, syst=None, sumw2=True):
    
    hist_name = sample
    #print([key for key in f.keys() if 'btagDDBvLV2passHwp' in key])
    if syst is not None:
        hist_name += "_" + syst
    h_vals = f[hist_name][0]
    h_sumw2 = f[hist_name][1]
    bins = obs.binning
    mergeTail = False
    # HARDCODED
    if ('logsv1mass' in obs.name) & (len(h_vals) == 80) & (mergeTail == True):
        h_vals  = h_vals[32:-8]
        h_sumw2 = h_sumw2[32:-8]
        bins = bins[32:-8]
        # rebinning
        val_N     = np.sum(h_vals[-7:])
        val_N_1   = np.sum(h_vals[-14:-7])
        sumw2_N   = np.sum(h_sumw2[-7:])
        sumw2_N_1 = np.sum(h_sumw2[-14:-7])
        bin_N   = 3.2
        bin_N_1 = 2.5
        h_vals  = h_vals[:-14]
        h_sumw2 = h_sumw2[:-14]
        bins = bins[:-14]
        h_vals  = np.concatenate((h_vals, [val_N_1, val_N]))
        h_sumw2 = np.concatenate((h_sumw2, [sumw2_N_1, sumw2_N]))
        bins = np.concatenate((bins, [2.5, 3.2]))
    #elif ('logsv1mass' in obs.name) & (len(h_vals) == 40):
    else:
        h_vals, h_sumw2, bins = rebin(h_vals, h_sumw2, bins, lo, hi)

    if not sumw2:
        return (h_vals, bins, obs.name)
    else:
        return (h_vals, bins, obs.name, h_sumw2)

def merge_pt_bins(template_1, template_2, data=False):

    if data:
        (h_vals_1, bins_1, obsname_1) = template_1
        (h_vals_2, bins_2, obsname_2) = template_2
    else:
        (h_vals_1, bins_1, obsname_1, h_sumw2_1) = template_1
        (h_vals_2, bins_2, obsname_2, h_sumw2_2) = template_2

    if ( (len(h_vals_1) != len(h_vals_2)) | (len(bins_1) != len(bins_2)) ):
        sys.exit("The histograms have a different number of bins")
    if( obsname_1 != obsname_2 ):
        sys.exit("Histograms of different observables cannot be merged")
    h_vals = h_vals_1 + h_vals_2
    if data:
        return (h_vals, bins_1, obsname_1)
    else:
        h_sumw2 = h_sumw2_1 + h_sumw2_2
        return (h_vals, bins_1, obsname_1, h_sumw2)

def test_sfmodel(tmpdir, var, lo, hi, inputFile, year, campaign, sel, tagger, wp, wpt='', pars_key=None, epsilon=0.0001, passonly=False, mergebbcc=False, fixbkg=False, splitflavor=False, mcstat=None, frac=None, flavorunc=1.20):
    pars = fit_parameters[pars_key][year]
    pars = pars[tagger][wp][wpt]

    lumi = rl.NuisanceParameter('CMS_lumi', 'lnN')
    jecs = rl.NuisanceParameter('CMS_jecs', 'lnN')
    pu = rl.NuisanceParameter('CMS_pu', 'lnN')

    overall  = rl.IndependentParameter('yield', 1., 0, 10)
    #if mergebbcc:
    #    bb_cc      = rl.IndependentParameter('bb_cc', **pars['bb_cc'])
    #    background = {
    #        'l'    : rl.NuisanceParameter('l', 'lnN'),
    #    }
    #else:
    #    signal     = {
    #        'c_cc': rl.IndependentParameter('c_cc', **pars['c_cc']),
    #        'b_bb': rl.IndependentParameter('b_bb', **pars['b_bb']),
    #    }
    #    background = {
    #        'b_bb' : rl.NuisanceParameter('b_bb', 'lnN'),
    #        'c_cc' : rl.NuisanceParameter('c_cc', 'lnN'),
    #        'l'    : rl.NuisanceParameter('l', 'lnN'),
    #    }

    if splitflavor:
        sample_names = sample_splitflavor_names
        flavor_fraction = {}
        for sName in sample_names:
            flavor_fraction[sName] = rl.NuisanceParameter('flavor_frac_{}'.format(sName), 'lnN')
    else:
        sample_names = sample_baseline_names

    if mergebbcc:
        signalName = 'bb_cc'
        scale_factors = {
            'cc' : rl.IndependentParameter('bb_cc', **pars['bb_cc']),
            'c'  : rl.IndependentParameter('bb_cc', **pars['bb_cc']),
            'bb' : rl.IndependentParameter('bb_cc', **pars['bb_cc']),
            'b'  : rl.IndependentParameter('bb_cc', **pars['bb_cc']),
            'l'  : rl.NuisanceParameter('l', 'lnN'),
        }
    elif 'DDC' in tagger:
        signalName = 'c_cc'
        xxbkgName  = 'b_bb'
        scale_factors = {
            'cc' : rl.IndependentParameter('c_cc', **pars['c_cc']),
            'c'  : rl.IndependentParameter('c_cc', **pars['c_cc']),
            'bb' : rl.NuisanceParameter('b_bb', 'lnN'),
            'b'  : rl.NuisanceParameter('b_bb', 'lnN'),
            'l'  : rl.NuisanceParameter('l', 'lnN'),
        }
    elif 'DDB' in tagger:
        signalName = 'b_bb'
        xxbkgName  = 'c_cc'
        scale_factors = {
            'bb' : rl.IndependentParameter('b_bb', **pars['b_bb']),
            'b'  : rl.IndependentParameter('b_bb', **pars['b_bb']),
            'cc' : rl.NuisanceParameter('c_cc', 'lnN'),
            'c'  : rl.NuisanceParameter('c_cc', 'lnN'),
            'l'  : rl.NuisanceParameter('l', 'lnN'),
        }

    pt_bins = PtBinning[campaign][year]
    name_map = {'n_or_arr' : 'num', 'lo' : 'start', 'hi' : 'stop'}
    arguments = dict((name_map[name], val) for name, val in histogram_settings[campaign]['variables'][var]['binning'].iteritems())
    arguments['num'] += 1
    bins = np.linspace(**arguments)

    observable = rl.Observable(var.split('_')[-1], bins)
    model = rl.Model("sfModel")

    regions = ['pass', 'fail']
    if passonly:
        regions = ['pass']
    fout = np.load(inputFile, allow_pickle=True)
        
    Nevts = 0
    Nl = 0
    for region in regions:
        ch = rl.Channel("sf{}".format(region))
        for sName in sample_names:
            if wpt == 'Inclusive':
                template = get_templ(fout, '{}_{}{}{}{}wp_QCD_{}'.format(var, sel, tagger, region, wp, sName), observable, lo, hi)
            elif wpt == 'M+H':
                (pt_low, pt_high) = pt_bins['M']
                template_M = get_templ(fout, '{}_{}{}{}{}wpPt-{}to{}_QCD_{}'.format(var, sel, tagger, region, wp, pt_low, pt_high, sName), observable, lo, hi)
                (pt_low, pt_high) = pt_bins['H']
                template_H = get_templ(fout, '{}_{}{}{}{}wpPt-{}to{}_QCD_{}'.format(var, sel, tagger, region, wp, pt_low, pt_high, sName), observable, lo, hi)
                template   = merge_pt_bins(template_M, template_H)
            else:
                (pt_low, pt_high) = pt_bins[wpt]
                template = get_templ(fout, '{}_{}{}{}{}wpPt-{}to{}_QCD_{}'.format(var, sel, tagger, region, wp, pt_low, pt_high, sName), observable, lo, hi)
            #print('template', template)

            if splitflavor:
                isSignal = True if sName in signalName else False
            else:
                if mergebbcc:
                    isSignal = True if sName.split('_')[-1] in signalName else False
                else:
                    isSignal = True if sName == signalName else False
            sType = rl.Sample.SIGNAL if isSignal else rl.Sample.BACKGROUND
            sample = rl.TemplateSample("{}_{}".format(ch.name, sName), sType, template)
            #print('sample',sample)
            
            # Systematic uncertainties
            #sample.setParamEffect(lumi, 1.023)
            #sample.setParamEffect(jecs, 1.02)
            #sample.setParamEffect(pu, 1.05)

            # Systematic uncertainty on relative flavor contribution
            flavor_unc = args.flavorunc
            if splitflavor:
                if sName in frac.split(','):
                    sample.setParamEffect(flavor_fraction[sName], flavor_unc)

            # MC stats
            if mcstat == None:
                sample.autoMCStats(epsilon=args.epsilon)
            else:
                if sName in args.mcstat.split(','):
                    sample.autoMCStats(epsilon=args.epsilon)
                else:
                    sample.autoMCStats(lnN=True)
            
            ch.addSample(sample)

        if wpt == 'Inclusive':
            #data_obs = get_templ(fout, 'fatjet_jetproba_{}{}{}wp_BtagMu'.format(sel, region, wp), jetproba, lo, hi)[:-1]
            data_obs = get_templ(fout, '{}_{}{}{}{}wp_BtagMu'.format(var, sel, tagger, region, wp), observable, lo, hi)[:-1]
        elif wpt == 'M+H':
            (pt_low, pt_high) = pt_bins['M']
            data_obs_M = get_templ(fout, '{}_{}{}{}{}wpPt-{}to{}_BtagMu'.format(var, sel, tagger, region, wp, pt_low, pt_high), observable, lo, hi)[:-1]
            (pt_low, pt_high) = pt_bins['H']
            data_obs_H = get_templ(fout, '{}_{}{}{}{}wpPt-{}to{}_BtagMu'.format(var, sel, tagger, region, wp, pt_low, pt_high), observable, lo, hi)[:-1]
            data_obs = merge_pt_bins(data_obs_M, data_obs_H, data=True)
        else:
            data_obs = get_templ(fout, '{}_{}{}{}{}wpPt-{}to{}_BtagMu'.format(var, sel, tagger, region, wp, pt_low, pt_high), observable, lo, hi)[:-1]
        print("data_obs", data_obs)
        ch.setObservation(data_obs)
        model.addChannel(ch)

    # SF effect in pass/fail regions
    #if splitflavor:
    #    if mergebbcc:
    #        scale_factors = [bb_cc, bb_cc, bb_cc, bb_cc, background['l']]
    #    else:
    #        scale_factors = [signal[signalName], background[xxbkgName], signal[signalName], background[xxbkgName], background['l']]
    #else:
    #    if mergebbcc:
    #        scale_factors = [bb_cc, bb_cc, background['l']]
    #    else:
    #        scale_factors = [signal[signalName], background[xxbkgName], background['l']]

    bkg_unc = 0.50
    #for sName, SF in zip(sample_names, scale_factors):
    for sName, SF in scale_factors.items():
        pass_sample = model['sfpass'][sName]
        fail_sample = model['sffail'][sName]
        pass_fail = pass_sample.getExpectation(nominal=True).sum() / fail_sample.getExpectation(nominal=True).sum()
        pass_sample.setParamEffect(overall, 1.0 * overall)
        fail_sample.setParamEffect(overall, 1.0 * overall)
        if mergebbcc:
            if ('c' in sName) | ('b' in sName):
                pass_sample.setParamEffect(SF, 1.0 * SF)
                fail_sample.setParamEffect(SF, (1 - SF) * pass_fail + 1)
            elif ('l' in sName):
                pass_sample.setParamEffect(SF, 1 + bkg_unc)
                fail_sample.setParamEffect(SF, 1 - bkg_unc * pass_fail)
        else:
            #if ('c' in sName):
            if (signalName[0] in sName):
                pass_sample.setParamEffect(SF, 1.0 * SF)
                fail_sample.setParamEffect(SF, (1 - SF) * pass_fail + 1)
            elif (xxbkgName[0] in sName) | ('l' in sName):
                pass_sample.setParamEffect(SF, 1 + bkg_unc)
                fail_sample.setParamEffect(SF, 1 - bkg_unc * pass_fail)

    model.renderCombine(tmpdir)
    with open(tmpdir+'/build.sh', 'a') as ifile:
        #ifile.write('\ncombine -M FitDiagnostics --expectSignal 1 -d model_combined.root --name {}Pt --cminDefaultMinimizerStrategy 0 --robustFit=1 --saveShapes  --rMin 0.5 --rMax 1.5'.format(wpt))
        #combineCommand = '\ncombine -M FitDiagnostics --expectSignal 1 -d model_combined.root --name {}wp{}Pt --cminDefaultMinimizerStrategy 2 --robustFit=1 --robustHesse 1 --saveShapes --saveWithUncertainties --saveOverallShapes --redefineSignalPOIs={} --setParameters r=1 --freezeParameters r --rMin 1 --rMax 1'.format(wp, wpt, signalName)
        #combineCommand = '\ncombine -M FitDiagnostics --expectSignal 1 -d model_combined.root --name {}wp{}Pt --cminDefaultMinimizerStrategy 2 --robustFit=1 --saveShapes --saveWithUncertainties --saveOverallShapes --redefineSignalPOIs={} --setParameters r=1 --freezeParameters r,flavor_frac_cc,flavor_frac_bb,flavor_frac_c,flavor_frac_b,flavor_frac_l --rMin 1 --rMax 1'.format(wp, wpt, signalName)
        combineCommand = '\ncombine -M FitDiagnostics --expectSignal 1 -d model_combined.root --name {}wp{}Pt --cminDefaultMinimizerStrategy 2 --robustFit=1 --saveShapes --saveWithUncertainties --saveOverallShapes --redefineSignalPOIs={} --setParameters r=1 --freezeParameters r --rMin 1 --rMax 1'.format(wp, wpt, signalName)
        #freeze = []
        #if freezeL:
        #    freeze.append('l')
        #if freezeB:
        #    freeze.append('b_bb')
        #if freezeC:
        #    freeze.append('c_cc')
        #ifile.write('\ncombine -M FitDiagnostics --expectSignal 1 -d model_combined.root --name {}wp{}Pt --cminDefaultMinimizerStrategy 2 --robustFit=1 --saveShapes --saveWithUncertainties --saveOverallShapes --redefineSignalPOIs={} --setParameters r=1,l=1 --freezeParameters r,l --rMin 1 --rMax 1'.format(wp, wpt, signalName))
        setParameters = 'r=1'
        freezeParameters = 'r'
        combineCommand = combineCommand.replace('--setParameters r=1', '--setParameters {}'.format(setParameters))
        combineCommand = combineCommand.replace('--freezeParameters r', '--freezeParameters {}'.format(freezeParameters))
        try: extra_args = ' ' + fit_extra_args[pars_key][year][tagger][wp][wpt]
        except:
            extra_args = ''
        combineCommand = combineCommand + ' ' + extra_args
        ifile.write(combineCommand)

    exec_me( 'bash build.sh', folder=tmpdir )

def save_results(output_dir, year, campaign, sel, tagger, wp, wpt, pars_key=None, mergebbcc=False, createcsv=False, createtex=False):

    if output_dir.rstrip("/") in os.getcwd():
        output_dir = ''
    combineFile = uproot.open(output_dir + "higgsCombine{}wp{}Pt.FitDiagnostics.mH120.root".format(wp, wpt))
        
    combineTree = combineFile['limit']
    combineBranches = combineTree.arrays()
    results = combineBranches['limit']

    combineCont, low, high, temp = results
    combineErrUp = high - combineCont
    combineErrDown = combineCont - low
    d = {}

    if mergebbcc:
        sample_names = sample_merged_names
        POI = 'bb_cc'
    else:
        sample_names = sample_baseline_names
        if (('DDB' in tagger) | ('Xbb' in tagger)):
            POI = 'b_bb'
        elif (('DDC' in tagger) | ('Xcc' in tagger)):
            POI = 'c_cc'
        else:
            raise NotImplementedError
    columns = ['year', 'campaign', 'selection', 'wp', 'pt',
                POI, '{}ErrUp'.format(POI), '{}ErrDown'.format(POI),
                'SF({})'.format(POI)]
    columns_for_latex = ['year', 'pt', 'SF({})'.format(POI)]
    d = {'year' : [year], 'campaign' : [campaign], 'selection' : [sel], 'tagger' : [tagger], 'wp' : [wp], 'pt' : [wpt],
        POI : [combineCont], '{}ErrUp'.format(POI) : [combineErrUp], '{}ErrDown'.format(POI) : [combineErrDown],
        'SF({})'.format(POI) : ['{}$^{{+{}}}_{{-{}}}$'.format(combineCont, combineErrUp, combineErrDown)]}

    if not pars_key:
        raise NotImplementedError
    else:
        pars = fit_parameters[pars_key][year]
    if wp in pars[tagger].keys():
        if wpt in pars[tagger][wp].keys():
            pars = pars[tagger][wp][wpt]
        elif wpt in pars[tagger].keys():
            pars = pars[tagger][wpt]
    elif set(pars[tagger].keys()) == {'c_cc', 'b_bb', 'l'}:
        pars = pars[tagger]
    value, lo, hi = (pars[POI]['value'], pars[POI]['lo'], pars[POI]['hi'])
    f = open(output_dir + "fitResults{}wp{}Pt.txt".format(wp, wpt), 'w')
    lineIntro = 'Best fit '
    firstline = '{}{}: {}  -{}/+{}  (68%  CL)  range = [{}, {}]\n'.format(lineIntro, POI, combineCont, combineErrDown, combineErrUp, lo, hi)
    f.write(firstline)
    fitResults = ROOT.TFile.Open(output_dir + "fitDiagnostics{}wp{}Pt.root".format(wp, wpt))
    fit_s = fitResults.Get('fit_s')
    for sName in sample_names + ['yield']:
        if (sName == POI): continue
        par_result = fit_s.floatParsFinal().find(sName)
        columns.append(sName)
        columns.append('{}Err'.format(sName))
        columns.append('SF({})'.format(sName))
        columns_for_latex.append('SF({})'.format(sName))
        if par_result == None:
            d.update({sName : -999, '{}Err'.format(sName) : -999, 'SF({})'.format(sName) : r'{}$\pm${}'.format(-999, -999)})
            continue
        parVal = par_result.getVal()
        parErr = par_result.getAsymErrorHi()
        gapSpace = ''.join( (len(lineIntro) + len(POI) - len(sName) )*[' '])
        lineResult = '{}{}: {}  -+{}'.format(gapSpace, sName, parVal, parErr)
        gapSpace2 = ''.join( (firstline.find('(') - len(lineResult) )*[' '])
        line = lineResult + gapSpace2 + '(68%  CL)\n'
        f.write(line)
        #columns.append(sName)
        #columns.append('{}Err'.format(sName))
        #columns.append('SF({})'.format(sName))
        #columns_for_latex.append('SF({})'.format(sName))
        d.update({sName : parVal, '{}Err'.format(sName) : parErr, 'SF({})'.format(sName) : r'{}$\pm${}'.format(parVal, parErr)})
    f.close()
    df = pd.DataFrame(data=d)
    csv_file = output_dir + "fitResults{}wp.csv".format(wp)
    if createcsv:
        df.to_csv(csv_file, columns=columns, mode='w', header=True)
    else:
        df.to_csv(csv_file, columns=columns, mode='a', header=False)
    if createtex:
        df_csv = pd.read_csv(csv_file)
        f = open(csv_file.replace('.csv', '.tex'), 'w')
        with pd.option_context("max_colwidth", 1000):
            f.write(df_csv.to_latex(columns=columns_for_latex, header=True, index=False, escape=False, float_format="%.4f"))
        f.close()
        f = open(csv_file.replace('.csv', '_rounded.tex'), 'w')
        with pd.option_context("max_colwidth", 1000):
            f.write(df_csv.to_latex(columns=columns_for_latex, header=True, index=False, escape=False, float_format="%.2f"))
        f.close()

    return combineCont, combineErrDown, combineErrUp

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--outputDir', type=str, default=None, help='Output directory')
    parser.add_argument('--campaign', type=str, choices={'EOY', 'UL'}, help='Dataset campaign.', required=True)
    parser.add_argument('--year', type=str, choices=['2016', '2017', '2018'], help='Year of data/MC samples', required=True)
    #parser.add_argument('--pt', type=int, default=500, help='Pt cut.', required=True)
    parser.add_argument('--var', type=str, default='sv_logsv1mass', help='Variable used in the template fit.')
    #parser.add_argument('--lo', type=float, default=-1.2, help='Variable used in the template fit.')
    parser.add_argument('--lo', type=float, default=-1.2, help='Variable used in the template fit.')
    parser.add_argument('--hi', type=float, default=2.0, help='Variable used in the template fit.')
    parser.add_argument('--selection', type=str, default='msd100tau06', help='Selection to compute SF.', required=True)
    parser.add_argument('--tagger', type=str, default='btagDDBvLV2', help='Tagger to calibrate.', required=True)
    parser.add_argument('--wp', type=str, default='M', help='Working point', required=True)
    parser.add_argument('--wpt', type=str, choices={'Inclusive', 'L', 'M', 'H', 'M+H'}, default='', help='Pt bin', required=True)
    #parser.add_argument("--freezeL", action='store_true', default=False, help="Freeze the light component in all fits")
    #parser.add_argument("--freezeB", action='store_true', default=False, help="Freeze the b+bb component in all fits")
    #parser.add_argument("--freezeC", action='store_true', default=False, help="Freeze the c+cc component in all fits")

    #parser.add_argument("--tp", "--template-pass", dest='tp', type=str,
    #                    default='histograms/hists_fattag_pileupJEC_2017_WPcuts_v01.pkl',
    #                    help="Pass(Pass/Pass) templates")  ##not used

    parser.add_argument("--tpf", "--template-passfail", dest='tpf', type=str,
                        default='histograms/hists_fattag_pileupJEC_2017_WPcuts_v01.pkl',
                        help="Pass/Fail templates, only for `fit=double`")
    parser.add_argument('--createcsv', action='store_true', default=False, help='Create new csv file')
    parser.add_argument('--createtex', action='store_true', default=False, help='Create tex file with table')
    parser.add_argument("--parameters", type=str, default=None, help='Run with custom parameters')
    parser.add_argument("--mcstat", type=str, default=None, help='List of templates to activate MCStats shape uncertainties')
    parser.add_argument("--epsilon", type=float, default=0.0001, help='Epsilon parameter for MC shape uncertainties')
    parser.add_argument('--passonly', action='store_true', default=False, help='Fit pass region only')
    parser.add_argument('--mergebbcc', action='store_true', default=False, help='Merge bb+cc')
    parser.add_argument('--mergeMH', action='store_true', default=False, help='Merge M+H pT bins')
    parser.add_argument('--fixbkg', action='store_true', default=False, help='Fix all the background templates in the fit')
    parser.add_argument('--splitflavor', action='store_true', default=False, help='Split b+bb and c+cc into b, bb, c, cc')
    parser.add_argument("--frac", type=str, default='', help='List of templates to activate flavor fraction shape uncertainties')
    parser.add_argument("--flavorunc", type=float, default=1.20, help='Flavor fraction systematic uncertainty')

    #parser.add_argument("--tf", "--template-fail", dest='tf', type=str,
    #                    default='histograms/hists_fattag_pileupJEC_2017_WPcuts_v01.pkl',
    #                    help="Fail templates")  ##not used

    args = parser.parse_args()

    print("Running with options:")
    print("    ", args)

    #if not args.selection[-3:] in ['DDB', 'DDC']:
    #    raise NotImplementedError
    if args.parameters:
        if not args.parameters in fit_parameters.keys():
            raise NotImplementedError
    for template in args.mcstat.split(','):
        if args.splitflavor:
            if template not in sample_splitflavor_names:
                sys.exit("Template '{}' does not exist. Redefine mcstat.".format(template))
        else:
            if template not in sample_baseline_names:
                sys.exit("Template '{}' does not exist. Redefine mcstat.".format(template))
    output_dir = args.outputDir if args.outputDir else os.getcwd()+"/fitdir/"+args.year+'/'+args.selection+'_'+args.tagger+'/'
    if not output_dir.endswith('/'):
        output_dir = output_dir + '/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    test_sfmodel(output_dir, args.var, args.lo, args.hi, args.tpf, args.year, args.campaign, args.selection, args.tagger, args.wp, args.wpt, args.parameters, args.epsilon, args.passonly, args.mergebbcc, args.fixbkg, args.splitflavor, args.mcstat, args.frac, args.flavorunc)
    save_results(output_dir, args.year, args.campaign, args.selection, args.tagger, args.wp, args.wpt, args.parameters, args.mergebbcc, args.createcsv, args.createtex)