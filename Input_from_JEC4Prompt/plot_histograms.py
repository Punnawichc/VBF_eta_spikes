import ROOT
import numpy as np
import mplhep as hep
import matplotlib.pyplot as plt
import argparse
import os


def th1_to_numpy(h):
    nbins  = h.GetNbinsX()
    values = np.array([h.GetBinContent(i) for i in range(1, nbins + 1)])
    edges  = np.array([h.GetBinLowEdge(i) for i in range(1, nbins + 2)])
    return values, edges


def plot_histogram(mc_values, data_values, edges, histname, outdir, lumi=None):

    bin_centers = 0.5 * (edges[:-1] + edges[1:])
    bin_width   = edges[1] - edges[0]

    lumi_fb = (lumi / 1000) if lumi else None

    hep.style.use("CMS")
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(12, 10),
                                   gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    hep.cms.label("Private", ax=ax, data=True, lumi=lumi_fb, com=13.6)

    ax.bar(bin_centers, mc_values, width=bin_width, color="orange", alpha=0.7, label="MC")

    data_err = np.sqrt(data_values)
    ax.errorbar(bin_centers, data_values, yerr=data_err,
                fmt="o", color="black", markersize=5, label="Data")

    ratio     = np.divide(data_values, mc_values,
                          out=np.zeros_like(data_values, dtype=float), where=mc_values != 0)
    ratio_err = np.divide(data_err,    mc_values,
                          out=np.zeros_like(data_err,    dtype=float), where=mc_values != 0)

    rax.errorbar(bin_centers, ratio, yerr=ratio_err,
                 fmt="o", color="black", markersize=5)
    rax.axhline(1.0, linestyle="--", color="black")
    rax.set_ylim(0, 2)

    # ax.set_yscale("log")
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

    parser = argparse.ArgumentParser(description="Plot MC/Data Comparison")
    parser.add_argument("-inp",  "--input",  type=str,   required=True, help="Input ROOT file from make_histograms.py")
    parser.add_argument("-out",  "--output", type=str,   required=True, help="Output directory for plots")
    parser.add_argument("-lumi", "--lumi",   type=float, default=None,  help="Lumi for label in pb-1")
    args = parser.parse_args()

    f = ROOT.TFile.Open(args.input, "READ")

    histnames = []
    for key in f.GetListOfKeys():
        name = key.GetName()
        if name.endswith("_mc"):
            histnames.append(name.replace("_mc", ""))

    print(f"\nFound histograms: {histnames}")
    print(f"Plotting from {args.input}...")

    for histname in histnames:
        h_mc   = f.Get(f"{histname}_mc")
        h_data = f.Get(f"{histname}_data")

        if not h_mc:
            print(f"  WARNING: {histname}_mc not found, skipping")
            continue
        if not h_data:
            print(f"  WARNING: {histname}_data not found, skipping")
            continue

        h_mc.SetDirectory(0)
        h_data.SetDirectory(0)

        mc_values,   edges = th1_to_numpy(h_mc)
        data_values, _     = th1_to_numpy(h_data)

        print(f"\n  [{histname}]")
        print(f"    MC   integral = {mc_values.sum():.2f}")
        print(f"    Data integral = {data_values.sum():.0f}")
        print(f"    Data/MC ratio = {data_values.sum() / mc_values.sum():.4f}" if mc_values.sum() > 0 else "    Data/MC ratio = inf")

        plot_histogram(mc_values, data_values, edges, histname, args.output, lumi=args.lumi)

    f.Close()
    print(f"\nDone! All plots saved to {args.output}/")