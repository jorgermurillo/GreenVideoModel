'''
Given a route from CAIDA, this script queries iGDB and obtains the shortest path between the two points. 
'''


import requests
import json
import pprint as pp
import copy
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import argparse
import random

src_loc = (42.35843, -71.05977)
dst_loc = (37.35411, -121.95524)   

low_confidence_locations = (
(59.3247, 18.056), # Stockholm, Sweden
(37.751, -97.822), # Wichita, Kansas
    )

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

        

def get_linestrings(src_loc, dst_loc, infer= True, port = None, hostname = None):
    if hostname is None:
        host = 'localhost'
    else:
        host = hostname
    if infer:
        url = f"http://{host}:{port}/shortest-route-infra/"
    else:
        url = f"http://{host}:{port}/shortest-route-infra-no-infer/"

    # print(f"URL: {url}", flush = True)
    retries = 5
    timeout = 60*10 # 10 minutes
    for i in range(retries):
        try:
            res = requests.get( url  , params={
                    'src_latitude': src_loc[0],
                    'src_longitude': src_loc[1],
                    'dst_latitude': dst_loc[0],
                    'dst_longitude': dst_loc[1],
                }, timeout=timeout)
            data = res.json()
            return data
        except requests.exceptions.JSONDecodeError as json_error:
            print(f"JSON Error querying 'src_latitude': {src_loc[0]}, 'src_longitude': {src_loc[1]}, 'dst_latitude': {dst_loc[0]},  'dst_longitude': {dst_loc[1]} on {i+1} try")
            if i == retries-1:
                raise json_error
        except requests.exceptions.ReadTimeout as timeout_error:
            print(f"Timeout Error querying 'src_latitude': {src_loc[0]}, 'src_longitude': {src_loc[1]}, 'dst_latitude': {dst_loc[0]},  'dst_longitude': {dst_loc[1]} on {i+1} try")
            if i == retries-1:
                raise timeout_error


    return data

def get_infrastructure_routes(route, port = None):
    
    route_copy = fill_locs(route)

    locations =[route_copy[0]["loc"]]
    linestrings = []
    cable_types = []
    for i in range(1, len(route_copy)):
        data = get_linestrings(route_copy[i-1]["loc"], route_copy[i]["loc"], port = port)
        
        if data["too_close"]:
            locations.append(route_copy[i]["loc"])
            linestrings.append( data["linestrings"] )
            cable_types.append( "land" )
        else:    
            
            # If the nodes are NOT too close, we need to obtain the cities in the middle.

       
            locations.extend(data["shortest_path_cities"][1:])
            locations[-1] = route[i]["loc"]

            linestrings.extend(data["linestrings"][1:])
            cable_types.extend(data["cable_types"][1:])

    return {"shortest_path_cities": locations, "linestrings": linestrings, "cable_types": cable_types }


def get_infrastructure_route_2(route, infer = True, port = None, hostname = None):
    error = False

    route_copy = fill_locs(route)

    return_route = [route_copy[0]]

    locations = [route_copy[0]]
    linestrings = []
    cable_types = []
    for i in range(1, len(route_copy)):
        data = get_linestrings(route_copy[i-1]["loc"], route_copy[i]["loc"], infer = infer, port = port, hostname = hostname)
        #pp.pprint(data["fiber_wkt_paths"])
        #print(len(data["fiber_wkt_paths"]))
        if "detail" in data.keys():
            if data["detail"] == "No shortest path found":
                locations.extend( [None, route_copy[i] ]) # We add a None, so that we can still get the rest of the route for debugging purposes.
                #locations.append( route_copy[i] )
                cable_types.append(None) # We add a None, so that we can still get the rest of the route for debugging purposes.
                error = True
                continue # keep augmenting the rest of the route
        #pp.pprint(data['routers_latlon'])
        sys.stdout.flush()
        locations.extend( [ {"id": None, "AS": None, "loc":loc} for loc in data['routers_latlon'][1:-1]  ])
        locations.append( route_copy[i] )
        cable_types.extend(data["fiber_types"])
        linestrings.extend(data["fiber_wkt_paths"])

    # assert(len(cable_types) == len(linestrings))
    if len(cable_types) != len(linestrings):
        print(f"Cable types: {len(cable_types)}, linestrings: {len(linestrings)}")
        print( cable_types )
        print( linestrings )
    return {"locations": locations, "linestrings": linestrings, "cable_types": cable_types, "error": error}


def test():
    '''
    routes_file = open("routes.1.json", "r")
    data = json.load(routes_file)

    boston_route = data["boston"]["us-west-1"]
    pp.pprint(boston_route)
    boston_route_fixed = fill_locs(boston_route)

    #pp.pprint(boston_route)
    pp.pprint(boston_route_fixed)
    '''
    same_city_route = [{'AS': 1299, 'id': 22548, 'loc': [42.35843, -71.05977]},
                       {'AS': 1299, 'id': 22548, 'loc': [42.35843, -71.06]}]

    boston_dublin_routes = [{'AS': 1299, 'id': 22548, 'loc': [42.35843, -71.05977]},
                       {'id': 60092078, 'loc': [53.3472, -6.2439], 'AS': 39233}]


    

    test_route =[{'AS': 1299, 'id': 22548, 'loc': [42.35843, -71.05977]},
                 {'AS': 1299, 'id': 333, 'loc': [41.82999, -87.75005]},
                 {'AS': 1299, 'id': 1504, 'loc': [33.942501, -118.407997]}]

    #routes = get_infrastructure_routes(boston_route_fixed)
    
    # routes = get_infrastructure_routes_2(test_route)
    # print("\n\n\n\n")
    # print("Final result!")
    # pp.pprint(routes)


    routes = get_infrastructure_route_2(test_route)
    print("\n\n\n\n")
    print("Final result!")
    #pp.pprint(routes)

    with open("augmented_results.json", "w") as f:
        json.dump(routes, f)

    # url = "http://localhost:8083/shortest-route-infra/"

    # res = requests.get( url  , params={
    #         'src_latitude': src_loc[0],
    #         'src_longitude': src_loc[1],
    #         'dst_latitude': dst_loc[0],
    #         'dst_longitude': dst_loc[1],
    #        })

    # data = res.json()

    # pp.pprint(data)
        



# Testing if the issues with generating routes that "wrap around the globe" (cross the 180th Meridian, generally because of a submarine cable)
def test_wrap_around():
    routes_filename  = "routes.3.json"
    out_filename = "wrap_around.test.json"

    with open(routes_filename, "r") as f:
        routes_original = json.load(f)
        boston_indonesia = {"boston": {"ap-southeast-3": routes_original["boston"]["ap-southeast-3"],
                                       "ap-southeast-5": routes_original["boston"]["ap-southeast-5"]
                                       },
                            "los angeles": {"ap-southeast-3": routes_original["los angeles"]["ap-southeast-3"],
                                       "ap-southeast-5": routes_original["los angeles"]["ap-southeast-5"]
                                       }
                            }
    pp.pprint(boston_indonesia["boston"].keys())

    routes_augmented = {}
    for city, routes in boston_indonesia.items():
        routes_to_cloud ={}
        for cloud, route in routes.items():
            # pp.pprint(cloud)
            # pp.pprint(route)
            # print("\n")
            if route is not None:
                augmented_route = get_infrastructure_route_2(route, infer=True)
                #pp.pprint(augmented_route["locations"])

            else:
                augmented_route = None
                #print(None)

            routes_to_cloud[cloud] = augmented_route
        #print("##############")
        routes_augmented[city] = routes_to_cloud
            

    with open(out_filename, "w") as outfile:
        json.dump(routes_augmented, outfile)

def get_route_no_infer():
    routes_filename  = "routes.3.json"
    out_filename = "boston.ap-southeast.no_infer.json"
    

    with open(routes_filename, "r") as f:
        routes_original = json.load(f)
        boston_indonesia = {"boston": {"ap-southeast-3": routes_original["boston"]["ap-southeast-3"],
                                       "ap-southeast-5": routes_original["boston"]["ap-southeast-5"]
                                       }
                            }
    pp.pprint(boston_indonesia["boston"].keys())

    routes_augmented = {}
    for city, routes in boston_indonesia.items():
        routes_to_cloud ={}
        for cloud, route in routes.items():
            # pp.pprint(cloud)
            # pp.pprint(route)
            # print("\n")
            if route is not None:
                augmented_route = get_infrastructure_route_2(route, infer=False)
                #pp.pprint(augmented_route["locations"])

            else:
                augmented_route = None
                #print(None)

            routes_to_cloud[cloud] = augmented_route
        #print("##############")
        routes_augmented[city] = routes_to_cloud
            

    with open(out_filename, "w") as outfile:
        json.dump(routes_augmented, outfile)


def test_symmetry():
    #routes_filename  = sys.argv[1]
    #out_filename = sys.argv[2]

    routes = {"test":{"barcelona_london": [{'id': 8462, 'loc': [41.38879, 2.15899], 'AS': 9049, 'region': 'ES'},
                                        {'id': 573718, 'loc': [51.4964, -0.1224], 'AS': 9049, 'region': 'GB'}],
            "london_barcelona": [ {'id': 573718, 'loc': [51.4964, -0.1224], 'AS': 9049, 'region': 'GB'},
                                 {'id': 8462, 'loc': [41.38879, 2.15899], 'AS': 9049, 'region': 'ES'}]
    }}

    pp.pprint(routes)
    
    routes_augmented = {}
    for city, routes in routes.items():
        routes_to_cloud ={}
        for cloud, route in routes.items():
            pp.pprint(cloud)
            pp.pprint(route)
            # print("\n")
            if route is not None:
                augmented_route = get_infrastructure_route_2(route)
                #pp.pprint(augmented_route["locations"])

            else:
                augmented_route = None
                #print(None)

            routes_to_cloud[cloud] = augmented_route
        #print("##############")
        routes_augmented[city] = routes_to_cloud

    with open("symmetry_routes.json", "w") as outfile:
        json.dump(routes_augmented, outfile)

def main(routes_filename = None, out_filename =None, port = None):
    # routes_filename  = sys.argv[1]
    # out_filename = sys.argv[2]

    with open(routes_filename, "r") as f:
        routes_original = json.load(f)

    routes_augmented = {}
    for city, routes in routes_original.items():
        routes_to_cloud ={}
        for cloud, route in routes.items():
            # pp.pprint(cloud)
            # pp.pprint(route)
            # print("\n")
            if route is not None:
                try:
                    augmented_route = get_infrastructure_route_2(route,port = port)
                except requests.exceptions.JSONDecodeError as e:
                    print(city, cloud)
                    raise e
                #pp.pprint(augmented_route["locations"])

            else:
                augmented_route = None
                #print(None)

            routes_to_cloud[cloud] = augmented_route
        #print("##############")
        routes_augmented[city] = routes_to_cloud
            

    with open(out_filename, "w") as outfile:
        json.dump(routes_augmented, outfile)


def augment_routes_parallel(routes_filename = None, out_filename =None, hostname = None, port = None, n_threads = 10):
    # routes_filename  = sys.argv[1]
    # out_filename = sys.argv[2]

    if routes_filename is None or out_filename is None or port is None:
        raise TypeError("At least one of the arguments is None.")

    with open(routes_filename, "r") as f:
        routes_original = json.load(f)
    

    routes_augmented_futures = {}

    # with ThreadPoolExecutor(n_threads) as executor:
    with ProcessPoolExecutor(n_threads) as executor:
        for city, routes in routes_original.items():
            #print(city)
            routes_to_cloud ={}
            routes_to_cloud_futures = {}
            for cloud, route in routes.items():
                #print(f"\t{cloud}")
                # pp.pprint(cloud)
                # pp.pprint(route)
                # print("\n")
                if route is not None:
                    #augmented_route = get_infrastructure_route_2(route)
                    
                    augmented_route_fut = executor.submit(get_infrastructure_route_2, route, port = port, hostname = hostname )
                    
                    #pp.pprint(augmented_route["locations"])

                else:
                    augmented_route_fut = None
                    #print(None)

                routes_to_cloud_futures[cloud] = augmented_route_fut
            #print("##############")
            routes_augmented_futures[city] = routes_to_cloud_futures
        # pp.pprint(routes_augmented_futures)
        sys.stdout.flush()
        # print("HEY!!")
        routes_augmented = {}
        for city, route_futures in routes_augmented_futures.items():
            print(city)
            routes_to_cloud = {}#{ cloud: route_fut for cloud, route_fut in }
            for cloud, route_fut in route_futures.items():
                print(f"\t{cloud}")
                if route_fut is None:
                    routes_to_cloud[cloud] = None
                else:
                    print("\t\twaiting for the future!!!", flush=True)
                    try:
                        routes_to_cloud[cloud] = route_fut.result()
                    except requests.exceptions.JSONDecodeError as jsonerror:
                        print(f'ERROR getting the route from {city} to {cloud}', flush=True)

            routes_augmented[city] = routes_to_cloud


    with open(out_filename, "w") as outfile:
        json.dump(routes_augmented, outfile)

    print("DONE!!", flush=True)


# def augment_routes_parallel_2(routes_filename = None, out_filename =None, hostnames = [], port = None, n_threads = 10):
#     # routes_filename  = sys.argv[1]
#     # out_filename = sys.argv[2]

#     if routes_filename is None or out_filename is None or port is None:
#         raise TypeError("At least one of the arguments is None.")

#     with open(routes_filename, "r") as f:
#         routes_original = json.load(f)
    

#     routes_augmented_futures = {}

#     # with ThreadPoolExecutor(n_threads) as executor:
#     with ProcessPoolExecutor(n_threads) as executor:
#         for city, routes in routes_original.items():
#             #print(city)
#             routes_to_cloud ={}
#             routes_to_cloud_futures = {}
#             for cloud, route in routes.items():
#                 #print(f"\t{cloud}")
#                 # pp.pprint(cloud)
#                 # pp.pprint(route)
#                 # print("\n")
#                 if route is not None:
#                     #augmented_route = get_infrastructure_route_2(route)
#                     augmented_route_fut = executor.submit(get_infrastructure_route_2, route, port = port, hostname = hostname )

#                     #pp.pprint(augmented_route["locations"])

#                 else:
#                     augmented_route_fut = None
#                     #print(None)

#                 routes_to_cloud_futures[cloud] = augmented_route_fut
#             #print("##############")
#             routes_augmented_futures[city] = routes_to_cloud_futures
#         # pp.pprint(routes_augmented_futures)
#         sys.stdout.flush()
#         # print("HEY!!")
#         routes_augmented = {}
#         for city, route_futures in routes_augmented_futures.items():
#             print(city)
#             routes_to_cloud = {}#{ cloud: route_fut for cloud, route_fut in }
#             for cloud, route_fut in route_futures.items():
#                 print(f"\t{cloud}")
#                 if route_fut is None:
#                     routes_to_cloud[cloud] = None
#                 else:
#                     print("\t\twaiting for the future!!!", flush=True)
#                     routes_to_cloud[cloud] = route_fut.result()
#             routes_augmented[city] = routes_to_cloud


#     with open(out_filename, "w") as outfile:
#         json.dump(routes_augmented, outfile)

#     print("DONE!!", flush=True)    

def parse_args():

    # routes_filename  = sys.argv[1]
    # out_filename = sys.argv[2]

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', help='Port where the application is running.', type=int, default=None)
    parser.add_argument('--routes_filename', help='Input file.', type=str, default=None)
    parser.add_argument('--out_filename', help='Output file.', type=str, default=None)
    parser.add_argument('--n_threads', help='Number threads.', type=int, default=None)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    #get_route_no_infer()
    #test_symmetry()
    #test_wrap_around()
    args = parse_args()
    print(args.n_threads)
    augment_routes_parallel(routes_filename=args.routes_filename, out_filename = args.out_filename, port = args.port, n_threads = args.n_threads)
    # main(routes_filename=args.routes_filename, out_filename = args.out_filename, port = args.port)