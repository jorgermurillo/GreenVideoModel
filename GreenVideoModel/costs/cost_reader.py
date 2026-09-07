import sqlite3
from functools import cache
from datetime import datetime
import time
import os

currdir = os.path.dirname(__file__)
dataset_directory = os.path.join(currdir, "../../","data")

@cache
def get_costs_USA(target_datetime):
    
    if type(target_datetime) is str:
        target_datetime_clean = datetime.fromisoformat(target_datetime)
    elif type(target_datetime) is datetime:
        target_datetime_clean = target_datetime
    elif type(target_datetime) is int:
        target_datetime_clean = datetime.fromtimestamp(target_datetime)
    #    print(target_datetime_clean)


    # with sqlite3.connect(f"{dataset_directory}/carbon_intensities/carbon_intensities.db") as conn:
    with sqlite3.connect(f"{dataset_directory}/cost/costs.db") as conn:

        # query = 'SELECT * FROM carbon_intensities LIMIT 1 ;'
        query = f"SELECT * FROM cost WHERE datetime = \'{target_datetime_clean}\'"
        # print(query)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)#.fetchone()
        row = cursor.fetchone()

        # print(row)
        # print(row.keys())
        data = dict(row)

        return data
    

def get_cost_USA(region, target_datetime):
    cis = get_costs_USA(target_datetime)

    return cis[region]



if __name__ == "__main__":

    dt = 1675382400#'2022-11-05 00:00:00'

    start_time = time.perf_counter()
    print(get_cost_USA('', dt))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")


    start_time = time.perf_counter()
    print(get_cost_USA('US-CAL-CISO', dt))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")


    start_time = time.perf_counter()
    print(get_cost_USA('BR-NE', dt))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")


    start_time = time.perf_counter()
    print(get_cost_USA('BR-NE', '2022-12-05 00:00:00'))
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")

