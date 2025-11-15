"""Network communication and reliability layer"""
import socket
import threading
import json
from typing import Dict, Any, Tuple, Optional

# Configuration
RECV_BUFFER = 65535
RETRANSMIT_TIMEOUT = 0.5   # seconds
RETRANSMIT_RETRIES = 3


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
        with self.lock:
            self.waiters[seq] = ev
        data = json.dumps(payload).encode('utf-8')
        tries = 0
        while tries <= max_retries:
            try:
                self.sock.sendto(data, addr)
            except Exception as e:
                print(f"[ReliableSender] send error: {e}")
            got = ev.wait(timeout)
            if got:
                with self.lock:
                    self.waiters.pop(seq, None)
                return True
            tries += 1
            print(f"[retransmit] seq={seq} try={tries}")
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
        self.sock.bind((bind_ip, bind_port))
        self.running = False
        self.recv_thread: Optional[threading.Thread] = None
        self.reliable = ReliableSender(self.sock)

    def start_receiving(self):
        self.running = True
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()

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
                except Exception:
                    continue
                
                # Auto-ack non-ACK messages that contain sequence_number
                if msg.get('message_type') != 'ACK' and 'sequence_number' in msg:
                    ack = {'message_type': 'ACK', 'ack_number': msg['sequence_number']}
                    try:
                        self.sock.sendto(json.dumps(ack).encode('utf-8'), addr)
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
            except Exception as e:
                if self.running:
                    print(f"[recv_loop] error: {e}")
                break

    def make_seq(self) -> int:
        self.seq_counter[self.name] = self.seq_counter.get(self.name, 0) + 1
        return self.seq_counter[self.name]

    def send(self, payload: Dict[str, Any], addr: Tuple[str, int], reliable: bool = True) -> bool:
        seq = self.make_seq()
        payload['sequence_number'] = seq
        payload['from'] = self.name
        if reliable:
            return self.reliable.send_with_ack(payload, addr)
        else:
            try:
                self.sock.sendto(json.dumps(payload).encode('utf-8'), addr)
                return True
            except Exception as e:
                print(f"[send] error: {e}")
                return False

    def handle_message(self, msg: Dict[str, Any], addr: Tuple[str, int]):
        print(f"[{self.name}] unhandled message: {msg} from {addr}")