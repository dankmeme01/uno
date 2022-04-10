from datetime import datetime
from threading import Thread, Lock
from unoengine import Table, Player, Card, card_to_id, id_to_card
from collections import namedtuple
from pathlib import Path
import socket
import json
import time

PORT = 48753
server_table = None
printlock = Lock()

LocalPlayer = namedtuple("LocalPlayer", ["name", "index", "cards"])

class Netsock:
    def start(self):
        Thread(target=self.mainloop, daemon=True).start()

    def mainloop(self):
        raise NotImplementedError("Must inherit")

class Client(Netsock):
    def __init__(self, address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serv_addr = address
        self.sendlock = Lock()
        self.loglock = Lock()
        self.fp = open(Path(__file__).parent / "client.log", "w")
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

        self.readypl = 0
        self.totalpl = 0

    def query_event(self, etype, edata):
        with self.sendlock:
            try:
                self.sock.send(json.dumps([etype, edata]).encode())
                return json.loads(self.sock.recv(4096).decode())
            except (ConnectionResetError, ConnectionAbortedError):
                self.log("Connection closed")
                self.stop()


    def ready(self):
        self.is_ready = self.query_event("ready", None)

    def place_card(self, card):
        res = self.query_event("move", card if isinstance(card, str) else card_to_id(card))
        return res

    def draw(self):
        res = self.query_event("draw", None)
        return res

    def mainloop(self):
        while True:
            if self.stopped:
                break

            if self.in_menu:
                resp = self.query_event("menu_state", None)
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

                self.moving, self.deck, self.topcard, self.clockwise = res
                time.sleep(0.1)
    
        self.sock.close()

    def stop(self):
        self.stopped = True
        self.log("Stopping client")
        self.fp.close()

    def log(self, *args, **kwargs):
        with self.loglock:
            prefix = f'[C] [{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]'
            print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=self.fp, flush=True)

class ServerThread(Netsock):
    def __init__(self, sock: socket.socket, table: Table, name, logfp):
        self.sock = sock
        self.name = name
        self.table = table
        self.stopped = False
        self.fp = logfp
        self.loglock = Lock()

    def mainloop(self):
        while True:
            if self.stopped:
                break
            
            try:
                data = self.sock.recv(4096).decode()
            except (ConnectionResetError, ConnectionAbortedError):
                self.log("Connection closed")
                break

            etype, edata = json.loads(data)
            if etype == 'exit':
                break
            reply = self.handle_event(etype, edata)
            self.sock.send(json.dumps(reply).encode('utf-8'))
        self.sock.close()

    def stop(self):
        self.stopped = True

    def handle_event(self, event, edata):
        # handles event
        match event:
            case "time":
                return datetime.now().strftime("%H:%M:%S")
            case "ready":
                if edata is None:
                    edata = not self.table.get_player(self.name).ready
                self.table.get_player(self.name).ready = edata
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
                return (self.table.moving, self.table.get_player(self.name).deck, self.table.topcard, self.table.clockwise)
            case "move":
                if self.table.indexof(self.name) != self.table.moving:
                    return False

                plcard = edata if isinstance(edata, list) else list(id_to_card(edata))
                if not self.table.validate_move(self.table.get_player(self.name), plcard[0], plcard[1]):
                    return False

                self.table.place(self.table.get_player(self.name), plcard[0], plcard[1])
                return True
            case "draw":
                if self.table.indexof(self.name) != self.table.moving:
                    return False
                self.table.draw(self.table.get_player(self.name))
                return True
    
    def log(self, *args, **kwargs):
        with self.loglock:
            prefix = f'[S-{self.name}] [{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]'
            print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=self.fp, flush=True)

class Server(Netsock):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = socket.gethostbyname(socket.gethostname())
        self.threads = []
        self.stopped = False
        self.table = Table()
        self.loglock = Lock()
        self.fp = open(Path(__file__).parent / "server.log", "w")
        self.sock.bind((self.address, PORT))
        self.sock.listen()

    def mainloop(self):
        self.log(f"Starting to listen on {self.address}:{PORT}")
        while True:
            if self.stopped:
                break

            user_sock, user_addr = self.sock.accept()
            uname = socket.gethostbyaddr(user_sock.getsockname()[0])[0]
            self.log(f"Received connection from {uname} ({user_addr[0]}:{user_addr[1]})")
            if self.table.started: 
                user_sock.send(b"Game already started")
                user_sock.close()
                continue
            while self.table.get_player(uname):
                uname += '-'
            server_thread = ServerThread(user_sock, self.table, uname, self.fp)
            server_thread.start()
            self.threads.append(server_thread)
            self.table.add_player(uname)
        self.sock.close()

    def stop(self):
        [t.stop() for t in self.threads]
        self.stopped = True
    
    def log(self, *args, **kwargs):
        with self.loglock:
            prefix = f'[S] [{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]'
            print(prefix, *args, **kwargs)
            print(prefix, *args, **kwargs, file=self.fp, flush=True)

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