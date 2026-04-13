import socket
import time
from datetime import datetime

# --- ANSI Color Codes ---
RESET = "\033[0m"
INFO = "\033[94m"    # Blue
SUCCESS = "\033[92m" # Green
WARNING = "\033[93m" # Yellow
ERROR = "\033[91m"   # Red

def log(level, message):
    """Prints a timestamped, color-coded log message."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}{message}{RESET}")

def compute_checksum(data):
    """Computes a simple checksum by summing the ASCII values of the characters."""
    return sum(ord(c) for c in data) % 256

def start_client():
    server_address = ('localhost', 12000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # RDT Timer: Wait 2 seconds before assuming packet/ACK is lost
    TIMEOUT = 2.0
    sock.settimeout(TIMEOUT) 

    messages = [
        "Project Initialized.", 
        "Sending crucial payload data.", 
        "Network integrity looks questionable.", 
        "Final message: Terminating connection."
    ]
    
    seq_num = 0

    log(INFO, f"RDT 3.0 Client preparing to send {len(messages)} messages...")
    print("-" * 60)

    for msg in messages:
        # Create Checksum and Packet
        checksum = compute_checksum(msg)
        packet = f"{seq_num}|{checksum}|{msg}".encode()
        
        acked = False
        attempt = 1

        while not acked:
            try:
                log(INFO, f"[CLIENT] Attempt {attempt} - Sending: SEQ {seq_num} | CHK {checksum} | Data: '{msg}'")
                sock.sendto(packet, server_address)

                # Wait for ACK
                ack_packet, _ = sock.recvfrom(1024)
                ack_seq = int(ack_packet.decode())

                # Validate ACK
                if ack_seq == seq_num:
                    log(SUCCESS, f"[CLIENT] Received valid ACK {ack_seq}.")
                    print("-" * 60)
                    acked = True
                    seq_num = 1 - seq_num # Toggle sequence number
                else:
                    log(WARNING, f"[CLIENT] Received out-of-order ACK {ack_seq}. Still waiting for ACK {seq_num}.")

            except socket.timeout:
                log(ERROR, f"[CLIENT] TIMEOUT! No valid ACK received for SEQ {seq_num} within {TIMEOUT}s. Retransmitting...")
                attempt += 1

    sock.close()
    log(SUCCESS, "All data transferred reliably! Client shutting down.")

if __name__ == "__main__":
    start_client()