"""Local, authenticated Tor bootstrap check; never probes an external site."""
import socket
from pathlib import Path

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.settimeout(3)
    client.connect("/run/tor-control/control.sock")
    stream = client.makefile("rwb", buffering=0)
    cookie = Path("/run/tor-control/control_auth_cookie").read_bytes().hex()
    stream.write(f"AUTHENTICATE {cookie}\r\n".encode())
    assert stream.readline().startswith(b"250 "), "Tor control authentication failed"
    stream.write(b"GETINFO status/bootstrap-phase\r\n")
    response = stream.readline()
    assert b"PROGRESS=100" in response, "Tor is still bootstrapping"
