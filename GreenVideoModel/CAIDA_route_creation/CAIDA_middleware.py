import requests
from fastapi import FastAPI, Request
import socket
# from pydantic import BaseModel
from contextlib import asynccontextmanager
# import shutil
import random

import subprocess
'''
#########

THIS CODE IS NOT NEEDED!!

#########
'''

NUMBER_OF_SERVERS = 8



# class RouteRequest(BaseModel):
#     method: str
#     src_lat: float
#     src_long: float
#     dst_lat: float
#     dst_long: float

Processes = {}
PORTS = []

def get_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def run_servers(app, number_servers):

    # ports = [get_port() for  i in range(number_servers)]
    
    # pp.pprint(ports)

    # python_cmd = shutil.which("python3.10")
    # print(python_cmd)
    #PORTS = []
    for i in range(number_servers):
        port_  = get_port()
        print(port_)

        command = ["fastapi", "run", "./GreenVideoModel/CAIDA_route_creation/CAIDA_Server.py", "--port", f"{port_}"]
        print(command)
        # command = ["pwd"]
        p = subprocess.Popen(command, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
        # p = subprocess.run(command)
        print(p)
        #time.sleep(1)
        app.processes[port_] = p  
        app.ports.append(port_)
        # run a subprocess of Serving_API_3.py
    print("Server is ready!!", flush = True)
    print("Ports:")
    for p in PORTS:
        print(f"\t{p}")

def shutdown_children(app):
    for port_, process in app.processes.items():
        print(f"Shutting down process listening on port {port_}")
        process.terminate()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Startup: Initialize database/resources")
    app.processes = {}
    app.ports = []
    run_servers(app, NUMBER_OF_SERVERS)
    yield
    # Shutdown logic
    shutdown_children(app)
    print("Shutdown: Cleanup resources")


app = FastAPI(lifespan = lifespan)



@app.post("/routes/")
async def get_routes_middleware(routeRequest: Request):
    # routeRequest_dict = routeRequest.model_dump()
    host = 'localhost'
    port = random.choice(app.ports)#'8000'
    print(port)
    data = await routeRequest.body()
    print(data)
    headers = routeRequest.headers
    print(headers)
    # res = requests.post(f"http://{host}:{port}/routes/", data = await routeRequest.body(), headers=routeRequest.headers.raw)
    res = requests.post(f"http://{host}:{port}/routes/", data = data, headers=headers)

    # body = await routeRequest.body()
    # print(body)

    return res.json()



# @app.middleware("http")
# async def forward_to_replica(request: Request, call_next):
#     # If request is meant for replica, forward it
#     async with httpx.AsyncClient(base_url=REPLICA_URL) as client:
#         # Reconstruct the request
#         rp_req = client.build_request(
#             method=request.method,
#             url=request.url.path,
#             headers=request.headers.raw,
#             content=await request.body()
#         )
#         # Send to replica
#         rp_resp = await client.send(rp_req, stream=True)
        
#         # Return replica response
#         return StreamingResponse(
#             rp_resp.aiter_raw(),
#             status_code=rp_resp.status_code,
#             headers=rp_resp.headers,
#         )