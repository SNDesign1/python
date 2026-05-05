from http.server import SimpleHTTPRequestHandler, HTTPServer
import subprocess 
import socket
import json
import importlib.util 
import sys

if importlib.util.find_spec("psutil") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "psutil"])

import psutil

PORT = 8080

class Handler(SimpleHTTPRequestHandler):
    processes = {}

    def getIpAddress(self) -> str:
        return socket.gethostbyname(socket.gethostname())

    def do_POST(self):
        try:
            if self.path == "/launch":
                contentLength = self.headers["Content-Length"]
                if contentLength == None:
                    raise Exception("missing body")

                length = int(contentLength)
                body = self.rfile.read(length).decode()
                body = json.loads(body)

                pName = None
                if "name" in body:
                    pName = body["name"]

                if "exe" not in body:
                    raise Exception("post missing 'exe'")

                exe = body["exe"]

                args = []
                if "args" in body:
                    args = body["args"]

                pipeArgs = []
                pipeArgs.append(exe)

                if len(args) > 0:
                    pipeArgs = pipeArgs + args

                process = subprocess.Popen(pipeArgs)
                pId = process.pid

                if psutil.pid_exists(pId) == False:
                    raise Exception("failed to create valid process")

                Handler.processes[pId] = pName

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "IpAddress": self.getIpAddress(),
                    "ProcessId": pId,
                    "ProcessName": pName
                    }).encode())
                self.wfile.flush()

            if self.path == "/kill": 
                killedProcesses = []
                failedProcesses = []

                contentLength = self.headers["Content-Length"]
                if contentLength == None:
                    for pId in list(Handler.processes): 
                        process = psutil.Process(pId)
                        process.kill()
                                                
                        if psutil.pid_exists(pId) == False:
                            killedProcesses.append(pId)
                            del Handler.processes[pId]
                        else:
                            failedProcesses.append(pId)
                else:
                    length = int(contentLength)
                    body = self.rfile.read(length).decode()
                    body = json.loads(body)

                    if "pId" in body:
                        pId = body["pId"]
                        process = psutil.Process(pId)
                        process.kill()
                                                
                        if psutil.pid_exists(pId) == False:
                            killedProcesses.append(pId)
                            del Handler.processes[pId]
                        else:
                            failedProcesses.append(pId)

                for fProcess in failedProcesses:
                    del Handler.processes[fProcess]
                    
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "IpAddress": self.getIpAddress(),
                    "KilledProcesses": killedProcesses,
                    "FailedProcesses": failedProcesses
                    }).encode())
                self.wfile.flush()

        except Exception as error:
            self.send_response(501)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "IpAddress": self.getIpAddress(),
                "Error": error.args
                }).encode())
            self.wfile.flush()

        except:
            self.send_response(501)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({ 
                "IpAddress": self.getIpAddress()
                }).encode())
            self.wfile.flush()

    def do_GET(self):
        try:
           if self.path == "/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                for pId in list(Handler.processes):
                    if psutil.pid_exists(pId) == False:
                        del Handler.processes[pId]

                self.wfile.write(json.dumps({
                        "IpAddress": self.getIpAddress(),
                        "Processes": Handler.processes,
                        }).encode())      
                self.wfile.flush()
        except Exception as error:
            self.send_response(501)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "IpAddress": self.getIpAddress(),
                "FailureReason": error.args
                }).encode())
            self.wfile.flush()

        except:
            self.send_response(501)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({ 
                "IpAddress": self.getIpAddress()
                }).encode())
            self.wfile.flush()


    
IpAddress = socket.gethostbyname(socket.gethostname())

with HTTPServer((IpAddress, PORT), Handler) as server:
   print(f"listening -- {socket.gethostname()} -- {IpAddress} -- {PORT}") 
   server.serve_forever() 
