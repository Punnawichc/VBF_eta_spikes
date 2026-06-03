import argparse
import os
import ROOT
import uproot
import json
import numpy as np


def get_value(data_tag, key):
    if key not in data_tag:
        print(f"[WARNING] Missing {key} in JSON. If no -{key} provided, default = 1")
        return data_tag.get(key, 1)
    return data_tag[key]


def get_sumw_from_json(args):
    with open(args.json, "r") as j:
        data = json.load(j)

    root_file_name = os.path.basename(args.mc)

    for tag in data:
        if tag in root_file_name:
            sumw = get_value(data[tag], "sumw")
            xsec = get_value(data[tag], "xsec")
            lumi = get_value(data[tag], "lumi")
            return sumw, xsec, lumi

    raise ValueError(f"No matching dataset found for {root_file_name}")


def calculate_scale_factor(args):
    sumw, xsec, lumi = get_sumw_from_json(args)

    # CLI values override JSON/default
    sumw = args.sumw if args.sumw is not None else sumw
    xsec = args.xsec if args.xsec is not None else xsec
    lumi = args.lumi if args.lumi is not None else lumi

    if sumw == 0:
        raise RuntimeError("sumw = 0, please check!")

    print(f"  xsec = {xsec} pb")
    print(f"  lumi = {lumi} pb-1  ({lumi/1000:.4f} fb-1)")
    print(f"  sumw = {sumw:.4e}")
    print(f"  w    = {xsec * lumi / sumw:.6e}")

    return (xsec * lumi) / sumw


branch_settings = {
    "Probe_eta": {"bins": 50, "range": (-5,      5)},
    "Probe_pt":  {"bins": 60, "range": (0,     300)},
    "Tag_eta":   {"bins": 50, "range": (-5,      5)},
    "Tag_pt":    {"bins": 60, "range": (0,     300)},
}


def make_histograms(mc_arrays, data_arrays, scale_factor, mc_mask, data_mask, out_file):

    for histname, setting in branch_settings.items():
        if histname not in mc_arrays or histname not in data_arrays:
            print(f"  [{histname}] not found, skipping")
            continue

        lo, hi = setting["range"]
        bins   = setting["bins"]

        h_mc   = ROOT.TH1D(f"{histname}_mc",   f"{histname} MC",   bins, lo, hi)
        h_data = ROOT.TH1D(f"{histname}_data", f"{histname} Data", bins, lo, hi)
        h_mc.SetDirectory(0)
        h_data.SetDirectory(0)

        # fill with FillN
        mc_arr   = mc_arrays[histname][mc_mask].astype(np.float64)
        data_arr = data_arrays[histname][data_mask].astype(np.float64)

        h_mc.FillN(len(mc_arr),   mc_arr,   np.ones(len(mc_arr)))
        h_data.FillN(len(data_arr), data_arr, np.ones(len(data_arr)))

        # scale MC — exactly h.Scale(w)
        h_mc.Scale(scale_factor)

        print(f"  [{histname}] MC integral = {h_mc.Integral():.2f}, Data integral = {h_data.Integral():.0f}")

        out_file.cd()
        h_mc.Write()
        h_data.Write()


def main(args):

    print(f"\nProcessing: {args.mc}")

    # calculate scale factor
    scale_factor = calculate_scale_factor(args)
    print(f"scale_factor = {scale_factor:.6e}")

    # read MC
    print(f"\nReading MC: {args.mc}")
    with uproot.open(args.mc) as mc_file:
        tree_mc   = mc_file[args.tree]
        mc_arrays = tree_mc.arrays(list(branch_settings.keys()), library="np")
        print(f"  N events = {len(mc_arrays['Probe_pt'])}")

    # read Data
    print(f"\nReading Data: {args.data}")
    with uproot.open(args.data) as data_file:
        tree_data   = data_file[args.tree]
        data_arrays = tree_data.arrays(list(branch_settings.keys()), library="np")
        print(f"  N events = {len(data_arrays['Probe_pt'])}")

    # build cut mask
    mc_mask   = np.ones(len(mc_arrays["Probe_pt"]),   dtype=bool)
    data_mask = np.ones(len(data_arrays["Probe_pt"]), dtype=bool)

    if args.ptmin is not None:
        mc_mask   &= mc_arrays["Probe_pt"]   >= args.ptmin
        data_mask &= data_arrays["Probe_pt"] >= args.ptmin
        print(f"\nCut: Probe_pt >= {args.ptmin}")

    if args.ptmax is not None:
        mc_mask   &= mc_arrays["Probe_pt"]   < args.ptmax
        data_mask &= data_arrays["Probe_pt"] < args.ptmax
        print(f"Cut: Probe_pt < {args.ptmax}")

    print(f"  MC   events after cut: {mc_mask.sum()} / {len(mc_mask)}")
    print(f"  Data events after cut: {data_mask.sum()} / {len(data_mask)}")

    # output file
    mc_file_name  = os.path.basename(args.mc).replace("J4PSkim_", "J4PHists_")
    out_file_path = f"{args.out}/{mc_file_name}"
    os.makedirs(args.out, exist_ok=True)

    out_file = ROOT.TFile.Open(out_file_path, "RECREATE")
    make_histograms(mc_arrays, data_arrays, scale_factor, mc_mask, data_mask, out_file)
    out_file.Close()

    print(f"\nOutput: {out_file_path}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Make and reweight histograms from J4PSkim")

    parser.add_argument("-mc",   "--mc",    type=str,   required=True,    help="MC J4PSkim root file")
    parser.add_argument("-data", "--data",  type=str,   required=True,    help="Data J4PSkim root file")
    parser.add_argument("-j",    "--json",  type=str,   required=True,    help="JSON with dataset info")
    parser.add_argument("-out",  "--out",   type=str,   default=".",      help="Output directory")
    parser.add_argument("-tree", "--tree",  type=str,   default="Events", help="TTree name")
    parser.add_argument("-sumw", "--sumw",  type=float, default=None,     help="Override sumw")
    parser.add_argument("-xsec", "--xsec",  type=float, default=None,     help="Override xsec")
    parser.add_argument("-lumi", "--lumi",  type=float, default=None,     help="Override lumi")
    parser.add_argument("-ptmin","--ptmin", type=float, default=None,     help="Probe_pt min cut")
    parser.add_argument("-ptmax","--ptmax", type=float, default=None,     help="Probe_pt max cut")
    args = parser.parse_args()

    main(args)