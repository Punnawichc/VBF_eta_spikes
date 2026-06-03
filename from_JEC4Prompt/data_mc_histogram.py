import ROOT
import uproot
import numpy as np
import mplhep as hep
import matplotlib.pyplot as plt
import argparse
import os


def plot_histogram(mc_values, data_values, edges, histname, outdir,
                   xsec=None, lumi=None, sumw=None):

    if xsec is not None and lumi is not None and sumw is not None:
        mc_scaled = mc_values * (xsec * lumi / sumw)
        print(f"  [{histname}] absolute normalization: xsec={xsec}, lumi={lumi}, sumw={sumw:.2f}")
    else:
        scale     = data_values.sum() / mc_values.sum() if mc_values.sum() > 0 else 1.0
        mc_scaled = mc_values * scale
        print(f"  [{histname}] data yield normalization: scale={scale:.4f}")

    bin_centers = 0.5 * (edges[:-1] + edges[1:])
    bin_width   = edges[1] - edges[0]

    hep.style.use("CMS")
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(12, 10),
                                   gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    hep.cms.label("Preliminary", ax=ax, data=True, lumi=lumi or 1.510, com=13.6)

    ax.bar(bin_centers, mc_scaled, width=bin_width, color="orange", alpha=0.7, label="MC")

    data_err = np.sqrt(data_values)
    ax.errorbar(bin_centers, data_values, yerr=data_err,
                fmt="o", color="black", markersize=5, label="Data")

    ratio     = np.divide(data_values, mc_scaled,
                          out=np.zeros_like(data_values, dtype=float), where=mc_scaled != 0)
    ratio_err = np.divide(data_err,    mc_scaled,
                          out=np.zeros_like(data_err,    dtype=float), where=mc_scaled != 0)

    rax.errorbar(bin_centers, ratio, yerr=ratio_err,
                 fmt="o", color="black", markersize=5)
    rax.axhline(1.0, linestyle="--", color="black")
    rax.set_ylim(0, 2)

    ax.set_yscale("log")
    ax.set_ylabel("Events")
    rax.set_ylabel("Data/MC")
    rax.set_xlabel(histname)
    ax.legend()
    plt.tight_layout()

    os.makedirs(outdir, exist_ok=True)
    plt.savefig(f"{outdir}/MC-Data_{histname}.png")
    plt.savefig(f"{outdir}/MC-Data_{histname}.pdf")
    plt.close()
    print(f"  [{histname}] saved to {outdir}/")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="MC/data Comparison")
    parser.add_argument("-mc",   "--MC",     type=str,   required=True,    help="MC root file (J4PSkim)")
    parser.add_argument("-data", "--DATA",   type=str,   required=True,    help="Data root file (J4PSkim)")
    parser.add_argument("-out",  "--output", type=str,   required=True,    help="Output directory")
    parser.add_argument("-xsec", "--xsec",   type=float, default=None,     help="Cross section in pb")
    parser.add_argument("-lumi", "--lumi",   type=float, default=None,     help="Integrated luminosity in pb-1")
    parser.add_argument("-sumw", "--sumw",   type=float, default=None,     help="Override sumw")
    parser.add_argument("-tree", "--tree",   type=str,   default="Events", help="TTree name (default: Events)")
    parser.add_argument("-ptmax","--ptmax",  type=float, default=None,     help="Probe_pt max cut")
    parser.add_argument("-ptmin","--ptmin",  type=float, default=None,     help="Probe_pt min cut")
    args = parser.parse_args()

    branch_settings = {
        "Probe_eta": {"bins": 50, "range": (-5,      5)},
        "Probe_pt":  {"bins": 60, "range": (0,     300)},
    }

    branches = list(set(list(branch_settings.keys()) + ["Probe_pt", "weight"]))

    # read MC
    print(f"\nReading MC: {args.MC}")
    with uproot.open(args.MC) as mc_file:
        tree_mc   = mc_file[args.tree]
        mc_arrays = tree_mc.arrays(branches, library="np")
        print(f"  N events = {len(mc_arrays['Probe_pt'])}")

    # read Data
    print(f"\nReading Data: {args.DATA}")
    with uproot.open(args.DATA) as data_file:
        tree_data   = data_file[args.tree]
        data_arrays = tree_data.arrays(branches, library="np")
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

    if args.sumw is not None:
        sumw = args.sumw
        print(f"  sumw = {sumw:.2f} (from argument)")
    else:
        with uproot.open(args.MC) as mc_file:
            sumw = mc_file["Runs"]["genEventSumw"].array(library="np").sum()
        print(f"  sumw = {sumw:.2f} (from Runs/genEventSumw)")

    # plot
    print(f"\nPlotting...")
    for histname, setting in branch_settings.items():

        mc_values,   edges = np.histogram(mc_arrays[histname][mc_mask],
                                          bins=setting["bins"], range=setting["range"])
        data_values, _     = np.histogram(data_arrays[histname][data_mask],
                                          bins=setting["bins"], range=setting["range"])

        plot_histogram(
            mc_values,
            data_values,
            edges,
            histname = histname,
            outdir   = args.output,
            xsec     = args.xsec,
            lumi     = args.lumi,
            sumw     = sumw,
        )

    print(f"\nDone! All plots saved to {args.output}/")

    with uproot.open(args.MC) as mc_file:
        sumw = mc_file["Runs"]["genEventSumw"].array(library="np").sum()

    w = args.xsec * args.lumi / sumw

    print(f"xsec = {args.xsec:.2f} pb")
    print(f"lumi = {args.lumi:.2f} pb-1")
    print(f"sumw = {sumw:.2f}")
    print(f"w    = {w:.6e}")

    # sanity check — expected yield should be close to data
    mc_expected = mc_mask.sum() * w
    print(f"\nMC expected yield = {mc_expected:.2f}")
    print(f"Data yield        = {data_mask.sum()}")
    print(f"Data/MC ratio     = {data_mask.sum() / mc_expected:.4f}")