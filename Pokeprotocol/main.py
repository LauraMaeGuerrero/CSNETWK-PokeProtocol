"""Main menu and CLI interface for PokeProtocol"""
import sys
from pokemon import PokemonManager, MOVES  # Added MOVES import
from peers import HostPeer, JoinerPeer, SpectatorPeer
from utils import color, CYAN, YELLOW, validate_sticker_data
from network import set_verbose
import base64


class PokeProtocolCLI:
    def __init__(self):
        try:
            self.pokemon_manager = PokemonManager()
        except Exception as e:
            print("Error loading CSV:", e)
            sys.exit(1)

    def send_chat(self, peer, dest):
        t = input("Send type TEXT or STICKER? ").strip().upper()
        if t == 'TEXT':
            text = input("Message: ")
            payload = {'message_type': 'CHAT_MESSAGE', 'sender_name': peer.name, 
                      'content_type': 'TEXT', 'message_text': text}
            peer.send(payload, dest)
        elif t == 'STICKER':
            path = input("Path to image file: ").strip()
            try:
                with open(path, 'rb') as f:
                    raw = f.read()
            except Exception as e:
                print("Cannot read file:", e)
                return
            if len(raw) > 10 * 1024 * 1024:
                print("Sticker exceeds 10MB")
                return
            b64 = base64.b64encode(raw).decode('ascii')
            payload = {'message_type': 'CHAT_MESSAGE', 'sender_name': peer.name, 
                      'content_type': 'STICKER', 'sticker_data': b64}
            peer.send(payload, dest)
        else:
            print("Unknown content type")

    def run_host(self, pname: str, port: int):
        try:
            host = HostPeer("HostPlayer", self.pokemon_manager, pname, bind_port=port)
        except Exception as e:
            print(f"[ERROR] Failed to create host: {e}")
            return
        host.start_receiving()
        print(f"[Host] hosting as {pname}. Waiting for joiner... (Ctrl-C to stop)")
        
        try:
            while True:
                print(color("Available host commands: attack | chat | status | exit", CYAN))
                cmd = input("Host command: ").strip().lower()
                if cmd == 'status':
                    print("Battle state:", host.battle_state)
                    print("Local Pokemon HP:", host.local_pokemon_row.get('hp'))
                    if host.joiner_pokemon_row:
                        print("Opponent HP (host view):", host.joiner_pokemon_row.get('hp'))
                elif cmd == 'attack':
                    if host.battle_state.get('turn') != 'host':
                        print(color("It's not your turn! Wait for opponent.", YELLOW))
                        continue
                    if not host.remote_addr:
                        print("No joiner connected yet")
                        continue
                    
                    moves = host.available_moves()
                    print("Available moves:")
                    for i, m in enumerate(moves, start=1):
                        # FIXED: Get move data from MOVES, not moves_by_pokemon
                        md = MOVES.get(m, {})
                        print(f"  {i}) {m} (type={md.get('type', 'Unknown')} power={md.get('power', 'Unknown')})")
                    
                    choice_mv = input("Choose move (number or name): ").strip()
                    if choice_mv.isdigit():
                        idx = int(choice_mv) - 1
                        if idx < 0 or idx >= len(moves):
                            print("Invalid move index")
                            continue
                        mv = moves[idx]
                    else:
                        mv = choice_mv
                        if mv not in moves:
                            print("Invalid move name")
                            continue
                    host.announce_attack(mv)
                elif cmd == 'chat':
                    if not host.remote_addr:
                        print("No remote yet")
                        continue
                    self.send_chat(host, host.remote_addr)
                elif cmd == 'exit':
                    host.stop()
                    break
                else:
                    print("Unknown command")
        except KeyboardInterrupt:
            host.stop()
            print("Host stopped")

    def run_joiner(self, pname: str, host_ip: str, host_port: int, bind_port: int):
        try:
            joiner = JoinerPeer("JoinerPlayer", self.pokemon_manager, pname, host_ip, host_port, bind_port)
        except Exception as e:
            print(f"[ERROR] Failed to create joiner: {e}")
            return
        joiner.start_receiving()
        print(f"[Joiner] Attempting to connect to {host_ip}:{host_port}...")
        joiner.start_handshake()
        print("[Joiner] handshake sent. Waiting for host responses. Commands: [attack|chat|status|exit]")
        
        try:
            while True:
                print(color("Available joiner commands: attack | chat | status | exit", CYAN))
                cmd = input("Joiner command: ").strip().lower()
                if cmd == 'attack':
                    if joiner.battle_state.get('turn') != 'joiner':
                        print(color("It's not your turn! Wait for opponent.", YELLOW))
                        continue
                    if not getattr(joiner, 'remote_addr', None):
                        print("Host not connected yet")
                        continue
                    
                    moves = joiner.available_moves()
                    print("Available moves:")
                    for i, m in enumerate(moves, start=1):
                        # FIXED: Get move data from MOVES, not moves_by_pokemon
                        md = MOVES.get(m, {})
                        print(f"  {i}) {m} (type={md.get('type', 'Unknown')} power={md.get('power', 'Unknown')})")
                    
                    choice_mv = input("Choose move (number or name): ").strip()
                    if choice_mv.isdigit():
                        idx = int(choice_mv) - 1
                        if idx < 0 or idx >= len(moves):
                            print("Invalid move index")
                            continue
                        mv = moves[idx]
                    else:
                        mv = choice_mv
                        if mv not in moves:
                            print("Invalid move name")
                            continue
                    joiner.announce_attack(mv)
                elif cmd == 'chat':
                    if not getattr(joiner, 'remote_addr', None):
                        print("No host addr yet")
                        continue
                    self.send_chat(joiner, joiner.remote_addr or joiner.host_addr)
                elif cmd == 'status':
                    print("Battle state:", joiner.battle_state)
                    print("Local Pokemon HP:", joiner.local_pokemon_row.get('hp'))
                    if joiner.host_pokemon_row:
                        print("Opponent HP (joiner view):", joiner.host_pokemon_row.get('hp'))
                elif cmd == 'exit':
                    joiner.stop()
                    break
                else:
                    print("Unknown command")
        except KeyboardInterrupt:
            joiner.stop()
            print("Joiner stopped")

    def run_spectator(self, host_ip: str, host_port: int, spec_name: str):
        spect = SpectatorPeer(spec_name, self.pokemon_manager, host_ip, host_port)
        spect.start_receiving()
        spect.join_as_spectator()
        
        try:
            while True:
                cmd = input("Spectator commands: [chat|exit]: ").strip().lower()
                if cmd == 'chat':
                    self.send_chat(spect, spect.host_addr)
                elif cmd == 'exit':
                    spect.stop()
                    break
                else:
                    print("Unknown")
        except KeyboardInterrupt:
            spect.stop()
            print("Spectator stopped")

    def main_menu(self):
        # Ask for verbose mode at startup
        verbose_choice = input("Enable verbose mode? (y/n): ").strip().lower()
        if verbose_choice == 'y':
            set_verbose(True)
            print("[Verbose mode ENABLED - all messages will be printed]")
        else:
            set_verbose(False)
            print("[Verbose mode DISABLED - only errors and game messages will be shown]")
        
        while True:
            print("\n=== PokeProtocol P2P ===")
            print("1) Start as Host")
            print("2) Start as Client (Join)")
            print("3) Start as Spectator")
            print("4) Exit")
            choice = input("Select option: ").strip()
            
            if choice == '1':
                names = self.pokemon_manager.get_pokemon_list(20)
                print("Available Pokémon (first 20):")
                for i, n in enumerate(names, start=1):
                    print(f"{i}. {n}")
                pick = input("Choose Pokémon number: ").strip()
                try:
                    idx = int(pick) - 1
                    pname = names[idx]
                except Exception:
                    print("Invalid selection, abort.")
                    continue
                try:
                    port = int(input("Bind port for host (default 5001): ").strip() or 5001)
                except Exception:
                    port = 5001
                self.run_host(pname, port)
                
            elif choice == '2':
                host_ip = input("Host IP (e.g. 127.0.0.1): ").strip()
                try:
                    host_port = int(input("Host port (e.g. 5001): ").strip() or 5001)
                except Exception:
                    host_port = 5001
                
                names = self.pokemon_manager.get_pokemon_list(20)
                print("Available Pokémon (first 20):")
                for i, n in enumerate(names, start=1):
                    print(f"{i}. {n}")
                pick = input("Choose Pokémon number: ").strip()
                try:
                    idx = int(pick) - 1
                    pname = names[idx]
                except Exception:
                    print("Invalid selection")
                    continue
                    
                try:
                    bind_port = int(input("Local bind port (0 for random): ").strip() or 0)
                except Exception:
                    bind_port = 0
                self.run_joiner(pname, host_ip, host_port, bind_port)
                
            elif choice == '3':
                host_ip = input("Host IP: ").strip()
                try:
                    host_port = int(input("Host port: ").strip() or 5001)
                except Exception:
                    host_port = 5001
                spec_name = input("Spectator name (default Spectator): ").strip() or "Spectator"
                self.run_spectator(host_ip, host_port, spec_name)
                
            elif choice == '4':
                print("Goodbye")
                return
            else:
                print("Invalid choice")


if __name__ == '__main__':
    cli = PokeProtocolCLI()
    cli.main_menu()