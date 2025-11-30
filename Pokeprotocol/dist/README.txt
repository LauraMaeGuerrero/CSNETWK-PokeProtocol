PokeProtocol - P2P Pokemon Battle
==================================

STANDALONE EXECUTABLES - No Python installation required!

FILES:
------
- PokeProtocol-GUI.exe - Graphical interface (recommended)
- PokeProtocol-CLI.exe - Command-line interface

GUI VERSION (PokeProtocol-GUI.exe):
-----------------------------------
1. Double-click PokeProtocol-GUI.exe
2. Choose HOST GAME, JOIN GAME, or SPECTATE
3. Select your Pokemon and configure settings
4. Battle with visual sprites and animations

CLI VERSION (PokeProtocol-CLI.exe):
-----------------------------------
1. SAME COMPUTER (Testing):
   - Open TWO command prompts
   - Terminal 1: Run PokeProtocol-CLI.exe as HOST
   - Terminal 2: Run PokeProtocol-CLI.exe as CLIENT
   - Connect to 127.0.0.1

2. DIFFERENT COMPUTERS (Real P2P):
   - Copy PokeProtocol-CLI.exe to both computers
   - Both computers must be on the SAME NETWORK
   - Host: Find your IP with "ipconfig" command
   - Client: Connect to the host's IP address

QUICK START (CLI):
------------------
HOST:
  > PokeProtocol-CLI.exe
  > n (verbose mode)
  > 1 (Start as Host)
  > 1 (Pick Pokemon)
  > 5001 (Port)

CLIENT:
  > PokeProtocol-CLI.exe
  > n (verbose mode)
  > 2 (Join)
  > [HOST_IP] (e.g., 192.168.1.100 or 127.0.0.1)
  > 5001 (Port)
  > 2 (Pick Pokemon)
  > 0 (Random port)

COMMANDS (CLI):
---------------
- attack: Attack opponent (when it's your turn)
- chat: Send text or sticker message
- status: View battle state and HP
- exit: Quit the game

TROUBLESHOOTING:
----------------
- If connection fails, check Windows Firewall
- Make sure both computers are on same network
- Try disabling firewall temporarily for testing
- Use verbose mode (y) to see all network messages

NOTES:
------
- All sprites and data files are bundled in the executables
- No external files needed to run
- GUI version includes Pokemon sprites and battle animations
- CLI version is text-based for terminal use
