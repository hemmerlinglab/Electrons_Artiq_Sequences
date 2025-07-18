# Electrons_Artiq_Sequences
Python files for running Electrons experiments with ARTIQ.

## How to run ARTIQ
1. Open a terminal and navigate to the project directory:
   ```
   cd ~/software/Electrons_Artiq_Sequences/artiq-master/
   ```
2. Deactivate the Conda environment (to prevent potential Python conflicts):
   ```
   conda deactivate
   ```
3. Set the `PYTHONPATH` to ensure ARTIQ uses the correct Python site-packages:
   ```
   export PYTHONPATH="$HOME/.nix-profile/lib/python3.8/site-packages:$PYTHONPATH"
   ```
4. Launch ARTIQ session:
   ```
   artiq_session
   ```
