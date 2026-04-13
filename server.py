import socket
import random
import time
from datetime import datetime

# --- ANSI Color Codes for Informative Output ---
RESET = "\033[0m"
INFO = "\033[94m"    # Blue
SUCCESS = "\033[92m" # Green
WARNING = "\033[93m" # Yellow
ERROR = "\033[91m"   # Red

# --- Configuration ---
DROP_PROBABILITY = 0.20    # 20% chance to drop a packet
CORRUPT_PROBABILITY = 0.15 # 15% chance to simulate a bit error

def log(level, message):
    """Prints a timestamped, color-coded log message."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}{message}{RESET}")

def compute_checksum(data):
    """Computes a simple checksum by summing the ASCII values of the characters."""
    return sum(ord(c) for c in data) % 256

def start_server():
    server_address = ('localhost', 12000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)
    
    expected_seq = 0
    log(INFO, f"RDT 3.0 Server started on {server_address[0]}:{server_address[1]}")
    log(INFO, f"Simulating Network: Drop Rate={DROP_PROBABILITY*100}%, Corrupt Rate={CORRUPT_PROBABILITY*100}%")
    print("-" * 60)

    while True:
        packet, client_address = sock.recvfrom(1024)
        data = packet.decode()
        
        # 1. Simulate Network Packet Loss
        if random.random() < DROP_PROBABILITY:
            log(ERROR, "[NETWORK] Packet dropped entirely. Silence...")
            continue

        # Parse the packet: "SEQ|CHECKSUM|PAYLOAD"
        try:
            seq_str, checksum_str, msg = data.split('|', 2)
            seq_num = int(seq_str)
            received_checksum = int(checksum_str)
        except ValueError:
            log(ERROR, "[SERVER] Received malformed packet format.")
            continue

        # 2. Simulate Data Corruption (Bit Errors)
        if random.random() < CORRUPT_PROBABILITY:
            log(WARNING, f"[NETWORK] Packet {seq_num} got corrupted in transit!")
            received_checksum = -1 # Force a checksum failure

        # 3. Verify Checksum
        calculated_checksum = compute_checksum(msg)
        is_corrupted = (received_checksum != calculated_checksum)

        if is_corrupted:
            log(ERROR, f"[SERVER] Checksum failed for SEQ {seq_num}. Expected {calculated_checksum}, got {received_checksum}. Ignoring packet.")
            # RDT 3.0 reaction to corruption: Send ACK for the *previous* successful sequence
            # This triggers a duplicate ACK on the sender side, forcing a timeout/retransmit
            prev_seq = 1 - expected_seq
            log(INFO, f"[SERVER] Sending duplicate ACK {prev_seq} to force retransmission.")
            sock.sendto(str(prev_seq).encode(), client_address)
            continue

        # 4. Process Sequence Numbers
        if seq_num == expected_seq:
            log(SUCCESS, f"[SERVER] Valid packet received (SEQ {seq_num}): '{msg}'")
            log(SUCCESS, f"[SERVER] Sending ACK {seq_num}")
            sock.sendto(str(seq_num).encode(), client_address)
            expected_seq = 1 - expected_seq # Toggle 0 <-> 1
        else:
            log(WARNING, f"[SERVER] Duplicate packet received (SEQ {seq_num}). Already processed.")
            log(INFO, f"[SERVER] Re-sending ACK {seq_num} to help client recover.")
            sock.sendto(str(seq_num).encode(), client_address)

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer shut down.")