import sqlite3
from functools import cache
from datetime import datetime
import time
import os
import re

currdir = os.path.dirname(__file__)
dataset_directory = os.path.join(currdir, "../../","data")

@cache
def get_carbon_intensities(target_datetime, mean= False):
    
    if mean:
        year = int(target_datetime)
        with sqlite3.connect(f"../../data/carbon_intensities/carbon_intensities.db") as conn:

            ### Get table column names
            columns_query =  "SELECT * FROM carbon_intensities LIMIT 1"
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(columns_query)#.fetchone()
            row = cursor.fetchone()
            columns_data = dict(row)
            # columns_data = {'AD':0}
            # columns = [f"SUM( CAST('{x}' AS REAL))" for x in columns_data.keys() if  x != 'datetime']
            columns = [f"AVG( \"{x}\" )" for x in columns_data.keys() if  x != 'datetime']
            # columns = [f"AVG( COALESCE('{x}', 0))" for x in columns_data.keys() if  x != 'datetime'] # COALESCE(column_name, 0)
            # columns = [f"{x}" for x in columns_data.keys()]
            columns_str = ', '.join(columns)

            # columns_str = 'AD, AE'
            
            
            # query = f"SELECT * FROM carbon_intensities WHERE datetime = \'{target_datetime_clean}\'"
            query = f"SELECT {columns_str} FROM carbon_intensities WHERE strftime('%Y', datetime) = '{year}';"
            # query = f"SELECT typeof(AD) FROM carbon_intensities LIMIT 1;"
            # print(query)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)#.fetchone()
            row = cursor.fetchone()
            data = dict(row)
            new_dict = {}
            for column, value in data.items():
                match = re.search(r'AVG\(\s*"([^"]+)"\s*\)', column)
                if match:
                    # print(match.group(1)) 
                    new_dict[match.group(1)] = value

            return new_dict

    else:

        if type(target_datetime) is str:
            target_datetime_clean = datetime.fromisoformat(target_datetime)
        elif type(target_datetime) is datetime:
            target_datetime_clean = target_datetime
        elif type(target_datetime) is int:
            target_datetime_clean = datetime.fromtimestamp(target_datetime)
        #    print(target_datetime_clean)


        with sqlite3.connect(f"{dataset_directory}/carbon_intensities/carbon_intensities.db") as conn:

            # query = 'SELECT * FROM carbon_intensities LIMIT 1 ;'
            query = f"SELECT * FROM carbon_intensities WHERE datetime = \'{target_datetime_clean}\'"
            # print(query)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)#.fetchone()
            row = cursor.fetchone()

            # print(row)
            # print(row.keys())
            data = dict(row)

            return data
    

def get_carbon_intensity(region, target_datetime, mean=False):
    cis = get_carbon_intensities(target_datetime, mean=mean)

    return cis[region]



if __name__ == "__main__":

    dt = 1675382400#'2022-11-05 00:00:00'

    start_time = time.perf_counter()
    print(get_carbon_intensity('US-CAL-CISO', dt))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")


    start_time = time.perf_counter()
    print(get_carbon_intensity('US-CAL-CISO', dt))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")


    start_time = time.perf_counter()
    print(get_carbon_intensity('BR-NE', dt))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")


    start_time = time.perf_counter()
    print(get_carbon_intensity('BR-NE', '2022-12-05 00:00:00'))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")

