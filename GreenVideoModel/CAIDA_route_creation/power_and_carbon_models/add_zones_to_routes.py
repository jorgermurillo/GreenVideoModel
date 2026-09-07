import geopandas as gpd
import pandas as pd
from shapely.geometry import  Point
from shapely.ops import transform
from multiprocessing import Pool
import pprint as pp
import os
import pyproj


currdir = os.path.dirname(__file__)

#print(f"Current dir: {currdir}")
dataset_directory = os.path.join(currdir, "../../..","data")
# print(dataset_directory)
#print(f"Dataset dir dir: {dataset_directory}")
shapefile_df = gpd.read_file(f"{dataset_directory}/world.geojson").to_crs('EPSG:3857')#.set_crs('EPSG:4326')#"./datasets/world.geojson")

# print(shapefile_df.crs)
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



def get_zonename(shapefile, routers):
    data = []
    for i, row in routers.iterrows():
        longitude = row["longitude"]
        latitude = row["latitude"]
        p = Point(longitude, latitude)
        # This series tells if Point p is contained in a Shape from shapefile_df
        contains_series = shapefile["geometry"].contains(p)
        indeces = contains_series[contains_series == True].index
        if indeces.size == 1:
            region = shapefile.loc[indeces[0], "zoneName"]
            #row_list = list(row)
            #row_list.append(region)
            #data.append(row_list)
        elif indeces.size == 0:
            #row_list = list(row)
            #row_list.append("")
            #data.append(row_list)
            #print("EMPTY: ", row, contains_series[contains_series == True])
            region = closest_region(shapefile, p)
    
        row_list = list(row)
        row_list.append(region)
        data.append(row_list)

    df = pd.DataFrame(data, columns = ["id", "latitude", "longitude", "state", "zoneName"])

    return df


def closest_region(shapefile, p):
    #routers_df = pd.read_csv("../datasets/node_location/US_nodes.csv")
    #shapefile_df = gpd.read_file("../world.geojson")
    #total_rows = routers_df.shape[0]

    #p = Point(routers_df["longitude"][0], routers_df["latitude"][0])
    p_meters = change_projection_to_meters(p)
    distances = p_meters.distance(shapefile["geometry"])
    #print(distances)
    ind = distances.argmin()
    #print("Index: ",ind)
    distance_km = distances.at[ind]/1000
    #print(distance_km)
    if distance_km > 200:
        return None
    answer = shapefile.loc[ind]
    
    return answer["zoneName"]

# def distance_to_shape_test():
#     routers_df = pd.read_csv("./data/US_nodes.csv")
#     shapefile_df = gpd.read_file("../world.geojson")
#     total_rows = routers_df.shape[0]

#     p = Point(routers_df["longitude"][0], routers_df["latitude"][0])

#     distances = p.distance(shapefile_df["geometry"])
#     #print(distances)
#     ind = distances.argmin()
#     #print("Index: ",ind)
#     #print(shapefile_df.loc[ind])

#     answer = shapefile_df.loc[ind]

#     return answer["zoneName"]
    

def get_carbon_regions(route, shapefile_df = shapefile_df):
    try:
        for node in route:
            if node is None:
                continue
            region = closest_region(shapefile_df,  Point(node["loc"][1],  node["loc"][0])  )
            node["region"] = region
    except TypeError as te:
        pp.pprint(route)
        raise te
    #regions = [ node + ( closest_region(shapefile_df, Point(node[1]["loc"][1],  node[1]["loc"][0])) ,) for node in route]
    #pp.pprint(regions)
    return route



def main():
    # ROUTES
    quebec_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
        (4841, {'loc': (42.3907, -71.1349)}, 14742),
        (711992, {'loc': (42.3643, -71.005203)}, 174),
        (3989, {'loc': (42.3643, -71.005203)}, 174),
        (17788, {'loc': (45.4706, -73.740799)}, 174),
        (528261, {'loc': (45.1987, -73.5675)}, 5769),
        (43744186, {'loc': (45.5954, -73.4365)}, 5769)]    
    
    washington_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
        (4841, {'loc': (42.3907, -71.1349)}, 14742),
        (711992, {'loc': (42.3643, -71.005203)}, 174),
        (3989, {'loc': (42.3643, -71.005203)}, 174),
        (27671, {'loc': (38.9445, -77.455803)}, 174),
        (34665, {'loc': (38.9057, -77.0319)}, 11179)]
    
    oregon_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
        (1742996, {'loc': (41.9786, -87.9048)}, 29791),
        (1931839, {'loc': (41.9786, -87.9048)}, 6939),
        (1735207, {'loc': (47.449001, -122.308998)}, 6939),
        (1815940, {'loc': (47.60621, -122.33207)}, 27008),
        (42386, {'loc': (44.0915, -121.4073)}, 27008),
        (3658067, {'loc': (44.0915, -121.4073)}, 11080),
        (16523900, {'loc': (44.0915, -121.4073)}, 11080),
        (3658066, {'loc': (45.8486, -119.2848)}, 11080)]
    
    san_jose_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
        (1742996, {'loc': (41.9786, -87.9048)}, 29791),
        (503967, {'loc': (37.751, -97.822)}, 11537),
        (2744401, {'loc': (41.87864, -87.64033)}, 49544),
        (10035, {'loc': (37.35411, -121.95524)}, 49544)]
    
    columbus_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
        (1742996, {'loc': (41.9786, -87.9048)}, 29791),
        (1931839, {'loc': (41.9786, -87.9048)}, 6939),
        (4377086, {'loc': (39.998001, -82.891899)}, 6939),
        (826291, {'loc': (39.998001, -82.891899)}, 394828),
        (826296, {'loc': (39.9914, -83.0034)}, 394828),
        (20455701, {'loc': (40.1873, -82.9899)}, 394828)]
    
    dublin_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
        (15232, {'loc': (52.308601, 4.76389)}, 30282),
        (5377185, {'loc': (52.2973, 4.7946)}, 29791),
        (770718, {'loc': (52.308601, 4.76389)}, 6939),
        (4041627, {'loc': (52.2973, 4.7946)}, 5466),
        (2115362, {'loc': (53.3379, -6.2591)}, 5466),
        (310391, {'loc': (53.3472, -6.2439)}, 5466)]
    #shapefile_df = gpd.read_file("../datasets/world.geojson")
    #print(shapefile_df.crs)
    #exit(0)

    get_carbon_regions(quebec_boston, shapefile_df)
    get_carbon_regions(san_jose_boston, shapefile_df)
    get_carbon_regions(oregon_boston, shapefile_df)
   
    #df.to_csv("US_nodes.geo.csv", index = False)   
    
    

if __name__ == "__main__":
    #main()
    #distance_to_shape_test()
    import unittest

    class TestAddZones(unittest.TestCase):

        def test1(self):
            dublin_boston = [(10758, {'loc': (42.35843, -71.05977)}, 14742),
                             (15232, {'loc': (52.308601, 4.76389)}, 30282),
                             (5377185, {'loc': (52.2973, 4.7946)}, 29791),
                             (770718, {'loc': (52.308601, 4.76389)}, 6939),
                             (4041627, {'loc': (52.2973, 4.7946)}, 5466),
                             (2115362, {'loc': (53.3379, -6.2591)}, 5466),
                             (310391, {'loc': (53.3472, -6.2439)}, 5466)]
            
            node = dublin_boston[0]
            self.assertTrue('US-NE-ISNE' == closest_region(shapefile_df, Point(node[1]["loc"][1],  node[1]["loc"][0]) )  )

            node = dublin_boston[-1]
            self.assertTrue('IE' == closest_region(shapefile_df, Point(node[1]["loc"][1],  node[1]["loc"][0]) )  )

            #node = dublin_boston[-1]
            p =  Point(-10.348705338900954, 52.60734160186341) # Point in the ocean just outside Ireland
            self.assertTrue('IE' == closest_region(shapefile_df, p )  )

            p =  Point(-17.028140670757793, -17.4854312081439)
            region = closest_region(shapefile_df, p ) 
            print(region)
            self.assertTrue(region is None)

        def test_proj(self):
            p = Point(42.35843, -71.05977)
            p_meters = change_projection_to_meters(p)
            print(p)
            print(p_meters)
            p_coord = change_projection_to_coordinates(p_meters)
            print(p_coord)

            self.assertAlmostEqual(p.x, p_coord.x)
            self.assertAlmostEqual(p.y, p_coord.y)

    unittest.main()







