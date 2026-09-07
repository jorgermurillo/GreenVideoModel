import subprocess
import argparse
import sys
import os

months = range(1,13)
# dirs_ = [f'/nfs/obelix/raid2/jrmurillo/ECORInfo_USA/{x:02d}' for x in range(1,13)]
hosts = [f'obelix{x}' for x in range(121,133)]
print(hosts)

def parse_args():
    parser = argparse.ArgumentParser(description='Run USA carbon experiment on multiple hosts.')
    # parser.add_argument('--months', nargs='+', type=int, default=list(range(1, 13)),
    #                     help='List of months to run the experiment for (default: all months)')
    # parser.add_argument('--hosts', nargs='+', type=str, default=[f'obelix{x}' for x in range(121, 133)] ,
    #                     help='List of hosts to run the experiment on (default: obelix121-obelix132)')
    # parser.add_argument('--output_dir', type=str, default='results/USA_carbon/',
    #                     help='Directory to save the output results (default: results/USA_carbon/)')
    parser.add_argument('--cancel', action='store_true', default=False,
                        help='Cancel the running jobs on the specified hosts (default: False)')
    parser.add_argument('--year', type=int, default=2022, help='Year for which to run the experiment (default: 2022)')
    parser.add_argument('--save_load_shifts', action='store_true', help='Save the load shifts data.')
    parser.add_argument('--peak_bit_load_file', type=str, default=None, help='File containing the peak bit load data (default: None)')
    parser.add_argument('--server_power_factor', type=float, default=None, help='Factor to scale the server power consumption (default: 1.0)')
    return parser.parse_args()
# print(dirs_)



if __name__ == "__main__":
    args = parse_args()
    year = args.year
    if args.cancel:
        for host in hosts:
            # cancel_command = "pkill -f USA_carbon_worker.py"
            cancel_command = "pkill -f python3"
            print(f"Cancelling jobs on host: {host}")
            ssh_cancel = subprocess.Popen(["ssh", "%s" % host, cancel_command], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = ssh_cancel.stdout.readlines()
            # if result == []:
            #     error = ssh_cancel.stderr.readlines()
            #     print(f"Error cancelling jobs on host {host}: {error}")
            # else:
            #     print(f"Jobs cancelled successfully on host {host}: {result}")
        sys.exit(0)

    else:
        
        peak_bit_load_file = args.peak_bit_load_file

        if peak_bit_load_file:
            load_shifts_dir = f'/nfs/obelix/raid/jrmurillo/GreenVideoModel_data/load_shifts/USA_{year}_peak/' if args.save_load_shifts else None
        else:
            load_shifts_dir = f'/nfs/obelix/raid/jrmurillo/GreenVideoModel_data/load_shifts/USA_{year}/' if args.save_load_shifts else None


        print("Starting USA carbon experiment on specified hosts and months.")
        for host, month in zip(hosts, months):
            dir_ = f'/nfs/obelix/raid2/jrmurillo/ECORInfo_USA_{year}/{month:02d}'
            print(f"Running on host: {host} with directory: {dir_}")
            # dir_ = f'/nfs/obelix/raid2/jrmurillo/ECORInfo_USA/{month:02d}'
            # COMMAND = '~/GreenVideoModel/scripts/experiment_scripts/USA_carbon_worker.sh   /nfs/obelix/raid2/jrmurillo/ECORInfo_USA/01 /nfs/obelix/raid2/jrmurillo/ECORInfo_USA/02 results/USA_carbon/'

            results_dir = f'results/USA_carbon_year_{year}/'
            os.makedirs(results_dir, exist_ok=True)

            output_dir = f'output/experiments/USA_carbon_year_{year}/'
            os.makedirs(output_dir, exist_ok=True)

            if load_shifts_dir:
                load_shifts_dir_month = os.path.join(load_shifts_dir,f"{month:02d}")
                print(load_shifts_dir_month)
                load_shifts_flag = f'--load_shifts_dir {load_shifts_dir_month}'

                
            else:
                load_shifts_flag = ''

            if peak_bit_load_file:
                peak_bit_load_flag = f'--peak_bit_load_file {peak_bit_load_file} --month {month}'
                results_dir = f'results/USA_carbon_year_{year}_peak/'
                output_dir = f'output/experiments/USA_carbon_year_{year}_peak/'
            else:
                peak_bit_load_flag = ''
                results_dir = f'results/USA_carbon_year_{year}/'
                output_dir = f'output/experiments/USA_carbon_year_{year}/'

            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)
            results_file_flag = f'--results_file {results_dir}USA_carbon_{host}_month_{month:02d}.csv'


            if args.server_power_factor is not None:
                server_power_factor = args.server_power_factor
                server_power_factor_flag = f'--server_power_factor {server_power_factor}'
            else:   
                server_power_factor_flag = ''
                
            COMMAND = f"source ~/python-greenstreaming/bin/activate && cd ~/GreenVideoModel && nohup python3 scripts/experiment_scripts/carbon_worker.py --region_counts_file data/region_counts/region_counts_us.json  --dirs {dir_}  {load_shifts_flag}  {peak_bit_load_flag} {server_power_factor_flag} {results_file_flag} > {output_dir}USA_carbon_{host}_{month:02d}.out 2>&1 &"
            

            '''
            if args.save_load_shifts:
                load_shifts_dir_month = os.path.join(load_shifts_dir,f"{month:02d}")
                print(load_shifts_dir_month)

                COMMAND = f"source ~/python-greenstreaming/bin/activate && cd ~/GreenVideoModel && nohup python3 scripts/experiment_scripts/carbon_worker.py --region_counts_file data/region_counts/region_counts_us.json  --dirs {dir_} --load_shifts_dir {load_shifts_dir_month} --results_file {results_dir}USA_carbon_{host}_month_{month:02d}.csv > {output_dir}USA_carbon_{host}_{month:02d}.out 2>&1 &"
            
            else:
                COMMAND = f"source ~/python-greenstreaming/bin/activate && cd ~/GreenVideoModel && nohup python3 scripts/experiment_scripts/carbon_worker.py --region_counts_file data/region_counts/region_counts_us.json  --dirs {dir_} --results_file {results_dir}USA_carbon_{host}_month_{month:02d}.csv > {output_dir}USA_carbon_{host}_{month:02d}.out 2>&1 &"
            '''
            print(f"Executing command: {COMMAND}")
            
            ssh = subprocess.Popen(["ssh", "%s" % host, COMMAND], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # result = ssh.stdout.readlines()
            # if result == []:
            #     error = ssh.stderr.readlines()
            #     print(f"Error executing command on host {host}: {error}")
            # else:
            #     print(f"Command executed successfully on host {host}: {result}")

        # ssh = subprocess.Popen(["ssh", "%s" % HOST, COMMAND], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

