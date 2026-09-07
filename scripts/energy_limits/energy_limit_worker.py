import argparse
import os
import pprint as pp
# from GreenVideoModel.optimizers.network_energy_cap_optimizer import optimize_carbon_energy_cap
from GreenVideoModel import optimize_carbon_energy_cap


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dirs', nargs='+', required=True, help='Directories containing the source CSV files.')
    parser.add_argument('--results_file', required=True, help='File in which to save the results.')
    parser.add_argument('--linear', action='store_true', help='Run the optimization in a linear fashion (for debugging purposes).')
    parser.add_argument('--region_counts_file', required=True, help='File containing the region counts.')
    parser.add_argument('--load_shifts_dir', help='Directory containing the load shifts data.', default=None)
    parser.add_argument('--max_extra_network_energy_fracs', nargs='+', type=float, default=None,
                        help='List of max fractions of extra network energy (over serving locally) a stream may use when shifted. '
                             'Each value is run as its own experiment, saved under its own frac_<value> subdirectory of --results_file (default: None, a single uncapped run).')
    parser.add_argument('--server_power_factor', type=float, default=1.0, help='Factor to scale server power.')
    args = parser.parse_args()
    return args


# Nests the results file (and, if given, the load shifts dir) under a
# frac_<value> subdirectory, e.g. ("results/foo.csv", 0.2) ->
# "results/frac_0.2/foo.csv", so each frac's experiment lives in its own dir.
def _nest_under_frac_dir(path, max_extra_network_energy_frac):
    parent_dir, basename = os.path.split(path)
    return os.path.join(parent_dir, f"frac_{max_extra_network_energy_frac}", basename)


if __name__ == "__main__":
    args = parse_args()
    pp.pprint(args.dirs)

    # None means "run a single uncapped experiment", so it still loops once.
    max_extra_network_energy_fracs = args.max_extra_network_energy_fracs if args.max_extra_network_energy_fracs is not None else [None]

    for max_extra_network_energy_frac in max_extra_network_energy_fracs:
        if max_extra_network_energy_frac is None:
            results_file = args.results_file
            load_shifts_dir = args.load_shifts_dir
        else:
            results_file = _nest_under_frac_dir(args.results_file, max_extra_network_energy_frac)
            load_shifts_dir = os.path.join(args.load_shifts_dir, f"frac_{max_extra_network_energy_frac}") if args.load_shifts_dir else None


        os.makedirs(os.path.dirname(results_file), exist_ok=True)

        # print(f"max_extra_network_energy_frac={max_extra_network_energy_frac} -> output file: {results_file}", flush=True)
        # print(f"load_shifts_dir={load_shifts_dir}", flush=True)
        optimize_carbon_energy_cap(args.dirs, results_file, args.region_counts_file, linear=args.linear,
                                    load_shifts_dir=load_shifts_dir,
                                    max_extra_network_energy_frac=max_extra_network_energy_frac,
                                    server_power_factor=args.server_power_factor)
