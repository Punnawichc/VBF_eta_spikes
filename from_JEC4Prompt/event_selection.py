import uproot
import numpy as np
import argparse
import os


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Event Selection")
    parser.add_argument("-mc",   "--MC",     type=str,   required=True,    help="MC root file (J4PSkim)")
    parser.add_argument("-data", "--DATA",   type=str,   required=True,    help="Data root file (J4PSkim)")
    parser.add_argument("-out",  "--output", type=str,   required=True,    help="Output directory")
    parser.add_argument("-tree", "--tree",   type=str,   default="Events", help="TTree name (default: Events)")
    parser.add_argument("-ptmax","--ptmax",  type=float, default=None,     help="Probe_pt max cut")
    parser.add_argument("-ptmin","--ptmin",  type=float, default=None,     help="Probe_pt min cut")
    parser.add_argument("-sumw", "--sumw",   type=float, default=None,     help="Override sumw")
    args = parser.parse_args()

    branches    = ["Probe_eta", "Probe_pt", "weight"]
    mc_branches = branches
    dt_branches = ["Probe_eta", "Probe_pt"]   # no weight for data

    # get sumw from Runs/genEventSumw
    if args.sumw is not None:
        sumw = args.sumw
        print(f"sumw = {sumw:.4e} (from argument)")
    else:
        with uproot.open(args.MC) as mc_file:
            sumw = mc_file["Runs"]["genEventSumw"].array(library="np").sum()
        print(f"sumw = {sumw:.4e} (from Runs/genEventSumw)")

    # read MC
    print(f"\nReading MC: {args.MC}")
    with uproot.open(args.MC) as mc_file:
        tree_mc   = mc_file[args.tree]
        mc_arrays = tree_mc.arrays(mc_branches, library="np")
        print(f"  N events       = {len(mc_arrays['Probe_pt'])}")
        print(f"  weight mean    = {mc_arrays['weight'].mean():.2f}")
        print(f"  weight sum     = {mc_arrays['weight'].sum():.4e}")
        print(f"  weight (+/-)   = {(mc_arrays['weight'] > 0).sum()} / {(mc_arrays['weight'] < 0).sum()}")

    # read Data
    print(f"\nReading Data: {args.DATA}")
    with uproot.open(args.DATA) as data_file:
        tree_data   = data_file[args.tree]
        data_arrays = tree_data.arrays(dt_branches, library="np")
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
    print(f"  weight sum after cut  = {mc_arrays['weight'][mc_mask].sum():.4e}")

    # save to ROOT file
    os.makedirs(args.output, exist_ok=True)
    out_path = f"{args.output}/selected.root"

    with uproot.recreate(out_path) as out_file:
        out_file["MC"]       = {b: mc_arrays[b][mc_mask]       for b in mc_branches}
        out_file["Data"]     = {b: data_arrays[b][data_mask]   for b in dt_branches}
        out_file["Metadata"] = {"sumw": np.array([sumw])}

    print(f"\nSaved to {out_path}")
    print(f"  TTree: MC       ({mc_mask.sum()} events, with weight)")
    print(f"  TTree: Data     ({data_mask.sum()} events)")
    print(f"  TTree: Metadata (sumw={sumw:.4e})")
    print(f"\nDone!")