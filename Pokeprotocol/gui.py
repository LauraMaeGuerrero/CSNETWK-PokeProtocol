"""
Tkinter GUI integration for PokeProtocol P2P project.
Fixed version with better Pokemon-style interface and no PIL dependency.
"""

import base64
import threading
import queue
import io
import os
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

# Import your project modules
try:
    from pokemon import PokemonManager, MOVES
    from peers import HostPeer, JoinerPeer, SpectatorPeer
except ImportError as e:
    print(f"Import error: {e}")
    # Create dummy classes for testing
    class PokemonManager:
        def get_pokemon_list(self, limit=50): return ["Pikachu", "Charmander", "Bulbasaur", "Squirtle"]
        def get_moves_for_pokemon(self, name): return ["Tackle", "Growl", "Quick Attack", "Thunder Shock"]
        def get_pokemon(self, name): return {"hp": 100}
    
    class HostPeer: 
        def __init__(self, *args, **kwargs): pass
        def start_receiving(self): pass
        def handle_message(self, msg, addr): pass
        def send(self, payload, dest): pass
        def stop(self): pass
        def announce_attack(self, move): pass
    
    class JoinerPeer: 
        def __init__(self, *args, **kwargs): pass 
        def start_receiving(self): pass
        def start_handshake(self): pass
        def handle_message(self, msg, addr): pass
        def send(self, payload, dest): pass
        def stop(self): pass
        def announce_attack(self, move): pass
    
    class SpectatorPeer: 
        def __init__(self, *args, **kwargs): pass
        def start_receiving(self): pass
        def join_as_spectator(self): pass
        def handle_message(self, msg, addr): pass
        def send(self, payload, dest): pass
        def stop(self): pass

# Safe attribute access utility
def safe_get(d, k, default=None):
    try:
        if d is None:
            return default
        if hasattr(d, 'get'):
            return d.get(k, default)
        elif hasattr(d, k):
            return getattr(d, k, default)
        else:
            return default
    except Exception:
        return default

# Pokemon-style colors
POKEMON_COLORS = {
    'red': '#FF0000',
    'blue': '#3B4CCA',
    'yellow': '#FFDE00',
    'green': '#00FF00',
    'white': '#FFFFFF',
    'black': '#000000',
    'hp_green': '#58D68D',
    'hp_yellow': '#F4D03F',
    'hp_red': '#E74C3C',
    'sky_blue': '#87CEEB',
    'grass_green': '#7CB342',
    'battle_bg': '#B8E6B8'
}

class PokeGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PokeProtocol P2P Battle")
        self.state('zoomed')
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Configure root window background
        self.configure(bg=POKEMON_COLORS['sky_blue'])

        self.verbose_mode = tk.BooleanVar(value=False)

        try:
            self.pm = PokemonManager()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Pokemon data: {e}")
            self.pm = PokemonManager()
            
        self.peer = None
        self.peer_role = None
        self.gui_queue = queue.Queue()
        self._orig_handle = None

        # UI frames
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.build_main_menu()

        self.battle_frame = None
        self.current_turn = None
        self.sprite_cache = {}
        
        # Canvas sprite IDs
        self.opp_sprite_id = None
        self.player_sprite_id = None
        self.bg_image_id = None
        self.player_trainer_id = None  # Add player trainer sprite ID
        self.opp_trainer_id = None     # Add opponent trainer sprite ID

        # Periodic updates
        self.after(100, self.process_queue)
        self.after(500, self.update_hp_display)
        
        self.setup_sprite_directories()

    def setup_sprite_directories(self):
        """Create sprite directories if they don't exist"""
        sprite_dirs = ["sprites", os.path.join("sprites", "pokemon")]
        
        for dir_path in sprite_dirs:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                    print(f"Created directory: {dir_path}")
                except Exception as e:
                    print(f"Error creating directory {dir_path}: {e}")

    def get_pokemon_sprite(self, pokemon_name):
        """Get Pokemon sprite - native GIF only (no PIL)"""
        if not pokemon_name:
            return None
        
        if pokemon_name in self.sprite_cache:
            return self.sprite_cache[pokemon_name]
        
        sprite = self._load_gif_sprite(pokemon_name)
        if sprite:
            self.sprite_cache[pokemon_name] = sprite
            return sprite
        
        return None

    def get_trainer_sprite(self, sprite_filename):
        """Get trainer sprite (player1.gif, player2.gif, spectator.gif) - ENLARGED"""
        cache_key = f"trainer_{sprite_filename}"
        
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]
        
        # Look in sprites folder
        sprite_path = os.path.join("sprites", sprite_filename)
        
        if os.path.exists(sprite_path):
            try:
                photo = tk.PhotoImage(file=sprite_path)
                
                # Enlarge the sprite by 2x using subsample/zoom
                try:
                    # Create enlarged version - zoom by 2x
                    enlarged = photo.zoom(2, 2)
                    self.sprite_cache[cache_key] = enlarged
                    print(f"Loaded and enlarged trainer sprite: {sprite_path} (2x)")
                    return enlarged
                except Exception as zoom_error:
                    print(f"Could not zoom sprite, using original: {zoom_error}")
                    self.sprite_cache[cache_key] = photo
                    return photo
                    
            except Exception as e:
                print(f"Error loading trainer sprite {sprite_path}: {e}")
                return None
        else:
            print(f"Trainer sprite not found: {sprite_path}")
            return None

    def _load_gif_sprite(self, pokemon_name):
        """Load GIF sprite using native Tkinter (no PIL) - ENLARGED"""
        clean_name = pokemon_name.strip().lower()
        
        possible_files = [
            f"{clean_name}.gif",
            f"{pokemon_name}.gif",
            f"{clean_name.replace(' ', '')}.gif",
            f"{clean_name.replace(' ', '_')}.gif",
        ]
        
        possible_dirs = ["sprites", os.path.join("sprites", "pokemon")]
        
        for sprite_dir in possible_dirs:
            if not os.path.exists(sprite_dir):
                continue
                
            for sprite_file in possible_files:
                sprite_path = os.path.join(sprite_dir, sprite_file)
                if os.path.exists(sprite_path):
                    try:
                        photo = tk.PhotoImage(file=sprite_path)
                        
                        # Enlarge Pokemon sprites by 2x
                        try:
                            enlarged = photo.zoom(2, 2)
                            print(f"Loaded and enlarged Pokemon GIF: {sprite_path} (2x)")
                            return enlarged
                        except Exception as zoom_error:
                            print(f"Could not zoom sprite, using original: {zoom_error}")
                            print(f"Loaded GIF: {sprite_path}")
                            return photo
                            
                    except Exception as e:
                        print(f"Error loading GIF sprite {sprite_path}: {e}")
                        continue
        return None

    # ========== MAIN MENU ==========
    def build_main_menu(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

        # Main container with Pokemon-style background
        container = tk.Frame(self.main_frame, bg=POKEMON_COLORS['sky_blue'])
        container.pack(fill=tk.BOTH, expand=True)

        # Title section
        title_frame = tk.Frame(container, bg=POKEMON_COLORS['sky_blue'])
        title_frame.pack(pady=40)

        # Try to load title image
        if os.path.exists("PokeProtocolTitle.gif"):
            try:
                title_photo = tk.PhotoImage(file="PokeProtocolTitle.gif")
                title_label = tk.Label(title_frame, image=title_photo, bg=POKEMON_COLORS['sky_blue'])
                title_label.image = title_photo
                title_label.pack(pady=20)
            except:
                self._create_text_title(title_frame)
        else:
            self._create_text_title(title_frame)

        # Menu buttons with Pokemon styling
        button_frame = tk.Frame(container, bg=POKEMON_COLORS['sky_blue'])
        button_frame.pack(pady=20)

        button_style = {
            'font': ('Pokemon GB', 14, 'bold'),
            'width': 25,
            'height': 2,
            'relief': tk.RAISED,
            'bd': 4,
            'cursor': 'hand2'
        }

        tk.Button(button_frame, text="HOST GAME", command=self.show_host_setup,
                 bg=POKEMON_COLORS['red'], fg='white', **button_style).pack(pady=8)
        tk.Button(button_frame, text="JOIN GAME", command=self.show_join_setup,
                 bg=POKEMON_COLORS['blue'], fg='white', **button_style).pack(pady=8)
        tk.Button(button_frame, text="SPECTATE", command=self.show_spec_setup,
                 bg=POKEMON_COLORS['yellow'], fg='black', **button_style).pack(pady=8)
        tk.Button(button_frame, text="EXIT", command=self.on_close,
                 bg='#555555', fg='white', **button_style).pack(pady=8)

    def _create_text_title(self, parent):
        """Create ASCII art title"""
        title_text = """
    ╔═══════════════════════════════╗
    ║   POKEPROTOCOL P2P BATTLE    ║
    ╚═══════════════════════════════╝
        """
        
        title_label = tk.Label(
            parent, 
            text=title_text,
            font=("Courier New", 16, "bold"),
            fg=POKEMON_COLORS['red'],
            bg=POKEMON_COLORS['sky_blue'],
            justify=tk.CENTER
        )
        title_label.pack()

    # ========== SETUP DIALOGS ==========
    def show_host_setup(self):
        dlg = tk.Toplevel(self)
        dlg.title("Host Setup")
        dlg.geometry("400x500")
        dlg.grab_set()

        ttk.Label(dlg, text="Player name:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=8)
        name_entry = ttk.Entry(dlg, width=25)
        name_entry.insert(0, "HostPlayer")
        name_entry.grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Bind port:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=8)
        port_entry = ttk.Entry(dlg, width=25)
        port_entry.insert(0, "5001")
        port_entry.grid(row=1, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Choose Pokemon:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=8)
        p_list = tk.Listbox(dlg, height=10, selectmode=tk.SINGLE, exportselection=False, width=25)
        pokes = self.pm.get_pokemon_list(50)
        for p in pokes:
            p_list.insert(tk.END, p)
        p_list.selection_set(0)
        p_list.grid(row=2, column=1, padx=10, pady=8)

        verbose_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dlg, text="Enable Verbose Mode", variable=verbose_var).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, padx=10, pady=8)

        def on_start():
            pname = name_entry.get().strip() or "HostPlayer"
            try:
                port = int(port_entry.get().strip())
            except:
                port = 5001
            sel = p_list.curselection()
            if not sel:
                messagebox.showerror("Error", "Pick a Pokemon!")
                return
            pokemon = pokes[sel[0]]
            self.set_verbose_mode(verbose_var.get())
            dlg.destroy()
            self.start_host(pname, pokemon, port)

        tk.Button(dlg, text="START HOST", command=on_start, bg=POKEMON_COLORS['red'],
                 fg='white', font=('Arial', 12, 'bold'), width=20, height=2).grid(
                     row=4, column=0, columnspan=2, pady=15)

    def show_join_setup(self):
        dlg = tk.Toplevel(self)
        dlg.title("Join Setup")
        dlg.geometry("400x550")
        dlg.grab_set()

        ttk.Label(dlg, text="Player name:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=8)
        name_entry = ttk.Entry(dlg, width=25)
        name_entry.insert(0, "JoinerPlayer")
        name_entry.grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Host IP:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=8)
        ip_entry = ttk.Entry(dlg, width=25)
        ip_entry.insert(0, "127.0.0.1")
        ip_entry.grid(row=1, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Host port:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=8)
        port_entry = ttk.Entry(dlg, width=25)
        port_entry.insert(0, "5001")
        port_entry.grid(row=2, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Local port (0=random):").grid(row=3, column=0, sticky=tk.W, padx=10, pady=8)
        bind_entry = ttk.Entry(dlg, width=25)
        bind_entry.insert(0, "0")
        bind_entry.grid(row=3, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Choose Pokemon:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=8)
        p_list = tk.Listbox(dlg, height=10, selectmode=tk.SINGLE, exportselection=False, width=25)
        pokes = self.pm.get_pokemon_list(50)
        for p in pokes:
            p_list.insert(tk.END, p)
        p_list.selection_set(0)
        p_list.grid(row=4, column=1, padx=10, pady=8)

        verbose_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dlg, text="Enable Verbose Mode", variable=verbose_var).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, padx=10, pady=8)

        def on_join():
            pname = name_entry.get().strip() or "JoinerPlayer"
            host_ip = ip_entry.get().strip() or "127.0.0.1"
            try:
                host_port = int(port_entry.get().strip())
            except:
                host_port = 5001
            try:
                bind_port = int(bind_entry.get().strip())
            except:
                bind_port = 0
            sel = p_list.curselection()
            if not sel:
                messagebox.showerror("Error", "Pick a Pokemon!")
                return
            pokemon = pokes[sel[0]]
            self.set_verbose_mode(verbose_var.get())
            dlg.destroy()
            self.start_joiner(pname, pokemon, host_ip, host_port, bind_port)

        tk.Button(dlg, text="JOIN GAME", command=on_join, bg=POKEMON_COLORS['blue'],
                 fg='white', font=('Arial', 12, 'bold'), width=20, height=2).grid(
                     row=6, column=0, columnspan=2, pady=15)

    def show_spec_setup(self):
        dlg = tk.Toplevel(self)
        dlg.title("Spectator Setup")
        dlg.geometry("400x300")
        dlg.grab_set()

        ttk.Label(dlg, text="Spectator name:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=8)
        name_entry = ttk.Entry(dlg, width=25)
        name_entry.insert(0, "Spectator")
        name_entry.grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Host IP:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=8)
        ip_entry = ttk.Entry(dlg, width=25)
        ip_entry.insert(0, "127.0.0.1")
        ip_entry.grid(row=1, column=1, padx=10, pady=8)

        ttk.Label(dlg, text="Host port:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=8)
        port_entry = ttk.Entry(dlg, width=25)
        port_entry.insert(0, "5001")
        port_entry.grid(row=2, column=1, padx=10, pady=8)

        def on_spec():
            name = name_entry.get().strip() or "Spectator"
            host_ip = ip_entry.get().strip() or "127.0.0.1"
            try:
                host_port = int(port_entry.get().strip())
            except:
                host_port = 5001
            dlg.destroy()
            self.start_spectator(name, host_ip, host_port)

        tk.Button(dlg, text="SPECTATE", command=on_spec, bg=POKEMON_COLORS['yellow'],
                 fg='black', font=('Arial', 12, 'bold'), width=20, height=2).grid(
                     row=3, column=0, columnspan=2, pady=15)

    # ========== START PEERS ==========
    def start_host(self, player_name, pokemon_name, port):
        try:
            host = HostPeer("Player 1", self.pm, pokemon_name, bind_port=port)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start host: {e}")
            return
        self.peer = host
        self.peer_role = 'host'
        host.start_receiving()
        self.hook_peer_for_gui(host)
        self.build_battle_ui(local_name=pokemon_name, remote_name="Waiting...")
        self.gui_queue.put(("info", f"Hosting as Player 1 on port {port}"))
        self.console_log(f"[SYSTEM] Host started as Player 1 on port {port} with {pokemon_name}")

    def start_joiner(self, player_name, pokemon_name, host_ip, host_port, bind_port):
        try:
            joiner = JoinerPeer("Player 2", self.pm, pokemon_name, host_ip, host_port, bind_port)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start joiner: {e}")
            return
        self.peer = joiner
        self.peer_role = 'joiner'
        joiner.start_receiving()
        self.hook_peer_for_gui(joiner)
        joiner.start_handshake()
        self.build_battle_ui(local_name=pokemon_name, remote_name="Waiting...")
        self.gui_queue.put(("info", "Joiner handshake sent; waiting for host..."))
        self.console_log(f"[SYSTEM] Joiner started as Player 2 connecting to {host_ip}:{host_port} with {pokemon_name}")

    def start_spectator(self, spec_name, host_ip, host_port):
        try:
            spect = SpectatorPeer(spec_name, self.pm, host_ip, host_port)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot start spectator: {e}")
            return
        self.peer = spect
        self.peer_role = 'spectator'
        spect.start_receiving()
        self.hook_peer_for_gui(spect)
        spect.join_as_spectator()
        self.build_battle_ui(local_name="(spectator)", remote_name="(observing)")
        self.gui_queue.put(("info", "Spectating..."))

    def hook_peer_for_gui(self, peer):
        self._orig_handle = peer.handle_message

        def new_handle(msg, addr, _orig=self._orig_handle, _peer=peer):
            try:
                _orig(msg, addr)
            except Exception as e:
                print("Error in original handle:", e)
            try:
                self.gui_queue.put(("network_msg", msg, addr, _peer))
            except Exception as e:
                print("gui_queue put error:", e)

        peer.handle_message = new_handle

    # ========== BATTLE UI ==========
    def build_battle_ui(self, local_name, remote_name):
        for w in self.main_frame.winfo_children():
            w.destroy()

        self.battle_frame = tk.Frame(self.main_frame, bg=POKEMON_COLORS['battle_bg'])
        self.battle_frame.pack(fill=tk.BOTH, expand=True)

        # Battle canvas (main battle scene)
        self.battle_canvas = tk.Canvas(
            self.battle_frame, 
            bg=POKEMON_COLORS['battle_bg'],
            highlightthickness=0
        )
        self.battle_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Load background
        self.load_battle_background()

        # Bind resize event
        self.battle_canvas.bind('<Configure>', self.on_canvas_resize)

        # Bottom UI panel
        bottom_panel = tk.Frame(self.battle_frame, bg='white', relief=tk.RIDGE, bd=3)
        bottom_panel.pack(fill=tk.X, padx=10, pady=10)

        # Left: Move buttons (2x2 grid)
        moves_frame = tk.Frame(bottom_panel, bg='white')
        moves_frame.pack(side=tk.LEFT, padx=15, pady=10)

        tk.Label(moves_frame, text="MOVES", font=('Arial', 12, 'bold'), bg='white').grid(
            row=0, column=0, columnspan=2, pady=5)

        self.move_buttons = []
        move_colors = [POKEMON_COLORS['red'], POKEMON_COLORS['blue'], 
                      POKEMON_COLORS['yellow'], POKEMON_COLORS['green']]
        
        for i in range(4):
            btn = tk.Button(
                moves_frame, 
                text=f"Move {i+1}",
                command=lambda idx=i: self.on_move_click(idx),
                width=15,
                height=2,
                font=('Arial', 10, 'bold'),
                bg=move_colors[i],
                fg='white' if i < 2 else 'black',
                relief=tk.RAISED,
                bd=3,
                cursor='hand2'
            )
            btn.grid(row=1 + (i//2), column=(i%2), padx=5, pady=5)
            self.move_buttons.append(btn)

        # Right: Battle log
        log_frame = tk.Frame(bottom_panel, bg='white')
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=10)

        tk.Label(log_frame, text="BATTLE LOG", font=('Arial', 12, 'bold'), bg='white').pack()

        chat_container = tk.Frame(log_frame, bg='white')
        chat_container.pack(fill=tk.BOTH, expand=True)

        self.chat_text = tk.Text(chat_container, state=tk.DISABLED, height=6, wrap=tk.WORD,
                                font=('Courier', 9), bg='#F0F0F0')
        scrollbar = ttk.Scrollbar(chat_container, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons
        control_frame = tk.Frame(log_frame, bg='white')
        control_frame.pack(fill=tk.X, pady=5)

        tk.Button(control_frame, text="Send Text", command=self.open_chat_text,
                 bg='#4CAF50', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=3)
        tk.Button(control_frame, text="Send Sticker", command=self.open_chat_sticker,
                 bg='#2196F3', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=3)
        tk.Button(control_frame, text="Return to Menu", command=self.stop_and_return,
                 bg='#F44336', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.RIGHT, padx=3)

        # Top status bar
        self.status_bar = tk.Frame(self.battle_frame, bg='#2C3E50', height=30)
        self.status_bar.pack(side=tk.TOP, fill=tk.X)

        self.turn_label = tk.Label(self.status_bar, text="Turn: Waiting...", 
                                   font=('Arial', 11, 'bold'), fg='white', bg='#2C3E50')
        self.turn_label.pack(side=tk.LEFT, padx=15)

        self.info_label = tk.Label(self.status_bar, text="Info: Ready", 
                                   font=('Arial', 10), fg='white', bg='#2C3E50')
        self.info_label.pack(side=tk.LEFT, padx=15)

        self.verbose_status_label = tk.Label(self.status_bar, text="Verbose: OFF",
                                             font=('Arial', 9), fg='#BDC3C7', bg='#2C3E50')
        self.verbose_status_label.pack(side=tk.RIGHT, padx=15)

        # HP bars and Pokemon info will be drawn on canvas
        self.create_pokemon_info_on_canvas()

        # Initialize
        self.after(100, self.refresh_moves_from_peer)
        self.after(200, self.update_sprites)

    def load_battle_background(self):
        """Load battle background"""
        if os.path.exists("battleground.gif"):
            try:
                self.bg_photo = tk.PhotoImage(file="battleground.gif")
                self.bg_photo = self.bg_photo.zoom(2, 2)  # Makes it 2x bigger
                self.bg_image_id = self.battle_canvas.create_image(
                    400, 300, image=self.bg_photo, anchor=tk.CENTER)
                print("Battle background loaded")
            except Exception as e:
                print(f"Error loading background: {e}")
                self.draw_default_background()
        else:
            self.draw_default_background()

    def draw_default_background(self):
        """Draw a Pokemon-style battle background matching the reference image"""
        # Sky gradient (light blue to white at horizon)
        self.battle_canvas.create_rectangle(0, 0, 2000, 250, fill='#87CEEB', outline='')
        self.battle_canvas.create_rectangle(0, 250, 2000, 300, fill='#B0E0E6', outline='')
        
        # Ground - light green grass
        self.battle_canvas.create_rectangle(0, 300, 2000, 600, fill='#90C865', outline='')
        
        # Opponent's battle platform (top grass oval - larger and more visible)
        # Outer shadow/border
        self.battle_canvas.create_oval(550, 220, 850, 280, fill='#7CB342', outline='#5E9025', width=3)
        # Inner platform
        self.battle_canvas.create_oval(560, 228, 840, 272, fill='#8FD14F', outline='')
        
        # Player's battle platform (bottom grass oval - larger)
        # Outer shadow/border
        self.battle_canvas.create_oval(100, 450, 450, 520, fill='#6B9E30', outline='#527A25', width=3)
        # Inner platform  
        self.battle_canvas.create_oval(110, 458, 440, 512, fill='#7CB342', outline='')

    def create_pokemon_info_on_canvas(self):
        """Create Pokemon info boxes on canvas"""
        # Opponent info box (top right)
        self.opp_info_bg = self.battle_canvas.create_rectangle(
            480, 30, 730, 120, fill='white', outline='black', width=3)
        
        if self.peer_role == 'host':
            opp_name = "PLAYER 2"
        elif self.peer_role == 'joiner':
            opp_name = "PLAYER 1"
        else:
            opp_name = "OPPONENT"
            
        self.opp_name_text = self.battle_canvas.create_text(
            490, 45, text=opp_name, anchor=tk.W, font=('Arial', 12, 'bold'))
        self.opp_pokemon_text = self.battle_canvas.create_text(
            490, 70, text="???", anchor=tk.W, font=('Arial', 10))
        
        # HP bar for opponent
        self.opp_hp_bg = self.battle_canvas.create_rectangle(
            490, 90, 720, 105, fill='#E0E0E0', outline='black', width=2)
        self.opp_hp_bar = self.battle_canvas.create_rectangle(
            490, 90, 720, 105, fill=POKEMON_COLORS['hp_green'], outline='')
        self.opp_hp_text = self.battle_canvas.create_text(
            605, 97, text="HP: ???", font=('Arial', 9, 'bold'))

        # Player info box (bottom left) - MOVED HIGHER to be above trainer sprite
        self.player_info_bg = self.battle_canvas.create_rectangle(
            50, 280, 300, 370, fill='white', outline='black', width=3)
        
        if self.peer_role == 'host':
            player_name = "PLAYER 1"
        elif self.peer_role == 'joiner':
            player_name = "PLAYER 2"
        else:
            player_name = "YOU"
            
        self.player_name_text = self.battle_canvas.create_text(
            60, 295, text=player_name, anchor=tk.W, font=('Arial', 12, 'bold'))
        self.player_pokemon_text = self.battle_canvas.create_text(
            60, 320, text="???", anchor=tk.W, font=('Arial', 10))
        
        # HP bar for player
        self.player_hp_bg = self.battle_canvas.create_rectangle(
            60, 340, 290, 355, fill='#E0E0E0', outline='black', width=2)
        self.player_hp_bar = self.battle_canvas.create_rectangle(
            60, 340, 290, 355, fill=POKEMON_COLORS['hp_green'], outline='')
        self.player_hp_text = self.battle_canvas.create_text(
            175, 347, text="HP: ???", font=('Arial', 9, 'bold'))

    def on_canvas_resize(self, event=None):
        """Handle canvas resize - reposition all elements"""
        if not hasattr(self, 'battle_canvas'):
            return
            
        try:
            width = self.battle_canvas.winfo_width()
            height = self.battle_canvas.winfo_height()
            
            if width < 50 or height < 50:
                return
            
            # Reposition background
            if hasattr(self, 'bg_image_id') and self.bg_image_id:
                self.battle_canvas.coords(self.bg_image_id, width/2, height/2)
            
            # Reposition opponent info (top right)
            if hasattr(self, 'opp_info_bg'):
                self.battle_canvas.coords(self.opp_info_bg, 
                    width-270, 30, width-20, 120)
                self.battle_canvas.coords(self.opp_name_text, width-260, 45)
                self.battle_canvas.coords(self.opp_pokemon_text, width-260, 70)
                self.battle_canvas.coords(self.opp_hp_bg, width-260, 90, width-30, 105)
                
                # Update HP bar within new bounds
                hp_percent = self.get_remote_hp_percent()
                bar_width = 230 * (hp_percent / 100)
                self.battle_canvas.coords(self.opp_hp_bar,
                    width-260, 90, width-260+bar_width, 105)
                self.battle_canvas.coords(self.opp_hp_text, width-145, 97)
            
            # Reposition sprites
            self.update_sprites()
            
        except Exception as e:
            print(f"Error in canvas resize: {e}")

    def update_sprites(self):
        """Update Pokemon AND player trainer sprites on canvas"""
        if not self.peer or not hasattr(self, 'battle_canvas'):
            return
        
        width = self.battle_canvas.winfo_width()
        height = self.battle_canvas.winfo_height()
        
        if width < 50:
            width = 800
        if height < 50:
            height = 600
        
        # Player trainer sprite 
        player_trainer_x = width * 0.10
        player_trainer_y = height * 0.65
        
        # Player Pokemon (slightly behind and to the right of trainer, on lower platform edge)
        player_pokemon_x = width * 0.22
        player_pokemon_y = height * 0.50
        
        # Opponent trainer sprite (far right, on the upper platform with Pokemon)
        opp_trainer_x = width * 0.82
        opp_trainer_y = height * 0.30
        
        # Opponent Pokemon (left of opponent trainer, on upper platform)
        opp_pokemon_x = width * 0.65
        opp_pokemon_y = height * 0.32
        width = 800
        if height < 50:
            height = 600
        
        # Opponent Pokemon (on the top grass platform - more centered and visible)
        opp_pokemon_x = width * 1.10
        opp_pokemon_y = height * 0.50
        
        # Player Pokemon (on the bottom grass platform - back position)
        player_pokemon_x = width * 0.80
        player_pokemon_y = height * 0.85
        
        # Player trainer sprite (in the foreground, front-left like the reference)
        player_trainer_x = width * 0.3
        player_trainer_y = height * 0.85
        
        # Opponent trainer sprite (on their platform, next to their Pokemon)
        opp_trainer_x = width * 1.60
        opp_trainer_y = height * 0.35

        # Update opponent Pokemon sprite
        try:
            remote_pokemon_name = self.get_remote_pokemon_name()
            if remote_pokemon_name and remote_pokemon_name != "???" and remote_pokemon_name != "Waiting...":
                sprite = self.get_pokemon_sprite(remote_pokemon_name)
                
                if self.opp_sprite_id:
                    self.battle_canvas.delete(self.opp_sprite_id)
                
                if sprite:
                    self.opp_sprite_id = self.battle_canvas.create_image(
                        opp_pokemon_x, opp_pokemon_y, image=sprite, anchor=tk.CENTER, tags='opp_pokemon')
                    self.battle_canvas.opp_sprite_ref = sprite
                else:
                    # Text fallback
                    self.opp_sprite_id = self.battle_canvas.create_text(
                        opp_pokemon_x, opp_pokemon_y, text=remote_pokemon_name[:12],
                        font=('Arial', 16, 'bold'), fill='#333333', tags='opp_pokemon')
                
                # Update name on canvas
                self.battle_canvas.itemconfig(self.opp_pokemon_text, text=remote_pokemon_name)
        except Exception as e:
            print(f"Error updating opponent sprite: {e}")

        # Update player Pokemon sprite
        try:
            local_pokemon_name = getattr(self.peer, "local_pokemon_name", None)
            if local_pokemon_name:
                sprite = self.get_pokemon_sprite(local_pokemon_name)
                
                if self.player_sprite_id:
                    self.battle_canvas.delete(self.player_sprite_id)
                
                if sprite:
                    self.player_sprite_id = self.battle_canvas.create_image(
                        player_pokemon_x, player_pokemon_y, image=sprite, anchor=tk.CENTER, tags='player_pokemon')
                    self.battle_canvas.player_sprite_ref = sprite
                else:
                    # Text fallback
                    self.player_sprite_id = self.battle_canvas.create_text(
                        player_pokemon_x, player_pokemon_y, text=local_pokemon_name[:12],
                        font=('Arial', 16, 'bold'), fill='#333333', tags='player_pokemon')
                
                # Update name on canvas
                self.battle_canvas.itemconfig(self.player_pokemon_text, text=local_pokemon_name)
        except Exception as e:
            print(f"Error updating player sprite: {e}")
        
        # Update player trainer sprite
        try:
            if self.peer_role == 'host':
                trainer_sprite = self.get_trainer_sprite('player1.gif')
            elif self.peer_role == 'joiner':
                trainer_sprite = self.get_trainer_sprite('player2.gif')
            else:
                trainer_sprite = self.get_trainer_sprite('spectator.gif')
            
            if hasattr(self, 'player_trainer_id') and self.player_trainer_id:
                self.battle_canvas.delete(self.player_trainer_id)
            
            if trainer_sprite:
                self.player_trainer_id = self.battle_canvas.create_image(
                    player_trainer_x, player_trainer_y, image=trainer_sprite, 
                    anchor=tk.CENTER, tags='player_trainer')
                self.battle_canvas.player_trainer_ref = trainer_sprite
                print(f"Loaded player trainer sprite for {self.peer_role}")
            else:
                print(f"No trainer sprite found for {self.peer_role}")
        except Exception as e:
            print(f"Error updating player trainer sprite: {e}")
        
        # Update opponent trainer sprite
        try:
            # Opponent gets the opposite player sprite
            if self.peer_role == 'host':
                opp_trainer_sprite = self.get_trainer_sprite('player2.gif')
            elif self.peer_role == 'joiner':
                opp_trainer_sprite = self.get_trainer_sprite('player1.gif')
            else:
                opp_trainer_sprite = None
            
            if hasattr(self, 'opp_trainer_id') and self.opp_trainer_id:
                self.battle_canvas.delete(self.opp_trainer_id)
            
            # Only show opponent trainer if we have a remote player
            remote_pokemon_name = self.get_remote_pokemon_name()
            if (opp_trainer_sprite and remote_pokemon_name and 
                remote_pokemon_name not in ["???", "Waiting..."]):
                self.opp_trainer_id = self.battle_canvas.create_image(
                    opp_trainer_x, opp_trainer_y, image=opp_trainer_sprite,
                    anchor=tk.CENTER, tags='opp_trainer')
                self.battle_canvas.opp_trainer_ref = opp_trainer_sprite
                print(f"Loaded opponent trainer sprite")
        except Exception as e:
            print(f"Error updating opponent trainer sprite: {e}")

    def get_remote_pokemon_name(self):
        """Get opponent Pokemon name"""
        if not self.peer:
            return "???"
        if self.peer_role == 'host' and hasattr(self.peer, 'joiner_pokemon_row'):
            return safe_get(self.peer.joiner_pokemon_row, "name", "???")
        elif self.peer_role == 'joiner' and hasattr(self.peer, 'host_pokemon_row'):
            return safe_get(self.peer.host_pokemon_row, "name", "???")
        return "???"

    def get_remote_hp_percent(self):
        """Get opponent HP percentage"""
        if not self.peer:
            return 100
        
        remote_hp = 0
        remote_max = 100
        
        try:
            if self.peer_role == 'host' and hasattr(self.peer, 'joiner_pokemon_row'):
                remote_hp = int(safe_get(self.peer.joiner_pokemon_row, "hp", 0))
                pname = safe_get(self.peer.joiner_pokemon_row, "name", "")
                if pname:
                    orig = self.pm.get_pokemon(pname)
                    if orig:
                        remote_max = int(safe_get(orig, "hp", 100))
            elif self.peer_role == 'joiner' and hasattr(self.peer, 'host_pokemon_row'):
                remote_hp = int(safe_get(self.peer.host_pokemon_row, "hp", 0))
                pname = safe_get(self.peer.host_pokemon_row, "name", "")
                if pname:
                    orig = self.pm.get_pokemon(pname)
                    if orig:
                        remote_max = int(safe_get(orig, "hp", 100))
        except:
            pass
        
        if remote_max <= 0:
            remote_max = 100
        return int((remote_hp / remote_max) * 100)

    def get_local_hp_percent(self):
        """Get player HP percentage"""
        if not self.peer or not hasattr(self.peer, "local_pokemon_row"):
            return 100
        
        try:
            local_hp = int(safe_get(self.peer.local_pokemon_row, "hp", 0))
            pname = safe_get(self.peer.local_pokemon_row, "name", "")
            local_max = 100
            if pname:
                orig = self.pm.get_pokemon(pname)
                if orig:
                    local_max = int(safe_get(orig, "hp", 100))
            
            if local_max <= 0:
                local_max = 100
            return int((local_hp / local_max) * 100)
        except:
            return 100

    # ========== MOVE ACTIONS ==========
    def on_move_click(self, idx):
        if not self.peer:
            return
        moves = self.pm.get_moves_for_pokemon(getattr(self.peer, "local_pokemon_name", ""))
        if idx >= len(moves):
            return
        mv = moves[idx]
        
        player_name = getattr(self.peer, "name", "Unknown")
        self.console_log(f"[BATTLE] {player_name} used {mv}")
        
        try:
            if hasattr(self.peer, 'announce_attack'):
                self.peer.announce_attack(mv)
                self.append_chat(f"You used {mv}!")
                for b in self.move_buttons:
                    b.config(state=tk.DISABLED)
            else:
                self.append_chat("[ERROR] Cannot announce attack")
        except Exception as e:
            self.append_chat(f"[ERROR] {e}")

    def refresh_moves_from_peer(self):
        """Update move buttons based on current state"""
        if not hasattr(self, "move_buttons") or not self.peer:
            return

        local_name = getattr(self.peer, "local_pokemon_name", "(unknown)")
        moves = []
        try:
            moves = self.pm.get_moves_for_pokemon(local_name) if local_name != "(unknown)" else []
        except:
            moves = []

        for i, btn in enumerate(self.move_buttons):
            if i < len(moves):
                btn.config(text=moves[i])
            else:
                btn.config(text="---")

        cur_turn = self.current_turn or safe_get(getattr(self.peer, "battle_state", {}), "turn", None)
        
        if cur_turn:
            self.turn_label.config(text=f"Turn: {cur_turn.upper()}")
        else:
            self.turn_label.config(text="Turn: Waiting...")

        my_role = self.peer_role
        is_my_turn = (cur_turn == my_role)
        if my_role == 'spectator':
            is_my_turn = False

        for btn in self.move_buttons:
            if btn.cget("text") == "---":
                btn.config(state=tk.DISABLED)
            else:
                btn.config(state=(tk.NORMAL if is_my_turn else tk.DISABLED))

    # ========== CHAT ==========
    def open_chat_text(self):
        if not self.peer:
            return
        text = simpledialog.askstring("Chat", "Message:")
        if not text:
            return
        payload = {'message_type': 'CHAT_MESSAGE', 'sender_name': getattr(self.peer, "name", "You"),
                   'content_type': 'TEXT', 'message_text': text}
        dest = self._determine_remote_addr()
        if not dest:
            self.append_chat("[SYSTEM] No remote connected")
            return
        try:
            self.peer.send(payload, dest)
            self.append_chat(f"[YOU] {text}")
        except Exception as e:
            self.append_chat(f"[ERROR] {e}")

    def open_chat_sticker(self):
        if not self.peer:
            return
        fpath = filedialog.askopenfilename(
            title="Choose sticker (GIF)",
            filetypes=[("GIF files", "*.gif")])
        if not fpath:
            return
        try:
            with open(fpath, "rb") as f:
                raw = f.read()
            if len(raw) > 10 * 1024 * 1024:
                messagebox.showerror("Error", "Sticker >10MB")
                return
            b64 = base64.b64encode(raw).decode("ascii")
            payload = {'message_type': 'CHAT_MESSAGE', 'sender_name': getattr(self.peer, "name", "You"),
                       'content_type': 'STICKER', 'sticker_data': b64}
            dest = self._determine_remote_addr()
            if not dest:
                self.append_chat("[SYSTEM] No remote connected")
                return
            self.peer.send(payload, dest)
            self.append_chat("[YOU] sent a sticker")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot send sticker: {e}")

    def _determine_remote_addr(self):
        if not self.peer:
            return None
        if self.peer_role == "host":
            return getattr(self.peer, "remote_addr", None)
        if self.peer_role == "joiner":
            return getattr(self.peer, "host_addr", None)
        return None

    def append_chat(self, text):
        try:
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.insert(tk.END, text + "\n")
            self.chat_text.see(tk.END)
            self.chat_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error appending chat: {e}")

    # ========== NETWORK MESSAGE PROCESSING ==========
    def process_queue(self):
        try:
            while True:
                item = self.gui_queue.get_nowait()
                self._handle_gui_queue_item(item)
        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def _handle_gui_queue_item(self, item):
        try:
            kind = item[0]
            if kind == "network_msg":
                _, msg, addr, peer = item
                self._process_network_message(msg, addr, peer)
            elif kind == "info":
                _, txt = item
                self.info_label.config(text=f"Info: {txt}")
                self.append_chat(f"[INFO] {txt}")
        except Exception as e:
            print(f"Error handling GUI queue: {e}")

    def _process_network_message(self, msg, addr, peer):
        try:
            mt = msg.get("message_type")
            
            def get_player_name():
                return msg.get("player_name") or msg.get("sender_name") or msg.get("attacker") or "Player"
            
            def get_pokemon_name():
                return msg.get("pokemon_name") or "Pokemon"

            # Chat messages
            if mt == "CHAT_MESSAGE":
                sender = get_player_name()
                content_type = msg.get("content_type")
                if content_type == "TEXT":
                    txt = msg.get("message_text", "")
                    self.append_chat(f"[{sender}] {txt}")
                    self.console_log(f"[CHAT] {sender}: {txt}")
                elif content_type == "STICKER":
                    self.append_chat(f"[{sender}] (sticker)")
                    self.console_log(f"[CHAT] {sender} sent a sticker")
                return

            # Turn assignment
            if mt == "TURN_ASSIGNMENT":
                new_turn = msg.get("current_turn")
                self.append_chat(f"[TURN] Now: {new_turn}")
                self.console_log(f"[BATTLE] Turn: {new_turn}")
                self.current_turn = new_turn
                self.refresh_moves_from_peer()
                return

            # Battle setup
            if mt == "BATTLE_SETUP":
                pname = get_pokemon_name()
                player_name = get_player_name()
                self.append_chat(f"[BATTLE] {player_name} sent {pname}!")
                self.console_log(f"[BATTLE] {player_name} sent {pname}")
                self.after(100, self.update_sprites)
                self.update_hp_display_once()
                return

            # Attack announce
            if mt == "ATTACK_ANNOUNCE":
                attacker = get_player_name()
                move = msg.get("move_name", "move")
                self.append_chat(f"[BATTLE] {attacker} used {move}!")
                self.console_log(f"[BATTLE] {attacker} used {move}")
                return

            # Calculation report
            if mt == "CALCULATION_REPORT":
                attacker = get_player_name()
                move = msg.get("move_used", "move")
                dmg = msg.get("damage_dealt", 0)
                hprem = msg.get("defender_hp_remaining", 0)
                self.append_chat(f"[REPORT] {move} dealt {dmg} damage! HP: {hprem}")
                self.console_log(f"[BATTLE] {attacker} {move} -> {dmg} dmg, HP: {hprem}")
                self.update_hp_display_once()
                if hprem <= 0:
                    self.on_battle_end()
                return

            # Handshake (verbose only)
            if mt in ("HANDSHAKE_REQUEST", "HANDSHAKE_RESPONSE"):
                if self.verbose_mode.get():
                    player = get_player_name()
                    pokemon = get_pokemon_name()
                    self.append_chat(f"[NET] {mt} from {player}")
                self.console_log(f"[NETWORK] {mt}", verbose_only=True)
                self.after(100, self.update_sprites)
                return

            # Other messages (verbose only)
            if self.verbose_mode.get():
                self.append_chat(f"[NET] {mt}")
            self.console_log(f"[NETWORK] {mt}", verbose_only=True)
            
        except Exception as e:
            print(f"Error processing network message: {e}")

    # ========== HP DISPLAY ==========
    def update_hp_display(self):
        """Periodic HP update"""
        try:
            self.update_hp_display_once()
            
            if (self.peer and hasattr(self.peer, 'battle_state') and 
                not hasattr(self, '_battle_ended')):
                
                battle_state = self.peer.battle_state
                host_hp = safe_get(battle_state, 'host_hp', 1) or 1
                joiner_hp = safe_get(battle_state, 'joiner_hp', 1) or 1
                
                try:
                    host_hp = int(host_hp)
                    joiner_hp = int(joiner_hp)
                except:
                    host_hp = 1
                    joiner_hp = 1
                
                if host_hp <= 0 or joiner_hp <= 0:
                    self._battle_ended = True
                    self.on_battle_end()
                    
        except Exception as e:
            print(f"Error in update_hp_display: {e}")
        
        self.after(500, self.update_hp_display)

    def update_hp_display_once(self):
        """Update HP bars on canvas"""
        if not hasattr(self, 'battle_canvas') or not self.peer:
            return
        
        try:
            # Update player HP
            player_hp_percent = self.get_local_hp_percent()
            player_hp_color = self.get_hp_color(player_hp_percent)
            
            if hasattr(self.peer, "local_pokemon_row"):
                local_hp = int(safe_get(self.peer.local_pokemon_row, "hp", 0))
                pname = safe_get(self.peer.local_pokemon_row, "name", "")
                local_max = 100
                if pname:
                    orig = self.pm.get_pokemon(pname)
                    if orig:
                        local_max = int(safe_get(orig, "hp", 100))
                
                # Update HP bar width - using new coordinates
                bar_width = 230 * (player_hp_percent / 100)
                self.battle_canvas.coords(self.player_hp_bar, 60, 340, 60+bar_width, 355)
                self.battle_canvas.itemconfig(self.player_hp_bar, fill=player_hp_color)
                self.battle_canvas.itemconfig(self.player_hp_text, text=f"HP: {local_hp}/{local_max}")
            
            # Update opponent HP
            remote_hp_percent = self.get_remote_hp_percent()
            remote_hp_color = self.get_hp_color(remote_hp_percent)
            
            remote_hp = 0
            remote_max = 100
            
            if self.peer_role == 'host' and hasattr(self.peer, 'joiner_pokemon_row'):
                remote_hp = int(safe_get(self.peer.joiner_pokemon_row, "hp", 0))
                pname = safe_get(self.peer.joiner_pokemon_row, "name", "")
                if pname:
                    orig = self.pm.get_pokemon(pname)
                    if orig:
                        remote_max = int(safe_get(orig, "hp", 100))
            elif self.peer_role == 'joiner' and hasattr(self.peer, 'host_pokemon_row'):
                remote_hp = int(safe_get(self.peer.host_pokemon_row, "hp", 0))
                pname = safe_get(self.peer.host_pokemon_row, "name", "")
                if pname:
                    orig = self.pm.get_pokemon(pname)
                    if orig:
                        remote_max = int(safe_get(orig, "hp", 100))
            
            # Get canvas width for positioning
            width = self.battle_canvas.winfo_width()
            if width < 50:
                width = 800
            
            # Update opponent HP bar
            bar_width = 230 * (remote_hp_percent / 100)
            self.battle_canvas.coords(self.opp_hp_bar, 
                width-260, 90, width-260+bar_width, 105)
            self.battle_canvas.itemconfig(self.opp_hp_bar, fill=remote_hp_color)
            self.battle_canvas.itemconfig(self.opp_hp_text, text=f"HP: {remote_hp}/{remote_max}")
            
        except Exception as e:
            print(f"Error in update_hp_display_once: {e}")

    def get_hp_color(self, hp_percent):
        """Get HP bar color based on percentage"""
        if hp_percent > 50:
            return POKEMON_COLORS['hp_green']
        elif hp_percent > 25:
            return POKEMON_COLORS['hp_yellow']
        else:
            return POKEMON_COLORS['hp_red']

    # ========== BATTLE END ==========
    def on_battle_end(self):
        """Handle battle end"""
        for b in self.move_buttons:
            b.config(state=tk.DISABLED)

        if not hasattr(self, '_battle_end_message_shown'):
            self._battle_end_message_shown = True
            
            if self.peer and hasattr(self.peer, 'battle_state'):
                battle_state = self.peer.battle_state
                host_hp = safe_get(battle_state, 'host_hp', 1) or 1
                joiner_hp = safe_get(battle_state, 'joiner_hp', 1) or 1
                
                try:
                    host_hp = int(host_hp)
                    joiner_hp = int(joiner_hp)
                except:
                    host_hp = 1
                    joiner_hp = 1
                
                if self.peer_role == 'host':
                    if host_hp <= 0:
                        message = "You lost! Your Pokemon fainted!"
                        self.console_log("[BATTLE] Player 1 lost!")
                    else:
                        message = "You won! Opponent's Pokemon fainted!"
                        self.console_log("[BATTLE] Player 1 won!")
                elif self.peer_role == 'joiner':
                    if joiner_hp <= 0:
                        message = "You lost! Your Pokemon fainted!"
                        self.console_log("[BATTLE] Player 2 lost!")
                    else:
                        message = "You won! Opponent's Pokemon fainted!"
                        self.console_log("[BATTLE] Player 2 won!")
                else:
                    message = "Battle ended!"
                    self.console_log("[BATTLE] Battle ended!")
                
                self.append_chat(f"[GAME OVER] {message}")
                messagebox.showinfo("Battle Over", message)

    # ========== UTILITIES ==========
    def set_verbose_mode(self, enabled):
        """Set verbose mode"""
        try:
            from network import set_verbose
            set_verbose(enabled)
            self.verbose_mode.set(enabled)
            status = "ON" if enabled else "OFF"
            
            if hasattr(self, 'verbose_status_label'):
                self.verbose_status_label.config(text=f"Verbose: {status}")
            print(f"[SYSTEM] Verbose mode {status}")
        except ImportError:
            print("Could not set verbose mode")

    def console_log(self, message, verbose_only=False):
        """Print to console based on verbose mode"""
        if not verbose_only or self.verbose_mode.get():
            print(message)

    def stop_and_return(self):
        """Return to main menu"""
        if hasattr(self, '_battle_ended'):
            del self._battle_ended
        if hasattr(self, '_battle_end_message_shown'):
            del self._battle_end_message_shown
            
        if self.peer:
            try:
                self.peer.stop()
            except:
                pass
            self.peer = None
            self.peer_role = None
        self.build_main_menu()

    def on_close(self):
        """Close application"""
        try:
            if self.peer:
                self.peer.stop()
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    try:
        app = PokeGUI()
        app.mainloop()
    except Exception as e:
        print("Failed to start GUI:", e)
        raise