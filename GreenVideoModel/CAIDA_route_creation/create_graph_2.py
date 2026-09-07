import pandas as pd
import networkx as nx
import time
import geopandas as gpd
from shapely import Point
from haversine import haversine
import argparse
import os


"""
Usage:

Run "create_graph.py --get-largest-connected-component-nodes" to obtain the biggest connected component of the graph.

Run "create_graph.py --load-largest-component" to get some routes between locations.

"""


#LARGEST_COMPONENTS_NODES_FILENAME = "./nodes_largest_component.csv"

def argmin(a):
    return min(range(len(a)), key=lambda x : a[x])

def argmax(a):
    return max(range(len(a)), key=lambda x : a[x])


class CAIDA_GRAPH():

    def __init__(self):
        currdir = os.path.dirname(__file__)
        print(f"Current directory: {currdir}", flush = True)
        dataset_directory = "./data/" \
        ""#os.path.join(currdir, "../../","datasets/")
        print(f"Dataset dir: {dataset_directory}")
        self.largest_component_nodes_filename = f"{currdir}/nodes_largest_component.csv"
        self.G = None
        self.node_locations = {}
        self.node_set = None
        self.ASes = None
        self.current_dir = currdir
        self.dataset_dir = dataset_directory

    def load_node_set(self, ):
        self.node_set = set()
        print("Loading node set!!", flush = True)
        with open(self.largest_component_nodes_filename, "r") as file_:
            for line in file_:
                node_id = int(line)
                self.node_set.add(node_id)
            print("Node set loaded!!", flush = True)

    def create_node_id_AS_mapping(self):
        self.ASes = {}
        with open(f"{self.dataset_dir}/CAIDA_data/midar-iff.nodes.as", "r") as file_:
            for line in file_:
                data = line.split("\t")
                node_id = int(data[1][1:])
                AS_id = int(data[2])
                self.ASes[node_id] = AS_id

    def get_nodes_from_line(self, line):
        fields = line.split(" ")
        nodes = [x[1:] for x in fields if x.startswith("N")]

        nodes_2 = []
        for i in range(len(nodes)):
            node = nodes[i]
            tmp = node.split(":")
            nodes_2.append(int(tmp[0]))

        return nodes_2

    def load_node_links(self, nodes):

        for node1 in nodes:
            for node2 in nodes:
                if node1 != node2:

                    node1_loc = self.G.nodes[node1]['loc']
                    node2_loc = self.G.nodes[node2]['loc']
                    distance = haversine(node1_loc, node2_loc)

                    self.G.add_edge(node1, node2, distance = distance)


    def add_location_to_dict(self, lat, long, node_id):
        key = (lat,long)

        list_ = self.node_locations.get(key, [])
        list_.append(node_id)
        self.node_locations[key] = list_

    def get_closest_point(self, position):
        nodes, distance_km = self.get_closest_points(position)
        return nodes[0], distance_km
    
    def get_closest_points(self, position):
        node_locations_set = list(self.node_locations.keys())
        distances = [haversine(position, p) for p in node_locations_set]

        min_distance_km_index = argmin(distances) #min( haversine(Boston_loc, p) for p in node_locations_set )
        min_distance_km = distances[min_distance_km_index]
        node_location = node_locations_set[min_distance_km_index]
        nodes = self.node_locations[node_location]

        return nodes, min_distance_km
    
    def get_largest_connected_component(self):
        connected_components = list(nx.connected_components(self.G))
        n_connected_comonents = len(connected_components)
        print(f"Number of connected components: {n_connected_comonents}", flush=True)
        print([len(c) for c in connected_components if len(c) > 1], flush=True)
        before_copy = time.time()
        largest_connected_component = max(connected_components, key=len)
        new_router_graph = self.G.subgraph(largest_connected_component).copy()
        after_copy = time.time()
        print(f"Time to create copy of graph: {after_copy - before_copy}", flush=True)
        print(f"Nodes: {len(new_router_graph.nodes)}, Edges: {len(new_router_graph.edges)}", flush=True)

        print("Writing nodes into file!", flush = True)
        # Write the ids of the nodes in the largest connected component to a file
        with open(self.largest_component_nodes_filename, "w") as file_:
        #with open(out_filename, "w") as file_:
            for node in new_router_graph.nodes:
                file_.write(f"{node}\n")

    """
This function creates a graph using the CAIDA dataset (midar-iff.nodes.geo and midar-iff.links)
node_set is a set of node ids that we are using to create the graph. Any id that is not in the set is not added to the graph ( and neither are the edges adjacent to it)

    """

    def create_graph(self, load_subset=False):
        start = time.time()
        #nodes = pd.read_csv("../datasets/node_location/location/US_nodes.geo.csv")
        node_locations = {}

        self.G = nx.Graph()
        print("Loading nodes!", flush = True)


        i = 0
        with open(f"{self.dataset_dir}/CAIDA_data/midar-iff.nodes.geo") as file_:
            for  line in file_:
                if line[0] == "#":
                    continue
                data = line.split("\t")
                node_id = int( data[0].split(" ")[1][1:-1] )
                # If we passed a node_set and the node_id is not in the set, we continue with the next node_id in the file
                if load_subset and not node_id in self.node_set:
                    continue
                lat = float(data[5])
                long = float(data[6])
                self.G.add_node(node_id, loc = (lat, long))
                self.add_location_to_dict(lat, long, node_id)
                i = i +1
                #if i == 200:
                #    break
        node_time = time.time()
        #node_locations_set = list(node_locations.keys())
        node_locations_set_time = time.time()
        load_node_time = node_time - start
        load_node_set_time = node_locations_set_time - node_time
        print(f"Time to load nodes: {load_node_time}", flush = True)
        print(f"Time to create node set : {load_node_set_time}", flush = True)
        #j = 0
        #print(len(node_locations_set), i)
        #locations = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lat, lon in node_locations_set], crs="EPSG:4326")




        print("Nodes loaded!", flush = True)
        print("Loading links!", flush = True)
        with open(f"{self.dataset_dir}/CAIDA_data/midar-iff.links") as file_:
            for j, line in enumerate(file_):
                #if j == 0:
                #        print(line)
                if line[0] =="#":
                    continue
                else:
                    # Example line ofrom this file
                    # link L17122553:  N13232567:224.215.142.140 N13232566

                    nodes = self.get_nodes_from_line(line)
                    if load_subset:
                        nodes = [node for node in nodes if node in self.node_set ]
                    # Filter out the nodes that have no geographic data (i.e. nodes that do not appear in the midar-iff.nodes.geo and thus are not already in the graph)
                    nodes = filter(lambda x: x in self.G.nodes, nodes)

                    #print(nodes)
                    self.load_node_links( nodes)
                #if j == 200:
                #    break
        print("Links Loaded!!")
        #print(router_graph)
        link_time = time.time()

        load_link_time = link_time - node_time
        print(f"Time to load links : {load_link_time}", flush = True)

        #return self.G, node_locations

    def get_all_routes_by_ids(self, start_id, dest_id):
        if not self.ASes:
            print("NO ASes!")
            self.create_node_id_AS_mapping()
            print(len(self.ASes))
        paths_generator = nx.all_simple_paths(self.G, source=start_id, target=dest_id)
        
        for path in paths_generator:
            path_2 = self.get_info_for_path( path)
            yield path_2
        

    def get_route_by_ids(self, start_id, dest_id):
        path = nx.shortest_path(self.G, source=start_id, target=dest_id)
        if not self.ASes:
            print("NO ASes!")
            self.create_node_id_AS_mapping()
            print(len(self.ASes))
        #path_1 = [(node_id , self.ASes.get(node_id, None)) for node_id in path ]
        #print(path_1, flush =True)
        #path_2 = [(node_id, G.nodes[node_id]["loc"] , AS_map.get(node_id, None)) for node_id in path ]
        path_2 = self.get_info_for_path( path)
        #path_2 = [(node_id, G.nodes[node_id] , AS_map.get(node_id, None)) for node_id in path ]
        #print(path_2, flush =True)
        #print(f"Nodes: {len(G.nodes)}, Edges: {len(G.edges)}", flush=True)
        return path_2

    def get_route(self, start_loc, dest_loc):
        start_node, start_distance = self.get_closest_point(start_loc)
        dest_node, dst_distance = self.get_closest_point(dest_loc)
        print(f"Start node: {start_node}, End node: {dest_node}", flush=True)
        print(f"Distances: {start_distance}, {dst_distance}", flush=True)
        # if not self.ASes:
        #     print("NO ASes!")
        #     self.create_node_id_AS_mapping()
        #     print(len(self.ASes))

        path = self.get_route_by_ids(start_node, dest_node)
        #path = nx.shortest_path(self.G, source=start_node, target=dest_node)
        
        #path_2 = self.get_info_for_path( path)
        
        return path

    def get_info_for_path(self, path):
        #path_2 = [(node_id, self.G.nodes[node_id] , self.ASes.get(node_id, None)) for node_id in path ]
        
        path_2 = [{"id": node_id, "loc":self.G.nodes[node_id]["loc"] , "AS": self.ASes.get(node_id, None)} for node_id in path ]
        #print(path_2, flush =True)
        return path_2

def parse_args():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--get-largest-connected-component-nodes', action='store_true', help='Get the ids of the nodes in the CAIDA dataset that form the largest connected component.')
    group.add_argument('--load-largest-component', action='store_true')
    #group.add_argument('--create-node-as-file', action='store_true', help='Create the csv file that maps node id to Autonomous System (AS) id.')
    #parser.add_argument('')

    args = parser.parse_args()

    return args



def main():
    args = parse_args()
    caida_graph = CAIDA_GRAPH()
    if args.get_largest_connected_component_nodes:
        caida_graph.create_graph()
        caida_graph.get_largest_connected_component()
    elif args.load_largest_component:
        caida_graph.load_node_set()
        print(f"Node set loaded! Size: {len(caida_graph.node_set)}",flush = True )
        caida_graph.create_graph(load_subset= True)

        connected_components = list(nx.connected_components(caida_graph.G))
        n_connected_comonents = len(connected_components)
        print(f"Number of connected components: {n_connected_comonents}", flush=True)
        print(f"Nodes: {len(caida_graph.G.nodes)}, Edges: {len(caida_graph.G.edges)}", flush=True)
        #node_locations_set = list(node_locations.keys())
        # Coordinates for Boston: 42.3555° N, 71.0565° W
        Boston_loc = (42.3555, -71.0565)
        # Washington DC 38.9072° N, 77.0369° W
        wash_dc_loc = (38.9, -77.03)
        san_fran_loc = (37.7749, -122)
        caida_graph.get_route(Boston_loc, wash_dc_loc)
        caida_graph.get_route(san_fran_loc, wash_dc_loc)
        #get_simple_routes(G, Boston_loc, wash_dc_loc, node_locations)
    else:
        caida_graph.create_graph()
        
       

if __name__ == "__main__":
    start = time.time()
    main()
    #nx.write_graphml(graph, "../datasets/US_router.graphml")
    end = time.time()
    print(end - start, flush = True)
