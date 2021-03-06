from datetime import datetime
from threading import Thread, Lock
from unoengine import Table, Card, card_to_id, id_to_card
from collections import namedtuple
from pathlib import Path
import random
import socket
import select
import json
import time

PORT = 48753
DEBUG = False

server_table = None
printlock = Lock()

LocalPlayer = namedtuple("LocalPlayer", ["name", "index", "cards"])

if DEBUG:
    from icecream import ic
else:
    ic = lambda *a, **kw: None

class Netsock:
    """Basic wrapper for a thread socket."""
    def start(self):
        Thread(target=self.mainloop, daemon=True).start()

    def mainloop(self):
        raise NotImplementedError("Must inherit")

class Client(Netsock):
    """Basic UNO client."""
    def __init__(self, address, version, settings=None, /, bot=False):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serv_addr = address
        self.name = socket.gethostname()
        self.sendlock = Lock()
        self.loglock = Lock()
        self.settings = settings
        self.version = version
        self.auth = False
        if self.settings:
            self.name = self.settings.get('name')

        self.fp = Path(__file__).parent / ("logs" if not bot else "bot_logs") / f"client-{time.time_ns()}.log"
        open(self.fp, 'w').close()
        self.sock.connect((address, PORT))
        self.log(f"Connected to {address}:{PORT}")
        # this is for gamestate
        self.init_values()

    def init_values(self):
        """Initializes all game values to their defaults."""
        self.players: list[LocalPlayer] = []
        self.lobbypls: list[tuple] = []
        self.deck: list[Card] = []
        self.topcard: Card = None
        self.moving: int = None
        self.clockwise: bool = True
        self.in_menu: bool = True
        self.is_ready: bool = False
        self.myindex: int = None
        self.lastwinner: str = None
        self.stopped: bool = False
        self.showdraw: Card = None
        self.waiting_color: bool = False
        self.prevres = None

        self.readypl = 0
        self.totalpl = 0

    def query_event(self, etype, edata):
        """Sends an event and returns the response."""
        with self.sendlock:
            try:
                self.sock.send(json.dumps([etype, edata]).encode())
                data = self.sock.recv(4096).decode()
                if not data or not data.strip():
                    self.log("Server closed connection.")
                    self.stop()

                return json.loads(data)
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                print(e)
                self.stop()

    def ready(self):
        """Sends a ready event."""
        self.is_ready = self.query_event("ready", None)

    def place_card(self, card):
        """Places a card on the table."""
        res = self.query_event("move", card if isinstance(card, str) else card_to_id(card))
        return res

    def draw_place(self):
        """Confirms a placing of a card in showdraw variable."""
        if not self.showdraw:
            return

        if self.showdraw.color == 'wild':
            self.waiting_color = Card(*self.showdraw)
            self.showdraw = None
        else:
            self.showdraw = None
            self.query_event("draw_place", None)

    def draw_take(self):
        """Confirms taking the card in showdraw variable."""
        self.showdraw = None
        self.query_event("draw_take", None)

    def draw(self):
        """Draws a card and if it can be placed, puts it into self.showdraw, and waits for the draw_place or draw_take event."""
        self.showdraw = self.query_event("draw", None)
        if self.showdraw is not None:
            self.showdraw = id_to_card(self.showdraw)

    def mainloop(self):
        """Main loop for the client."""
        while True:
            if self.stopped:
                break

            if not self.auth:
                self.auth = self.query_event("auth", [self.name, self.version])
                if self.auth is not True:
                    self.log("Failed to authorize. Message:", self.auth)
                    self.auth = False
                    self.stopped = True
                    break

            if self.in_menu:
                resp = self.query_event("menu_state", None)
                if self.stopped:
                    break

                if resp == False:
                    self.in_menu = False
                else:
                    self.lobbypls.clear()
                    for name, ready in resp:
                        self.lobbypls.append((name, ready))
                        if ready:
                            self.readypl += 1
                    time.sleep(0.33)
            else:
                res = self.query_event("status", None)
                if self.stopped:
                    break

                if res[0] == 'end':
                    self.init_values()
                    self.lastwinner = res[1]
                    continue

                if res != self.prevres:
                    self.log(f'Status change. Moving: {res[0]}, topcard: {res[2]}, deck: {res[1]}')
                    self.prevres = res

                self.myindex, self.moving, self.deck, self.topcard, self.clockwise, players = res
                self.players = [LocalPlayer(name, i, cards) for name, i, cards in players]
                self.deck = [id_to_card(c) for c in self.deck]
                self.topcard = id_to_card(self.topcard)
                time.sleep(0.1)

        self.sock.close()

    def stop(self):
        """Stops the client."""
        self.stopped = True
        self.log("Stopping client")
        self.sock.close()

    def log(self, *args, **kwargs):
        """Logs a message to the log file."""
        with self.loglock, open(self.fp, 'a') as fp:
            prefix = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [C]'
            print(prefix, *args, **kwargs, file=fp, flush=True)

class ServerThread(Netsock):
    """Thread for the serverthread that's bound to one player."""
    def __init__(self, sock: socket.socket, table: Table, name, logfp, version):
        self.sock = sock
        self.sock.setblocking(0)
        self.sockname = name
        self.name = name
        self.version = version
        self.table: Table = table
        self.stopped = False
        self.fp = logfp
        self.authed = False
        self.bot = False
        self.loglock = Lock()
        self.player = self.table.get_player(self.name)

    def mainloop(self):
        """Main loop for the server thread."""
        while True:
            if self.stopped:
                break
            try:
                ready = select.select([self.sock], [], [], 15)
                if not ready[0]:
                    self.log("Connection issues detected, no reply for 15+ seconds. Closing connection.")
                    break

                data = self.sock.recv(4096).decode()
                if not data or self.stopped:
                    break

                etype, edata = json.loads(data)
                if etype == 'exit':
                    break
                reply = self.handle_event(etype, edata)

                # dont log those events because they occur many times a second
                if etype not in ("status", "menu_state"):
                    self.log(f"Event: {etype}, edata: {edata}, response: {reply}")

                self.sock.send(json.dumps(reply).encode('utf-8'))
            except (ConnectionResetError, ConnectionAbortedError):
                break

        # gracefully remove the player from the game if the connection is closed
        self.table.remove_player(self.name)
        self.stop()

    def stop(self):
        """Stops the server thread."""
        self.log("Stopping thread..")
        self.sock.close()
        self.stopped = True

    def handle_event(self, event, edata):
        # handles event (could also call it a packet if that's better for you)
        if event == "time": # test event that returns a time
            return datetime.now().strftime("%H:%M:%S")
        elif event == "auth": # event that authenticates the client, storing it's name and checking the version
            name, version = edata

            if version == 'bot':
                self.bot = True
                self.log("Warning: Player registered as bot.")
            elif version != self.version:
                return f'Version mismatch. Server: {self.version}, client: {version}'

            name = str(name)
            if len(name) > 24:
                name = name[:24]

            names = [p.name for p in self.table.players]
            while name in names:
                if name == '-'*24:
                    name = f'Player-{random.randrange(1_000_000, 10_000_000)}'
                if len(name) >= 24:
                    name = name[:24]
                    name = name[:-1] + '-'
                else:
                    name += '-'

            self.player.name = self.name = name
            self.authed = True
            return True
        elif event == "ready": # event that sets the player's ready state
            if not self.authed:
                return False

            if edata is None:
                edata = not self.player.ready
            self.player.ready = edata
            if self.table.check_all_ready() and len(self.table.players) > 1:
                self.table.start()
            return edata
        elif event == "menu_state": # event that returns the lobby state
            if self.table.started:
                return False
            return [(x.name, x.ready) for x in self.table.players]
        elif event == "status": # event that returns the game state
            if not self.table.started:
                return ("end", self.table.lastwinner if self.table.lastwinner else None)

            if len(self.table.players) < 2:
                self.table.started = False
                return ("end", self.table.lastwinner if self.table.lastwinner else None)

            return (self.table.indexof(self.name), self.table.moving, [card_to_id(c) for c in self.player.deck], card_to_id(self.table.topcard), self.table.clockwise, [(x.name, n, len(x.deck)) for n,x in enumerate(self.table.players)])
        elif event == "move": # event that places a card on the table
            plcard = Card(*edata) if isinstance(edata, list) else id_to_card(edata)
            ic(plcard, self.player.waiting_action)
            if isinstance(self.player.waiting_action, Card):
                if self.player.waiting_action.type == plcard.type and self.player.waiting_action.color == 'wild':
                    self.player.waiting_action = None
                    self.table.place(self.player, plcard)
                    return True

            if self.table.indexof(self.name) != self.table.moving or self.player.waiting_action:
                return False

            if not self.table.validate_move(self.player, plcard):
                return False

            self.table.place(self.player, plcard)
            return True
        elif event == "draw": # event that draws a card
            if self.table.indexof(self.name) != self.table.moving or self.player.waiting_action:
                return None

            card = self.table.draw(self.player)
            if isinstance(card, Card):
                self.player.waiting_action = card
                return card_to_id(card)
            else:
                return None
        elif event == "draw_place": # event that draws a card and places it on the table
            if self.table.indexof(self.name) != self.table.moving or not self.player.waiting_action:
                return False

            self.table.place(self.player, self.player.waiting_action)
            self.player.waiting_action = False
            return True
        elif event == "draw_take": # event that draws a card and takes it from the table
            if self.table.indexof(self.name) != self.table.moving or not self.player.waiting_action:
                return False

            self.player.deck.append(self.player.waiting_action)
            self.player.waiting_action = False
            self.table.nextmoving()
            return True


    def log(self, *args, **kwargs):
        with self.loglock, open(self.fp, 'a') as fp:
            prefix = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [S-{self.name} ({self.sockname})]'
            if DEBUG:
                print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=fp, flush=True)

class Server(Netsock):
    """A thread for a dedicated server that handles connections."""
    def __init__(self, version, settings=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = socket.gethostbyname(socket.gethostname())
        self.threads = []
        self.stopped = False
        self.settings = settings
        self.version = version
        self.table = Table()
        self.loglock = Lock()
        self.fp = Path(__file__).parent / "logs" / f"server-{time.time_ns()}.log"
        open(self.fp, 'w').close()
        self.sock.bind((self.address, PORT))
        self.sock.listen()

    def mainloop(self):
        """Main loop for the server."""
        self.log(f"Starting to listen on {self.address}:{PORT}. Version: {self.version}")
        while True:
            if self.stopped:
                break

            try:
                user_sock, user_addr = self.sock.accept()
            except OSError:
                break

            uname = socket.gethostbyaddr(user_sock.getpeername()[0])[0]
            self.log(f"Received connection from {uname} ({user_addr[0]}:{user_addr[1]})")
            if self.table.started:
                user_sock.send(b"Game already started")
                user_sock.close()
                continue
            while self.table.get_player(uname):
                uname += '-'
            self.table.add_player(uname)
            server_thread = ServerThread(user_sock, self.table, uname, self.fp, self.version)
            server_thread.start()
            self.threads.append(server_thread)
        self.sock.close()

    def stop(self):
        """Stop the server."""
        [t.stop() for t in self.threads]
        self.log("Stopping the main server..")
        self.sock.close()
        self.stopped = True

    def log(self, *args, **kwargs):
        """Log a message to the server log."""
        with self.loglock, open(self.fp, 'a') as fp:
            prefix = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [S]'
            if DEBUG:
                print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=fp, flush=True)
