import subprocess
import argparse
import sys
import os

months = range(1,13)
hosts = [f'obelix{x}' for x in range(121,133)]
print(hosts)

def parse_args():
    parser = argparse.ArgumentParser(description='Run USA network-energy-cap experiment on multiple hosts.')
    parser.add_argument('--cancel', action='store_true', default=False,
                        help='Cancel the running jobs on the specified hosts (default: False)')
    parser.add_argument('--year', type=int, default=2022, help='Year for which to run the experiment (default: 2022)')
    parser.add_argument('--save_load_shifts', action='store_true', help='Save the load shifts data.')
    parser.add_argument('--max_extra_network_energy_fracs', nargs='+', type=float, default=None,
                        help='List of max fractions of extra network energy (over serving locally) a stream may use when shifted. '
                             'Each value is run as its own experiment (default: None, a single uncapped run).')
    parser.add_argument('--server_power_factor', type=float, default=None, help='Factor to scale the server power consumption (default: 1.0)')
    return parser.parse_args()



if __name__ == "__main__":
    args = parse_args()
    year = args.year

    if args.cancel:
        for host in hosts:
            cancel_command = "pkill -f python3"
            print(f"Cancelling jobs on host: {host}")
            ssh_cancel = subprocess.Popen(["ssh", "%s" % host, cancel_command], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = ssh_cancel.stdout.readlines()
        sys.exit(0)

    else:
        max_extra_network_energy_fracs = args.max_extra_network_energy_fracs

        if max_extra_network_energy_fracs is not None:
            load_shifts_dir = f'/nfs/obelix/raid/jrmurillo/GreenVideoModel_data/load_shifts/USA_{year}_energy_limit/' if args.save_load_shifts else None
        else:
            load_shifts_dir = f'/nfs/obelix/raid/jrmurillo/GreenVideoModel_data/load_shifts/USA_{year}/' if args.save_load_shifts else None

        print("Starting USA network-energy-cap experiment on specified hosts and months.")

        for host, month in zip(hosts, months):
            dir_ = f'/nfs/obelix/raid2/jrmurillo/ECORInfo_USA_{year}/{month:02d}'
            print(f"Running on host: {host} with directory: {dir_}")

            if load_shifts_dir:
                load_shifts_dir_month = os.path.join(load_shifts_dir,f"{month:02d}")
                print(load_shifts_dir_month)
                load_shifts_flag = f'--load_shifts_dir {load_shifts_dir_month}'

            else:
                load_shifts_flag = ''

            # The worker nests each frac's own results (and load shifts, if saved) under
            # a frac_<value> subdirectory of results_dir/load_shifts_dir, so results_dir
            # and output_dir here stay constant regardless of how many fracs are swept.
            if max_extra_network_energy_fracs is not None:
                fracs_str = ' '.join(str(f) for f in max_extra_network_energy_fracs)
                energy_limit_flag = f'--max_extra_network_energy_fracs {fracs_str}'
            else:
                energy_limit_flag = ''

            results_dir = f'results/USA_energy_limit_year_{year}/'
            output_dir = f'output/experiments/USA_energy_limit_year_{year}/'

            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)
            results_file_flag = f'--results_file {results_dir}USA_energy_limit_{host}_month_{month:02d}.csv'

            if args.server_power_factor is not None:
                server_power_factor = args.server_power_factor
                server_power_factor_flag = f'--server_power_factor {server_power_factor}'
            else:
                server_power_factor_flag = ''

            COMMAND = f"source ~/python-greenstreaming/bin/activate && cd ~/GreenVideoModel && nohup python3 scripts/energy_limits/energy_limit_worker.py --region_counts_file data/region_counts/region_counts_us.json  --dirs {dir_}  {load_shifts_flag}  {energy_limit_flag} {server_power_factor_flag} {results_file_flag} > {output_dir}USA_energy_limit_{host}_{month:02d}.out 2>&1 &"

            print(f"Executing command: {COMMAND}")

            ssh = subprocess.Popen(["ssh", "%s" % host, COMMAND], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
