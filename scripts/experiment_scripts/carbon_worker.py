import argparse
import pprint as pp
from GreenVideoModel import optimize_carbon


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dirs', nargs='+', required=True, help='Directories containing the source CSV files.')
    parser.add_argument('--results_file', required=True, help='File in which to save the results.')
    parser.add_argument('--linear', action='store_true', help='Run the optimization in a linear fashion (for debugging purposes).')
    parser.add_argument('--region_counts_file', required=True, help='File containing the region counts.')
    parser.add_argument('--load_shifts_dir', help='Directory containing the load shifts data.', default=None)

    parser.add_argument('--peak_bit_load_file', help='File containing the peak bit load data.', default=None)
    parser.add_argument('--month', type=int, help='Month for the optimization.', default=None)
    # parser.add_argument('--server_power_factor', type=float, help='Factor to scale server power.', default=1.0)
    # parser.add_argument('--server_power_factors', nargs='+', type=float, help='List of factors to scale server power.', default=None)
    args = parser.parse_args()
    return args

# dirs = [f'/nfs/obelix/raid2/jrmurillo/ECORInfo_USA/{x:02d}' for x in range(1,3)]

if __name__ == "__main__":
    args = parse_args()
    pp.pprint(args.dirs)
    if (args.peak_bit_load_file is not None and args.month is None) or (args.peak_bit_load_file is None and args.month is not None):
        raise ValueError("If peak_bit_load_file is provided, month must also be specified.")
    
    print(f"Output file: {args.results_file}", flush=True)

    # if args.server_power_factors is None:
        
    optimize_carbon(args.dirs, args.results_file, args.region_counts_file, linear=args.linear, load_shifts_dir = args.load_shifts_dir, 
                            peak_bit_load_file = args.peak_bit_load_file, month = args.month, server_power_factor = 1.0)
    # else:
    #     for server_power_factor in args.server_power_factors:
    #         output_dir = 
    #         print(f"Running optimization with server power factor: {server_power_factor}", flush=True)
    #         optimize_carbon(args.dirs, args.results_file, args.region_counts_file, linear=args.linear, load_shifts_dir = args.load_shifts_dir, 
    #                         peak_bit_load_file = args.peak_bit_load_file, month = args.month, server_power_factor = server_power_factor)
   