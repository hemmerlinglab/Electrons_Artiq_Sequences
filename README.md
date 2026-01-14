# Electrons_Artiq_Sequences
Python files for running Electrons experiments with ARTIQ.

Our ARTIQ relies on Python in `nix` environment, not conda or system bare Python. However, our Python environment is disastrous: a lot of nix Pythons, conda Pythons and unexpected bare Pythons exists in the computer. So make sure you are operating the correct one.

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
   export PYTHONPATH="$HOME/.nix-profile/lib/python3.8/site-packages:$(pwd)/repository:$PYTHONPATH"
   ```
4. Launch ARTIQ session:
   ```
   artiq_session
   ```

## How to install packages to Python used by Artiq
1. Deactivate the Conda environment (to prevent potential Python conflicts):
   ```
   conda deactivate
   ```
2. Install package with nix command (use Pandas as an example, change to the package you would like to install).

   If you need to install a package (e.g. `pandas`) and its dependencies (`numpy`, `pytz`, and `python-dateutil` for `pandas`), use:
   ```
   nix-env -iA \
       nixpkgs.python38Packages.pandas \
       nixpkgs.python38Packages.numpy \
       nixpkgs.python38Packages.pytz \
       nixpkgs.python38Packages.python-dateutil
   ```
   You do not need to worry about installed packages, nix will skip them if already installed.'
   
   If you only need to install a single package, you could use single line command:
   ```
   nix-env -iA nixpkgs.python38Packages.pandas
   ```

## How to commit code changes to GitHub?
Backing up our code on GitHub is very important, remember to do this after changing the code.
1. Go to the base path of the project directory:
   ```
   cd ~/software/Electrons_Artiq_Sequences/
   ```
2. (Optional) List add modifications since last git update:
   ```
   git status
   ```
3. Add all changes in the repository:
   ```
   git add .
   ```
4. (Optional) List add modifications to see if they are added:
   ```
   git status
   ```
5. Apply the changes to the git repository:
   ```
   git commit -m "<your update note>"
   ```
6. Upload changes to GitHub:
   ```
   git push
   ```
