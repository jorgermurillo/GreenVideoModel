from GreenVideoModel import generate_monthly_data


if __name__ == "__main__":
    years = [2021, 2022, 2023, 2024]  # List of years to process
    # years = [2021, 2023, 2024] 
    region = "US"
    input_dir = "/nfs/obelix/raid2/jrmurillo/ECORInfo"
    for year in years:
        print(f"Processing year: {year}")
        output_dir = f"/nfs/obelix/raid2/jrmurillo/ECORInfo_NA_{year}/"
        generate_monthly_data(input_dir, output_dir, region, year=year)