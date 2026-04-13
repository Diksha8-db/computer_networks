import socket
import time
import threading
from datetime import datetime

# --- ANSI Colors ---
RESET = "\033[0m"
INFO = "\033[94m"    # Blue
SUCCESS = "\033[92m" # Green
WARNING = "\033[93m" # Yellow
ERROR = "\033[91m"   # Red

# --- Config ---
WINDOW_SIZE = 4
TIMEOUT = 2.0

# --- Global State Variables for Threading ---
send_base = 0
next_seq_num = 0
lock = threading.Lock()

messages = [f"Payload Data Block {i}" for i in range(10)]
num_packets = len(messages)

ack_status = [False] * num_packets
send_times = [0.0] * num_packets

def log(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}{message}{RESET}")

def compute_checksum(data):
    return sum(ord(c) for c in data) % 256

def listen_for_acks(sock):
    """Background thread to listen for incoming ACKs asynchronously."""
    global send_base
    while send_base < num_packets:
        try:
            # Non-blocking wait for ACKs
            ack_packet, _ = sock.recvfrom(1024)
            ack_seq = int(ack_packet.decode())
            
            with lock:
                if send_base <= ack_seq < send_base + WINDOW_SIZE:
                    if not ack_status[ack_seq]:
                        log(SUCCESS, f"<-- [CLIENT] Received ACK {ack_seq}")
                        ack_status[ack_seq] = True

                        # Slide window forward if the base packet is ACKed
                        while send_base < num_packets and ack_status[send_base]:
                            send_base += 1
                            log(INFO, f"*** Client Window Slid to Base: {send_base} ***")
        except socket.timeout:
            continue

def start_client():
    global send_base, next_seq_num
    
    server_address = ('localhost', 12000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5) # Short timeout for the listen thread to periodically yield

    # Start the background listening thread
    listener_thread = threading.Thread(target=listen_for_acks, args=(sock,), daemon=True)
    listener_thread.start()

    log(INFO, f"Selective Repeat Client starting. Sending {num_packets} packets.")
    print("-" * 60)

    # Main Sending/Timeout Loop
    while send_base < num_packets:
        with lock:
            # 1. Send new packets if the window has space
            while next_seq_num < send_base + WINDOW_SIZE and next_seq_num < num_packets:
                msg = messages[next_seq_num]
                chk = compute_checksum(msg)
                packet = f"{next_seq_num}|{chk}|{msg}".encode()
                
                log(INFO, f"--> [CLIENT] Sending SEQ {next_seq_num}")
                sock.sendto(packet, server_address)
                send_times[next_seq_num] = time.time()
                next_seq_num += 1

            # 2. Check for Timeouts on unacknowledged packets
            for i in range(send_base, next_seq_num):
                if not ack_status[i]:
                    if (time.time() - send_times[i]) > TIMEOUT:
                        log(ERROR, f"[!] TIMEOUT for SEQ {i}. Retransmitting specifically SEQ {i}...")
                        msg = messages[i]
                        chk = compute_checksum(msg)
                        packet = f"{i}|{chk}|{msg}".encode()
                        sock.sendto(packet, server_address)
                        send_times[i] = time.time() # Reset timer for this specific packet

        time.sleep(0.1) # Small delay to prevent CPU maxing out while looping

    listener_thread.join(timeout=1.0)
    sock.close()
    log(SUCCESS, "\nAll data transferred successfully! Selective Repeat completed.")

if __name__ == "__main__":
    start_client()