import collections
import numpy as np
import awkward as ak

def get_nsv(sj, sv, R=0.4):

    sv_dr = sj.delta_r(sv.p4)
    nsv = ak.count(sv_dr[sv_dr < R], axis=1)

    return nsv

def get_sv_in_jet(jet, sv, R=0.8):

    sv_dr = jet.delta_r(sv.p4)
    sv_in_jet = sv_dr < R

    return sv_in_jet
