import os
import shutil

base_dir = "/eos/user/j/jecpcl/public/jec4prompt/runs/Run2025G"
dest_dir = "/eos/home-p/pchokepr/CMSDAW_2026/JME-VBF_eta_spikes/from_JEC4Prompt/data_skim"

for run_dir in os.listdir(base_dir):
    run_path = os.path.join(base_dir, run_dir)

    for channel in os.listdir(run_path):
        if channel == "zmm":
            channel_path = os.path.join(run_path, channel)
            
            for f in os.listdir(channel_path):
                if f.startswith("J4PSkim_"):
                    src = os.path.join(channel_path, f)
                    dst = os.path.join(dest_dir, f)
                    shutil.copy(src, dst)
                    print(f"Copied {f}")