import os

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--outputDir', type=str, default=None, help='Output directory')
    parser.add_argument('--year', type=str, choices=['2016', '2017', '2018'], help='Year of data/MC samples')
    parser.add_argument('--pt', type=int, default=500, help='Pt cut.')
    parser.add_argument("--tpf", "--template-passfail", dest='tpf', type=str,
                        default='histograms/hists_fattag_pileupJEC_2017_WPcuts_v01.pkl',
                        help="Pass/Fail templates, only for `fit=double`")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Show combine log to stdout')
    args = parser.parse_args()

    #for year in ['2016', '2017', '2018']:
    for tagger in ['DDC', 'DDB']:
        for wp in [ 'M' ]:
            for wpt in ['Inclusive', 'M', 'H']:
                subDir = "{}/msd100tau06{}{}wp".format(args.outputDir, tagger, wp)
                if not os.path.exists(subDir):
                    os.makedirs(subDir)
                logFile = "{}/sf{}{}{}wp{}Pt.log".format(subDir, args.year, tagger, wp, wpt)
                
                submissionCommand = ( "python scaleFactorComputation.py --year {} --tpf {} --outputDir {}".format(args.year, args.tpf, subDir) +
                                      " --selection msd100tau06{} --wp {} --wpt {} --pt {}".format(tagger, wp, wpt, args.pt) +
                                      " | tee {}".format(logFile) )
                if not args.verbose:
                    submissionCommand = submissionCommand.split('|')[0] + " > {}".format(logFile)

                line = ''.join(200*['-'])
                print(line)
                print( submissionCommand + '\n')
                os.system( submissionCommand )
                print("{} {} {} wp {} Pt".format(args.year, tagger, wp, wpt))
                os.system('cat {}/msd100tau06{}{}wp/fitResults{}wp{}Pt.txt'.format(args.outputDir, tagger, wp, wp, wpt))