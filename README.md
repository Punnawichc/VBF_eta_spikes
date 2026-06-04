# VBF η Spikes

Investigation of anomalous jet η spikes at 2.5 < |η| < 3.0 in Z(μμ)+jet events.
The goal is to measure Data/MC differences and understand their origin in terms of jet energy corrections (JEC).
This study using input files from JEC4Prompt (J4PSkim_)

More details from CMS 2025-2025 Data Analysis Workshop [JME project](https://indico.cern.ch/event/1681344/timetable/?view=standard#6-project-from-the-jme-pog)

---

## Set up

```
git clone git@github.com:Punnawichc/VBF_eta_spikes.git
cd VBF_eta_spikes/Input_from_JEC4Prompt
```

---

## Analysis Structure

```
Input_from_JEC4Prompt/
├── event_selection.py     # Step 1: read TTree, apply cuts, save arrays
├── make_histograms.py     # Step 2: fill TH1D, apply MC reweighting
├── plot_histograms.py     # Step 3: plot Data/MC comparison
└── output/
    ├── selected.root      # output of event_selection.py
    ├── histograms.root    # output of make_histograms.py
    └── plots/             # output of plot_histograms.py
```

---

## How to Run

### Step 1 — Event selection
Reads TTree, applies pT cuts, saves selected arrays to ROOT file.

```bash
python3 event_selection.py \
    -mc /eos/project/j/jec4prompt/public/MC/Summer24/skim/zmm/J4PSkim_zmm_DYto2Mu-2Jets_Bin-MLL-50.root \
    -data /eos/user/j/jecpcl/public/jec4prompt/runs/Run2025G/run398027/zmm/J4PSkim_runs398027to398027_zmm.root \
    -out output \
    -ptmin 20 -ptmax 25
```

Only needs to run once per pT bin — output is saved to `output/selected.root`.

### Step 2 — Make histograms with MC reweighting
Fills ROOT TH1D histograms and applies MC scale factor `w = xsec * lumi / sumw`.

xsec -> please check from https://cmsweb.cern.ch/das/, now we use the dataset below which has xsec = 2240.0 pb
```
/DYto2Mu-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v6/NANOAODSIM
```
sumw -> getting automatically from the MC input file in event_selection.py
lumi -> please check with 
```
source /cvmfs/cms-bril.cern.ch/cms-lumi-pog/brilws-docker/brilws-env
brilcalc lumi -u /pb -i /eos/user/c/cmsdqm/www/CAF/certification/Collisions25/Cert_Collisions2025_391658_398903_Golden.json -r 398027 --without-checkjson
```
For run 398027 -> lumi = 1033.097330108 pb-1

```bash
python3 make_histograms.py \
    -inp output \
    -out output/histograms.root \
    -xsec 2240.0 \
    -lumi 1033.097330108
```

Re-run when xsec or lumi changes — no need to redo event selection.

### Step 3 — Plot Data/MC comparison

```bash
python3 plot_histograms.py \
    -inp output/histograms.root \
    -out output/plots \
    -lumi 1033.097330108
```

---

## Next Steps

```
[ ] Split MC into GEN-matched / no-GEN-matched components
[ ] Plot Probe_eta in multiple pT bins to separate threshold vs detector effects
[ ] Study DB (Direct Balance) Data/MC vs eta to measure JEC disagreement
[ ] Check jet purity in spike region (Probe_genJetIdx)
```

---