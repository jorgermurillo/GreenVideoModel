from concurrent.futures import  ProcessPoolExecutor, ThreadPoolExecutor
import glob
import json
from functools import cache
import time
from collections import Counter
import traceback
import pandas as pd
from datetime import datetime
import numpy as np
from GreenVideoModel.dataset_creation.aggregation import aggregate_us_dcs
from GreenVideoModel import get_carbon_intensity, get_carbon_intensities
import pprint as pp
import os

from ortools.init.python import init
from ortools.linear_solver import pywraplp



import subprocess
import sys
import pickle

_WORKER_CODE = (
    "import sys, pickle\n"
    "func, args, kwargs = pickle.load(sys.stdin.buffer)\n"
    "try:\n"
    "    result = ('ok', func(*args, **kwargs))\n"
    "except Exception as exc:\n"
    "    result = ('error', exc)\n"
    "pickle.dump(result, sys.stdout.buffer)\n"
)

def run_in_subprocess(func, *args, timeout=None, **kwargs):
    """Run func(*args, **kwargs) in a separate process and return its result."""
    payload = pickle.dumps((func, args, kwargs))

    proc = subprocess.run(
        [sys.executable, "-c", _WORKER_CODE],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )

    if proc.returncode != 0:
        raise RuntimeError(f"subprocess failed:\n{proc.stderr.decode()}")

    status, value = pickle.loads(proc.stdout)
    if status == "error":
        raise value
    return value




_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# print(_REPO_ROOT)
# _DATACENTER_INFO_USA_PATH = os.path.join(_REPO_ROOT, "data", "aggregated_dcs", "datacenter_info_USA.csv")
_ROUTES_CARBON_PATH = os.path.join(_REPO_ROOT, "data", "routes_carbon", "akamai_us_agg", "{src_dc_id}.json")

bandwidth_load_video_stream = 15555555.555555556
    
def solution_value(x):
    return x.solution_value()

solution_value_v = np.vectorize(solution_value)

def get_routes_energy_intensities(src_dc_id, dst_ids, target_datetime, regions_data):
    src_dc_id_str = str(src_dc_id)
    # carbon_intensities = get_carbon_intensities(target_datetime)
    ei_routers_arr = np.zeros(len(dst_ids))
    ei_regenerators_arr = np.zeros(len(dst_ids))
    ei_amplifiers_arr = np.zeros(len(dst_ids))
    # result = {k: dict1[k] * dict2[k] for k in dict1.keys() & dict2.keys()}
    dst_ids_strs = [str(x) for x in dst_ids]
    for i, dst_dc_id in enumerate(dst_ids_strs):
        routers_regions = regions_data[src_dc_id_str]['locations'][dst_dc_id]
        # try:
        #     ci_routers =  {k: routers_regions[k]  for k in routers_regions.keys() }
        # except TypeError as te:
        #     print(src_dc_id, dst_dc_id)
        #     pp.pprint(routers_regions)
        #     # pp.pprint(carbon_intensities)
        #     raise te
        ei_routers_total = sum(routers_regions.values())
        ei_routers_arr[i] = ei_routers_total

        if src_dc_id_str != dst_dc_id:
            # print(src_dc_id_str, dst_dc_id)
            land_regenerators_regions = regions_data[src_dc_id_str]['land_regenerators'][dst_dc_id]
            # ci_regenerators = {k: land_regenerators_regions[k] * carbon_intensities[k] for k in land_regenerators_regions.keys() & carbon_intensities.keys()}
            ei_regenerators_total = sum(land_regenerators_regions.values())
            ei_regenerators_arr[i] = ei_regenerators_total

            land_amplifiers_regions = regions_data[src_dc_id_str]['land_amplifiers'][dst_dc_id]
            # ci_amplifiers = {k: land_amplifiers_regions[k] * carbon_intensities[k] for k in land_amplifiers_regions.keys() & carbon_intensities.keys()}
            ei_amplifiers_total = sum(land_amplifiers_regions.values())
            ei_amplifiers_arr[i] = ei_amplifiers_total

    return ei_routers_arr, ei_amplifiers_arr, ei_regenerators_arr

def get_network_energy_terms(datacenter_df, target_datetime,  region_counts):

    
    number_dcs = datacenter_df.shape[0]
    network_carbon_objective_eis = np.zeros((number_dcs,number_dcs))

    # print(region_counts)
    # network_ci_factors = np.array([[1.],[0.01315789],[1.31578947]])
    network_energy_intensities_factors = np.array([[2.28], [0.03], [3]])
    
    for i, row in datacenter_df.iterrows():
        dc_id = row["a.ecor"]
        # Get the Carbon intensities of the network from datacenter i to all other datacenters j
        
        eis = get_routes_energy_intensities(dc_id, datacenter_df['a.ecor'], target_datetime, region_counts) 
        
        
        # Get the effective and normalized carbon intensities of the network from datacenter i to all other datacenters j
        eis_to_other_dcs = (eis * network_energy_intensities_factors ).sum(axis = 0)
        network_carbon_objective_eis[i] = eis_to_other_dcs
    return network_carbon_objective_eis


##########

def get_routes_carbon_intensities(src_dc_id, dst_ids, target_datetime, regions_data, mean=False):
    src_dc_id_str = str(src_dc_id)
    carbon_intensities = get_carbon_intensities(target_datetime, mean=mean)
    ci_routers_arr = np.zeros(len(dst_ids))
    ci_regenerators_arr = np.zeros(len(dst_ids))
    ci_amplifiers_arr = np.zeros(len(dst_ids))
    # result = {k: dict1[k] * dict2[k] for k in dict1.keys() & dict2.keys()}
    dst_ids_strs = [str(x) for x in dst_ids]
    for i, dst_dc_id in enumerate(dst_ids_strs):
        routers_regions = regions_data[src_dc_id_str]['locations'][dst_dc_id]
        try:
            ci_routers =  {k: routers_regions[k] * carbon_intensities[k] for k in routers_regions.keys() & carbon_intensities.keys()}
        except TypeError as te:
            print(src_dc_id, dst_dc_id)
            pp.pprint(routers_regions)
            pp.pprint(carbon_intensities)
            raise te
        ci_routers_total = sum(ci_routers.values())
        ci_routers_arr[i] = ci_routers_total

        if src_dc_id_str != dst_dc_id:
            # print(src_dc_id_str, dst_dc_id)
            land_regenerators_regions = regions_data[src_dc_id_str]['land_regenerators'][dst_dc_id]
            ci_regenerators = {k: land_regenerators_regions[k] * carbon_intensities[k] for k in land_regenerators_regions.keys() & carbon_intensities.keys()}
            ci_regenerators_total = sum(ci_regenerators.values())
            ci_regenerators_arr[i] = ci_regenerators_total

            land_amplifiers_regions = regions_data[src_dc_id_str]['land_amplifiers'][dst_dc_id]
            ci_amplifiers = {k: land_amplifiers_regions[k] * carbon_intensities[k] for k in land_amplifiers_regions.keys() & carbon_intensities.keys()}
            ci_amplifiers_total = sum(ci_amplifiers.values())
            ci_amplifiers_arr[i] = ci_amplifiers_total

    return ci_routers_arr, ci_amplifiers_arr, ci_regenerators_arr, 

def get_network_objective_terms(datacenter_df, target_datetime,  region_counts, mean=False):

    
    number_dcs = datacenter_df.shape[0]
    network_carbon_objective_cis = np.zeros((number_dcs,number_dcs))

    # print(region_counts)
    # network_ci_factors = np.array([[1.],[0.01315789],[1.31578947]])
    network_energy_intensities_factors = np.array([[2.28], [0.03], [3]])
    
    for i, row in datacenter_df.iterrows():
        dc_id = row["a.ecor"]
        # Get the Carbon intensities of the network from datacenter i to all other datacenters j
       
        cis = get_routes_carbon_intensities(dc_id, datacenter_df['a.ecor'], target_datetime, region_counts, mean = mean) 
        
        
        # Get the effective and normalized carbon intensities of the network from datacenter i to all other datacenters j
        cis_to_other_dcs = (cis * network_energy_intensities_factors ).sum(axis = 0)
        network_carbon_objective_cis[i] = cis_to_other_dcs
    return network_carbon_objective_cis


@cache
def get_route_data(src_dc_id):
    filename_ = _ROUTES_CARBON_PATH.format(src_dc_id=src_dc_id)
    print(filename_)
    with open(filename_, 'r') as f:
        routes = json.load(f)[f'{src_dc_id}']
    # print(routes)
    return routes

def count_regions(device_region_list):
    

    regions = [x['region'] for x in device_region_list]
    counts = Counter(regions)
    return counts
def get_regions_counts_for_routes(src_dc_id, dst_ids):
    src_dc_id_str = str(src_dc_id)
    routes = get_route_data(src_dc_id_str)
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

def get_regions_counts_for_routes_multiple(src_ids, dst_ids):
    region_counts = {}

    for src_dc_id in src_ids:
        data = get_regions_counts_for_routes(src_dc_id, dst_ids)
        region_counts[str(src_dc_id)] = data
    return region_counts




# This function solves the optimization problem of shifting load around a CDN to decrease carbon footprint, 
# while considering the footprint of both the server and the network.
# It is WRONG!!!
def solve_optimization_nominal_power_old(data_df, network_carbon_objective_cis = None):
    data_df['nominal_power'] = data_df['bit_load']/ bandwidth_load_video_stream
    
    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
    number_dcs = data_df.shape[0]
    load_shifts = np.empty((number_dcs, number_dcs), dtype=object)
    
    for i, row_i in data_df.iterrows():
        for j, row_j in data_df.iterrows():
            var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
            load_shifts[i,j] = var
    # print("Capacity constraint")
    # Set bandwidth capacity constraints
    # constraint = solver.Constraint(-infinity, 2, "ct")
    for i, row_i in data_df.iterrows():
        solver.Add(load_shifts[:,i].sum() <= row_i["bit_capacity"])
    # print("Load conservation constraint")
    # Set BANDWIDTH load conservation constraints
    for i, row_i in data_df.iterrows():
        solver.Add( load_shifts[i].sum() == row_i["bit_load"] )
    
    network_carbon_objective_terms =  1e-9*load_shifts * network_carbon_objective_cis 
    # This one works!!!

    server_carbon_objective_terms = 1000*load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy()
    # server_carbon_objective_terms = load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy()

    # server_carbon_objective_terms = load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy() / 1000/12
    objective = (server_carbon_objective_terms + network_carbon_objective_terms).sum()
    #objective = network_carbon_objective_terms.sum()
    solver.Minimize(objective)

    # print(f"Solving with {solver.SolverVersion()}")

    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        # print("Solution:")
        # print(f"Objective value = {solver.Objective().Value():0.1f}")
        load_shift_values = solution_value_v(load_shifts)
        return load_shift_values, solver, status
    #print(f"x = {x.solution_value():0.1f}")
    #print(f"y = {y.solution_value():0.1f}")
    else:
        # print("The problem does not have an optimal solution.")
        return None, None, None
    
# This function solves the optimization problem of shifting load around a CDN to decrease carbon footprint, 
# while considering the footprint of both the server and the network.
# New function that works!!!
def solve_optimization_nominal_power(data_df, network_carbon_objective_cis = None, server_power_factor = 1):
    data_df['nominal_power'] = server_power_factor*data_df['bit_load']/ bandwidth_load_video_stream
    
    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
    number_dcs = data_df.shape[0]
    load_shifts = np.empty((number_dcs, number_dcs), dtype=object)
    
    for i, row_i in data_df.iterrows():
        for j, row_j in data_df.iterrows():
            var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
            load_shifts[i,j] = var
    # print("Capacity constraint")
    # Set bandwidth capacity constraints
    # constraint = solver.Constraint(-infinity, 2, "ct")
    for i, row_i in data_df.iterrows():
        solver.Add(load_shifts[:,i].sum() <= row_i["bit_capacity"])
    # print("Load conservation constraint")
    # Set BANDWIDTH load conservation constraints
    for i, row_i in data_df.iterrows():
        solver.Add( load_shifts[i].sum() == row_i["bit_load"] )

    watts_to_kwatts_converison_term = 1e-3
    bits_to_gigabits_conversion_term = 1e-9
    
    # network_carbon_objective_terms =  1e-9 * load_shifts * network_carbon_objective_cis # ORIGINAL
    network_carbon_objective_terms =  bits_to_gigabits_conversion_term * watts_to_kwatts_converison_term * load_shifts * network_carbon_objective_cis 
    
    # This one works!!!

    # server_carbon_objective_terms = 1000*load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy() # ORIGINAL
    server_carbon_objective_terms = watts_to_kwatts_converison_term * (load_shifts/bandwidth_load_video_stream) * data_df['carbon_intensity'].to_numpy()

    # server_carbon_objective_terms = load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy() / 1000/12
    objective = (server_carbon_objective_terms + network_carbon_objective_terms).sum()
    #objective = network_carbon_objective_terms.sum()
    solver.Minimize(objective)

    # print(f"Solving with {solver.SolverVersion()}")

    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        # print("Solution:")
        # print(f"Objective value = {solver.Objective().Value():0.1f}")
        load_shift_values = solution_value_v(load_shifts)
        return load_shift_values, solver, status
    #print(f"x = {x.solution_value():0.1f}")
    #print(f"y = {y.solution_value():0.1f}")
    else:
        # print("The problem does not have an optimal solution.")
        return None, None, None

# Same as solve_optimization_nominal_power(), but additionally caps the total
# load a datacenter can receive after shifting via an optional peak_bit_load
# argument, independent of its raw bit_capacity.
def solve_optimization_nominal_power_peak_load(data_df, network_carbon_objective_cis = None, peak_bit_load = None, server_power_factor = 1):
    data_df['nominal_power'] = server_power_factor * data_df['bit_load']/ bandwidth_load_video_stream

    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
    number_dcs = data_df.shape[0]
    load_shifts = np.empty((number_dcs, number_dcs), dtype=object)

    for i, row_i in data_df.iterrows():
        for j, row_j in data_df.iterrows():
            var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
            load_shifts[i,j] = var
    # Set bandwidth capacity constraints, tightened by the optional peak
    # bit_load cap: a single constraint per datacenter using the minimum of
    # bit_capacity and peak_bit_load, instead of two separate constraints.
    # peak_bit_load can be a single scalar (applied to every datacenter) or
    # an array-like of length number_dcs (one value per datacenter, in the
    # same row order as data_df).
    if peak_bit_load is not None:
        if np.isscalar(peak_bit_load):
            peak_bit_load_values = np.full(number_dcs, peak_bit_load)
        else:
            peak_bit_load_values = np.asarray(peak_bit_load)
            assert len(peak_bit_load_values) == number_dcs, \
                "peak_bit_load must be a scalar or match the number of datacenters in data_df"
        capacity_values = np.minimum(data_df["bit_capacity"].to_numpy(), peak_bit_load_values)
    else:
        capacity_values = data_df["bit_capacity"].to_numpy()
    # print("Capacities:")
    # print(data_df['bit_capacity'].to_numpy(), flush=True)
    # print("Actual capacities:", flush = True)
    # print(capacity_values, flush=True)
    for i, row_i in data_df.iterrows():
        solver.Add(load_shifts[:,i].sum() <= capacity_values[i])
    # Set BANDWIDTH load conservation constraints
    for i, row_i in data_df.iterrows():
        solver.Add( load_shifts[i].sum() == row_i["bit_load"] )

    watts_to_kwatts_converison_term = 1e-3
    bits_to_gigabits_conversion_term = 1e-9

    network_carbon_objective_terms =  bits_to_gigabits_conversion_term * watts_to_kwatts_converison_term * load_shifts * network_carbon_objective_cis

    server_carbon_objective_terms = watts_to_kwatts_converison_term * (load_shifts/bandwidth_load_video_stream) * data_df['carbon_intensity'].to_numpy()

    objective = (server_carbon_objective_terms + network_carbon_objective_terms).sum()
    solver.Minimize(objective)

    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        load_shift_values = solution_value_v(load_shifts)
        return load_shift_values, solver, status
    else:
        return None, None, None


def calculate_carbon_emissions(data_df, load_shift_values, network_carbon_objective_cis = None):

    data_df['grams_CO2_server'] = (data_df['nominal_power']/1000)*data_df['carbon_intensity']
    data_df['grams_CO2_server_new'] = (data_df['nominal_power_new']/1000)*data_df['carbon_intensity']
    
    network_route_emissions = ( data_df['bit_load'] * np.diag(network_carbon_objective_cis)/(1e9)/1000/12).sum()
    network_route_emissions_new = (load_shift_values * network_carbon_objective_cis / (1e9)/1000/12).sum()
    # print(network_route_emissions, network_route_emissions_new)
    server_emissions = data_df['grams_CO2_server'].sum()
    server_emissions_new = data_df['grams_CO2_server_new'].sum()
    # print(server_emissions, server_emissions_new)
    total_emissions = network_route_emissions + server_emissions
    total_emissions_new = network_route_emissions_new + server_emissions_new
    
    return 100*(1-(total_emissions_new/total_emissions))


def calculate_results(data_df, load_shift_values, network_carbon_objective_cis = None, network_energy_objective_eis = None):


    server_energy = (data_df['nominal_power']/1000/12).sum()
    server_energy_new = (data_df['nominal_power_new']/1000/12).sum()

    network_energy = ( data_df['bit_load'] * np.diag(network_energy_objective_eis)/ 1000/(1e9)/12 ).sum()
    network_energy_new = ( load_shift_values * network_energy_objective_eis/ 1000/(1e9)/12 ).sum()

    # data_df['grams_CO2_server'] = (data_df['nominal_power']/1000)*data_df['carbon_intensity']
    # data_df['grams_CO2_server_new'] = (data_df['nominal_power_new']/1000)*data_df['carbon_intensity']

    data_df['grams_CO2_server'] = (data_df['nominal_power']/1000/12)*data_df['carbon_intensity']
    data_df['grams_CO2_server_new'] = (data_df['nominal_power_new']/1000/12)*data_df['carbon_intensity']
    
    network_emissions = ( data_df['bit_load'] * np.diag(network_carbon_objective_cis)/(1e9)/1000/12).sum()
    network_emissions_new = (load_shift_values * network_carbon_objective_cis / (1e9)/1000/12).sum()
    # print(network_route_emissions, network_route_emissions_new)
    server_emissions = data_df['grams_CO2_server'].sum()
    server_emissions_new = data_df['grams_CO2_server_new'].sum()
    # print(server_emissions, server_emissions_new)


    # total_emissions = network_emissions + server_emissions
    # total_emissions_new = network_emissions_new + server_emissions_new
    column_names = [f'{x}_NETWORK_AWARE' for x in ['server_energy', 'server_energy_new', 'network_energy', 'network_energy_new' , 'server_emissions', 'server_emissions_new', 'network_emissions', 'network_emissions_new']]
    results = pd.DataFrame( [[server_energy, server_energy_new, network_energy, network_energy_new, server_emissions, server_emissions_new, network_emissions, network_emissions_new]] ,columns = column_names)

    return results
    #return 100*(1-(total_emissions_new/total_emissions))

def calculate_results_based_on_server(data_df, load_shift_values, network_carbon_objective_cis = None, network_energy_objective_eis = None):


    data_df['grams_CO2_server'] = (data_df['nominal_power']/1000/12)*data_df['carbon_intensity']
    data_df['grams_CO2_server_new'] = (data_df['nominal_power_new']/1000/12)*data_df['carbon_intensity']
    # print(data_df['nominal_power'].sum(), data_df['nominal_power_new'].sum())
    
    server_energy = (data_df['nominal_power']/1000/12).sum()
    server_energy_new = (data_df['nominal_power_new']/1000/12).sum()

    network_energy = ( data_df['bit_load'] * np.diag(network_energy_objective_eis)/(1e9)/1000/12).sum() # ( data_df['bit_load'] * np.diag(network_energy_objective_eis)/ 1000/(1e9)/12 ).sum()
    network_energy_new = ((load_shift_values/(1e9)/1000/12)*network_energy_objective_eis).sum() # ( data_df['bit_load_new'] * np.diag(network_energy_objective_eis)/ 1000/(1e9)/12 ).sum()

    network_emissions = ( data_df['bit_load'] * np.diag(network_carbon_objective_cis)/(1e9)/1000/12).sum()
    network_emissions_new = ((load_shift_values /(1e9)/1000/12)*network_carbon_objective_cis).sum()#  data_df['carbon_intensity'].to_numpy()).sum()#(load_shift_values * network_carbon_objective_cis / (1e9)/1000/12).sum()
    
    # print(network_route_emissions, network_route_emissions_new)
    server_emissions = data_df['grams_CO2_server'].sum()
    server_emissions_new = data_df['grams_CO2_server_new'].sum()

    # print(server_emissions, server_emissions_new)
    # total_emissions = network_emissions + server_emissions
    # total_emissions_new = network_emissions_new + server_emissions_new


    # total_emissions = network_emissions + server_emissions
    # total_emissions_new = network_emissions_new + server_emissions_new
    column_names = [f'{x}_SERVER_BASED' for x in ['server_energy', 'server_energy_new', 'network_energy', 'network_energy_new' , 'server_emissions', 'server_emissions_new', 'network_emissions', 'network_emissions_new']]
    results = pd.DataFrame( [[server_energy, server_energy_new, network_energy, network_energy_new, server_emissions, server_emissions_new, network_emissions, network_emissions_new]] ,columns = column_names)

    # results = pd.DataFrame( [[server_energy, server_energy_new, network_energy, network_energy_new, server_emissions, server_emissions_new, network_emissions, network_emissions_new]] ,columns = ['server_energy', 'server_energy_new', 'network_energy', 'network_energy_new' , 'server_emissions', 'server_emissions_new', 'network_emissions', 'network_emissions_new'])

    return results





def calculate_carbon_emissions_based_on_server(data_df, load_shift_values, network_carbon_objective_cis = None):
    # print(data_df['bit_load'].sum())
    # print((load_shift_values * bandwidth_load_video_stream).sum())
    
    data_df['grams_CO2_server'] = (data_df['nominal_power']/1000)*data_df['carbon_intensity']
    data_df['grams_CO2_server_new'] = (data_df['nominal_power_new']/1000)*data_df['carbon_intensity']
    # print(data_df['nominal_power'].sum(), data_df['nominal_power_new'].sum())
    
    network_route_emissions = ( data_df['bit_load'] * np.diag(network_carbon_objective_cis)/(1e9)/1000/12).sum()
    network_route_emissions_new = ((load_shift_values * bandwidth_load_video_stream/(1e9)/1000/12)*network_carbon_objective_cis).sum()#  data_df['carbon_intensity'].to_numpy()).sum()#(load_shift_values * network_carbon_objective_cis / (1e9)/1000/12).sum()
    
    # print(network_route_emissions, network_route_emissions_new)
    server_emissions = data_df['grams_CO2_server'].sum()
    server_emissions_new = data_df['grams_CO2_server_new'].sum()
    # print(server_emissions, server_emissions_new)
    total_emissions = network_route_emissions + server_emissions
    total_emissions_new = network_route_emissions_new + server_emissions_new
    
    return 100*(1-(total_emissions_new/total_emissions))



# This function solves the optimization problem of shifting load around a CDN to decrease carbon footprint, 
# while considering the footprint of ONLY the server.
# def solve_optimization_nominal_power_based_on_server_OLD(data_df):
#     data_df['nominal_power'] = data_df['bit_load']/ bandwidth_load_video_stream
#     data_df['nominal_power_server_capacity'] = data_df['bit_capacity']/ bandwidth_load_video_stream
#     # data_df['server_power_to_bandwidth_frac'] = 1 / data_df['bandwidth_to_flit_frac]
#     # Create the linear solver with the GLOP backend.
#     solver = pywraplp.Solver.CreateSolver("GLOP")
#     if not solver:
#         print("Could not create solver GLOP")
#     number_dcs = data_df.shape[0]
#     load_shifts = np.empty((number_dcs, number_dcs), dtype=object)
    
#     for i, row_i in data_df.iterrows():
#         for j, row_j in data_df.iterrows():
#             var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
#             load_shifts[i,j] = var
#     # print("Capacity constraint")
#     # Set bandwidth capacity constraints
#     # constraint = solver.Constraint(-infinity, 2, "ct")
#     # for i, row_i in data_df.iterrows():
#     #     solver.Add(load_shifts[:,i].sum() <= row_i["bit_capacity"])
#     # print("Load conservation constraint")
#     # # Set BANDWIDTH load conservation constraints
#     # for i, row_i in data_df.iterrows():
#     #     solver.Add( load_shifts[i].sum() == row_i["bit_load"] )


#     for i, row_i in data_df.iterrows():
#         solver.Add( (load_shifts[:,i]/ bandwidth_load_video_stream).sum() <= row_i["nominal_power_server_capacity"] )
        
#     for i, row_i in data_df.iterrows():
#         solver.Add( load_shifts[i].sum() == row_i["nominal_power"] )
    
#     # network_carbon_objective_terms =  1e-9*load_shifts * network_carbon_objective_cis 
#     server_carbon_objective_terms = 1000*load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy()
#     # server_carbon_objective_terms = load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy() / 1000/12
#     objective = server_carbon_objective_terms.sum() #+ network_carbon_objective_terms).sum()
#     #objective = network_carbon_objective_terms.sum()
#     solver.Minimize(objective)
#     # print(f"Solving with {solver.SolverVersion()}")
#     status = solver.Solve()
#     if status == pywraplp.Solver.OPTIMAL:
#         # print("Solution:")
#         # print(f"Objective value = {solver.Objective().Value():0.1f}")
#         load_shift_values = solution_value_v(load_shifts)
#         return load_shift_values, solver, status
#     #print(f"x = {x.solution_value():0.1f}")
#     #print(f"y = {y.solution_value():0.1f}")
#     else:
#         print("The problem does not have an optimal solution.")
#         return None, None, None

def solve_optimization_nominal_power_based_on_server(data_df, distances = None,server_power_factor = 1):
    data_df['nominal_power'] = server_power_factor *data_df['bit_load']/ bandwidth_load_video_stream
    # data_df['nominal_power_server_capacity'] = server_power_factor*data_df['bit_capacity']/ bandwidth_load_video_stream  # BUG: unused now, only fed the buggy constraint below
    # data_df['server_power_to_bandwidth_frac'] = 1 / data_df['bandwidth_to_flit_frac]
    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
    number_dcs = data_df.shape[0]
    load_shifts = np.empty((number_dcs, number_dcs), dtype=object)
    
    for i, row_i in data_df.iterrows():
        for j, row_j in data_df.iterrows():
            var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
            load_shifts[i,j] = var
    
    # for i, row_i in data_df.iterrows():  # BUG: caps with nominal_power_server_capacity (bit_capacity * server_power_factor) instead of raw bit_capacity
    #     solver.Add( (load_shifts[:,i]/ bandwidth_load_video_stream).sum() <= row_i["nominal_power_server_capacity"] )

    # for i, row_i in data_df.iterrows():  # BUG: conserves nominal_power (bit_load * server_power_factor) instead of bit_load, inflating routed traffic by server_power_factor
    #     solver.Add( (load_shifts[i]/ bandwidth_load_video_stream).sum() == row_i["nominal_power"] )
    for i, row_i in data_df.iterrows():
        solver.Add( load_shifts[i].sum() == row_i["bit_load"] )

    # Bandwidth capacity
    for i, row_i in data_df.iterrows():
        solver.Add( (load_shifts[:,i]).sum() <= row_i["bit_capacity"] )
    
    # network_carbon_objective_terms =  1e-9*load_shifts * network_carbon_objective_cis 

    
    # server_carbon_objective_terms = 1000*load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy()

    regularization_term = 0.00001
    
    if not distances is None:
        server_carbon_objective_terms = (load_shifts/bandwidth_load_video_stream).sum(axis=0) * data_df['carbon_intensity'] + (regularization_term*load_shifts*distances).sum(axis=1)
    else:
        server_carbon_objective_terms = (load_shifts/bandwidth_load_video_stream).sum(axis=0) * data_df['carbon_intensity']

    
    # server_carbon_objective_terms = load_shifts/bandwidth_load_video_stream *  data_df['carbon_intensity'].to_numpy() / 1000/12
    objective = server_carbon_objective_terms.sum() #+ network_carbon_objective_terms).sum()
    #objective = network_carbon_objective_terms.sum()
    solver.Minimize(objective)
    # print(f"Solving with {solver.SolverVersion()}")
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        # print("Solution:")
        # print(f"Objective value = {solver.Objective().Value():0.1f}")
        load_shift_values = solution_value_v(load_shifts)
        return load_shift_values, solver, status
    #print(f"x = {x.solution_value():0.1f}")
    #print(f"y = {y.solution_value():0.1f}")
    else:
        print("The problem does not have an optimal solution.")
        return None, None, None

# Same as solve_optimization_nominal_power_based_on_server(), but additionally
# caps the total load a datacenter can receive after shifting via an optional
# peak_load argument, merged with the bit_capacity constraint just like
# solve_optimization_nominal_power_peak_load().
def solve_optimization_nominal_power_based_on_server_peak_load(data_df, distances = None, peak_load = None, server_power_factor = 1):
    data_df['nominal_power'] = server_power_factor * data_df['bit_load']/ bandwidth_load_video_stream
    # data_df['nominal_power_server_capacity'] = server_power_factor * data_df['bit_capacity']/ bandwidth_load_video_stream  # BUG: unused now, only fed the buggy constraint below
    # data_df['server_power_to_bandwidth_frac'] = 1 / data_df['bandwidth_to_flit_frac]
    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
    number_dcs = data_df.shape[0]
    load_shifts = np.empty((number_dcs, number_dcs), dtype=object)

    for i, row_i in data_df.iterrows():
        for j, row_j in data_df.iterrows():
            var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
            load_shifts[i,j] = var

    # for i, row_i in data_df.iterrows():  # BUG: caps with nominal_power_server_capacity (bit_capacity * server_power_factor) instead of raw bit_capacity
    #     solver.Add( (load_shifts[:,i]/ bandwidth_load_video_stream).sum() <= row_i["nominal_power_server_capacity"] )

    # for i, row_i in data_df.iterrows():  # BUG: conserves nominal_power (bit_load * server_power_factor) instead of bit_load, inflating routed traffic by server_power_factor
    #     solver.Add( (load_shifts[i]/ bandwidth_load_video_stream).sum() == row_i["nominal_power"] )
    for i, row_i in data_df.iterrows():
        solver.Add( load_shifts[i].sum() == row_i["bit_load"] )

    # Bandwidth capacity, tightened by the optional peak load cap: a single
    # constraint per datacenter using the minimum of bit_capacity and
    # peak_load, instead of two separate constraints. peak_load can be a
    # single scalar (applied to every datacenter) or an array-like of length
    # number_dcs (one value per datacenter, in the same row order as data_df).
    if peak_load is not None:
        if np.isscalar(peak_load):
            peak_load_values = np.full(number_dcs, peak_load)
        else:
            peak_load_values = np.asarray(peak_load)
            assert len(peak_load_values) == number_dcs, \
                "peak_load must be a scalar or match the number of datacenters in data_df"
        capacity_values = np.minimum(data_df["bit_capacity"].to_numpy(), peak_load_values)
    else:
        capacity_values = data_df["bit_capacity"].to_numpy()

    for i, row_i in data_df.iterrows():
        solver.Add( (load_shifts[:,i]).sum() <= capacity_values[i] )

    regularization_term = 0.00001

    if not distances is None:
        server_carbon_objective_terms = (load_shifts/bandwidth_load_video_stream).sum(axis=0) * data_df['carbon_intensity'] + (regularization_term*load_shifts*distances).sum(axis=1)
    else:
        server_carbon_objective_terms = (load_shifts/bandwidth_load_video_stream).sum(axis=0) * data_df['carbon_intensity']

    objective = server_carbon_objective_terms.sum()
    solver.Minimize(objective)
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        load_shift_values = solution_value_v(load_shifts)
        return load_shift_values, solver, status
    else:
        print("The problem does not have an optimal solution.")
        return None, None, None


def optimize_files_dummy(files, region_counts_files, server_power_factor =1):

    results = run_in_subprocess(optimize_files, files, region_counts_files, server_power_factor =server_power_factor)

    # results = optimize_files(files, network_region_counts)
    return results




def optimize_files(files, region_counts_file, load_shifts_dir = None, peak_bit_load_file = None, month = None, server_power_factor =1):

    if peak_bit_load_file is not None:
        with open(peak_bit_load_file, 'r') as f:
            # print("Peak bit load file:", peak_bit_load_file, flush=True)
            peak_bit_load_df = pd.read_csv(f).set_index('a.ecor')
            peak_bit_load_df.columns = [int(x) for x in peak_bit_load_df.columns]

    with open(region_counts_file, 'r') as f:
        network_region_counts = json.load(f)
    results_list = []

    for file in files:

        df = pd.read_csv(file)

        if peak_bit_load_file is not None:
            peak_bit_load = peak_bit_load_df.loc[df['a.ecor'], month].values#.flatten()
        else:
            peak_bit_load = None

        
        df['datetime'] = pd.to_datetime(df['datetime'])
        file_datetime = df['datetime'][0]
        df2 = df.copy()
        target_datetime = datetime(year = file_datetime.year, month = file_datetime.month, day = file_datetime.day, hour = file_datetime.hour)
        # df_agg = aggregate_us_dcs(df_tmp, target_datetime)
        network_carbon_terms = get_network_objective_terms(df, target_datetime, network_region_counts)
        network_energy_terms = get_network_energy_terms(df, target_datetime,  network_region_counts)
        try:
            # loads, solver, status = solve_optimization_nominal_power(df, network_carbon_objective_cis = network_carbon_terms)
            loads, solver, status = solve_optimization_nominal_power_peak_load(df, network_carbon_objective_cis = network_carbon_terms, peak_bit_load = peak_bit_load, 
                                                                               server_power_factor = server_power_factor )
            
            df['bit_load_new'] = loads.sum(axis=0)#.astype(int)
            df['nominal_power_new'] = server_power_factor * df['bit_load_new']/ bandwidth_load_video_stream
            # emissions_savings = calculate_carbon_emissions(df, loads, network_carbon_objective_cis = network_carbon_terms)
            emissions_results = calculate_results(df, loads, network_carbon_objective_cis = network_carbon_terms, network_energy_objective_eis = network_energy_terms)
            # NETWORK_AWARE_savings_list.append(emissions_results)

            loads_server, solver_server, status_server = solve_optimization_nominal_power_based_on_server_peak_load(df2, peak_load = peak_bit_load, distances = None, 
                                                                                                                    server_power_factor = server_power_factor)
            # emissions_savings_server = calculate_carbon_emissions_based_on_server(df, loads_server, network_carbon_objective_cis = network_carbon_terms)
            df2['bit_load_new'] = loads_server.sum(axis=0)
            df2['nominal_power_new'] = server_power_factor * df2['bit_load_new']/ bandwidth_load_video_stream
            emissions_results_server = calculate_results_based_on_server(df2, loads_server, network_carbon_objective_cis = network_carbon_terms, network_energy_objective_eis = network_energy_terms)
            # SERVER_BASED_savings_server_list.append(emissions_results_server)
            if load_shifts_dir is not None:
                load_shifts_network_aware_dir = os.path.join(load_shifts_dir, 'network_aware')
                load_shifts_server_based_dir = os.path.join(load_shifts_dir, 'server_based')
                
                df_load_shifts_network_aware = pd.DataFrame(loads, columns =  list(df['a.ecor']))
                df_load_shifts_server_based = pd.DataFrame(loads_server, columns =  list(df2['a.ecor']))
                load_shifts_filename_network_aware = os.path.join(load_shifts_network_aware_dir, f'{int(file_datetime.timestamp())}.parquet')
                load_shifts_filename_server_based = os.path.join(load_shifts_server_based_dir, f'{int(file_datetime.timestamp())}.parquet')

                assert(np.abs(loads.sum().sum() - loads_server.sum().sum()) < 1e-3)

                # print(f"Saving load shifts to {load_shifts_filename_network_aware} and {load_shifts_filename_server_based}")
                df_load_shifts_network_aware.to_parquet(load_shifts_filename_network_aware, index=False)
                df_load_shifts_server_based.to_parquet(load_shifts_filename_server_based, index=False)
            
            results = pd.concat([emissions_results, emissions_results_server], axis=1)
            results_list.append(results)
        except:
            print(f"Exception in file {file}")
            # print(loads.sum().sum(), loads_server.sum().sum())
            print(traceback.format_exc(), flush=True)
            
            
        # df2 = df.copy()
        # loads_server, solver_server, status_server = solve_optimization_nominal_power_based_on_server(df2)
        # df2['nominal_power_new'] = loads_server.sum(axis=0)#df['bit_load_new']/ bandwidth_load_video_stream
        # emissions_savings_server = calculate_carbon_emissions_based_on_server(df2, loads_server, network_carbon_objective_cis = network_terms)
        # savings_server_list.append(emissions_savings_server)
    # return NETWORK_AWARE_savings_list, SERVER_BASED_savings_server_list
    
    if len(results_list) == 0:
        return pd.DataFrame()
    else:
        results_df = pd.concat(results_list, axis=0)
        return results_df


# Argument 'linear' set to true means the computation is done in a linear fashion. mostly for debugging purposes.
# Argument 'linear' set to false means the computation is done in parallel using multiple processes.

def optimize_carbon(input_dirs, output_file, region_counts_file, linear=False, load_shifts_dir = None, peak_bit_load_file = None, month = None, server_power_factor =1):

    if (peak_bit_load_file is not None and month is None) or (peak_bit_load_file is None and month is not None):
        raise ValueError("If peak_bit_load_file is provided, month must also be specified. If month is provided, peak_bit_load_file must also be specified.")

    start_time = time.perf_counter()
    workers = 40

    files = []

    for input_dir in input_dirs:
        files.extend(glob.glob(f'{input_dir}/*.gz'))
    

    # files = glob.glob('/nfs/obelix/raid2/jrmurillo/ECORInfo_USA/*/*.gz')
    files.sort()
    # files = files[0:5]
    # files = files[0:50]

    n_files = len(files)

    # datacenter_ids = list(range(402))
    # print(f"Loading the region information for {len(datacenter_ids)} datacenters", flush=True)
    # regioncounts_ml = get_regions_counts_for_routes_multiple(datacenter_ids, datacenter_ids)
    # print(regioncounts_ml)
    # pp.pprint(regioncounts_ml)

    ranges = [ ( int((x/workers)*n_files), int (((x+1)/workers)*n_files)  ) for x in range(0, workers)] 
    
    if linear == True:
        print("Running in linear mode", flush=True)
        results = []
        for file in files:
        # for start, end in ranges:
            # file_slice = files[start:end]
            # print(file, flush=True)
            
            # res = optimize_files([file], regioncounts_ml)
            res = optimize_files([file], region_counts_file)
            results.append(res)       
        return
    else:
        print("Running in parallel mode", flush=True)
        futures =[]
        # results =[]

        # Create directory to store the load shifts if it does not exist and if needed
        if load_shifts_dir is not None:
            if not os.path.exists(load_shifts_dir):
                load_shifts_network_aware_dir = os.path.join(load_shifts_dir, 'network_aware')
                load_shifts_server_based_dir = os.path.join(load_shifts_dir, 'server_based')
                print(f"Creating directory {load_shifts_network_aware_dir} and {load_shifts_server_based_dir} to store the load shifts")
                os.makedirs(load_shifts_network_aware_dir, exist_ok=True)
                os.makedirs(load_shifts_server_based_dir, exist_ok=True)
        # return     
        
        print(f"Running with {workers} workers", flush=True)
        with ProcessPoolExecutor(workers) as pool:
        # with ThreadPoolExecutor(workers) as pool:
            for start, end in ranges:

                    file_slice = files[start:end]
                    # fut = pool.submit(optimize_files_dummy, file_slice, regioncounts_ml)
                    # fut = pool.submit(optimize_files_dummy, file_slice, region_counts_file)
                    fut = pool.submit(optimize_files, file_slice, region_counts_file, load_shifts_dir = load_shifts_dir, peak_bit_load_file = peak_bit_load_file, month = month, server_power_factor=server_power_factor)
                    # print(fut)
                    futures.append(fut) 
                    
                
            # pp.pprint(futures)
            results = [x.result() for x in futures]
    # pp.pprint(results[0:10])
    # pp.pprint(results)


    final_results = pd.concat(results, axis=0)
    final_results.to_csv(output_file, index=False)
    
    # network_results =  [x[0] for x in results]
    # server_only_results = [x[1] for x in results]

    # network_flat_list = [item for sublist in network_results for item in sublist]
    # server_only_flat_list = [item for sublist in server_only_results for item in sublist]

    # network_savings = pd.Series(network_flat_list)
    # server_only_savings = pd.Series(server_only_flat_list)
    
    # final_results = pd.DataFrame({'network_savings': network_savings, 'server_only_savings': server_only_savings})
    # final_results.to_csv(output_file, index=False)
    
    end_time = time.perf_counter()




    print(f'Time to execute: {end_time - start_time}')