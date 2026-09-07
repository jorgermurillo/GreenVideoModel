import argparse
import glob
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

CASES = ["network_aware", "server_based"]
MONTH_DIRS = [f"{month:02d}" for month in range(1, 13)]

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_matrix(file_path):
    df = pd.read_parquet(file_path)
    df.index = df.index.astype(int)
    df.columns = df.columns.astype(int)
    return df


def _add_matrix(sum_df, df):
    all_ids = sum_df.index.union(df.index).union(sum_df.columns).union(df.columns)
    sum_df = sum_df.reindex(index=all_ids, columns=all_ids, fill_value=0)
    df = df.reindex(index=all_ids, columns=all_ids, fill_value=0)
    return sum_df.add(df, fill_value=0)


def _sum_files(files):
    """Worker entry point: read this worker's slice of files and reduce them to a
    single partial sum, so the main process only has to combine one result per
    worker instead of reducing every file one at a time."""
    sum_df = None
    n_files = 0
    for file_path in files:
        try:
            df = _load_matrix(file_path)
        except Exception as exc:
            print(f"Skipping unreadable file {file_path}: {exc}")
            continue

        sum_df = df if sum_df is None else _add_matrix(sum_df, df)
        n_files += 1

    return sum_df, n_files


def average_case(root_dir, case, workers=None):
    """Average every load-shift matrix for a single case (network_aware or server_based)
    across all month subdirectories, aligning on the union of datacenter ids seen so far."""
    files = []
    for month_dir in MONTH_DIRS:
        case_dir = os.path.join(root_dir, month_dir, case)
        if not os.path.isdir(case_dir):
            print(f"Skipping missing directory: {case_dir}")
            continue

        files.extend(sorted(glob.glob(os.path.join(case_dir, "*.parquet"))))

    if not files:
        print(f"No parquet files found for case '{case}' under {root_dir}")
        return None

    n_workers = max(1, min(workers or os.cpu_count() or 1, len(files)))
    chunks = [files[i::n_workers] for i in range(n_workers)]

    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        partial_results = pool.map(_sum_files, chunks)

    sum_df = None
    n_files = 0
    for partial_sum, partial_count in partial_results:
        if partial_sum is None:
            continue
        sum_df = partial_sum if sum_df is None else _add_matrix(sum_df, partial_sum)
        n_files += partial_count

    if sum_df is None:
        print(f"No parquet files found for case '{case}' under {root_dir}")
        return None

    average_df = (sum_df / n_files).sort_index().sort_index(axis=1)
    print(f"Averaged {n_files} files for case '{case}' ({average_df.shape[0]} datacenters)")
    return average_df


def aggregate_by_region(average_df, datacenter_info_path):
    """Aggregate a datacenter-level load-shift matrix into a region-level matrix by
    summing the loads shifted between every pair of datacenters that belong to the
    same pair of regions. Regions come from the 'region' field in the datacenter
    info CSV, keyed by datacenter id (the 'a.ecor' field)."""
    datacenter_info = pd.read_csv(datacenter_info_path)
    id_to_region = datacenter_info.set_index("a.ecor")["region"]

    missing_ids = set(average_df.index).union(average_df.columns) - set(id_to_region.index)
    if missing_ids:
        print(f"Warning: dropping {len(missing_ids)} datacenter id(s) with no region "
              f"mapping in {datacenter_info_path}: {sorted(missing_ids)}")
        average_df = average_df.drop(index=missing_ids, columns=missing_ids, errors="ignore")

    row_regions = id_to_region.reindex(average_df.index)
    col_regions = id_to_region.reindex(average_df.columns)

    region_df = average_df.groupby(row_regions).sum()
    region_df = region_df.T.groupby(col_regions).sum().T
    return region_df


def normalize_region_shifts_by_initial_load(region_shift_df):
    """Normalize a region-to-region load-shift matrix by each source region's total
    initial (pre-shift) load, computed as the row sum of the matrix itself (all
    outgoing load from region i, including load that stayed at i). Returns
    shift[i, j] / initial_load[i], i.e. the fraction of region i's original load
    that ended up at region j."""
    initial_load_by_region = region_shift_df.sum(axis=1)
    return region_shift_df.div(initial_load_by_region, axis=0)


def plot_region_shift_heatmap(region_df, output_path=None, title="Normalized load shift between regions", ax=None, **heatmap_kwargs):
    """Plot a heatmap of a region-to-region load-shift matrix, e.g. the output of
    normalize_region_shifts_by_initial_load. Draws onto `ax` if given (e.g. from
    plot_region_shift_heatmaps_side_by_side), otherwise creates its own figure and
    saves it to output_path if given. Returns the matplotlib Axes."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    owns_figure = ax is None
    if owns_figure:
        fig, ax = plt.subplots(
            figsize=(max(8, 0.4 * len(region_df.columns)), max(6, 0.4 * len(region_df.index)))
        )

    heatmap_kwargs.setdefault("cmap", "viridis")
    heatmap_kwargs.setdefault("cbar_kws", {"label": "Fraction of source region's original load"})
    sns.heatmap(
        region_df,
        ax=ax,
        **heatmap_kwargs,
    )
    ax.set_xlabel("Destination region")
    ax.set_ylabel("Source region")
    ax.set_title(title)

    if owns_figure:
        fig.tight_layout()
        if output_path is not None:
            fig.savefig(output_path)
            print(f"Saved heatmap to {output_path}")

    return ax


def plot_region_shift_heatmaps_side_by_side(
    region_df_left,
    region_df_right,
    titles=("Network aware", "Server based"),
    output_path=None,
    **heatmap_kwargs,
):
    """Plot two region-to-region load-shift matrices side by side (e.g. network_aware
    vs server_based), sharing a single colorbar over the assumed [0, 1] value range
    so both panels are directly comparable. Saves the figure to output_path if given
    and returns the pair of matplotlib Axes."""
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    cmap = heatmap_kwargs.pop("cmap", "viridis")
    vmin = heatmap_kwargs.pop("vmin", 0)
    vmax = heatmap_kwargs.pop("vmax", 1)

    n_cols = max(len(region_df_left.columns), len(region_df_right.columns))
    n_rows = max(len(region_df_left.index), len(region_df_right.index))
    fig, axes = plt.subplots(
        1, 2, figsize=(2 * max(8, 0.4 * n_cols), max(6, 0.4 * n_rows)), constrained_layout=True
    )

    for ax, region_df, title in zip(axes, (region_df_left, region_df_right), titles):
        plot_region_shift_heatmap(
            region_df, title=title, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax, cbar=False, **heatmap_kwargs
        )

    mappable = ScalarMappable(norm=Normalize(vmin=vmin, vmax=vmax), cmap=cmap)
    fig.colorbar(mappable, ax=axes, label="Fraction of source region's original load")

    if output_path is not None:
        fig.savefig(output_path)
        print(f"Saved heatmap comparison to {output_path}")

    return axes


def plot_datacenter_load_comparison(
    peak_shift_df,
    no_peak_shift_df,
    labels=("With peak constraint", "Without peak constraint"),
    peak_cap=None,
    top_n=None,
    output_path=None,
    figsize=None,
):
    """Plot the total load served at each datacenter/region (column sums of a
    source-to-destination load-shift matrix) for a peak-constrained run and an
    unconstrained run, as two vertically stacked bar charts sharing an x- and
    y-axis so bar heights are directly comparable. Locations are ordered by
    unconstrained load (descending) so the same location sits at the same x
    position in both panels, making it easy to see which locations the peak
    constraint pulled load away from. `peak_shift_df` and `no_peak_shift_df` are
    source x destination matrices like those returned by `average_case` or
    `aggregate_by_region`; pass region-level matrices to plot per-region load
    instead of per-datacenter. `peak_cap` can be a single value or a pd.Series
    indexed like the matrices, drawn as a reference line on both panels."""
    import matplotlib.pyplot as plt

    peak_load = peak_shift_df.sum(axis=0)
    no_peak_load = no_peak_shift_df.sum(axis=0)

    all_ids = peak_load.index.union(no_peak_load.index)
    peak_load = peak_load.reindex(all_ids, fill_value=0)
    no_peak_load = no_peak_load.reindex(all_ids, fill_value=0)

    order = no_peak_load.sort_values(ascending=False).index
    if top_n is not None:
        order = order[:top_n]
    peak_load = peak_load.loc[order]
    no_peak_load = no_peak_load.loc[order]

    n = len(order)
    if figsize is None:
        figsize = (max(10, 0.35 * n), 8)

    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True, sharey=True, constrained_layout=True)

    x_labels = [str(i) for i in order]
    for ax, series, label in zip(axes, (peak_load, no_peak_load), labels):
        ax.bar(x_labels, series.values, color="steelblue")
        ax.set_title(label)
        ax.set_ylabel("Load")
        ax.grid(axis="y", alpha=0.3)

        if peak_cap is not None:
            if isinstance(peak_cap, pd.Series):
                ax.plot(x_labels, peak_cap.reindex(order).values, "r--", linewidth=1, label="Peak cap")
            else:
                ax.axhline(peak_cap, color="crimson", linestyle="--", linewidth=1, label="Peak cap")
            ax.legend(loc="upper right")

    axes[-1].set_xlabel("Datacenter / region")
    axes[-1].tick_params(axis="x", rotation=90)
    fig.suptitle("Load per datacenter/region: peak-constrained vs unconstrained")

    if output_path is not None:
        fig.savefig(output_path)
        print(f"Saved plot to {output_path}")

    return axes


def _lorenz_curve(shift_df):
    """Compute the Lorenz curve of load-per-destination for one source-to-destination
    load-shift matrix: locations sorted ascending by load, cumulative share of
    locations vs. cumulative share of total load, plus the Gini coefficient implied
    by that curve. Returns (cum_location_share, cum_load_share, gini), where the
    first two are numpy arrays running from (0, 0) to (1, 1)."""
    load = shift_df.sum(axis=0).sort_values(ascending=True).clip(lower=0)
    total = load.sum()
    n = len(load)

    cum_location_share = np.linspace(0.0, 1.0, n + 1)
    cum_load_share = np.concatenate(([0.0], np.cumsum(load.values) / total))

    gini = 1 - 2 * np.trapz(cum_load_share, cum_location_share)

    return cum_location_share, cum_load_share, gini


def compute_lorenz_curves(peak_shift_df, no_peak_shift_df):
    """Given the peak-constrained and unconstrained source-to-destination load-shift
    matrices for the same experiment, compute the Lorenz curve of load-per-destination
    for each. Returns {'peak': (x, y, gini), 'no_peak': (x, y, gini)}, ready to pass
    to plot_lorenz_curves."""
    return {
        "peak": _lorenz_curve(peak_shift_df),
        "no_peak": _lorenz_curve(no_peak_shift_df),
    }


def plot_lorenz_curves(
    lorenz_data,
    labels=("With peak constraint", "Without peak constraint"),
    separate_panels=False,
    output_path=None,
    figsize=None,
):
    """Plot the Lorenz curves from compute_lorenz_curves against the line of perfect
    equality. By default both curves are overlaid on a single set of axes (with their
    Gini coefficients in the legend), which is the more readable layout for judging
    the gap between the two distributions. Pass separate_panels=True to instead get
    two side-by-side panels, one curve per panel, e.g. to match the side-by-side
    heatmap layout used elsewhere in this file."""
    import matplotlib.pyplot as plt

    keys = ("peak", "no_peak")

    if separate_panels:
        fig, axes = plt.subplots(
            1, 2, figsize=figsize or (10, 5), sharex=True, sharey=True, constrained_layout=True
        )
        for ax, key, label in zip(axes, keys, labels):
            x, y, gini = lorenz_data[key]
            ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1, label="Perfect equality")
            ax.plot(x, y, color="steelblue", linewidth=2, label=f"Gini={gini:.3f}")
            ax.set_title(label)
            ax.set_xlabel("Cumulative share of locations")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_aspect("equal")
            ax.legend(loc="upper left")
        axes[0].set_ylabel("Cumulative share of load")
        result = axes
    else:
        fig, ax = plt.subplots(figsize=figsize or (6, 6), constrained_layout=True)
        ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1, label="Perfect equality")
        for key, label in zip(keys, labels):
            x, y, gini = lorenz_data[key]
            ax.plot(x, y, linewidth=2, label=f"{label} (Gini={gini:.3f})")
        ax.set_xlabel("Cumulative share of datacenters/regions")
        ax.set_ylabel("Cumulative share of load")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.legend(loc="upper left")
        result = ax

    fig.suptitle("Lorenz curve of load distribution across locations")

    if output_path is not None:
        fig.savefig(output_path)
        print(f"Saved plot to {output_path}")

    return result


def main():

    parser = argparse.ArgumentParser(
        description="Average load-shift matrices across the 01-12 month subdirectories "
        "for the network_aware and server_based cases."
    )
    parser.add_argument(
        "--root_dir",
        help="Directory containing the 01-12 month subdirectories, each with "
        "'network_aware' and 'server_based' folders of parquet matrices.",
    )
    parser.add_argument(
        "--output_dir",
        default=os.path.join(_REPO_ROOT, "results", "load_shift_averages"),
        help="Directory to save the averaged matrices to (default: results/load_shift_averages).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=40,
        help="Number of worker processes to use for reading parquet files (default: os.cpu_count()).",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    start = time.time()
    for case in CASES:
        average_df = average_case(args.root_dir, case, workers=args.workers)
        if average_df is None:
            continue

        # output_path_parquet = os.path.join(args.output_dir, f"{case}_average.parquet")
        output_path_csv = os.path.join(args.output_dir, f"{case}_average.csv")
        # average_df.to_parquet(output_path_parquet)
        average_df.to_csv(output_path_csv)
        # print(f"Saved {case} average matrix to {output_path_parquet} and {output_path_csv}")
        print(f"Saved {case} average matrix to {output_path_csv}")
    end = time.time()
    print(f"Completed averaging in {end - start:.2f} seconds.")


if __name__ == "__main__":
    main()
