import pandas as pd
import pprint as pp
import os

#print("Power MODELS!!!")


# This function returns the number of times a carbon intensity region appears on a route
# use_case can be "router" or "amplifier"
def region_counts(route, use_case = "router"):
    region_counts_ = {}
    for n in route:
        region = n["region"]
        # If we have an amplifier that is geolocated in a body of water (because we go through a right of way that represents a tunnel in the black sea, for example), we
        # ignore the amplfiers in the specific stretch of the route.
        if use_case == "amplifier" and region is None:
            continue
            #del region_counts_[None]
        count = region_counts_.get(region, 0)
        region_counts_[region] = count + 1
   
    

    # pp.pprint(region_counts_)
    return region_counts_

# ***********************************************
#
# Our model
#
# ***********************************************

def get_ci_year(region, year=2024):
    #filename = f"../datasets/electricity_maps_2021-2024/{region}/{region}_{year}_hourly.csv"
    currdir = os.path.dirname(__file__)

    dataset_directory = os.path.join(currdir, "../../","datasets/")
    
    #filename =  f"../datasets/carbon_intensities_clean/regions/{region}.csv"
    filename = f"{dataset_directory}carbon_intensities_clean/regions/{region}.csv"
    # Carbon intensity gCO₂eq/kWh (direct)
    try:
        df = pd.read_csv(filename)[["Datetime (UTC)",  "Carbon intensity gCO₂eq/kWh (Life cycle)"]]
    except FileNotFoundError as fnfe:
        print(f"Carbon emissions file not found for region: {region}, {filename}")
        raise fnfe
    df = df.rename({"Carbon intensity gCO₂eq/kWh (Life cycle)": "carbon_intensity_avg", "Datetime (UTC)": "datetime"}, axis = 1)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    intensities = df[df["datetime"].dt.year == year].set_index("datetime", drop=True)
    return intensities

# Yubo uses 5 W per core
# def server_energy(cores = 1, hours = 1, power_per_core_watts = 5):
#     return power_per_core_watts*cores*hours / 1000 # Number in kWh

def get_server_energy(hours = 1, power_watts = 5):
    return power_watts*hours / 1000 # Number in kWh

#def server_emissions(region,year =2022, cores=1, hours=1, power_per_core_watts =5):
def get_server_emissions(region, year =2022, hours=1, power_watts =5, get_ci_year=get_ci_year):
    #print(f"Region: {region}")
    #filename = f"../datasets/electricity-maps-2020-2022-all-regions-marginal-average/{region}.csv"
    #filename = f"../datasets/carbon_intensities_clean/regions/{region}.csv"
    # filename = f"../datasets/electricity_maps_2021-2024/{region}_{year}_hourly.csv"
    # df = pd.read_csv(filename)[["datetime", "carbon_intensity_avg"]]
    # #print(df)
    # df["datetime"] = pd.to_datetime(df["datetime"])
    # df = df.sort_values("datetime")
    # intensities = df[df["datetime"].dt.year == year].set_index("datetime", drop=True)
    
    intensities = get_ci_year(region, year=year)
    
    #print("Intensities:")
    #print(intensities)
    if intensities.empty:
        print(f"Region {region} has no ci data for year {year}")
        return None
    #df = df[df["datetime"].dt.year == year].sort_values("datetime")
    energy = get_server_energy( hours=hours, power_watts = power_watts)
    #print(f"Energy: {energy}")
    #print(f"Carbon Intensities:")
    #print(intensities)
    emissions = intensities * energy
    return emissions["carbon_intensity_avg"]

# energy_intensity is given in J/Gbit
# The result of this function is given in kWh
def network_hop_energy(stream_data_size = 7, energy_intensity =10):
    return ((stream_data_size * 8) * energy_intensity) / 3600000

# energy_intensity is given in J/Gbit
# stream_data_size is given in GB
def get_network_emissions(route, stream_data_size = 7, energy_intensity =10, year=2024, get_ci_year = get_ci_year, use_case = None):
    #print(f"YEAR: {year}")
    if use_case is None:
        raise TypeError("'use_case' can be None!!")
    # print("Hola")
    per_hop_energy_usage =  network_hop_energy(stream_data_size = stream_data_size, energy_intensity = energy_intensity)#stream_data_size * (8 * energy_intensity) / 3600000  # Need this figure in kWh
    # print("Chao")
    counts = region_counts(route, use_case = use_case)
    #pp.pprint(counts)
    carbon_intensity_list = []
    regions = []

    
    for i, region in enumerate(counts.keys()):
        #print(region)
        # If the location of this device has been geolocated to a position in a large body of water (an ocean or the black sea), we ignore them.
        
        regions.append(region)
        #filename = f"../datasets/electricity-maps-2020-2022-all-regions-marginal-average/{region}.csv"
        #filename = f"../datasets/carbon_intensities_clean/regions/{region}.csv"
        #filename = f"../datasets/electricity_maps_2021-2024/{region}_{year}_hourly.csv"
        count = counts[region]
        df = get_ci_year(region, year=year)
        # df = pd.read_csv(filename)[["datetime", "carbon_intensity_avg"]]
        # df["datetime"] = pd.to_datetime(df["datetime"])
        # df = df[df["datetime"].dt.year == year].sort_values("datetime")#.set_index("datetime", drop=True)
        #df = df.sort_values("datetime")
        if i == 0:
            index_ = df.index#["datetime"]
        #df = df.set_index("datetime", drop=True)

        df["carbon_intensity_avg"] = df["carbon_intensity_avg"] * count
        carbon_intensity_list.append(df["carbon_intensity_avg"])

    if len(carbon_intensity_list) ==0:
        return 0, None

    carbon_intensities = pd.concat(carbon_intensity_list, axis=1)
    #print(carbon_intensities)
    carbon_intensities.index = index_
    carbon_intensities.columns = regions
    #print(emissions)
    emissions = (carbon_intensities * per_hop_energy_usage).sum(axis=1) # This gives us the carbon emissions in gCO2. # (gCO2/kWh) * kWh
    return emissions, counts  



# ***********************************************
#
# Caribou's models
#
# ***********************************************

# Return 3.5 kWh
def get_server_energy_caribou_max():
    return 3.5e-3

# Return 0.75 kWh
def get_server_energy_caribou_min():
    return 7.5e-4 


# def get_server_emissions_caribou(region, year= 2022, value = "min"):
#     if value == "min":
#         server_energy_func = get_server_energy_caribou_min
#     elif value == "max":
#         server_energy_func = get_server_energy_caribou_max
#     else:
#         raise Exception("Argument 'value' should be either 'min' or 'max'")
    
#     filename = f"../datasets/electricity-maps-2020-2022-all-regions-marginal-average/{region}.csv"
#     df = pd.read_csv(filename)[["datetime", "carbon_intensity_avg"]]
#     df["datetime"] = pd.to_datetime(df["datetime"])
#     df = df.sort_values("datetime")
#     df = df[df["datetime"].dt.year == year].set_index("datetime", drop=True)
    
#     emissions = df * server_energy_func()
#     return emissions["carbon_intensity_avg"]

# # Caribou assigns an average  energy intensity to the whole network, regardless of number of hops or length. They use two values: 0.001 and 0.005
# # kWh/GB as optimistic and pessimistic values to analyze. We will make it so that route will interpolate betwwen these two values based on route length.
# def get_network_energy_caribou(route, stream_data_size):
#     MAX_ROUTE_LENGTH = 14
#     MIN_ROUTE_LENGTH = 3
#     number_hops = len(route)

#     # INTERPOLATION
#     SLOPE = (0.005-0.001) / (MAX_ROUTE_LENGTH - MIN_ROUTE_LENGTH)

#     energy_intensity_route = number_hops * SLOPE #+ 0.001
#     energy = energy_intensity_route * stream_data_size
#     return energy

# # Caribou assigns an average  energy intensity to the whole network, regardless of number of hops or length. They use two values: 0.001 and 0.005
# # kWh/GB as optimistic and pessimistic values to analyze. We will make it so that route will interpolate betwwen these two values based on route length.
# def get_network_emissions_caribou(route, stream_data_size, year=2022):
#     # route_energy is the energy intensity FOR THE WHOLE ROUTE
#     route_energy = get_network_energy_caribou(route, stream_data_size)
#     # per_hop_energy_usage is the energy used by each node in the route
#     per_hop_energy_usage = route_energy/len(route)

#     counts = region_counts(route)
#     pp.pprint(counts)
#     carbon_intensity_list = []
#     regions = []
#     for i, region in enumerate(counts.keys()):
#         print(region)
#         regions.append(region)
#         filename = f"../datasets/electricity-maps-2020-2022-all-regions-marginal-average/{region}.csv"
#         count = counts[region]
#         df = pd.read_csv(filename)[["datetime", "carbon_intensity_avg"]]
#         df["datetime"] = pd.to_datetime(df["datetime"])
#         df = df[df["datetime"].dt.year == year].sort_values("datetime")#.set_index("datetime", drop=True)
#         #df = df.sort_values("datetime")
#         if i == 0:
#             index_ = df["datetime"]
#         df["carbon_intensity_avg"] = df["carbon_intensity_avg"] * count
#         carbon_intensity_list.append(df["carbon_intensity_avg"])
#     carbon_intensities = pd.concat(carbon_intensity_list, axis=1)
#     carbon_intensities.index = index_
#     carbon_intensities.columns = regions
#     #print(emissions)
#     emissions = (carbon_intensities * per_hop_energy_usage).sum(axis=1) # This gives us the carbon emissions in gCO2. # (gCO2/kWh) * (J/GB) * (kWh/J) * (Gb)
#     return emissions, counts



###########################

# ***********************************************
#
# Baliga, et al's models (Energy Consumption in Optical IP Networks)
#
# ***********************************************

# def get_network_energy_baliga(route, stream_data_size):
#     #MAX_ROUTE_LENGTH = 14
#     #MIN_ROUTE_LENGTH = 3
#     number_hops = len(route)
#     energy_intensity_baliga = 5e-07 # kWh/GB

#     energy = number_hops* energy_intensity_baliga*stream_data_size
#     return energy



if __name__ == "__main__":
    import unittest
    from unittest.mock import Mock, create_autospec
    import random
    from datetime import datetime, timedelta, tzinfo
    from dateutil import tz
    import geopandas as gpd

    class TestServerEmissions(unittest.TestCase):

        def test_network_energy(self):
            #self.assertEqual('foo'.upper(), 'FOO')
            self.assertTrue(abs(network_hop_energy(stream_data_size =7,  energy_intensity =10) - 2.7777778e-6 ) < 1e-2 )
            self.assertTrue(abs(network_hop_energy(stream_data_size =1,  energy_intensity =1) - 8/3600000 ) < 1e-2 )
        def test_server_energy(self):
            #for 
            for i in range(100):
                hours = random.uniform(0, i*40)
                power_watts = random.uniform(0, i*40)
                self.assertTrue(abs(get_server_energy(hours = hours, power_watts= power_watts) - hours*power_watts/1000) < 1e-2)

        def test_region_counts(self):
            route_1 = [{'id': 10758,
                     'loc': [42.35843, -71.05977],
                     'AS': 14742,
                     'region': 'US-NE-ISNE'},
                    {'id': 6507,
                     'loc': [42.35843, -71.05977],
                     'AS': 14742,
                     'region': 'US-NE-ISNE'},
                    {'id': 22548,
                     'loc': [42.35843, -71.05977],
                     'AS': 1299,
                     'region': 'US-NE-ISNE'},
                    {'id': 8193,
                     'loc': [42.35843, -71.05977],
                     'AS': 1299,
                     'region': 'US-NE-ISNE'},
                    {'id': None,
                     'AS': None,
                     'loc': [42.32991, -71.06998],
                     'region': 'US-NE-ISNE'},
                    {'id': None, 'AS': None, 'loc': [41.7695, -72.6915], 'region': 'US-NE-ISNE'},
                    {'id': None, 'AS': None, 'loc': [40.8375, -73.2905], 'region': 'US-NY-NYIS'},
                    {'id': None, 'AS': None, 'loc': [40.5405, -74.4285], 'region': 'US-MIDA-PJM'},
                    {'id': None, 'AS': None, 'loc': [39.7115, -75.1015], 'region': 'US-MIDA-PJM'},
                    {'id': None,
                     'AS': None,
                     'loc': [38.89956, -77.00912],
                     'region': 'US-MIDA-PJM'},
                    {'id': None,
                     'AS': None,
                     'loc': [38.30351, -77.46079],
                     'region': 'US-MIDA-PJM'},
                    {'id': None,
                     'AS': None,
                     'loc': [38.02883, -78.47707],
                     'region': 'US-MIDA-PJM'},
                    {'id': None,
                     'AS': None,
                     'loc': [36.58623, -79.39534],
                     'region': 'US-MIDA-PJM'},
                    {'id': None,
                     'AS': None,
                     'loc': [36.07004, -79.80108],
                     'region': 'US-CAR-DUK'},
                    {'id': None, 'AS': None, 'loc': [35.3297, -80.766], 'region': 'US-CAR-DUK'},
                    {'id': 8191, 'loc': [34.0389, -84.3826], 'AS': 7029, 'region': 'US-SE-SOCO'},
                    {'id': 728891,
                     'loc': [34.0389, -84.3826],
                     'AS': 7029,
                     'region': 'US-SE-SOCO'},
                    {'id': 27940, 'loc': [34.0389, -84.3826], 'AS': 7029, 'region': 'US-SE-SOCO'},
                    {'id': 726413,
                     'loc': [34.0389, -84.3826],
                     'AS': 7029,
                     'region': 'US-SE-SOCO'},
                    {'id': None,
                     'AS': None,
                     'loc': [33.82974, -84.39928],
                     'region': 'US-SE-SOCO'},
                    {'id': None, 'AS': None, 'loc': [33.4695, -86.6695], 'region': 'US-SE-SOCO'},
                    {'id': None, 'AS': None, 'loc': [35.2031, -89.8086], 'region': 'US-TEN-TVA'},
                    {'id': None,
                     'AS': None,
                     'loc': [34.7375, -92.1185],
                     'region': 'US-MIDW-MISO'},
                    {'id': None,
                     'AS': None,
                     'loc': [35.4315, -97.4315],
                     'region': 'US-CENT-SWPP'},
                    {'id': None,
                     'AS': None,
                     'loc': [35.5415, -98.7125],
                     'region': 'US-CENT-SWPP'},
                    {'id': 20607841,
                     'loc': [35.7481, -117.3808],
                     'AS': 7029,
                     'region': 'US-CAL-CISO'}]
       
            counts = region_counts(route_1)

            counts_truth = {"US-NE-ISNE" : 6, 
                            "US-NY-NYIS" : 1,
                            "US-MIDA-PJM": 6,
                            "US-CAR-DUK" : 2,
                            "US-SE-SOCO" : 6,
                            "US-TEN-TVA" : 1,
                            "US-MIDW-MISO" : 1,
                            "US-CENT-SWPP" : 2,
                            "US-CAL-CISO" : 1
                            }
            # Test they have the same keys
            # print(counts.keys())
            # print(counts_truth.keys())

            self.assertTrue( set(counts.keys()) == set(counts_truth.keys()) )

            for key in counts.keys():
                self.assertTrue(counts_truth[key] == counts[key])

           
           

        # Testing that it doesn't matter which order the regions appear in the route
        def test_region_counts_order(self):
            route_1 = [{'id': 10758,
                     'loc': [42.35843, -71.05977],
                     'AS': 14742,
                     'region': 'US-NE-ISNE'},
                    {'id': 6507,
                     'loc': [42.35843, -71.05977],
                     'AS': 14742,
                     'region': 'US-MIDW-MISO'},
                    {'id': 22548,
                     'loc': [42.35843, -71.05977],
                     'AS': 1299,
                     'region': 'US-NE-ISNE'},
                     {'id': None,
                     'AS': None,
                     'loc': [33.82974, -84.39928],
                     'region': 'US-SE-SOCO'}]
            
            counts = region_counts(route_1)

            counts_truth = {'US-NE-ISNE' : 2, 
                            'US-SE-SOCO' : 1,
                            'US-MIDW-MISO' : 1}
            self.assertTrue( set(counts.keys()) == set(counts_truth.keys()) )

            for key in counts.keys():
                self.assertTrue(counts_truth[key] == counts[key])


        def test_carbon_emissions(self):
            time_delta = timedelta(hours=1)

            year = 2024
            start_ = datetime(year=year, month=1, day=1, tzinfo=tz.UTC)
            end_= datetime(year=year+1, month=1, day=1, tzinfo=tz.UTC)
            datetime_list = []
            datetime_tmp = start_#.copy()

            

            while datetime_tmp <end_:
                datetime_list.append(datetime_tmp)
                datetime_tmp = datetime_tmp + time_delta
            number_hours = len(datetime_list)
            # pp.pprint(datetime_list[0:30])
            # pp.pprint(datetime_list[-1])
            MAGICK_VALUE = 12
            dataframe = pd.DataFrame([MAGICK_VALUE]*number_hours, index = datetime_list, columns=["carbon_intensity_avg"])
            dataframe.index.name = "datetime"
            get_ci_year_mock = create_autospec(get_ci_year, return_value = dataframe )
            #print(get_ci_year_mock("IE"))

            #print(get_ci_year("IE"))

            emissions = get_server_emissions("IE", year =2022, hours=1, power_watts =1, get_ci_year=get_ci_year_mock)

            self.assertTrue(emissions.shape[0] <= number_hours )
            self.assertTrue(type(emissions) == pd.Series )
    

        def test_carbon_emissions_real(self):
            # time_delta = timedelta(hours=1)

            
            # start_ = datetime(year=year, month=1, day=1, tzinfo=tz.UTC)
            # end_= datetime(year=year+1, month=1, day=1, tzinfo=tz.UTC)
            # datetime_list = []
            # datetime_tmp = start_#.copy()

            

            # while datetime_tmp <end_:
            #     datetime_list.append(datetime_tmp)
            #     datetime_tmp = datetime_tmp + time_delta
            # number_hours = len(datetime_list)
            # pp.pprint(datetime_list[0:30])
            # pp.pprint(datetime_list[-1])
            # MAGICK_VALUE = 12
            # dataframe = pd.DataFrame([MAGICK_VALUE]*number_hours, index = datetime_list, columns=["carbon_intensity_avg"])
            # dataframe.index.name = "datetime"
            # get_ci_year_mock = create_autospec(get_ci_year, return_value = dataframe )
            #print(get_ci_year_mock("IE"))

            #print(get_ci_year("IE"))

            currdir = os.path.dirname(__file__)
            import calendar

            def get_hours_in_year(year):
                if calendar.isleap(year):
                    return 366 * 24
                else:
                    return 365 * 24

            #print(f"Current dir: {currdir}")
            dataset_directory = os.path.join(currdir, "../../","datasets")
            shapefile_df = gpd.read_file(f"{dataset_directory}/world.geojson")#.to_crs('EPSG:3857')
            regions = list(shapefile_df["zoneName"].unique())
            regions.sort()
            for region in shapefile_df["zoneName"].unique():
                # Andorra (AD) and Lichenstein (LI need to be fixed)
                # ES-CE doesn't have data for 2021
                # if region in set(["US-HI-OA", "AD", "EH", "HM", "LI", "PT-MA", "SJ", "ST", "TF", "TG", "UA", "UA-CR"]):
                if region in set(["US-HI-OA",  "EH", "HM", "PT-MA", "SJ", "ST", "TF", "TG", "UA", "UA-CR"]):
                    continue
                for year in [2021, 2022, 2023, 2024]:
                    if region == "ES-CE" and year ==2021:
                        continue
                    emissions = get_server_emissions(region, year =year, hours=1, power_watts =1)
                    if emissions is None:
                        print(f"NONE!  {region} {year}")
                    self.assertTrue(emissions.shape[0] <= get_hours_in_year(year) )
                    self.assertTrue(type(emissions) == pd.Series )

    unittest.main()
    

    



