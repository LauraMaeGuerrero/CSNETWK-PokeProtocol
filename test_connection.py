"""Simple UDP connection test"""
import socket
import sys

def test_host(port=5001):
    """Test as host"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', port))
        print(f"✓ Host bound to port {port}")
        print(f"  Waiting for message...")
        sock.settimeout(10)
        data, addr = sock.recvfrom(1024)
        print(f"✓ Received from {addr}: {data.decode()}")
        sock.sendto(b"ACK", addr)
        print(f"✓ Sent ACK to {addr}")
    except socket.timeout:
        print("✗ Timeout - no message received")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        sock.close()

def test_client(host_ip='127.0.0.1', host_port=5001):
    """Test as client"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('0.0.0.0', 0))
        local_port = sock.getsockname()[1]
        print(f"✓ Client bound to port {local_port}")
        print(f"  Sending to {host_ip}:{host_port}...")
        sock.sendto(b"HELLO", (host_ip, host_port))
        print(f"✓ Sent message")
        sock.settimeout(5)
        data, addr = sock.recvfrom(1024)
        print(f"✓ Received from {addr}: {data.decode()}")
    except socket.timeout:
        print("✗ Timeout - no response from host")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        sock.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Host: python test_connection.py host [port]")
        print("  Client: python test_connection.py client [host_ip] [host_port]")
        sys.exit(1)
    
    mode = sys.argv[1]
    if mode == 'host':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001
        test_host(port)
    elif mode == 'client':
        host_ip = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
        host_port = int(sys.argv[3]) if len(sys.argv) > 3 else 5001
        test_client(host_ip, host_port)
    else:
        print("Invalid mode. Use 'host' or 'client'")
