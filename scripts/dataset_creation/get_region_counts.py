from collections import Counter
from functools import cache
import os
import json
import argparse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# print(_REPO_ROOT)
# _DATACENTER_INFO_USA_PATH = os.path.join(_REPO_ROOT, "data", "aggregated_dcs", "datacenter_info_USA.csv")
# _ROUTES_CARBON_PATH = os.path.join(_REPO_ROOT, "data", "routes_carbon")#, "akamai_us_agg", "{src_dc_id}.json")


@cache
def get_route_data(src_dc_id, region):

    if region == "US":
        # _ROUTES_CARBON_PATH = os.path.join(_REPO_ROOT, "data", "routes_carbon", "akamai_us_agg", "{src_dc_id}.json")
        _ROUTES_CARBON_PATH = os.path.join(_REPO_ROOT, "data", "routes_carbon", "akamai_us_agg", "{src_dc_id}.json")
    elif region == "EU":
        _ROUTES_CARBON_PATH = os.path.join(_REPO_ROOT, "data", "routes_carbon", "akamai_eu_agg", "{src_dc_id}.json")

    filename_ = _ROUTES_CARBON_PATH.format(src_dc_id=src_dc_id)

    # print(filename_)
    with open(filename_, 'r') as f:
        routes = json.load(f)[f'{src_dc_id}']
    # print(routes)
    return routes

def count_regions(device_region_list):
    

    regions = [x['region'] for x in device_region_list]
    counts = Counter(regions)
    return counts
def get_regions_counts_for_routes(src_dc_id, dst_ids, region):
    src_dc_id_str = str(src_dc_id)
    routes = get_route_data(src_dc_id_str, region)
    # pp.pprint(routes)
    data = {'locations': {}, 'land_regenerators': {}, 'land_amplifiers': {}}
    # 'hops' or routers
    for dst_dc_id in [str(x) for x in dst_ids]:
        # print(type(dst_dc_id))
        if dst_dc_id == src_dc_id_str:
            #print(type(dst_dc_id))
            random_key = list(routes.keys())[0]
            data_tmp = routes[f'{random_key}']
            # We need to append the carbon intensity of the location where the datacenter resides
            region = data_tmp['locations'][0]['region']
            data['locations'][src_dc_id_str] = {region:1}
        else:
            # print(dst_dc_id)
            data['locations'][dst_dc_id] = count_regions(routes[dst_dc_id]['locations'])
            data['land_regenerators'][dst_dc_id] = count_regions(routes[dst_dc_id]['land_regenerators'])
            data['land_amplifiers'][dst_dc_id] = count_regions(routes[dst_dc_id]['land_amplifiers'])
    return data

def get_regions_counts_for_routes_multiple(src_ids, dst_ids, region = None):

    if not region in ["US", "EU"]:
        raise ValueError("Region must be one of 'US' or 'EU'.")
    region_counts = {}

    for src_dc_id in src_ids:
        try:
            data = get_regions_counts_for_routes(src_dc_id, dst_ids, region)
            region_counts[str(src_dc_id)] = data
        except FileNotFoundError:
            pass

    return region_counts


def parse_args():
    parser = argparse.ArgumentParser(description='Get region counts for routes between source and destination datacenters.')
    # parser.add_argument('--src_ids', nargs='+', type=int, required=True, help='List of source datacenter IDs.')
    # parser.add_argument('--dst_ids', nargs='+', type=int, required=True, help='List of destination datacenter IDs.')
    parser.add_argument('--region', type=str, choices=['US', 'EU'], required=True, help='Region for which to get the route data (US or EU).')
    return parser.parse_args()

if __name__ == "__main__":
    # src_ids = [1, 2, 3]
    # dst_ids = [4, 5, 6]
    args = parse_args()
    region = args.region
    if region == "US":
        src_ids = list(range(402))
    elif region == "EU":
        src_ids = list(range( 149))
    dst_ids = src_ids
    region_counts = get_regions_counts_for_routes_multiple(src_ids, dst_ids, region)
    # output_file = f"./data/region_counts/region_counts_{region.lower()}.json"
    output_file = f"./data/region_counts/region_counts_{region.lower()}.json"
    # print(region_counts)
    with open(output_file, 'w') as f:
        json.dump(region_counts, f, indent=4)