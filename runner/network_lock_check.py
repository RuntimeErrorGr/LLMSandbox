import socket
import sys
import time

PROBE = ("1.1.1.1", 443)
ATTEMPTS = 30


def egress_open() -> bool:
    try:
        socket.create_connection(PROBE, timeout=2).close()
        return True
    except OSError:
        return False


for attempt in range(1, ATTEMPTS + 1):
    if not egress_open():
        print(f"network locked after {attempt} check(s)", flush=True)
        sys.exit(0)
    time.sleep(1)

print("network is still open, refusing to start the module", flush=True)
sys.exit(1)
