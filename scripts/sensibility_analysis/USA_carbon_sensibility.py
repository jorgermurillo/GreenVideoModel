import subprocess
import argparse
import sys
import os

months = range(1,13)
hosts = [f'obelix{x}' for x in range(121,133)]
print(hosts)

def parse_args():
    parser = argparse.ArgumentParser(description='Run USA carbon server-power sensibility analysis on multiple hosts.')
    parser.add_argument('--cancel', action='store_true', default=False,
                        help='Cancel the running jobs on the specified hosts (default: False)')
    parser.add_argument('--year', type=int, default=2022, help='Year for which to run the experiment (default: 2022)')
    parser.add_argument('--save_load_shifts', action='store_true', help='Save the load shifts data.')
    parser.add_argument('--peak_bit_load_file', type=str, default=None, help='File containing the peak bit load data (default: None)')
    parser.add_argument('--server_power_factors', nargs='+', type=float, default=[1.0],
                        help='List of factors to scale the server power consumption (default: [1.0])')
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
        load_shifts_dir = f'/nfs/obelix/raid/jrmurillo/GreenVideoModel_data/load_shifts/USA_{year}/' if args.save_load_shifts else None
        peak_bit_load_file = args.peak_bit_load_file
        server_power_factors = " ".join(str(f) for f in args.server_power_factors)
        server_power_factor_flag = f'--server_power_factors {server_power_factors}'
        print("Starting USA carbon server-power sensibility analysis on specified hosts and months.")


        for host, month in list(zip(hosts, months)):

            dir_ = f'/nfs/obelix/raid2/jrmurillo/ECORInfo_USA_{year}/{month:02d}'
            print(f"Running on host: {host} with directory: {dir_}")

            if load_shifts_dir:
                load_shifts_dir_month = os.path.join(load_shifts_dir,f"{month:02d}")
                print(load_shifts_dir_month)
                load_shifts_flag = f'--load_shifts_dir {load_shifts_dir_month}'

            else:
                load_shifts_flag = ''

            if peak_bit_load_file:
                peak_bit_load_flag = f'--peak_bit_load_file {peak_bit_load_file} --month {month}'
                results_dir = f'results/sensibility_analysis/USA/USA_carbon_sensibility_year_{year}_peak/'
                output_dir = f'output/experiments/sensibility_analysis/USA/USA_carbon_sensibility_year_{year}_peak/'
            else:
                peak_bit_load_flag = ''
                results_dir = f'results/sensibility_analysis/USA/USA_carbon_sensibility_year_{year}/'
                output_dir = f'output/experiments/sensibility_analysis/USA/USA_carbon_sensibility_year_{year}/'

            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)

            results_dir_flag = f'--results_dir {results_dir}'

            COMMAND = f"source ~/python-greenstreaming/bin/activate && cd ~/GreenVideoModel && nohup python3 scripts/experiment_scripts/carbon_worker_sensibility.py --region_counts_file data/region_counts/region_counts_us.json  --dirs {dir_}  {load_shifts_flag}  {peak_bit_load_flag} {server_power_factor_flag} {results_dir_flag} > {output_dir}USA_carbon_{host}_{month:02d}.out 2>&1 &"

            print(f"Executing command: {COMMAND}")
            ssh = subprocess.Popen(["ssh", "%s" % host, COMMAND], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
