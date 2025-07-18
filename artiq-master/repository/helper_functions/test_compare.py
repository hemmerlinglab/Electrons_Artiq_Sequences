import matplotlib.pyplot as plt
import numpy as np
from dc_electrodes import Electrodes

e1 = Electrodes()
e2 = Electrodes("Single PCB")
multipole_names = ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5']

def plot_all_modes():
    for mode_name in multipole_names:
        multipole_vector = {m: 0.0 for m in multipole_names}
        multipole_vector[mode_name] = 1.0

        print(f"Plotting {mode_name}...")
        grid1, tg1 = e1.get_voltage_grid(multipole_vector)
        grid2, tg2 = e2.get_voltage_grid(multipole_vector)

        vmax1 = np.nanmax(np.abs(grid1))
        vmax2 = np.nanmax(np.abs(grid2))

        fig, axs = plt.subplots(1, 2, figsize=(12, 5))

        for ax, grid, tg, vmax, title in zip(
            axs, [grid1, grid2], [tg1, tg2], [vmax1, vmax2], ["Trap 1", "Trap 2"]
        ):
            im = ax.imshow(grid, cmap='coolwarm', vmin=-vmax, vmax=vmax)
            n_rows, n_cols = grid.shape
            for i in range(n_rows):
                for j in range(n_cols):
                    if not np.isnan(grid[i, j]):
                        ax.text(j, i, f"{grid[i,j]:.2f}", ha='center', va='center', fontsize=8)

            full_title = title
            if tg is not None and not np.isnan(tg):
                full_title += f" (tg={tg:.2f}V)"
            ax.set_title(full_title)
            ax.set_xticks(range(n_cols))
            ax.set_yticks(range(n_rows))
            ax.set_xticklabels(range(1, n_cols+1))
            ax.set_yticklabels(['bl','br','tl','tr'])
            ax.set_xlabel("Order")
            ax.set_ylabel("Row")

            # independent colorbar on the right
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.ax.tick_params(labelsize=8)

        fig.suptitle(f"Multipole: {mode_name}")
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == "__main__":
    plot_all_modes()
