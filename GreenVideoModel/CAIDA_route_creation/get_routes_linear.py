from .create_graph_2 import CAIDA_GRAPH
import networkx as nx
from concurrent.futures import ProcessPoolExecutor
import pprint as pp
import time
from haversine import haversine
import json
import sys
import copy
import argparse

low_confidence_locations = {
                (59.3247, 18.056), # Stockholm, Sweden
                (37.751, -97.822), # Wichita, Kansas
}

def check_loc_eq(loc1, loc2, epsilon = 0.01):
    lat1, long1 = loc1
    lat2, long2 = loc2

    if abs(lat1- lat2) < epsilon and abs(long1- long2) < epsilon:
        return True
    else:
        return False

def fill_locs(route):
    route_copy = copy.deepcopy(route)

    
    # Generally speaking, the first location wont be "low confidence"
    previous_loc = route_copy[0]["loc"]
    for hop in route_copy[1:]:
        loc = hop["loc"]
        changed = False
        for low_con_loc in low_confidence_locations:
            if check_loc_eq(loc, low_con_loc):
                # Fill the location with the previous value
                #print("Low confidence!!")
                hop["loc"] = previous_loc
                changed = True
                break
            
        if not changed:
            previous_loc = loc

    return route_copy


def get_node_gen(nodelist):
    for node in nodelist:
        yield node

def get_distances_route(route):
    distances = []
    for i in range(1, len(route)):
        distance = haversine(route[i-1]["loc"], route[i]["loc"])
        distances.append(distance)
    total = sum(distances)
    #mean_ = total/len(route)
    return total#, mean_

# Returns True if the total distanxce of the route is less than the haversine distance from the beginning location
# to the end location times the multiplier.
def validate_route_length(route, multiplier = 2):
    route_distance = get_distances_route(route)

    distance_start_to_end = haversine(route[0]["loc"], route[-1]["loc"])

    return route_distance <= multiplier* distance_start_to_end


def get_longest_route(client_loc, datacenter_loc, caida_graph, multiplier = 2):
    closest_points_client, closest_points_client_distance = caida_graph.get_closest_points(client_loc)
    #print(closest_points_client)
    closest_node_client = closest_points_client[0]
    #print(closest_node_client)
    closest_points_dc, closest_points_dc_distance = caida_graph.get_closest_points(datacenter_loc)
    closest_nodes_gen = get_node_gen(closest_points_dc)
    current_route = None
    current_route_length = 0
    while True:
        try:
            next_node = next(closest_nodes_gen)
            #print(next_node)
        except StopIteration as si:

            if current_route is None:
                current_route = caida_graph.get_info_for_path([closest_node_client, next_node])
            return current_route
        route = caida_graph.get_route_by_ids(closest_node_client, next_node)
        fixed_route = fill_locs(route)
        if not validate_route_length(fixed_route):
            continue
        if len(fixed_route) > current_route_length:
            current_route = fixed_route
            current_route_length = len(current_route)


def get_a_route(client_loc, datacenter_loc, caida_graph, multiplier = 2):
    closest_points_client, closest_points_client_distance = caida_graph.get_closest_points(client_loc)
    #print(closest_points_client)
    closest_node_client = closest_points_client[0]
    #print(closest_node_client)
    closest_points_dc, closest_points_dc_distance = caida_graph.get_closest_points(datacenter_loc)
    closest_nodes_gen = get_node_gen(closest_points_dc)
    while True:
        try:
            next_node = next(closest_nodes_gen)
            #print(next_node)
        except StopIteration as si:
            #print("Iteration stopped!!")
            route = caida_graph.get_info_for_path([closest_node_client, next_node])
            return route
        route = caida_graph.get_route_by_ids(closest_node_client, next_node)
        fixed_route = fill_locs(route)
        if validate_route_length(fixed_route):
            return route
        
        # if len(fixed_route) > current_route_length:
        #     current_route = fixed_route
        #     current_route_length = len(current_route)

def get_route_main(src_dst_filename, results_filename , longest_route = False):
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--src_dst_filename', help='path to the json file that contains the source and destinations.')
    # parser.add_argument('--results_filename', help='path to the json file that contains the routes between sources and destinations.')
    # parser.add_argument("--longest_route", action='store_true')
    # args = parser.parse_args()
    #parser.print_help()

    # src_dst_filename = args.src_dst_filename #sys.argv[1]
    # results_filename = args.results_filename #sys.argv[2]

    # number_processes = 20
    with open(src_dst_filename, "r") as f:
        src_dst_json = json.load(f)

    print("Loading Graph!", flush = True)
    start = time.time()
    caida_graph = CAIDA_GRAPH()
    caida_graph.load_node_set()
    caida_graph.create_graph(load_subset= True) 
    caida_graph.create_node_id_AS_mapping()
    mid = time.time()
    
    if longest_route:
        get_route_func = get_longest_route
    else:
        get_route_func = get_a_route

    print("Graph Loaded!", flush=True)
    print(f"Time to load graph: {mid - start}", flush = True)
    #with ProcessPoolExecutor(number_processes) as pool:
    client_dc_routes = {}
    for client_name, client_info in src_dst_json.items():
        client_loc = client_info["client_loc"]
        datacenter_locations = client_info["server_locs"]
        client_dc_routes[client_name] = {}
        #print(client_name, flush = True)
        for carbon_region, server_location in datacenter_locations.items():
            #print(f"\t{carbon_region}", flush = True)
            route_fut = get_route_func(client_loc, server_location, caida_graph)
            #print("Submitted!")
            client_dc_routes[client_name][carbon_region] = route_fut
            #break
        #break
    #print(client_dc_routes_futures)
    # client_dc_routes_results = {}
    # for k,v in client_dc_routes_futures.items():
    #     dict_ = {k2:v2.result() for k2,v2 in v.items()}
    #     client_dc_routes_results[k] = dict_
    end =time.time()
    with open(results_filename, "w") as f:
        #pp.pprint(client_dc_routes_results, stream = f)
        json.dump(client_dc_routes, f)
    print(f"Time to get all routes: {end-mid}", flush=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--src_dst_filename', help='path to the json file that contains the source and destinations.')
    parser.add_argument('--results_filename', help='path to the json file that contains the routes between sources and destinations.')
    parser.add_argument("--longest_route", action='store_true')
    args = parser.parse_args()
    #parser.print_help()

    src_dst_filename = args.src_dst_filename #sys.argv[1]
    results_filename = args.results_filename #sys.argv[2]

    number_processes = 20
    with open(src_dst_filename, "r") as f:
        src_dst_json = json.load(f)

    print("Loading Graph!", flush = True)
    start = time.time()
    caida_graph = CAIDA_GRAPH()
    caida_graph.load_node_set()
    caida_graph.create_graph(load_subset= True) 
    caida_graph.create_node_id_AS_mapping()
    mid = time.time()
    
    if args.longest_route:
        get_route_func = get_longest_route
    else:
        print("Using get_a_route function for route retrieval.")
        get_route_func = get_a_route

    print("Graph Loaded!", flush=True)
    print(f"Time to load graph: {mid - start}", flush = True)
    #with ProcessPoolExecutor(number_processes) as pool:
    client_dc_routes = {}
    for client_name, client_info in src_dst_json.items():
        client_loc = client_info["client_loc"]
        datacenter_locations = client_info["server_locs"]
        client_dc_routes[client_name] = {}
        print(client_name, flush = True)
        for carbon_region, server_location in datacenter_locations.items():
            print(f"\t{carbon_region}", flush = True)
            route_fut = get_route_func(client_loc, server_location, caida_graph)
            #print("Submitted!")
            client_dc_routes[client_name][carbon_region] = route_fut
            #break
        #break
    #print(client_dc_routes_futures)
    # client_dc_routes_results = {}
    # for k,v in client_dc_routes_futures.items():
    #     dict_ = {k2:v2.result() for k2,v2 in v.items()}
    #     client_dc_routes_results[k] = dict_
    end =time.time()
    with open(results_filename, "w") as f:
        #pp.pprint(client_dc_routes_results, stream = f)
        json.dump(client_dc_routes, f)
    print(f"Time to get all routes: {end-mid}", flush=True)

    