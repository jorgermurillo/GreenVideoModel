from GreenVideoModel.CAIDA_route_creation.power_and_carbon_models.route_curation import add_amplifiers_and_carbon_regions
import os
import json
import pprint as pp
import time
import argparse

def get_carbon_regions_EU():
    currdir = os.path.dirname(__file__)

    dataset_directory = os.path.join(currdir, "../","datasets/")

    with open(f"{dataset_directory}routes/EU_Akamai_aug.json","r") as f:
        EU_routes = json.load(f)
    

    #pp.pprint(EU_routes)

    EU_routes_carbon = add_amplifiers_and_carbon_regions(EU_routes)
    with open(f"{dataset_directory}routes/EU_Akamai_carbon_regions.json","w") as f:
        json.dump(EU_routes_carbon, f)


def get_carbon_regions_NA():
    # Get datasets directory
    currdir = os.path.dirname(__file__)
    dataset_directory = os.path.join(currdir, "../","datasets/")

    # Add carbon regions to NA Akamai routes
    with open(f"{dataset_directory}routes/NA_akamai_aug.json","r") as f:
        NA_akamai_routes = json.load(f)
    NA_akamai_routes_carbon = add_amplifiers_and_carbon_regions(NA_akamai_routes)
    # Save NA Akamai carbon regions
    with open(f"{dataset_directory}routes/NA_akamai_carbon_regions.json","w") as f:
        json.dump(NA_akamai_routes_carbon, f)
   

   # Add carbon regions to NA AWS routes
    with open(f"{dataset_directory}routes/NA_aws_aug.json","r") as f:
        NA_aws_routes = json.load(f)
    NA_aws_routes_carbon = add_amplifiers_and_carbon_regions(NA_aws_routes)
    # Save NA AWS carbon region
    with open(f"{dataset_directory}routes/NA_aws_carbon_regions.json","w") as f:
        json.dump(NA_aws_routes_carbon, f)
   

def get_carbon_regions_test():
    # Get datasets directory
    currdir = os.path.dirname(__file__)
    dataset_directory = os.path.join(currdir, "../","datasets/")

    # Add carbon regions to NA Akamai routes
    with open(f"{dataset_directory}routes/tests/submarine_routes.json","r") as f:
        test_routes = json.load(f)
    test_routes_carbon = add_amplifiers_and_carbon_regions(test_routes)
    # Save NA Akamai carbon regions
    with open(f"{dataset_directory}routes/tests/submarine_routes_carbon.json","w") as f:
        json.dump(test_routes_carbon, f)
   
def get_carbon_regions_EU():
    # Get datasets directory
    currdir = os.path.dirname(__file__)
    dataset_directory = os.path.join(currdir, "../","datasets/")

    # Add carbon regions to EU Akamai routes
    with open(f"{dataset_directory}routes/EU_akamai_aug.json","r") as f:
        EU_akamai_routes = json.load(f)
    EU_akamai_routes_carbon = add_amplifiers_and_carbon_regions(EU_akamai_routes)
    # Save EU Akamai carbon regions
    with open(f"{dataset_directory}routes/EU_akamai_carbon_regions.json","w") as f:
        json.dump(EU_akamai_routes_carbon, f)
   

   # Add carbon regions to EU AWS routes
    with open(f"{dataset_directory}routes/EU_aws_aug.json","r") as f:
        EU_aws_routes = json.load(f)
    EU_aws_routes_carbon = add_amplifiers_and_carbon_regions(EU_aws_routes)
    # Save EU AWS carbon region
    with open(f"{dataset_directory}routes/EU_aws_carbon_regions.json","w") as f:
        json.dump(EU_aws_routes_carbon, f)

def get_carbon_regions(input_file, output_file):
    # Get datasets directory
    currdir = os.path.dirname(__file__)
    # dataset_directory = os.path.join(currdir, "../","datasets/")

    # Add carbon regions to EU Akamai routes
    # with open(f"{dataset_directory}routes/EU_akamai_aug.json","r") as f:
    with open(input_file,"r") as f:
        input_routes = json.load(f)
    carbon_routes = add_amplifiers_and_carbon_regions(input_routes)
    # Save EU Akamai carbon regions
    # with open(f"{dataset_directory}routes/EU_akamai_carbon_regions.json","w") as f:
    with open(output_file,"w") as f:
        json.dump(carbon_routes, f)
   

#    # Add carbon regions to EU AWS routes
#     with open(f"{dataset_directory}routes/EU_aws_aug.json","r") as f:
#         EU_aws_routes = json.load(f)
#     EU_aws_routes_carbon = add_amplifiers_and_carbon_regions(EU_aws_routes)
#     # Save EU AWS carbon region
#     with open(f"{dataset_directory}routes/EU_aws_carbon_regions.json","w") as f:
#         json.dump(EU_aws_routes_carbon, f)

def parse_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--region', help='dataset.')
    parser.add_argument('--input_file', help='File with routes.')
    parser.add_argument("--output_file", help='File with routes containing carbon regions')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    start = time.time()
    # get_carbon_regions_NA()
    # get_carbon_regions_EU()
    # if args.region == "NA":
    #     get_carbon_regions_NA()
    # elif args.region == "EU":
    #     get_carbon_regions_EU()
    # elif args.region == "test":
    #     get_carbon_regions_test()

    get_carbon_regions(args.input_file, args.output_file)


    end = time.time()

    print(f"Time to complete: {end - start}")