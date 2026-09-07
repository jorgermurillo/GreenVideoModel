"""
Sketch of a load-shifting optimizer that caps how much EXTRA network energy
a stream is allowed to consume as a result of being shifted away from its
origin datacenter, as opposed to solve_optimization_nominal_power_peak_load()
(GreenVideoModel/optimizers/carbon_optimizer.py) which caps the total bit
load a destination datacenter can *receive*.

Structure mirrors solve_optimization_nominal_power_peak_load() closely so the
two can be swapped in/out for experiments.
"""

import glob
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

from GreenVideoModel.optimizers.carbon_optimizer import (
    bandwidth_load_video_stream,
    solution_value_v,
    get_network_objective_terms,
    get_network_energy_terms,
    calculate_results,
    calculate_results_based_on_server,
    solve_optimization_nominal_power_based_on_server,
    run_in_subprocess,
)


# Same as solve_optimization_nominal_power(), but additionally caps the extra
# network energy a stream (a row of load_shifts, i.e. traffic originating at
# datacenter i) is allowed to incur relative to serving that same traffic
# locally (i == j). This bounds "how much more network energy a video stream
# can use" instead of bounding how much load a destination can receive.
def solve_optimization_network_energy_cap(
    data_df,
    network_carbon_objective_cis=None,
    network_energy_objective_eis=None,
    max_extra_network_energy_frac=None,
    server_power_factor=1,
):
    """
    max_extra_network_energy_frac controls, per origin datacenter i, how much
    more network energy the shifted traffic can use versus the baseline of
    serving all of that datacenter's bit_load locally (network_energy_objective_eis[i, i]).
    A value of 0 forces all traffic to stay local (network-energy-neutral);
    0.2 allows the stream's network energy to grow by up to 20% over baseline.
    Can be a scalar (applied to every datacenter) or an array-like of length
    number_dcs (one value per datacenter, in the same row order as data_df).
    None disables the cap entirely (equivalent to solve_optimization_nominal_power()).
    """
    assert network_energy_objective_eis is not None, \
        "network_energy_objective_eis is required to compute the network energy cap"

    data_df['nominal_power'] = server_power_factor * data_df['bit_load'] / bandwidth_load_video_stream

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        print("Could not create solver GLOP")
    number_dcs = data_df.shape[0]
    load_shifts = np.empty((number_dcs, number_dcs), dtype=object)

    for i, row_i in data_df.iterrows():
        for j, row_j in data_df.iterrows():
            var = solver.NumVar(0, solver.infinity(), f"{i}_{j}")
            load_shifts[i, j] = var

    # Bandwidth capacity constraints (unchanged from solve_optimization_nominal_power)
    for i, row_i in data_df.iterrows():
        solver.Add(load_shifts[:, i].sum() <= row_i["bit_capacity"])

    # Load conservation constraints (unchanged from solve_optimization_nominal_power)
    for i, row_i in data_df.iterrows():
        solver.Add(load_shifts[i].sum() == row_i["bit_load"])

    # Extra-network-energy cap per origin stream: total network energy spent
    # shifting datacenter i's traffic cannot exceed (1 + frac) times what it
    # would have spent serving that same bit_load locally.
    if max_extra_network_energy_frac is not None:
        if np.isscalar(max_extra_network_energy_frac):
            max_extra_network_energy_frac_values = np.full(number_dcs, max_extra_network_energy_frac)
        else:
            max_extra_network_energy_frac_values = np.asarray(max_extra_network_energy_frac)
            assert len(max_extra_network_energy_frac_values) == number_dcs, \
                "max_extra_network_energy_frac must be a scalar or match the number of datacenters in data_df"

        for i, row_i in data_df.iterrows():
            baseline_network_energy_i = network_energy_objective_eis[i, i] * row_i["bit_load"]
            energy_budget_i = (1 + max_extra_network_energy_frac_values[i]) * baseline_network_energy_i
            solver.Add(
                (load_shifts[i] * network_energy_objective_eis[i]).sum() <= energy_budget_i
            )

    watts_to_kwatts_converison_term = 1e-3
    bits_to_gigabits_conversion_term = 1e-9

    network_carbon_objective_terms = bits_to_gigabits_conversion_term * watts_to_kwatts_converison_term * load_shifts * network_carbon_objective_cis

    server_carbon_objective_terms = watts_to_kwatts_converison_term * (load_shifts / bandwidth_load_video_stream) * data_df['carbon_intensity'].to_numpy()

    objective = (server_carbon_objective_terms + network_carbon_objective_terms).sum()
    solver.Minimize(objective)

    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        load_shift_values = solution_value_v(load_shifts)
        return load_shift_values, solver, status
    else:
        return None, None, None


def optimize_files_dummy_energy_cap(files, region_counts_files, max_extra_network_energy_frac=None, server_power_factor=1):
    results = run_in_subprocess(
        optimize_files_energy_cap, files, region_counts_files,
        max_extra_network_energy_frac=max_extra_network_energy_frac, server_power_factor=server_power_factor,
    )
    return results


# Same as optimize_files() in carbon_optimizer.py, but the network-aware
# solve uses solve_optimization_network_energy_cap() instead of
# solve_optimization_nominal_power_peak_load(), so shifted traffic is capped
# by extra network energy rather than by destination bit-load capacity. The
# server-based comparison point is left unconstrained (solve_optimization_nominal_power_based_on_server)
# since that model doesn't account for network energy in the first place.
def optimize_files_energy_cap(files, region_counts_file, load_shifts_dir=None, max_extra_network_energy_frac=None, server_power_factor=1):

    with open(region_counts_file, 'r') as f:
        network_region_counts = json.load(f)
    results_list = []

    for file in files:

        df = pd.read_csv(file)

        df['datetime'] = pd.to_datetime(df['datetime'])
        file_datetime = df['datetime'][0]
        df2 = df.copy()
        target_datetime = datetime(year=file_datetime.year, month=file_datetime.month, day=file_datetime.day, hour=file_datetime.hour)
        network_carbon_terms = get_network_objective_terms(df, target_datetime, network_region_counts)
        network_energy_terms = get_network_energy_terms(df, target_datetime, network_region_counts)
        try:
            loads, solver, status = solve_optimization_network_energy_cap(
                df, network_carbon_objective_cis=network_carbon_terms, network_energy_objective_eis=network_energy_terms,
                max_extra_network_energy_frac=max_extra_network_energy_frac, server_power_factor=server_power_factor,
            )

            df['bit_load_new'] = loads.sum(axis=0)
            df['nominal_power_new'] = server_power_factor * df['bit_load_new'] / bandwidth_load_video_stream
            emissions_results = calculate_results(df, loads, network_carbon_objective_cis=network_carbon_terms, network_energy_objective_eis=network_energy_terms)

            loads_server, solver_server, status_server = solve_optimization_nominal_power_based_on_server(
                df2, distances=None, server_power_factor=server_power_factor,
            )
            df2['bit_load_new'] = loads_server.sum(axis=0)
            df2['nominal_power_new'] = server_power_factor * df2['bit_load_new'] / bandwidth_load_video_stream
            emissions_results_server = calculate_results_based_on_server(df2, loads_server, network_carbon_objective_cis=network_carbon_terms, network_energy_objective_eis=network_energy_terms)

            if load_shifts_dir is not None:
                load_shifts_network_aware_dir = os.path.join(load_shifts_dir, 'network_aware')
                load_shifts_server_based_dir = os.path.join(load_shifts_dir, 'server_based')

                df_load_shifts_network_aware = pd.DataFrame(loads, columns=list(df['a.ecor']))
                df_load_shifts_server_based = pd.DataFrame(loads_server, columns=list(df2['a.ecor']))
                load_shifts_filename_network_aware = os.path.join(load_shifts_network_aware_dir, f'{int(file_datetime.timestamp())}.parquet')
                load_shifts_filename_server_based = os.path.join(load_shifts_server_based_dir, f'{int(file_datetime.timestamp())}.parquet')

                assert np.abs(loads.sum().sum() - loads_server.sum().sum()) < 1e-3

                df_load_shifts_network_aware.to_parquet(load_shifts_filename_network_aware, index=False)
                df_load_shifts_server_based.to_parquet(load_shifts_filename_server_based, index=False)

            results = pd.concat([emissions_results, emissions_results_server], axis=1)
            results_list.append(results)
        except Exception:
            print(f"Exception in file {file}")
            print(traceback.format_exc(), flush=True)

    if len(results_list) == 0:
        return pd.DataFrame()
    else:
        results_df = pd.concat(results_list, axis=0)
        return results_df


# Same as optimize_carbon() in carbon_optimizer.py, but dispatches to
# optimize_files_energy_cap() and takes a single max_extra_network_energy_frac
# instead of a peak_bit_load_file/month pair (the network energy cap is a
# fixed budget, not something that needs to be looked up per month).
def optimize_carbon_energy_cap(input_dirs, output_file, region_counts_file, linear=False, load_shifts_dir=None, max_extra_network_energy_frac=None, server_power_factor=1):

    start_time = time.perf_counter()
    workers = 40

    files = []
    for input_dir in input_dirs:
        files.extend(glob.glob(f'{input_dir}/*.gz'))
    files.sort()

    n_files = len(files)

    ranges = [(int((x / workers) * n_files), int(((x + 1) / workers) * n_files)) for x in range(0, workers)]

    if linear:
        print("Running in linear mode", flush=True)
        results = []
        for file in files:
            res = optimize_files_energy_cap(
                [file], region_counts_file, load_shifts_dir=load_shifts_dir,
                max_extra_network_energy_frac=max_extra_network_energy_frac, server_power_factor=server_power_factor,
            )
            results.append(res)
    else:
        print("Running in parallel mode", flush=True)
        futures = []

        if load_shifts_dir is not None:
            if not os.path.exists(load_shifts_dir):
                load_shifts_network_aware_dir = os.path.join(load_shifts_dir, 'network_aware')
                load_shifts_server_based_dir = os.path.join(load_shifts_dir, 'server_based')
                print(f"Creating directory {load_shifts_network_aware_dir} and {load_shifts_server_based_dir} to store the load shifts")
                os.makedirs(load_shifts_network_aware_dir, exist_ok=True)
                os.makedirs(load_shifts_server_based_dir, exist_ok=True)

        print(f"Running with {workers} workers", flush=True)
        with ProcessPoolExecutor(workers) as pool:
            for start, end in ranges:
                file_slice = files[start:end]
                fut = pool.submit(
                    optimize_files_energy_cap, file_slice, region_counts_file, load_shifts_dir=load_shifts_dir,
                    max_extra_network_energy_frac=max_extra_network_energy_frac, server_power_factor=server_power_factor,
                )
                futures.append(fut)

            results = [x.result() for x in futures]

    final_results = pd.concat(results, axis=0)
    final_results.to_csv(output_file, index=False)

    end_time = time.perf_counter()
    print(f'Time to execute: {end_time - start_time}')
