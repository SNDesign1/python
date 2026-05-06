from http.server import SimpleHTTPRequestHandler, HTTPServer
import subprocess 
import socket
import json
import sys
import os
import importlib.util

def isAvailable(module_name):
    return importlib.util.find_spec(module_name) is not None

if isAvailable("obswebsocket"):
    from obswebsocket import obsws, requests

if sys.platform == "linux":
    import signal

PORT = 8080
OBS_PORT = 4455

class Handler(SimpleHTTPRequestHandler):
    processes = {}

    def getIpAddress(self) -> str:
        return socket.gethostbyname(socket.gethostname())


    def isPortUsed(self, port): 
        try:
            s = socket.create_connection((self.getIpAddress(), port), timeout=1)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            return False

    def do_POST(self):
        try:
            if self.path == "/obs":
                if isAvailable("obswebsocket") == False:
                    raise Exception("module missing: pip install obs-websocket-py")

                contentLength = self.headers["Content-Length"]
                if contentLength == None:
                    raise Exception("missing body")
                
                length = int(contentLength)
                body = self.rfile.read(length).decode()
                body = json.loads(body)

                if "scene" not in body:
                    raise Exception("post missing 'scene':")

                scene = body["scene"]

                if self.isPortUsed(OBS_PORT):
                    ws = obsws(self.getIpAddress(), OBS_PORT)
                    ws.connect()
                    ws.call(requests.SetCurrentProgramScene(sceneName=scene))
                    ws.disconnect()
                else:
                    if "exe" not in body:
                        raise Exception("exe not contained in body and obs not open")

                    exe = body["exe"]
                    exeDir = os.path.dirname(exe)
                    process = subprocess.Popen([exe, "--scene", scene], cwd=exeDir) # launches from obs' dir
                    pId = process.pid

                    Handler.processes[pId] = exe
                    print(f"launched obs {pId}")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "IpAddress": self.getIpAddress()
                    }).encode())
                self.wfile.flush()

            if self.path == "/launch":
                contentLength = self.headers["Content-Length"]
                if contentLength == None:
                    raise Exception("missing body")

                length = int(contentLength)
                body = self.rfile.read(length).decode()
                body = json.loads(body)

                if "exe" not in body:
                    raise Exception("post missing 'exe'")

                exe = body["exe"]

                args = []
                if "args" in body:
                    args = body["args"]

                process = subprocess.Popen([exe] + args)
                pId = process.pid

                Handler.processes[pId] = exe
                print(f"Created process {pId} {exe} {args}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "IpAddress": self.getIpAddress(),
                    "ProcessId": pId,
                    "ProcessExe": exe
                    }).encode())
                self.wfile.flush()

            if self.path == "/kill": 
                contentLength = self.headers["Content-Length"]
                if contentLength == None or int(contentLength) == 0:
                    for pId in list(Handler.processes): 
                        if sys.platform == "win32":
                            subprocess.run(["taskkill", "/F", "/IM", os.path.basename(Handler.processes[pId]), "/T"], capture_output=True)
                        else:
                            os.killpg(os.getpgid(pId), signal.SIGTERM)

                        del Handler.processes[pId]
                        print(f"Killing {pId}")
                else:
                    length = int(contentLength)
                    body = self.rfile.read(length).decode()
                    body = json.loads(body)

                    if "pId" in body:
                        pId = body["pId"]

                        if sys.platform == "win32":
                            subprocess.run(["taskkill", "/F", "/IM", os.path.basename(Handler.processes[pId]), "/T"], capture_output=True)
                        else:
                            os.killpg(os.getpgid(pId), signal.SIGTERM)

                        del Handler.processes[pId]
                        print(f"Killing {pId}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "IpAddress": self.getIpAddress()
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
