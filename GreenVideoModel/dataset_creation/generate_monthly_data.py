import argparse
import calendar
import glob
import os
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import pandas as pd
import pprint as pp
from .aggregation import aggregate_na_dcs, aggregate_us_dcs, aggregate_eu_dcs, aggregate_asia_dcs

# def parse_args():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--region', required=True, help='Region between US, EU or ASIA.')
#     parser.add_argument('--input_dir', required=True, help='Directory containing the source CSV files.')
#     parser.add_argument('--output_dir', required=True, help='Directory in which subdirectories 1-12 (one per month) will be created.')
#     args = parser.parse_args()
#     return args


# The source day/hour come from the unix timestamp prefixed to each filename
# (e.g. "1375315200_data.csv"), matching the naming convention used elsewhere
# in this repo (see optimize_files() in network_carbon_terms.py).
def get_target_datetime(filepath, month, year = 2022):
    filename = os.path.basename(filepath)
    timestamp = int(filename.split('_')[0])
    file_date = datetime.fromtimestamp(timestamp)

    _, days_in_month = calendar.monthrange(year, month)
    day = min(file_date.day, days_in_month)

    return datetime(year=year, month=month, day=day, hour=file_date.hour, minute=file_date.minute)

def process_month(input_dir, output_dir, month, aggregation_function, year=2022):
    # month_dir = os.path.join(output_dir, str(month))
    month_dir = os.path.join(output_dir, f'{month:02d}')
    os.makedirs(month_dir, exist_ok=True)

    files = glob.glob(os.path.join(input_dir, '*_data.dat.clean.gz'))
    files.sort()
    # files = files[0:1]  # Limit to first two files for testing; remove this line for full processing
    # print(files)
    for filepath in files:
        # print(filepath)
        target_datetime = get_target_datetime(filepath, month, year=year)
        # print(target_datetime)
        data = pd.read_csv(filepath)
        # print("Original shape")
        # print(data.shape)
        # The carbon intensity data has an hourly granularity, so we need to round the target datetime to the nearest hour for accurate aggregation.
        target_datetime_carbon_intensity = datetime(year=target_datetime.year, month=target_datetime.month, day=target_datetime.day, hour=target_datetime.hour)
        # data_agg = aggregate_us_dcs(data, target_datetime)
        data_agg = aggregation_function(data, target_datetime_carbon_intensity)
        data_agg['datetime'] = target_datetime
        # print("results DF shape")
        # print(data_agg.shape)
        # print(data_agg)
        filename = os.path.basename(filepath)
        _, rest = filename.split('_', 1)
        new_filename = f"{int(target_datetime.timestamp())}_{rest}"
        # print(new_filename)
        # print(data_agg)
        data_agg.to_csv(os.path.join(month_dir, new_filename), index=False)
    return f"Processed month {month} and saved to {month_dir}"

# def main():
#     args = parse_args()
#     os.makedirs(args.output_dir, exist_ok=True)



def generate_monthly_data(input_dir, output_dir, region, year=2022):
    # region = args.region.upper()
    if region not in ['US', 'EU', 'ASIA']:
        raise ValueError("Region must be one of 'US', 'EU', or 'ASIA'.")    
    if region == 'US':
        aggregate_function = aggregate_us_dcs
    elif region == 'EU':
        aggregate_function = aggregate_eu_dcs
    elif region == 'NA':
        aggregate_function = aggregate_na_dcs
    elif region == 'ASIA':  
        aggregate_function = aggregate_asia_dcs



    # for month in range(1, 13):
    #     process_month(input_dir, output_dir, month, aggregate_function)
    futures = []
    with ProcessPoolExecutor() as executor:
        # for month in range(1, 2):
        for month in range(1, 13):
            fut = executor.submit(process_month, input_dir, output_dir, month, aggregate_function, year=year)
            futures.append(fut)
            # break  # Remove this break to process all months; it's here for testing purposes
        # executor.map(lambda month: process_month(input_dir, output_dir, month, aggregate_function), range(1, 13))
        results = [x.result() for x in futures]
    pp.pprint(results)
# if __name__ == '__main__':
#     main()
