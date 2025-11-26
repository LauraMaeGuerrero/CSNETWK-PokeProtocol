PokeProtocol - P2P Pokemon Battle
==================================

STANDALONE EXECUTABLE - No Python installation required!

HOW TO USE:
-----------

1. SAME COMPUTER (Testing):
   - Open TWO command prompts
   - Terminal 1: Run PokeProtocol.exe as HOST
   - Terminal 2: Run PokeProtocol.exe as CLIENT
   - Connect to 127.0.0.1

2. DIFFERENT COMPUTERS (Real P2P):
   - Copy PokeProtocol.exe to both computers
   - Both computers must be on the SAME NETWORK
   - Host: Find your IP with "ipconfig" command
   - Client: Connect to the host's IP address

QUICK START:
------------

HOST (Computer 1):
  > PokeProtocol.exe
  > n (verbose mode)
  > 1 (Start as Host)
  > 1 (Pick Pokemon)
  > 5001 (Port)

CLIENT (Computer 2):
  > PokeProtocol.exe
  > n (verbose mode)
  > 2 (Join)
  > [HOST_IP] (e.g., 192.168.1.100 or 127.0.0.1)
  > 5001 (Port)
  > 2 (Pick Pokemon)
  > 0 (Random port)

COMMANDS:
---------
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

File size: ~8 MB
Includes: All dependencies + pokemon.csv data
