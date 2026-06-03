import argparse
import os
import ROOT
import json
import numpy as np


# python3 reweight_histograms.py -d automation_out/out_skim/zmm/Summer24 -j metadata/Summer24/zmm/zmm.json -lumi 1510.704612163 -out reweighted_plots/385444_385515/zmm

def get_value(data_tag, key):
    
    if key not in data_tag:
        print(f"[WARNING] Missing {key} in JSON. If no -{key} provided, default = 1") 
        return data_tag.get(key, 1)
    
    return data_tag[key]


def get_sumw_from_json(args):

    with open(args.json, "r") as j:
        data = json.load(j)

    root_file_name = os.path.basename(args.file)

    for tag in data:
        if tag in root_file_name:

            sumw = get_value(data[tag], "sumw") 
            xsec = get_value(data[tag], "xsec")
            lumi = get_value(data[tag], "lumi")

            return sumw, xsec, lumi

    raise ValueError(f"No matching dataset found for {root_file_name}")


def calculate_scale_factor(args):

    sumw, xsec, lumi = get_sumw_from_json(args)

    # CLI values override JSON/default, if provided
    sumw = args.sumw if args.sumw is not None else sumw
    xsec = args.xsec if args.xsec is not None else xsec
    lumi = args.lumi if args.lumi is not None else lumi

    if sumw == 0:
        raise RuntimeError("sumw = 0, please check!")

    return (xsec * lumi) / sumw


def reweight_hist_nd(h, w, name):
    out = h.Clone(name)
    out.Scale(w) # work for TH1D and TH2D, wrong for TProfile
    return out


# According to the TProfile documentation:
# https://root.cern.ch/doc/v636/classTProfile.html

# The relevant variables are defined as follows:
# W  = out.GetBinEntries(i)           # sum of weights: Σw
# E  = out.GetSumw2()[i]              # sum of weighted squares: Σ(w * y^2)
# h  = out.GetBinContent(i)           # mean value

# H  = h * W                          # sum of weighted y: Σ(w * y)
# Alternatively, H can be set via out.SetBinContent(i, H)
# which will internally update h.

# The standard deviation is:
# s = sqrt(E / W - h^2)

# The bin error is:
# e = out.GetBinError(i)
#   = s / sqrt(neff)
# Note: this differs from the documentation, which states s / sqrt(W)

# The effective number of entries is:
# neff = W^2 / W2
#     = out.GetBinEffectiveEntries(i)
# W2 = out.GetBinSumw2()[i]           # Σ(w^2)


def reweight_profile_1d(in_, w, name):
    out = in_.Clone(name)

    for i in range(1, in_.GetNbinsX() + 1):

        W = in_.GetBinEntries(i)
        if W == 0:
            continue
        
        out.SetBinEntries(i, w * W) # entries changed

        h = in_.GetBinContent(i)
        out.SetBinContent(i, h * (w * W)) # content unchanged

        out.GetSumw2()[i] = in_.GetSumw2()[i] * w

        # some TProfile don't have list of sumw2
        if in_.GetBinSumw2().GetSize() <= i:
            continue

        out.GetBinSumw2()[i] = in_.GetBinSumw2()[i] * w**2  # error unchanged

    return out


def reweight_profile_2d(in_, w, name):
    out = in_.Clone(name)

    for i in range(1, in_.GetNbinsX() + 1):
        for j in range(1, in_.GetNbinsY() + 1):

            bin_ = in_.GetBin(i, j)

            W = in_.GetBinEntries(bin_)
            if W == 0:
                continue

            out.SetBinEntries(bin_, w * W)

            h = in_.GetBinContent(bin_)
            out.SetBinContent(bin_, h * (w * W))

            out.GetSumw2()[bin_] = in_.GetSumw2()[bin_] * w

            if in_.GetBinSumw2().GetSize() <= i:
                continue

            out.GetBinSumw2()[bin_] = in_.GetBinSumw2()[bin_] * w**2

    return out


def main(args):

    in_file = ROOT.TFile.Open(args.file, "READ")
    
    root_file_name = os.path.basename(args.file)
    out_file_path = f"{args.out}/reweighted_{root_file_name}"

    out_file = ROOT.TFile.Open(out_file_path, "RECREATE")

    scale_factor = calculate_scale_factor(args)
    print(f"scale_factor = {scale_factor}")

    for key in in_file.GetListOfKeys():

        hist = key.ReadObj() 

        hist_name = hist.GetName()
        hist_class = hist.ClassName()

        # if hist_class != "TProfile2D": 
        #     continue

        if hist_class == "TH1D" or hist_class == "TH2D":
            print("TH1", hist_name)
            reweighted_hist = reweight_hist_nd(hist, scale_factor, hist_name)

        elif hist_class == "TProfile":
            print("TProfile", hist_name)
            reweighted_hist = reweight_profile_1d(hist, scale_factor, hist_name)

        elif hist_class == "TProfile2D":
            print("TProfile2D", hist_name)
            reweighted_hist = reweight_profile_2d(hist, scale_factor, hist_name)

        out_file.cd()
        reweighted_hist.Write()

        print(f"{hist_class} {hist_name} has been reweighted.")

    in_file.Close()
    out_file.Close()

    print(f"Output: {out_file_path}")
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="reweighted histogram")

    group1 = parser.add_mutually_exclusive_group(required=True)

    group1.add_argument("-f", "--file", help="Histogram file")
    group1.add_argument("-d", "--dir", required=False, help="Histogram directory")
    
    parser.add_argument("-j", "--json", type=str, help="JSON that contains dataset information")

    parser.add_argument("-sumw", "--sumw", type=float, help="sumw (override JSON/default, if provided)")
    parser.add_argument("-xsec", "--xsec", type=float, help="Cross section (override JSON/default, if provided)")
    parser.add_argument("-lumi", "--lumi", type=float, help="Luminosity (override JSON/default, if provided)")

    parser.add_argument("-out", "--out", default=".", help="Output directory (default: current directory)")
    
    args = parser.parse_args()

    if args.dir:
        for root_file_name in os.listdir(args.dir):
            if root_file_name.startswith("J4PHists_") and root_file_name.endswith(".root"):

                args.file = os.path.join(args.dir, root_file_name)
                main(args)

    elif args.file:
        main(args)

    else:
        print("Please add input file (-f) or directory (-d)")

        