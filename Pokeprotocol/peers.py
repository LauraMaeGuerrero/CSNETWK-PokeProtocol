"""Host, Joiner, and Spectator peer implementations"""
import random
from typing import Dict, Any, Tuple, Optional
from network import BasePeer, VERBOSE_MODE
from pokemon import PokemonManager, MOVES
from utils import color, emphasize, CYAN, YELLOW, GREEN, RED, MAGENTA


def display_calc_report(msg: Dict[str, Any]):
    """Display calculation report with colors"""
    seq = msg.get('sequence_number')
    attacker = msg.get('attacker')
    move_used = msg.get('move_used')
    damage = msg.get('damage_dealt')
    defender_hp = msg.get('defender_hp_remaining')
    status = msg.get('status_message')
    print(color(f"--- Calculation Report (seq={seq}) ---", CYAN))
    print(f"Attacker: {color(attacker, MAGENTA)}")
    print(f"Move: {color(move_used, MAGENTA)}")
    print(f"Damage Dealt: {color(str(damage), RED)}")
    try:
        hp_val = int(defender_hp)
    except Exception:
        hp_val = None
    if hp_val is not None:
        if hp_val > 50:
            hp_col = GREEN
        elif hp_val > 20:
            hp_col = YELLOW
        else:
            hp_col = RED
        print(f"Defender HP Remaining: {color(str(hp_val), hp_col)}")
    else:
        print(f"Defender HP Remaining: {defender_hp}")
    if status:
        print(color(status, CYAN))
    print(color("-------------------------------", CYAN))


class HostPeer(BasePeer):
    def __init__(self, name: str, pokemon_manager: PokemonManager, pokemon_name: str, 
                 bind_ip='0.0.0.0', bind_port: int = 5001):
        super().__init__(name, bind_ip, bind_port)
        self.pokemon_manager = pokemon_manager
        if pokemon_name not in pokemon_manager.pokemon_db:
            raise ValueError(f"Pokemon '{pokemon_name}' not found in CSV")
        
        self.local_pokemon_name = pokemon_name
        self.local_pokemon_row = dict(pokemon_manager.pokemon_db[pokemon_name])
        # FIXED: Host always starts first
        self.battle_state = {
            'host_hp': self.local_pokemon_row['hp'],
            'joiner_hp': None,
            'turn': 'host',  # Host starts first
            'stat_boosts': None
        }
        self.seed = random.randint(0, 999999)
        self.peer_role = None
        self.joiner_pokemon_name: Optional[str] = None
        self.joiner_pokemon_row: Optional[Dict[str, Any]] = None
        self.last_announced_move: Optional[str] = None
        self.spectators = []  # List of spectator addresses

    def available_moves(self) -> list:
        return self.pokemon_manager.get_moves_for_pokemon(self.local_pokemon_name)

    def handle_message(self, msg: Dict[str, Any], addr: Tuple[str, int]):
        mt = msg.get('message_type')
        if mt == 'HANDSHAKE_REQUEST':
            if not VERBOSE_MODE:
                print(f"[Host] handshake request from {addr}")
            else:
                print(f"[Host] handshake request from {addr}")
            self.remote_addr = addr
            resp = {'message_type': 'HANDSHAKE_RESPONSE', 'seed': self.seed}
            self.send(resp, addr)
        elif mt == 'SPECTATOR_REQUEST':
            if not VERBOSE_MODE:
                print(f"[Host] spectator joined: {addr}")
            else:
                print(f"[Host] spectator joined: {addr}")
            self.spectators.append(addr)
            resp = {'message_type': 'HANDSHAKE_RESPONSE', 'seed': self.seed, 'role': 'spectator'}
            self.send(resp, addr)
            # Send current battle state to spectator
            if self.joiner_pokemon_row:
                self.send({
                    'message_type': 'BATTLE_SETUP',
                    'pokemon_name': self.joiner_pokemon_name,
                    'pokemon': self.joiner_pokemon_row
                }, addr)
                self.send({
                    'message_type': 'BATTLE_SETUP',
                    'pokemon_name': self.local_pokemon_name,
                    'pokemon': self.local_pokemon_row
                }, addr)
        elif mt == 'BATTLE_SETUP':
            if not VERBOSE_MODE:
                print("[Host] received BATTLE_SETUP")
            else:
                print("[Host] received BATTLE_SETUP")
            self.remote_addr = addr
            pdata = msg.get('pokemon', {})
            pname = msg.get('pokemon_name')
            if pname and pdata:
                self.battle_state['joiner_hp'] = int(pdata.get('hp', 0))
                self.battle_state['stat_boosts'] = msg.get('stat_boosts')
                self.joiner_pokemon_name = pname
                if pname in self.pokemon_manager.pokemon_db:
                    self.joiner_pokemon_row = dict(self.pokemon_manager.pokemon_db[pname])
                else:
                    self.joiner_pokemon_row = dict(pdata)
                print(f"[Host] joiner Pokemon: {pname} HP={self.battle_state['joiner_hp']}")
            
            my_setup = {
                'message_type': 'BATTLE_SETUP',
                'communication_mode': 'P2P',
                'pokemon_name': self.local_pokemon_name,
                'stat_boosts': {'special_attack_uses': 5, 'special_defense_uses': 5},
                'pokemon': {
                    'type1': self.local_pokemon_row['type1'],
                    'type2': self.local_pokemon_row['type2'],
                    'hp': self.local_pokemon_row['hp'],
                    'attack': self.local_pokemon_row['attack'],
                    'defense': self.local_pokemon_row['defense'],
                    'sp_attack': self.local_pokemon_row['sp_attack'],
                    'sp_defense': self.local_pokemon_row['sp_defense'],
                    'speed': self.local_pokemon_row['speed'],
                }
            }
            self.send(my_setup, addr)
            print("[Host] sent own BATTLE_SETUP")
            # FIXED: Send initial turn assignment
            turn_msg = {
                'message_type': 'TURN_ASSIGNMENT',
                'current_turn': 'host'  # Host starts first
            }
            self.send(turn_msg, addr)
            # Broadcast to spectators
            for spec in self.spectators:
                self.send(my_setup, spec)
                self.send(turn_msg, spec)
            self.print_turn_state()
        
        # BATTLE MESSAGE HANDLERS
        elif mt == 'ATTACK_ANNOUNCE':
            if not VERBOSE_MODE:
                print(f"[Host] ATTACK_ANNOUNCE from joiner: {msg.get('move_name')}")
            else:
                print(f"[Host] ATTACK_ANNOUNCE from joiner: {msg.get('move_name')}")
            
            # FIXED: Validate it's actually joiner's turn
            if self.battle_state['turn'] != 'joiner':
                print(f"[Host] ERROR: Joiner attacked out of turn! Current turn: {self.battle_state['turn']}")
                return
                
            # Defender (host) should send DEFENSE_ANNOUNCE
            resp = {'message_type': 'DEFENSE_ANNOUNCE'}
            self.send(resp, addr)
            # Broadcast attack to spectators
            for spec in self.spectators:
                self.send(msg, spec)
            
            # Compute damage: attacker is joiner, defender is host
            move_name = msg.get('move_name')
            move = MOVES.get(move_name)
            attacker_row = self.joiner_pokemon_row
            
            if not move or not attacker_row or not self.local_pokemon_row:
                print("[Host] missing data to calculate damage as defender")
            else:
                damage = self.pokemon_manager.calculate_damage(attacker_row, self.local_pokemon_row, move)
                # update host HP locally
                self.local_pokemon_row['hp'] = max(0, self.local_pokemon_row.get('hp', 0) - damage)
                self.battle_state['host_hp'] = self.local_pokemon_row['hp']
                report = {
                    'message_type': 'CALCULATION_REPORT',
                    'attacker': self.joiner_pokemon_name,
                    'move_used': move_name,
                    'damage_dealt': damage,
                    'defender_hp_remaining': self.local_pokemon_row.get('hp', 0),
                    'status_message': f"{self.local_pokemon_name} was hit by {move_name} for {damage} dmg"
                }
                self.send(report, addr)
                # Broadcast to spectators
                for spec in self.spectators:
                    self.send(report, spec)
                
        elif mt == 'DEFENSE_ANNOUNCE':
            # Host was the attacker; remote acknowledged and is ready
            move_name = getattr(self, 'last_announced_move', None)
            if not move_name:
                print("[Host] received DEFENSE_ANNOUNCE but no last_announced_move stored")
            else:
                move = MOVES.get(move_name)
                if not move or not getattr(self, 'joiner_pokemon_row', None):
                    print("[Host] missing move/joiner data to compute attack report")
                else:
                    damage = self.pokemon_manager.calculate_damage(self.local_pokemon_row, self.joiner_pokemon_row, move)
                    # update joiner local hp (host's view)
                    self.joiner_pokemon_row['hp'] = max(0, self.joiner_pokemon_row.get('hp', 0) - damage)
                    self.battle_state['joiner_hp'] = self.joiner_pokemon_row['hp']
                    report = {
                        'message_type': 'CALCULATION_REPORT',
                        'attacker': self.local_pokemon_name,
                        'move_used': move_name,
                        'damage_dealt': damage,
                        'defender_hp_remaining': self.joiner_pokemon_row.get('hp', 0),
                        'status_message': f"{self.local_pokemon_name} used {move_name}!"
                    }
                    self.send(report, addr)
                    # Broadcast to spectators
                    for spec in self.spectators:
                        self.send(report, spec)
                    
        elif mt == 'CALCULATION_REPORT':
            if not VERBOSE_MODE:
                print(f"[Host] CALCULATION_REPORT received")
            display_calc_report(msg)
            attacker = msg.get('attacker')
            move_name = msg.get('move_used')
            damage_dealt = int(msg.get('damage_dealt', 0))
            defender_hp = int(msg.get('defender_hp_remaining', 0))
            
            # Validate calculation
            expected = None
            if attacker == self.local_pokemon_name:
                # host attacked - this is joiner's report back to us
                if getattr(self, 'joiner_pokemon_row', None):
                    expected = self.pokemon_manager.calculate_damage(
                        self.local_pokemon_row, self.joiner_pokemon_row, MOVES.get(move_name, {}))
            else:
                # joiner attacked - this is our own report we sent
                if getattr(self, 'joiner_pokemon_row', None):
                    expected = self.pokemon_manager.calculate_damage(
                        self.joiner_pokemon_row, self.local_pokemon_row, MOVES.get(move_name, {}))
            
            if expected is None:
                print("[Host] cannot validate calculation_report (missing data)")
                return
                
            if expected == damage_dealt:
                # Update HP based on who was attacked
                if attacker == self.local_pokemon_name:
                    # Host attacked, update joiner HP
                    self.joiner_pokemon_row['hp'] = defender_hp
                    self.battle_state['joiner_hp'] = defender_hp
                else:
                    # Joiner attacked, update host HP
                    self.local_pokemon_row['hp'] = defender_hp
                    self.battle_state['host_hp'] = defender_hp
                
                self.send({'message_type': 'CALCULATION_CONFIRM'}, addr)
                
                # Check for game over conditions AFTER sending confirm
                if self.local_pokemon_row['hp'] <= 0:
                    winner = self.joiner_pokemon_name or 'Joiner'
                    game_over_msg = {
                        'message_type': 'GAME_OVER',
                        'winner': winner,
                        'reason': f"{self.local_pokemon_name} fainted!"
                    }
                    self.send(game_over_msg, addr)
                    # Broadcast to spectators
                    for spec in self.spectators:
                        self.send(game_over_msg, spec)
                    print(color(emphasize(f"\n=== GAME OVER ==="), RED))
                    print(color(f"Winner: {winner}", GREEN))
                    print(color(f"{self.local_pokemon_name} fainted!", RED))
                    self.battle_state['game_over'] = True
                    return
                elif self.joiner_pokemon_row and self.joiner_pokemon_row['hp'] <= 0:
                    winner = self.local_pokemon_name
                    game_over_msg = {
                        'message_type': 'GAME_OVER',
                        'winner': winner,
                        'reason': f"{self.joiner_pokemon_name} fainted!"
                    }
                    self.send(game_over_msg, addr)
                    # Broadcast to spectators
                    for spec in self.spectators:
                        self.send(game_over_msg, spec)
                    print(color(emphasize(f"\n=== GAME OVER ==="), RED))
                    print(color(f"Winner: {winner}", GREEN))
                    print(color(f"{self.joiner_pokemon_name} fainted!", RED))
                    self.battle_state['game_over'] = True
                    return
                
                # FIXED: Only switch turns when receiving joiner's report (joiner attacked us)
                # When we attacked, we already sent the report and will switch on CALCULATION_CONFIRM
                if attacker != self.local_pokemon_name:  # Joiner attacked
                    self.battle_state['turn'] = 'host'
                    turn_msg = {
                        'message_type': 'TURN_ASSIGNMENT', 
                        'current_turn': 'host'
                    }
                    self.send(turn_msg, addr)
                    # Broadcast to spectators
                    for spec in self.spectators:
                        self.send(turn_msg, spec)
                    self.print_turn_state()
            else:
                print(f"[Host] Damage mismatch: expected {expected}, got {damage_dealt}")
                my_calc = {
                    'message_type': 'RESOLUTION_REQUEST',
                    'attacker': attacker,
                    'move_used': move_name,
                    'damage_dealt': expected
                }
                self.send(my_calc, addr)
                
        elif mt == 'CALCULATION_CONFIRM':
            if not VERBOSE_MODE:
                print("[Host] CALCULATION_CONFIRM received")
            # Switch turn to joiner after host's attack is confirmed
            if self.battle_state['turn'] == 'host':
                self.battle_state['turn'] = 'joiner'
                turn_msg = {
                    'message_type': 'TURN_ASSIGNMENT',
                    'current_turn': 'joiner'
                }
                self.send(turn_msg, addr)
                # Broadcast to spectators
                for spec in self.spectators:
                    self.send(turn_msg, spec)
                self.print_turn_state()
            
        elif mt == 'RESOLUTION_REQUEST':
            print(f"[Host] RESOLUTION_REQUEST: {msg}")
            # For now, just accept the resolution and switch turns
            self.send({'message_type': 'CALCULATION_CONFIRM'}, addr)
            self.battle_state['turn'] = 'joiner'
            turn_msg = {
                'message_type': 'TURN_ASSIGNMENT',
                'current_turn': 'joiner'
            }
            self.send(turn_msg, addr)
            self.print_turn_state()
            
        # FIXED: Add TURN_ASSIGNMENT handler
        elif mt == 'TURN_ASSIGNMENT':
            new_turn = msg.get('current_turn')
            if not VERBOSE_MODE:
                print(f"[Host] Received turn assignment: {new_turn}")
            self.battle_state['turn'] = new_turn
            self.print_turn_state()
            
        elif mt == 'GAME_OVER':
            if not self.battle_state.get('game_over'):
                winner = msg.get('winner', 'Unknown')
                reason = msg.get('reason', 'Battle ended')
                print(color(emphasize(f"\n=== GAME OVER ==="), RED))
                print(color(f"Winner: {winner}", GREEN))
                print(color(reason, YELLOW))
                self.battle_state['game_over'] = True
            
        # CHAT MESSAGE HANDLER
        elif mt == 'CHAT_MESSAGE':
            sender = msg.get('sender_name', 'Unknown')
            content_type = msg.get('content_type')
            if content_type == 'TEXT':
                text = msg.get('message_text', '')
                print(f"[CHAT] {sender}: {text}")
            elif content_type == 'STICKER':
                print(f"[CHAT] {sender} sent a sticker")
            else:
                print(f"[CHAT] {sender}: [Unknown message type]")
                
        else:
            print(f"[Host] unknown message_type: {mt}")

    def print_turn_state(self):
        turn = self.battle_state.get('turn')
        if turn == 'host':
            print(color(emphasize(f"== YOUR TURN ({self.name}) =="), GREEN))
        else:
            print(color(emphasize(f"== OPPONENT'S TURN ({self.name}) =="), YELLOW))

    def announce_attack(self, move_name: str):
        if not self.remote_addr:
            print("[Host] no remote peer")
            return
            
        # FIXED: Validate it's actually host's turn
        if self.battle_state['turn'] != 'host':
            print(color("It's not your turn! Wait for opponent.", YELLOW))
            return
            
        self.last_announced_move = move_name
        payload = {'message_type': 'ATTACK_ANNOUNCE', 'move_name': move_name}
        self.send(payload, self.remote_addr)


class JoinerPeer(BasePeer):
    def __init__(self, name: str, pokemon_manager: PokemonManager, pokemon_name: str, 
                 host_ip: str, host_port: int, bind_port: int = 0):
        super().__init__(name, '0.0.0.0', bind_port)
        self.pokemon_manager = pokemon_manager
        if pokemon_name not in pokemon_manager.pokemon_db:
            raise ValueError(f"Pokemon '{pokemon_name}' not found")
        
        self.local_pokemon_name = pokemon_name
        self.local_pokemon_row = dict(pokemon_manager.pokemon_db[pokemon_name])
        self.host_addr = (host_ip, host_port)
        # FIXED: Joiner starts waiting for host's turn assignment
        self.battle_state = {'joiner_hp': self.local_pokemon_row['hp'], 
                           'host_hp': None, 'turn': None}  # No turn until assigned
        self.host_pokemon_name: Optional[str] = None
        self.host_pokemon_row: Optional[Dict[str, Any]] = None
        self.last_announced_move: Optional[str] = None

    def available_moves(self) -> list:
        return self.pokemon_manager.get_moves_for_pokemon(self.local_pokemon_name)

    def start_handshake(self):
        print("[Joiner] sending HANDSHAKE_REQUEST")
        self.send({'message_type': 'HANDSHAKE_REQUEST'}, self.host_addr)

    def handle_message(self, msg: Dict[str, Any], addr: Tuple[str, int]):
        mt = msg.get('message_type')
        if mt == 'HANDSHAKE_RESPONSE':
            if not VERBOSE_MODE:
                print(f"[Joiner] handshake response seed={msg.get('seed')}")
            else:
                print(f"[Joiner] handshake response seed={msg.get('seed')}")
            self.remote_addr = addr
            seed = msg.get('seed')
            random.seed(seed)
            setup = {
                'message_type': 'BATTLE_SETUP',
                'communication_mode': 'P2P',
                'pokemon_name': self.local_pokemon_name,
                'stat_boosts': {'special_attack_uses': 5, 'special_defense_uses': 5},
                'pokemon': {
                    'type1': self.local_pokemon_row['type1'],
                    'type2': self.local_pokemon_row['type2'],
                    'hp': self.local_pokemon_row['hp'],
                    'attack': self.local_pokemon_row['attack'],
                    'defense': self.local_pokemon_row['defense'],
                    'sp_attack': self.local_pokemon_row['sp_attack'],
                    'sp_defense': self.local_pokemon_row['sp_defense'],
                    'speed': self.local_pokemon_row['speed'],
                }
            }
            self.send(setup, self.host_addr)
            print("[Joiner] sent BATTLE_SETUP")
            
        elif mt == 'BATTLE_SETUP':
            if not VERBOSE_MODE:
                print("[Joiner] received host BATTLE_SETUP")
            else:
                print("[Joiner] received host BATTLE_SETUP")
            pdata = msg.get('pokemon', {})
            pname = msg.get('pokemon_name')
            self.battle_state['host_hp'] = int(pdata.get('hp', 0))
            # store host pokemon info
            self.host_pokemon_name = pname
            if pname in self.pokemon_manager.pokemon_db:
                self.host_pokemon_row = dict(self.pokemon_manager.pokemon_db[pname])
            else:
                self.host_pokemon_row = dict(pdata)
            print(f"[Joiner] host HP = {self.battle_state['host_hp']}")
            # Wait for turn assignment from host
            
        # FIXED: Add TURN_ASSIGNMENT handler
        elif mt == 'TURN_ASSIGNMENT':
            new_turn = msg.get('current_turn')
            if not VERBOSE_MODE:
                print(f"[Joiner] Received turn assignment: {new_turn}")
            self.battle_state['turn'] = new_turn
            self.print_turn_state()
            
        # BATTLE MESSAGE HANDLERS
        elif mt == 'ATTACK_ANNOUNCE':
            move_name = msg.get('move_name')
            if not VERBOSE_MODE:
                print(f"[Joiner] ATTACK_ANNOUNCE from host: {move_name}")
            else:
                print(f"[Joiner] ATTACK_ANNOUNCE from host: {move_name}")
            
            # FIXED: Validate it's actually host's turn
            if self.battle_state['turn'] != 'host':
                print(f"[Joiner] ERROR: Host attacked out of turn! Current turn: {self.battle_state['turn']}")
                return
                
            # Reply with DEFENSE_ANNOUNCE
            self.send({'message_type': 'DEFENSE_ANNOUNCE'}, addr)
            
            # Compute damage: attacker (host) -> defender (joiner)
            attacker_row = getattr(self, 'host_pokemon_row', None)
            move = MOVES.get(move_name)
            if not move or not attacker_row or not self.local_pokemon_row:
                print("[Joiner] missing data to calculate damage as defender")
            else:
                damage = self.pokemon_manager.calculate_damage(attacker_row, self.local_pokemon_row, move)
                # update local HP
                self.local_pokemon_row['hp'] = max(0, self.local_pokemon_row.get('hp', 0) - damage)
                self.battle_state['joiner_hp'] = self.local_pokemon_row['hp']
                report = {
                    'message_type': 'CALCULATION_REPORT',
                    'attacker': self.host_pokemon_name,
                    'move_used': move_name,
                    'damage_dealt': damage,
                    'defender_hp_remaining': self.local_pokemon_row.get('hp', 0),
                    'status_message': f"{self.local_pokemon_name} was hit by {move_name} for {damage} dmg"
                }
                self.send(report, addr)
                
        elif mt == 'DEFENSE_ANNOUNCE':
            # Joiner was attacker and remote acknowledged
            move_name = getattr(self, 'last_announced_move', None)
            if not move_name:
                print("[Joiner] got DEFENSE_ANNOUNCE but no last_announced_move stored")
            else:
                move = MOVES.get(move_name)
                if not move or not getattr(self, 'host_pokemon_row', None):
                    print("[Joiner] missing move/host data to compute attack report")
                else:
                    damage = self.pokemon_manager.calculate_damage(self.local_pokemon_row, self.host_pokemon_row, move)
                    self.host_pokemon_row['hp'] = max(0, self.host_pokemon_row.get('hp', 0) - damage)
                    self.battle_state['host_hp'] = self.host_pokemon_row['hp']
                    report = {
                        'message_type': 'CALCULATION_REPORT',
                        'attacker': self.local_pokemon_name,
                        'move_used': move_name,
                        'damage_dealt': damage,
                        'defender_hp_remaining': self.host_pokemon_row.get('hp', 0),
                        'status_message': f"{self.local_pokemon_name} used {move_name}!"
                    }
                    self.send(report, addr)
                    
        elif mt == 'CALCULATION_REPORT':
            if not VERBOSE_MODE:
                print(f"[Joiner] CALCULATION_REPORT received")
            display_calc_report(msg)
            attacker = msg.get('attacker')
            move_name = msg.get('move_used')
            damage_dealt = int(msg.get('damage_dealt', 0))
            defender_hp = int(msg.get('defender_hp_remaining', 0))
            
            expected = None
            if attacker == self.local_pokemon_name:
                # Joiner attacked
                if getattr(self, 'host_pokemon_row', None):
                    expected = self.pokemon_manager.calculate_damage(
                        self.local_pokemon_row, self.host_pokemon_row, MOVES.get(move_name, {}))
            else:
                # Host attacked
                if getattr(self, 'host_pokemon_row', None):
                    expected = self.pokemon_manager.calculate_damage(
                        self.host_pokemon_row, self.local_pokemon_row, MOVES.get(move_name, {}))
                        
            if expected is None:
                print("[Joiner] cannot validate calculation_report (missing data)")
                return
                
            if expected == damage_dealt:
                # Update HP based on who was attacked
                if attacker == self.local_pokemon_name:
                    # Joiner attacked, update host HP
                    self.host_pokemon_row['hp'] = defender_hp
                    self.battle_state['host_hp'] = defender_hp
                else:
                    # Host attacked, update joiner HP
                    self.local_pokemon_row['hp'] = defender_hp
                    self.battle_state['joiner_hp'] = defender_hp
                
                # Check for game over conditions FIRST
                if self.local_pokemon_row['hp'] <= 0 or (self.host_pokemon_row and self.host_pokemon_row['hp'] <= 0):
                    # Don't send CALCULATION_CONFIRM on game over, host will detect and send GAME_OVER
                    if self.local_pokemon_row['hp'] <= 0:
                        print(color(emphasize(f"\n=== GAME OVER ==="), RED))
                        print(color(f"Winner: {self.host_pokemon_name or 'Host'}", GREEN))
                        print(color(f"{self.local_pokemon_name} fainted!", RED))
                    else:
                        print(color(emphasize(f"\n=== GAME OVER ==="), RED))
                        print(color(f"Winner: {self.local_pokemon_name}", GREEN))
                        print(color(f"{self.host_pokemon_name} fainted!", RED))
                    self.battle_state['game_over'] = True
                    return
                
                self.send({'message_type': 'CALCULATION_CONFIRM'}, addr)
                
                # Turn switching is now handled by host via TURN_ASSIGNMENT
            else:
                print(f"[Joiner] Damage mismatch: expected {expected}, got {damage_dealt}")
                my_calc = {
                    'message_type': 'RESOLUTION_REQUEST',
                    'attacker': attacker,
                    'move_used': move_name,
                    'damage_dealt': expected
                }
                self.send(my_calc, addr)
                
        elif mt == 'CALCULATION_CONFIRM':
            if not VERBOSE_MODE:
                print("[Joiner] CALCULATION_CONFIRM received")
            # Turn switching is now handled by host via TURN_ASSIGNMENT
            
        elif mt == 'RESOLUTION_REQUEST':
            print("[Joiner] RESOLUTION_REQUEST received")
            # For now, just accept
            self.send({'message_type': 'CALCULATION_CONFIRM'}, self.host_addr)
            
        # CHAT MESSAGE HANDLER
        elif mt == 'CHAT_MESSAGE':
            sender = msg.get('sender_name', 'Unknown')
            content_type = msg.get('content_type')
            if content_type == 'TEXT':
                text = msg.get('message_text', '')
                print(f"[CHAT] {sender}: {text}")
            elif content_type == 'STICKER':
                print(f"[CHAT] {sender} sent a sticker")
            else:
                print(f"[CHAT] {sender}: [Unknown message type]")
                
        elif mt == 'GAME_OVER':
            if not self.battle_state.get('game_over'):
                winner = msg.get('winner', 'Unknown')
                reason = msg.get('reason', 'Battle ended')
                print(color(emphasize(f"\n=== GAME OVER ==="), RED))
                print(color(f"Winner: {winner}", GREEN))
                print(color(reason, YELLOW))
                self.battle_state['game_over'] = True
        else:
            print(f"[Joiner] unhandled: {mt}")

    def print_turn_state(self):
        turn = self.battle_state.get('turn')
        if turn == 'joiner':
            print(color(emphasize(f"== YOUR TURN ({self.name}) =="), GREEN))
        elif turn == 'host':
            print(color(emphasize(f"== OPPONENT'S TURN ({self.name}) =="), YELLOW))
        else:
            print(color(emphasize(f"== WAITING FOR TURN ASSIGNMENT =="), CYAN))

    def announce_attack(self, move_name: str):
        # FIXED: Validate it's actually joiner's turn
        if self.battle_state['turn'] != 'joiner':
            print(color("It's not your turn! Wait for opponent.", YELLOW))
            return
            
        self.last_announced_move = move_name
        payload = {'message_type': 'ATTACK_ANNOUNCE', 'move_name': move_name}
        self.send(payload, self.host_addr)


class SpectatorPeer(BasePeer):
    def __init__(self, name: str, pokemon_manager: PokemonManager, 
                 host_ip: str, host_port: int, bind_port: int = 0):
        super().__init__(name, bind_port=bind_port)
        self.pokemon_manager = pokemon_manager
        self.host_addr = (host_ip, host_port)
        self.host_pokemon_name = None
        self.joiner_pokemon_name = None
        self.host_hp = None
        self.joiner_hp = None

    def join_as_spectator(self):
        print("[Spectator] sending SPECTATOR_REQUEST")
        self.send({'message_type': 'SPECTATOR_REQUEST'}, self.host_addr)

    def handle_message(self, msg: Dict[str, Any], addr: Tuple[str, int]):
        mt = msg.get('message_type')
        if mt == 'HANDSHAKE_RESPONSE' and msg.get('role') == 'spectator':
            print("[Spectator] joined as spectator")
        elif mt == 'BATTLE_SETUP':
            pname = msg.get('pokemon_name')
            pdata = msg.get('pokemon', {})
            hp = pdata.get('hp')
            if not self.host_pokemon_name:
                self.host_pokemon_name = pname
                self.host_hp = hp
                print(f"[Spectator] Host Pokemon: {pname} (HP: {hp})")
            else:
                self.joiner_pokemon_name = pname
                self.joiner_hp = hp
                print(f"[Spectator] Joiner Pokemon: {pname} (HP: {hp})")
        elif mt == 'TURN_ASSIGNMENT':
            turn = msg.get('current_turn')
            print(color(f"[Spectator] Turn: {turn.upper()}", CYAN))
        elif mt == 'ATTACK_ANNOUNCE':
            move = msg.get('move_name')
            print(color(f"[Spectator] Attack announced: {move}", YELLOW))
        elif mt == 'CALCULATION_REPORT':
            display_calc_report(msg)
            defender_hp = msg.get('defender_hp_remaining')
            attacker = msg.get('attacker')
            if attacker == self.host_pokemon_name:
                self.joiner_hp = defender_hp
            else:
                self.host_hp = defender_hp
            print(f"[Spectator] Current HP - Host: {self.host_hp}, Joiner: {self.joiner_hp}")
        elif mt == 'GAME_OVER':
            winner = msg.get('winner', 'Unknown')
            reason = msg.get('reason', 'Battle ended')
            print(color(emphasize(f"\n=== GAME OVER ==="), RED))
            print(color(f"Winner: {winner}", GREEN))
            print(color(reason, YELLOW))
        elif mt == 'CHAT_MESSAGE':
            sender = msg.get('sender_name', 'Unknown')
            content_type = msg.get('content_type')
            if content_type == 'TEXT':
                text = msg.get('message_text', '')
                print(f"[CHAT] {sender}: {text}")
            elif content_type == 'STICKER':
                print(f"[CHAT] {sender} sent a sticker")
            else:
                print(f"[CHAT] {sender}: [Unknown message type]")
        else:
            if VERBOSE_MODE:
                print(f"[Spectator] observed: {mt}")