import ROOT
import uproot
import numpy as np
import argparse
import os


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Make Histograms")
    parser.add_argument("-inp",  "--input",  type=str,   required=True,  help="Directory with selected.root")
    parser.add_argument("-out",  "--output", type=str,   required=True,  help="Output ROOT file")
    parser.add_argument("-xsec", "--xsec",   type=float, required=True,  help="Cross section in pb")
    parser.add_argument("-lumi", "--lumi",   type=float, required=True,  help="Integrated luminosity in pb-1")
    parser.add_argument("-sumw", "--sumw",   type=float, default=None,   help="Override sumw")
    args = parser.parse_args()

    branch_settings = {
        "Probe_eta": {"bins": 50, "range": (-5,      5)},
        "Probe_pt":  {"bins": 60, "range": (0,     300)},
    }

    # load selected arrays from ROOT file
    print(f"\nReading selected.root from {args.input}/")
    with uproot.open(f"{args.input}/selected.root") as f:
        mc_arrays   = f["MC"].arrays(library="np")
        data_arrays = f["Data"].arrays(library="np")
        sumw_stored = float(f["Metadata"]["sumw"].array(library="np")[0])

    # get sumw
    if args.sumw is not None:
        sumw = args.sumw
        print(f"  sumw = {sumw:.4e} (from argument)")
    else:
        sumw = sumw_stored
        print(f"  sumw = {sumw:.4e} (from selected.root)")

    # compute scale weight
    w = args.xsec * args.lumi / sumw

    # weight from MC
    weight = mc_arrays["weight"].astype(np.float64)

    print(f"\n=== Normalization ===")
    print(f"  xsec         = {args.xsec} pb")
    print(f"  lumi         = {args.lumi} pb-1  ({args.lumi/1000:.4f} fb-1)")
    print(f"  sumw         = {sumw:.4e}")
    print(f"  w            = {w:.6e}")
    print(f"  MC N events  = {len(mc_arrays['Probe_pt'])}")
    print(f"  Data N events= {len(data_arrays['Probe_pt'])}")

    # create output ROOT file
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    out_file = ROOT.TFile.Open(args.output, "RECREATE")

    for histname, setting in branch_settings.items():
        lo, hi = setting["range"]
        bins   = setting["bins"]

        h_mc   = ROOT.TH1D(f"{histname}_mc",   f"{histname} MC",   bins, lo, hi)
        h_data = ROOT.TH1D(f"{histname}_data", f"{histname} Data", bins, lo, hi)
        h_mc.SetDirectory(0)
        h_data.SetDirectory(0)

        mc_arr   = mc_arrays[histname].astype(np.float64)
        data_arr = data_arrays[histname].astype(np.float64)

        # fill MC with weight
        h_mc.FillN(len(mc_arr),   mc_arr,   weight)
        h_data.FillN(len(data_arr), data_arr, np.ones(len(data_arr)))

        # scale MC
        h_mc.Scale(w)

        print(f"\n  [{histname}]")
        print(f"    MC   integral after scale = {h_mc.Integral():.2f}")
        print(f"    Data integral             = {h_data.Integral():.2f}")
        print(f"    Data/MC                   = {h_data.Integral() / h_mc.Integral():.4f}" if h_mc.Integral() > 0 else "    Data/MC = inf")

        out_file.cd()
        h_mc.Write()
        h_data.Write()

    out_file.Close()
    print(f"\nSaved histograms to {args.output}")
    print(f"\nDone!")