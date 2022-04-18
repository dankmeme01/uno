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
    def start(self):
        Thread(target=self.mainloop, daemon=True).start()

    def mainloop(self):
        raise NotImplementedError("Must inherit")

class Client(Netsock):
    def __init__(self, address, version, settings=None):
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

        self.fp = Path(__file__).parent / "client.log"
        open(self.fp, 'w').close()
        self.sock.connect((address, PORT))
        self.log(f"Connected to {address}:{PORT}")
        # this is for gamestate
        self.init_values()

    def init_values(self):
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
        with self.sendlock:
            try:
                self.sock.send(json.dumps([etype, edata]).encode())
                data = self.sock.recv(4096).decode()
                if not data:
                    self.log("Server closed connection.")
                    self.stop()

                return json.loads(data)
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                print(e)
                self.stop()


    def ready(self):
        self.is_ready = self.query_event("ready", None)

    def place_card(self, card):
        res = self.query_event("move", card if isinstance(card, str) else card_to_id(card))
        return res

    def draw_place(self):
        if not self.showdraw:
            return

        if self.showdraw.color == 'wild':
            self.waiting_color = Card(*self.showdraw)
            self.showdraw = None
        else:
            self.showdraw = None
            self.query_event("draw_place", None)

    def draw_take(self):
        self.showdraw = None
        self.query_event("draw_take", None)

    def draw(self):
        self.showdraw = self.query_event("draw", None)
        if self.showdraw is not None:
            self.showdraw = id_to_card(self.showdraw)

    def mainloop(self):
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
                if not self.players:
                    resp = self.query_event("begin_state", None)
                    if resp[0] == 'end':
                        self.init_values()
                        self.lastwinner = resp[1]
                        continue

                    self.myindex, state = resp
                    self.players = [LocalPlayer(name, i, cards) for name, i, cards in state]

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

                self.moving, self.deck, self.topcard, self.clockwise, players = res
                self.players = [LocalPlayer(name, i, cards) for name, i, cards in players]
                self.deck = [id_to_card(c) for c in self.deck]
                self.topcard = id_to_card(self.topcard)
                time.sleep(0.1)
    
        self.sock.close()

    def stop(self):
        self.stopped = True
        self.log("Stopping client")
        self.sock.close()

    def log(self, *args, **kwargs):
        with self.loglock, open(self.fp, 'a') as fp:
            prefix = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [C]'
            if DEBUG:
                print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=fp, flush=True)

class ServerThread(Netsock):
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
        self.loglock = Lock()
        self.player = self.table.get_player(self.name)

    def mainloop(self):
        while True:
            if self.stopped:
                break
            try:
                ready = select.select([self.sock], [], [], 30)
                if not ready[0]:
                    self.log("AFK detected, no reply for 30 seconds. Closing connection.")
                    break
                data = self.sock.recv(4096).decode()
                if not data or self.stopped:
                    break

                etype, edata = json.loads(data)
                if etype == 'exit':
                    break
                reply = self.handle_event(etype, edata)

                if etype not in ("status", "menu_state"):
                    self.log(f"Event: {etype}, edata: {edata}, response: {reply}")

                self.sock.send(json.dumps(reply).encode('utf-8'))
            except (ConnectionResetError, ConnectionAbortedError):
                break
    
        self.table.remove_player(self.name)
        self.stop()

    def stop(self):
        self.log("Stopping thread..")
        self.sock.close()
        self.stopped = True

    def handle_event(self, event, edata):
        # handles event
        match event:
            case "time":
                return datetime.now().strftime("%H:%M:%S")
            case "auth":
                name, version = edata
                if version != self.version:
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
            case "ready":
                if not self.authed:
                    return False

                if edata is None:
                    edata = not self.player.ready
                self.player.ready = edata
                if self.table.check_all_ready() and len(self.table.players) > 1:
                    self.table.start()
                return edata
            case "menu_state":
                if self.table.started:
                    return False
                return [(x.name, x.ready) for x in self.table.players]
            case "begin_state":
                if not self.table.started:
                    return ("end", self.table.lastwinner if self.table.lastwinner else None)
                return (self.table.indexof(self.name), [(x.name, n, len(x.deck)) for n,x in enumerate(self.table.players)])
            case "status":
                if not self.table.started:
                    return ("end", self.table.lastwinner if self.table.lastwinner else None)

                if len(self.table.players) < 2:
                    self.table.started = False
                    return ("end", self.table.lastwinner if self.table.lastwinner else None)

                return (self.table.moving, [card_to_id(c) for c in self.player.deck], card_to_id(self.table.topcard), self.table.clockwise, [(x.name, n, len(x.deck)) for n,x in enumerate(self.table.players)])
            case "move":
                plcard = Card(*edata) if isinstance(edata, list) else id_to_card(edata)
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
            case "draw":
                if self.table.indexof(self.name) != self.table.moving or self.player.waiting_action:
                    return None

                card = self.table.draw(self.player)
                if isinstance(card, Card):
                    self.player.waiting_action = card
                    return card_to_id(card)
                else:
                    return None
            case "draw_place":
                if self.table.indexof(self.name) != self.table.moving or not self.player.waiting_action:
                    return False

                self.table.place(self.player, self.player.waiting_action)
                self.player.waiting_action = False
                return True
            case "draw_take":
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
    def __init__(self, version, settings=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = socket.gethostbyname(socket.gethostname())
        self.threads = []
        self.stopped = False
        self.settings = settings
        self.version = version
        self.table = Table()
        self.loglock = Lock()
        self.fp = Path(__file__).parent / "server.log"
        open(self.fp, 'w').close()
        self.sock.bind((self.address, PORT))
        self.sock.listen()

    def mainloop(self):
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
        [t.stop() for t in self.threads]
        self.log("Stopping the main server..")
        self.sock.close()
        self.stopped = True
    
    def log(self, *args, **kwargs):
        with self.loglock, open(self.fp, 'a') as fp:
            prefix = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [S]'
            if DEBUG:
                print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=fp, flush=True)

"""

netcode logic:
when the game starts everyone requests data from server
with event 'status'

then the server replies to everyone with their deck
and the person who moves first

also it sends how many cards everyone else has and what is the top card

for every player that is NOT moving, they wait 0.5 seconds and send 'status' again
and so on.

when the moving player moves, they send 'move' with the card they want to move
server validates that card to prevent cheating
and if it is correct, then server replies to them True

then when everyone else requests 'status', server will send them the new top card, and who is moving.
a bit hard to understand but hopefully it will clear up later

"""