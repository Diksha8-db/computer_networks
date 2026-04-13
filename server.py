import socket
import random
from datetime import datetime

# --- ANSI Colors ---
RESET = "\033[0m"
INFO = "\033[94m"    # Blue
SUCCESS = "\033[92m" # Green
WARNING = "\033[93m" # Yellow
ERROR = "\033[91m"   # Red

# --- Config ---
DROP_PROBABILITY = 0.20
CORRUPT_PROBABILITY = 0.15
WINDOW_SIZE = 4

def log(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}{message}{RESET}")

def compute_checksum(data):
    return sum(ord(c) for c in data) % 256

def start_server():
    server_address = ('localhost', 12000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)
    
    rcv_base = 0
    buffer = {} # Dictionary to store out-of-order packets

    log(INFO, f"Selective Repeat Server started. Window Size: {WINDOW_SIZE}")
    print("-" * 60)

    while True:
        packet, client_address = sock.recvfrom(1024)
        data = packet.decode()

        # Simulate network failures
        if random.random() < DROP_PROBABILITY:
            log(ERROR, "[NETWORK] Packet dropped entirely.")
            continue

        try:
            seq_str, chk_str, msg = data.split('|', 2)
            seq_num = int(seq_str)
            received_chk = int(chk_str)
        except ValueError:
            continue

        if random.random() < CORRUPT_PROBABILITY:
            log(WARNING, f"[NETWORK] Packet {seq_num} corrupted!")
            received_chk = -1 

        if compute_checksum(msg) != received_chk:
            log(ERROR, f"[SERVER] Checksum failed for SEQ {seq_num}. Dropping packet.")
            continue # In Selective Repeat, we do NOT send duplicate ACKs for corruption. We stay silent.

        # Packet is pristine. Check where it falls in our window.
        if rcv_base <= seq_num < rcv_base + WINDOW_SIZE:
            log(INFO, f"[SERVER] Sending ACK {seq_num}")
            sock.sendto(str(seq_num).encode(), client_address)

            if seq_num not in buffer:
                buffer[seq_num] = msg
                log(WARNING, f"    -> Buffered out-of-order packet (SEQ {seq_num})")

            # Deliver consecutive packets and slide window
            if seq_num == rcv_base:
                while rcv_base in buffer:
                    log(SUCCESS, f"[SERVER] App Layer Delivery: '{buffer[rcv_base]}'")
                    del buffer[rcv_base]
                    rcv_base += 1
                log(INFO, f"[SERVER] Window slid forward. New Base: {rcv_base}")

        elif seq_num < rcv_base:
            # Sender's previous ACK was lost. We must re-ACK it so sender can move on.
            log(WARNING, f"[SERVER] Received old packet (SEQ {seq_num}). Re-sending ACK.")
            sock.sendto(str(seq_num).encode(), client_address)

if __name__ == "__main__":
    start_server()