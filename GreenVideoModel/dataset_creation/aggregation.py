import os
import pandas as pd
import glob
from GreenVideoModel import get_carbon_intensity, get_carbon_intensities

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# print(_REPO_ROOT)
_DATACENTER_INFO_USA_PATH = os.path.join(_REPO_ROOT, "data", "aggregated_dcs", "datacenter_info_USA.csv")
_DATACENTER_INFO_EU_PATH = os.path.join(_REPO_ROOT, "data", "aggregated_dcs", "datacenter_info_EU.csv")
# print(_DATACENTER_INFO_USA_PATH)

def get_dc_ids_us(data_df):
    datacenter_info = pd.read_csv(_DATACENTER_INFO_USA_PATH)[['b.country', 'b.state', 'b.city', 'a.ecor', 'region']]
    
    merged_df = data_df.merge(datacenter_info, on = ['b.country', 'b.state', 'b.city'])
    
    return merged_df
def get_dc_ids_eu(data_df):
    datacenter_info = pd.read_csv(_DATACENTER_INFO_EU_PATH)[['b.country', 'b.state', 'b.city', 'a.ecor', 'region']]
    
    merged_df = data_df.merge(datacenter_info, on = ['b.country', 'b.state', 'b.city'])
    
    return merged_df

def aggregate_na_dcs(data, target_datetime):
    data_grouped_by_city_na = data[(data['b.country'] == "United States") | (data['b.country'] == "Canada")].groupby(['b.country', 'b.city', 'b.state']).agg({'b.latitude': 'mean', 'b.longitude':'mean', 
                                                                 'bit_capacity':'sum', 'bit_load':'sum',
                                                                 'flit_capacity':'sum', 'flit_load':'sum', 'SUM(a.numGhosts)': 'sum'} ).sort_values(['b.state', 'b.city']).reset_index()
    data_grouped_by_city_na = get_dc_ids_us(data_grouped_by_city_na)
    data_grouped_by_city_na = data_grouped_by_city_na[ (~data_grouped_by_city_na['b.state'].isin(['AK', 'HI'])) & (data_grouped_by_city_na['flit_capacity'] != 0 )  ].reset_index(drop=True)
    # print(data_grouped_by_city_us[data_grouped_by_city_us['region'] == None])
    # data_grouped_by_city_us = get_carbon_intensity(data_grouped_by_city_us, datetime(year = 2022, month = 11, day = 11, hour = 5))
    data_grouped_by_city_na['carbon_intensity'] = data_grouped_by_city_na.apply(lambda x: get_carbon_intensity(x['region'], target_datetime), axis=1)

    data_grouped_by_city_na['bandwidth_to_flit_frac'] = data_grouped_by_city_na['bit_load']/data_grouped_by_city_na['flit_load']
    return data_grouped_by_city_na

def aggregate_us_dcs(data, target_datetime):
    data_grouped_by_city_us = data[data['b.country'] == "United States"].groupby(['b.country', 'b.city', 'b.state']).agg({'b.latitude': 'mean', 'b.longitude':'mean', 
                                                                 'bit_capacity':'sum', 'bit_load':'sum',
                                                                 'flit_capacity':'sum', 'flit_load':'sum', 'SUM(a.numGhosts)': 'sum'} ).sort_values(['b.state', 'b.city']).reset_index()
    data_grouped_by_city_us = get_dc_ids_us(data_grouped_by_city_us)
    data_grouped_by_city_us = data_grouped_by_city_us[ (~data_grouped_by_city_us['b.state'].isin(['AK', 'HI'])) & (data_grouped_by_city_us['flit_capacity'] != 0 )  ].reset_index(drop=True)
    # print(data_grouped_by_city_us[data_grouped_by_city_us['region'] == None])
    # data_grouped_by_city_us = get_carbon_intensity(data_grouped_by_city_us, datetime(year = 2022, month = 11, day = 11, hour = 5))
    data_grouped_by_city_us['carbon_intensity'] = data_grouped_by_city_us.apply(lambda x: get_carbon_intensity(x['region'], target_datetime), axis=1)

    data_grouped_by_city_us['bandwidth_to_flit_frac'] = data_grouped_by_city_us['bit_load']/data_grouped_by_city_us['flit_load']
    return data_grouped_by_city_us


def aggregate_eu_dcs(data, target_datetime):

    # print(data[data['b.continent'] == "Europe"])
    data_grouped_by_city_eu = data[data['b.continent'] == "Europe"].groupby(['b.country', 'b.city', 'b.state'], dropna=False).agg({'b.latitude': 'mean', 'b.longitude':'mean', 
                                                                 'bit_capacity':'sum', 'bit_load':'sum',
                                                                 'flit_capacity':'sum', 'flit_load':'sum', 'SUM(a.numGhosts)': 'sum'} ).sort_values(['b.state', 'b.city']).reset_index()
    
    # data_grouped_by_city_eu = data[data['b.continent'] == "Europe"].groupby(['b.country', 'b.city']).agg({'b.latitude': 'mean', 'b.longitude':'mean', 
    #                                                              'bit_capacity':'sum', 'bit_load':'sum',
    #                                                              'flit_capacity':'sum', 'flit_load':'sum', 'SUM(a.numGhosts)': 'sum'}, dropna=False ).sort_values([ 'b.city']).reset_index()
    # print("Aggregated shape")
    # print(data_grouped_by_city_eu.shape)
    # print("Inside aggregation function for EU datacenters")
    # print(data_grouped_by_city_eu)
    data_grouped_by_city_eu = get_dc_ids_eu(data_grouped_by_city_eu)
    # print("MErged shape")
    # print(data_grouped_by_city_eu.shape)
    data_grouped_by_city_eu = data_grouped_by_city_eu[ (data_grouped_by_city_eu['flit_capacity'] != 0 )  ].reset_index(drop=True)
    # print(data_grouped_by_city_eu.shape)
    # print(data_grouped_by_city_eu)
    # print(data_grouped_by_city_eu[data_grouped_by_city_eu['region'] == None])
    # data_grouped_by_city_eu = get_carbon_intensity(data_grouped_by_city_eu, datetime(year = 2022, month = 11, day = 11, hour = 5))
    data_grouped_by_city_eu['carbon_intensity'] = data_grouped_by_city_eu.apply(lambda x: get_carbon_intensity(x['region'], target_datetime), axis=1)
    # print("CArbon intensity shape")
    # print(data_grouped_by_city_eu.shape)
    data_grouped_by_city_eu['bandwidth_to_flit_frac'] = data_grouped_by_city_eu['bit_load']/data_grouped_by_city_eu['flit_load']
    return data_grouped_by_city_eu

def aggregate_asia_dcs(data, target_datetime):
    pass

