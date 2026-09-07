import pandas as pd
#import geopandas as gpd
#import matplotlib.pyplot as plt
#import power_models
from .add_zones_to_routes import get_carbon_regions
#import json
#import pprint as pp
#import route_cleanup
#import matplotlib.patches as mpatches
from haversine import haversine

#from shapely import get_srid, set_srid
#from shapely.geometry import MultiLineString
from shapely.wkt import loads

#import importlib
#importlib.reload(power_models)
#importlib.reload(add_zones_to_routes)

import pyproj
#from shapely import Point
from shapely.ops import transform
from copy import deepcopy
import pprint as pp
from shapely.geometry import LineString, MultiLineString
import pprint as pp
import shapely

DISTANCE_BETWEEN_AMPLIFIERS = 80*1000
DISTANCE_BETWEEN_REGENERATORS = 1500*1000

# def cut_line(linestring, epsilon = 1e-3):
#     lines_list = []
#     line_coords = []
#     previous_coord = None
#     for coord in linestring.coords:
#         # Need to fix this condition so it doesn't cut cables going through the Prime Meridian 
#         #if previous_coord is not None and float_equal(previous_coord[0], -1*coord[0], epsilon = epsilon):
#         if previous_coord is not None and abs(previous_coord[0] - coord[0]) >= 180: #float_equal(previous_coord[0], -1*coord[0], epsilon = epsilon):
#             #print("Hey!!!!!", previous_coord, coord, abs(previous_coord[0] - coord[0]))
#             lines_list.append(line_coords)
#             line_coords = [coord]
#             previous_coord = coord
#             continue
#         line_coords.append(coord)
#         previous_coord = coord
#     lines_list.append(line_coords)
#     #linestrings_list = [LineString(x) for x in lines_list]
#     #return linestrings_list
#     #print(lines_list)
#     multiline = MultiLineString(lines_list)
#     return multiline



class CableIndexingError(Exception):
    """
    Custom exception raised for specific error scenarios in your application.
    """
    def __init__(self, message="A custom error occurred"):
        self.message = message
        super().__init__(self.message)

class GenericCableError(Exception):
    """
    Custom exception raised for specific error scenarios in your application.
    """
    def __init__(self, message="A custom error occurred"):
        self.message = message
        super().__init__(self.message)


def get_lines_from_multilinestrings(multilinestrings):
    lines = []
    for ml in multilinestrings:
    #for line in ml.geoms:
        lines.extend(ml.geoms)
    return lines

# Change projection of geometry from CRS '4326' to '3857' (coordinates to meters)
def change_projection_to_meters(geometry):
    wgs84 = pyproj.CRS('EPSG:4326')
    #utm = pyproj.CRS('EPSG:32618')
    new_crs = pyproj.CRS('EPSG:3857')
    project = pyproj.Transformer.from_crs(wgs84, new_crs, always_xy=True).transform
    geometry_meters = transform(project, geometry)
    return geometry_meters

# Change projection of geometry from CRS  '3857' to '4326'  (meters to coordinates)
def change_projection_to_coordinates(geometry):
    old_crs = pyproj.CRS('EPSG:3857')
    wgs84 = pyproj.CRS('EPSG:4326')
    #utm = pyproj.CRS('EPSG:32618')
    
    project = pyproj.Transformer.from_crs(old_crs, wgs84, always_xy=True).transform
    geometry_coordinates = transform(project, geometry)
    return geometry_coordinates

# Returns sum of haversine distances between points and the avg haversine distance between points.( IN Kilometers)
def get_distances_route_haversine(route):
    distances = []
    for i in range(1, len(route["locations"])):
        distance = haversine(route["locations"][i-1]["loc"], route["locations"][i]["loc"])
        #print(distance)
        distances.append(distance)
    total = sum(distances)
    mean_ = total/len(route)
    return total, mean_


# Returns sum of distances between points and the avg haversine distance between points.( IN Kilometers)
def get_distances_route(route):
    multilinestrings = loads(route["linestrings"])
    linestrings = get_lines_from_multilinestrings(multilinestrings)
    linestrings_3857 = [ change_projection_to_meters(linestring) for linestring in linestrings]
    distances = []
    for line in linestrings_3857:
        distance = line.length/1000
        #print(distance)
        distances.append(distance)
    total = sum(distances)
    mean_ = total/len(linestrings)
    return total, mean_#, len(linestrings_3857)

# Check if there any routes that are equal to None.
def check_for_empty_routes(streaming_routes):
    empty_routes = []
    for city, routes in streaming_routes.items():
        for cloud_region, route in routes.items():
            if route is None:
                empty_routes.append((city, cloud_region))

    return empty_routes

# Add amplifier positions along specific LineString that represents an internet cable going through land.
# 'line' represents a LineString. The LineString should be in coordinate system thhat uses meters
def get_amplifiers_position_in_line(line, distance_between_devices = 100000):
    regenerators_positions = []
    #line = lines_meters[i-1]
    length_line = line.length
    #print(length_line)
    if length_line < distance_between_devices: #DISTANCE_BETWEEN_REGENERATORS:
        #print("TOO SHORT!!")
        return [] # Empty list
    i = 1 
    # We iteratively position amplifiers on the route until we 'run out' of line.
    while True:
        total_distance = i * distance_between_devices #DISTANCE_BETWEEN_REGENERATORS
        if total_distance >=  length_line:
            break
        position_regenerator = line.interpolate(total_distance)
        i = i + 1
        #print(position_regenerator)
        regenerators_positions.append(position_regenerator)
    return regenerators_positions


def float_equal(x1, x2, epsilon = 1e-3):
    return abs(x1-x2) < epsilon

# Return True if coordinates are the same (approx. equal)
def same_coordinates(coord1, coord2, epsilon = 1e-3):
    return float_equal(coord1[0], coord2[0], epsilon = epsilon) and float_equal(coord1[1], coord2[1], epsilon = epsilon)

# # Given a specific route, ***return*** the location of amplifiers on land cables
# # NOTE: some submarine cables get cut into two linestrings. That means that the lengths of the route[]'cable_types'] and 
# # linestrings_3857 are not necessarily the same.
# def get_amplifier_locations_old(route, distance_between_amps = DISTANCE_BETWEEN_AMPLIFIERS):
    
    
#     multilinestrings = loads(route["linestrings"])
    
#     # The way route augmentation works, for each hop, the is a LineString representing the physical route. However, they are grouped together
#     # into several MultiLineStrings for some reason. Here, we unpack them.
#     linestrings = get_lines_from_multilinestrings( multilinestrings )
#     #print(linestrings)
#     # Using EPSG:3857
#     linestrings_3857 = [ change_projection_to_meters(linestring) for linestring in linestrings]

#     regenerators_positions = []
#     cable_types = route["cable_types"]
    
#     tolerance = 1e-1
#     nodes = route["locations"]
#     linestrings_index = 0
#     cable_types_index = linestrings_index
#     #for i in range(len(linestrings_3857)):
#     while linestrings_index < len(linestrings):
#         start_coords_line = (linestrings[linestrings_index].coords[0][1], linestrings[linestrings_index].coords[0][0]) # Coordinates have to be reversed
#         end_coords_line = (linestrings[linestrings_index].coords[-1][1], linestrings[linestrings_index].coords[-1][0]) # Coordinates have to be reversed
#         #loc_1 = hops[i-1]["loc"]
#         #loc_2 = hops[i]["loc"]
#         try:
#             point1_loc = nodes[linestrings_index]["loc"]
#         except IndexError as ie:
#             print(route)
#             print(len(route['linestrings']))
#             print(len(route['locations']))
#             print(route['cable_types'])
#             raise CableIndexingError()
#         try:
#             point2_loc = nodes[linestrings_index+1]["loc"]
#         except IndexError:
#             # We have arrived at the end of the 
#             #print(linestrings_index, start_coords_line, point1_loc, end_coords_line, )
#             # We have reached the last cable. We need to check if it is a land cable to add regenerators/amplifiers
#             if cable_types[cable_types_index] == "land":
#                 points = add_amplifiers_to_land_route(line, distance_between_devices = distance_between_amps)
#                 #pp.pprint(points)
#                 regenerators_positions.extend(points)
#             break
        
#         # We have found a submarine cable split into two linestrings, so linestring[i] and linestring[i+1] represent the same cable
#         if (not (same_coordinates(start_coords_line, point1_loc, epsilon=tolerance) and same_coordinates(end_coords_line, point2_loc, epsilon=tolerance ) ) )and cable_types[cable_types_index] == "submarine" :
#         # if (  ) and cable_types[cable_types_index] == "submarine" :
              
            
#             linestrings_index = linestrings_index + 2
#             cable_types_index = cable_types_index+1
#             continue

#         # We have found a submarine cable that is not split into two.
#         elif  cable_types[cable_types_index] == "submarine" :
#             linestrings_index = linestrings_index+1
#             cable_types_index =cable_types_index +1
#             continue
#         # We have found a land cable
#         else:
#             line = linestrings_3857[linestrings_index]
#             points = add_amplifiers_to_land_route(line, distance_between_devices = distance_between_amps)
#             #pp.pprint(points)
#             regenerators_positions.extend(points)

#             linestrings_index = linestrings_index+1
#             cable_types_index =cable_types_index +1

#         # # If the cable goes through land
#         # if cable_types[i] == "land":
#         #     #print("LAND!")
#         #     line = linestrings_3857[i]
#         #     #print(linestrings[i])
#         #     #print(line)
#         #     points = add_amplifiers_to_land_route(line, distance_between_amps = distance_between_amps)
#         #     #pp.pprint(points)
#         #     regenerators_positions.extend(points)
#         # # If the cable is a submarine cable
#         # else:
#         #     # 
#         #     continue
       
#     regenerator_points = [change_projection_to_coordinates(x) for x in regenerators_positions]
#     #regenerator_coordinates = [ (point.y, point.x) for point in regenerator_points ]
#     regenerator_coordinates = [ {"loc": [point.y, point.x]} for point in regenerator_points ]
#     return regenerator_coordinates



def get_amplifier_locations(route, distance_between_devices = DISTANCE_BETWEEN_AMPLIFIERS):
    
    try:
        multilinestrings = loads(route["linestrings"])
    except shapely.errors.GEOSException as e:
        # print(route["linestrings"])
        raise e
    # The way route augmentation works, for each hop, the is a LineString representing the physical route. However, they are grouped together
    # into several MultiLineStrings for some reason. Here, we unpack them.
    linestrings = get_lines_from_multilinestrings( multilinestrings )
    #print(linestrings)
    # Using EPSG:3857
    multilinestrings_3857 = [ change_projection_to_meters(multilinestring) for multilinestring in multilinestrings]

    regenerators_positions = []
    cable_types = route["cable_types"]
    
    tolerance = 1e-1
    nodes = route["locations"]
    linestrings_index = 0
    cable_types_index = linestrings_index
    #for i in range(len(linestrings_3857)):
    # print(f"Number of linestrings: {len(linestrings)}, Number of cable_types: {len(cable_types)}")
    # assert(len(cable_types)  == len(multilinestrings_3857))
    if len(cable_types)  != len(multilinestrings_3857):
        print(f"Number of cable types: {len(cable_types)}")
        print(f"Number of multilinestrings: {len(multilinestrings)}")
        print(f"Number of linestrings: {len(linestrings)}")
        print(cable_types)
        print(multilinestrings)
        print(linestrings)
        raise GenericCableError("Whoops!")
    # assert(len(cable_types)  == len(multilinestrings_3857))
    
    for mlinestring, cable_type in zip(multilinestrings_3857, cable_types):
        if cable_type == "land":
            points = get_amplifiers_position_in_line(mlinestring, distance_between_devices = distance_between_devices)
            regenerators_positions.extend(points)

    regenerator_points = [change_projection_to_coordinates(x) for x in regenerators_positions]
    #regenerator_coordinates = [ (point.y, point.x) for point in regenerator_points ]
    regenerator_coordinates = [ {"loc": [point.y, point.x]} for point in regenerator_points ]
    return regenerator_coordinates
    

# def get_amplifier_locations_old_2(route, distance_between_amps = DISTANCE_BETWEEN_AMPLIFIERS):
    
#     try:
#         multilinestrings = loads(route["linestrings"])
#     except shapely.errors.GEOSException as e:
#         # print(route["linestrings"])
#         raise e
#     # The way route augmentation works, for each hop, the is a LineString representing the physical route. However, they are grouped together
#     # into several MultiLineStrings for some reason. Here, we unpack them.
#     linestrings = get_lines_from_multilinestrings( multilinestrings )
#     #print(linestrings)
#     # Using EPSG:3857
#     linestrings_3857 = [ change_projection_to_meters(linestring) for linestring in linestrings]

#     regenerators_positions = []
#     cable_types = route["cable_types"]
    
#     tolerance = 1e-1
#     nodes = route["locations"]
#     linestrings_index = 0
#     cable_types_index = linestrings_index
#     #for i in range(len(linestrings_3857)):
#     # print(f"Number of linestrings: {len(linestrings)}, Number of cable_types: {len(cable_types)}")


#     # NOTE: MIGHT NEED TO CHANGE THIS LOGIC, as the 

#     while linestrings_index < len(linestrings):
#         print(f"linestring index: {linestrings_index}, cable_type index: {cable_types_index}, cable type: {cable_types[cable_types_index]}")
#         # print(len(cut_line(linestrings[linestrings_index]).geoms ))
#         # start_coords_line = (linestrings[linestrings_index].coords[0][1], linestrings[linestrings_index].coords[0][0]) # Coordinates have to be reversed
#         line_end_coords = (linestrings[linestrings_index].coords[-1][1], linestrings[linestrings_index].coords[-1][0]) # Coordinates have to be reversed
#         try:
#             next_line_start_coords = (linestrings[linestrings_index + 1].coords[0][1], linestrings[linestrings_index + 1].coords[0][0]) # Coordinates have to be reversed
#         # We have reached the end of the list of linestrings, so we have to check if the last cable is a land cable. If so, we add regenerators
#         except IndexError as ie:
#             if cable_types[cable_types_index] == "land":
#                 points = add_amplifiers_to_land_route(linestrings[linestrings_index], distance_between_amps = distance_between_amps)
#                 regenerators_positions.extend(points)
#                 break
       
        
#         # We have found a submarine cable split into two linestrings, so linestring[i] and linestring[i+1] represent the same cable
#         # If the linestrings "wraps around" the globe and its type is "submarine", then we have found a submarine cable whose linestring representation was cut into two.
#         if ( abs(next_line_start_coords[1] - line_end_coords[1] ) >= 180  ) and cable_types[cable_types_index] == "submarine" :
#             # print("\n\nHELLO!\n\n")
            
#             linestrings_index = linestrings_index + 2
#             cable_types_index = cable_types_index + 1
#             continue

#         # We have found a submarine cable that is not split into two.
#         elif  cable_types[cable_types_index] == "submarine" :
#             linestrings_index = linestrings_index + 1
#             cable_types_index =cable_types_index  + 1
#             continue
#         # We have found a land cable
#         else:
#             line = linestrings_3857[linestrings_index]
#             points = add_amplifiers_to_land_route(line, distance_between_amps = distance_between_amps)
#             #pp.pprint(points)
#             regenerators_positions.extend(points)

#             linestrings_index = linestrings_index + 1
#             cable_types_index =cable_types_index  + 1

#     # print(f"linestring: {linestrings_index}, cable_type: {cable_types_index}")
#     regenerator_points = [change_projection_to_coordinates(x) for x in regenerators_positions]
#     #regenerator_coordinates = [ (point.y, point.x) for point in regenerator_points ]
#     regenerator_coordinates = [ {"loc": [point.y, point.x]} for point in regenerator_points ]
#     return regenerator_coordinates



# Given a specific route, ***return*** the location of amplifiers on land cables
# NOTE: some submarine cables get cut into two linestrings. That means that the lengths of the route[]'cable_types'] and 
# linestrings_3857 are not necessarily the same.
# def get_amplifier_locations_original(route, distance_between_amps = DISTANCE_BETWEEN_AMPLIFIERS):
    
    
#     multilinestrings = loads(route["linestrings"])
    
#     # The way route augmentation works, for each hop, the is a LineString representing the physical route. However, they are grouped together
#     # into several MultiLineStrings for some reason. Here, we unpack them.
#     linestrings = get_lines_from_multilinestrings( multilinestrings )
#     #print(linestrings)
#     # Using EPSG:3857
#     linestrings_3857 = [ change_projection_to_meters(linestring) for linestring in linestrings]

#     regenerators_positions = []
#     cable_types = route["cable_types"]
    
    

#     for i in range(len(linestrings_3857)):
#         #loc_1 = hops[i-1]["loc"]
#         #loc_2 = hops[i]["loc"]
        
#         # If the cable goes through land
#         if cable_types[i] == "land":
#             #print("LAND!")
#             line = linestrings_3857[i]
#             #print(linestrings[i])
#             #print(line)
#             points = add_amplifiers_to_land_route(line, distance_between_amps = distance_between_amps)
#             #pp.pprint(points)
#             regenerators_positions.extend(points)
#         # If the cable is a submarine cable
#         else:
#             # 
#             continue
       
#     regenerator_points = [change_projection_to_coordinates(x) for x in regenerators_positions]
#     #regenerator_coordinates = [ (point.y, point.x) for point in regenerator_points ]
#     regenerator_coordinates = [ {"loc": [point.y, point.x]} for point in regenerator_points ]
#     return regenerator_coordinates


# Add locations of amplifiers on land routes 
def add_amplifier_locations(streaming_routes, distance_between_devices = DISTANCE_BETWEEN_AMPLIFIERS ):
    for user_loc, routes in streaming_routes.items():
            for cloud_region, route_info in routes.items():
                # try:
                if not route_info["error"]:
                    try:
                        amplifiers = get_amplifier_locations(route_info, distance_between_devices = distance_between_devices)
                        route_info["land_amplifiers"] = amplifiers
                    except CableIndexingError as cie:
                        print(f"Error from user location: {user_loc}, streaming from {cloud_region}")
                        #print()
                        raise cie
                    except shapely.errors.GEOSException as e:
                        print(user_loc, cloud_region)
                        raise e
                    except GenericCableError as error:
                        print(user_loc, cloud_region)
                        raise error
                        

                # except:
                #     print(user_loc, cloud_region)
    return streaming_routes

# Add locations of amplifiers on land routes 
def add_regenerator_locations(streaming_routes, distance_between_devices = DISTANCE_BETWEEN_REGENERATORS ):
    for user_loc, routes in streaming_routes.items():
            for cloud_region, route_info in routes.items():
                # try:
                if not route_info["error"]:
                    try:
                        amplifiers = get_amplifier_locations(route_info, distance_between_devices = distance_between_devices)
                        route_info["land_regenerators"] = amplifiers
                    except CableIndexingError as cie:
                        print(f"Error from user location: {user_loc}, streaming from {cloud_region}")
                        #print()
                        raise cie
                    except shapely.errors.GEOSException as e:
                        print(user_loc, cloud_region)
                        raise e
                    except GenericCableError as error:
                        print(user_loc, cloud_region)
                        raise error
                        

                # except:
                #     print(user_loc, cloud_region)
    return streaming_routes
            
# Add carbon regions to routers along the route
def add_carbon_regions_to_hops(streaming_routes):
    routes_regions = deepcopy(streaming_routes)
    for user_loc, routes in routes_regions.items():
        #inner_dict = {}
        for cloud_region, route in routes.items():
            #print(route)
            if route != None:
            #clean_route = route_cleanup.fill_locs(route)
            #new_route = add_zones_to_routes.get_carbon_regions(clean_route)
            
                new_route = get_carbon_regions(route["locations"])
            else:
                new_route = route
            routes_regions[user_loc][cloud_region]["locations"] = new_route
            #inner_dict[cloud_region] = new_route
        #routes_regions[user_loc] = inner_dict
    return routes_regions

# Add carbon regions to amplifiers
def add_carbon_regions_to_amplifiers(streaming_routes):
    #routes_regions = deepcopy(streaming_routes)
    for user_loc, routes in streaming_routes.items():
        #inner_dict = {}
        for cloud_region, route in routes.items():
            #print(route)
            if route != None:
            #clean_route = route_cleanup.fill_locs(route)
            #new_route = add_zones_to_routes.get_carbon_regions(clean_route)
            
                #new_route = add_zones_to_routes.get_carbon_regions(route["locations"])
                try:
                    amplifiers_with_carbon_regions = get_carbon_regions(route["land_amplifiers"])
                except KeyError as ke:
                    print(user_loc, cloud_region)
                    pp.pprint(route.keys())
                    
            else:
                new_route = route
            streaming_routes[user_loc][cloud_region]["land_amplifiers"] = amplifiers_with_carbon_regions
            #inner_dict[cloud_region] = new_route
        #routes_regions[user_loc] = inner_dict
    return streaming_routes

# Add carbon regions to amplifiers
def add_carbon_regions_to_regenerators(streaming_routes):
    #routes_regions = deepcopy(streaming_routes)
    for user_loc, routes in streaming_routes.items():
        #inner_dict = {}
        for cloud_region, route in routes.items():
            #print(route)
            if route != None:
            #clean_route = route_cleanup.fill_locs(route)
            #new_route = add_zones_to_routes.get_carbon_regions(clean_route)
            
                #new_route = add_zones_to_routes.get_carbon_regions(route["locations"])
                try:
                    regenerators_with_carbon_regions = get_carbon_regions(route["land_regenerators"])
                except KeyError as ke:
                    print(user_loc, cloud_region)
                    pp.pprint(route.keys())
                    
            else:
                new_route = route
            streaming_routes[user_loc][cloud_region]["land_regenerators"] = regenerators_with_carbon_regions
            #inner_dict[cloud_region] = new_route
        #routes_regions[user_loc] = inner_dict
    return streaming_routes

# Add amplifiers and identify the carbon region for every router and amplifier
def add_amplifiers_and_carbon_regions(streaming_routes, distance_between_amps = DISTANCE_BETWEEN_AMPLIFIERS, distance_between_regens = DISTANCE_BETWEEN_REGENERATORS):

    print("Adding amplifiers to land routes", flush = True)
    streaming_routes = add_amplifier_locations(streaming_routes, distance_between_devices = distance_between_amps)
    print("Adding amplifiers to land routes", flush = True)
    streaming_routes = add_regenerator_locations(streaming_routes, distance_between_devices = distance_between_regens)
    print("Adding carbon regions to routers", flush = True)
    streaming_routes = add_carbon_regions_to_hops(streaming_routes)
    print("Adding carbon regions to amplifiers", flush = True)
    streaming_routes = add_carbon_regions_to_amplifiers(streaming_routes)
    print("Adding carbon regions to regenerators", flush = True)
    streaming_routes = add_carbon_regions_to_regenerators(streaming_routes)
    return streaming_routes


###############################



