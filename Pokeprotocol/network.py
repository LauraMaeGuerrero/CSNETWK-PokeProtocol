"""Network communication and reliability layer"""
import socket
import threading
import json
from typing import Dict, Any, Tuple, Optional

# Configuration
RECV_BUFFER = 65535
RETRANSMIT_TIMEOUT = 0.5   # seconds
RETRANSMIT_RETRIES = 3
VERBOSE_MODE = False  # Global verbose flag


def set_verbose(enabled: bool):
    global VERBOSE_MODE
    VERBOSE_MODE = enabled

def vprint(msg: str):
    """Print only in verbose mode"""
    if VERBOSE_MODE:
        print(f"[VERBOSE] {msg}")

class ReliableSender:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.lock = threading.Lock()
        self.waiters = {}  # seq -> threading.Event

    def send_with_ack(self, payload: Dict[str, Any], addr: Tuple[str, int], 
                     timeout=RETRANSMIT_TIMEOUT, max_retries=RETRANSMIT_RETRIES) -> bool:
        seq = payload.get('sequence_number')
        if seq is None:
            raise ValueError("Payload must contain sequence_number")
        ev = threading.Event()
        # Register waiter BEFORE sending to avoid race condition
        with self.lock:
            self.waiters[seq] = ev
        data = json.dumps(payload).encode('utf-8')
        tries = 0
        while tries <= max_retries:
            try:
                self.sock.sendto(data, addr)
                vprint(f"SENT: {json.dumps(payload)} -> {addr}")
            except Exception as e:
                print(f"[ERROR] send error: {e}")
                with self.lock:
                    self.waiters.pop(seq, None)
                return False
            got = ev.wait(timeout)
            if got:
                with self.lock:
                    self.waiters.pop(seq, None)
                vprint(f"ACK received for seq={seq}")
                return True
            tries += 1
            vprint(f"Retransmit seq={seq} try={tries}")
        with self.lock:
            self.waiters.pop(seq, None)
        return False

    def notify_ack(self, ack_number: int):
        with self.lock:
            ev = self.waiters.get(ack_number)
            if ev:
                ev.set()


class BasePeer:
    def __init__(self, name: str, bind_ip: str = '0.0.0.0', bind_port: int = 0):
        self.name = name
        self.remote_addr: Optional[Tuple[str, int]] = None
        self.seq_counter: Dict[str, int] = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(1.0)  # 1 second timeout for recv
        try:
            self.sock.bind((bind_ip, bind_port))
            actual_port = self.sock.getsockname()[1]
            print(f"[{name}] Bound to {bind_ip}:{actual_port}")
        except Exception as e:
            print(f"[ERROR] Failed to bind socket: {e}")
            raise
        self.running = False
        self.recv_thread: Optional[threading.Thread] = None
        self.reliable = ReliableSender(self.sock)

    def start_receiving(self):
        self.running = True
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()
        # Give the thread time to start
        import time
        time.sleep(0.1)

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def _recv_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(RECV_BUFFER)
                try:
                    msg = json.loads(data.decode('utf-8'))
                    vprint(f"RECV: {json.dumps(msg)} <- {addr}")
                except Exception:
                    continue
                
                # Auto-ack non-ACK messages that contain sequence_number
                if msg.get('message_type') != 'ACK' and 'sequence_number' in msg:
                    ack = {'message_type': 'ACK', 'ack_number': msg['sequence_number']}
                    try:
                        self.sock.sendto(json.dumps(ack).encode('utf-8'), addr)
                        vprint(f"SENT ACK: {json.dumps(ack)} -> {addr}")
                    except Exception:
                        pass
                
                # If it's an ACK notify reliable sender
                if msg.get('message_type') == 'ACK' and 'ack_number' in msg:
                    try:
                        self.reliable.notify_ack(int(msg['ack_number']))
                    except Exception:
                        pass
                    continue
                
                # dispatch to handler
                threading.Thread(target=self.handle_message, args=(msg, addr), daemon=True).start()
            except socket.timeout:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] recv_loop error: {e}")
                # Don't break, continue trying
                continue

    def make_seq(self) -> int:
        self.seq_counter[self.name] = self.seq_counter.get(self.name, 0) + 1
        return self.seq_counter[self.name]

    def send(self, payload: Dict[str, Any], addr: Tuple[str, int], reliable: bool = True) -> bool:
        seq = self.make_seq()
        payload['sequence_number'] = seq
        payload['from'] = self.name
        if reliable:
            success = self.reliable.send_with_ack(payload, addr)
            if not success:
                print(f"[ERROR] Failed to send {payload.get('message_type')} after retries")
            return success
        else:
            try:
                self.sock.sendto(json.dumps(payload).encode('utf-8'), addr)
                vprint(f"SENT (unreliable): {json.dumps(payload)} -> {addr}")
                return True
            except Exception as e:
                print(f"[ERROR] send error: {e}")
                return False

    def handle_message(self, msg: Dict[str, Any], addr: Tuple[str, int]):
        print(f"[{self.name}] unhandled message: {msg} from {addr}")