# This script is not recommended to use in actual games (because it's cheating duh)
# Originally created only for testing. The server knows if you're a bot or not. You can obviously change it but you will be an asshole then.

from networking import Client, LocalPlayer, Server
from unoengine import card_to_id, id_to_card, Card
from pathlib import Path
from colored import bg, fg, attr
import json
import os

clear = lambda: os.system('cls') if os.name == 'nt' else os.system('clear')

#from classes import Settings

# to prevent pygame import.
class Settings:
    def __init__(self, savepath, **defaults) -> None:
        self.values = defaults
        self.sp = Path(savepath)
        if self.sp.exists():
            self.load()

    def get(self, key):
        return self.values[key]

    def set(self, key, value, dont_save = False):
        self.values[key] = value
        if not dont_save:
            self.save()

    def load(self):
        with open(self.sp, 'r') as f:
            values = json.loads(f.read())
            for k,v in values.items():
                self.values[k] = v

    def save(self):
        with open(self.sp, 'w') as f:
            f.write(json.dumps(self.values))

    def run_on(self, key, function_name, *args, dont_save = False, **kwargs):
        # Run a function on the value of a key
        # This is useful for changing the value of a key without getting it first
        # Example: run_on('list', 'append', 'a')

        # Get the value
        value = self.values[key]
        func = getattr(value, function_name)
        res = func(*args, **kwargs)
        if not dont_save:
            self.save()
        return res

version = 'bot'
settings = Settings(Path(__file__).parent / '.bot_settings', saveaddr = [], name = 'bot ivan')
state = 'wait'

def waitroomtick():
    global client, state
    if client.stopped:
        print("Connection to the server has been ended. If this is shouldn't have happened, check the 'client.log' file for the error.")
        return exit(0)

    if not client.in_menu:
        state == 'game'
        return

    if not client.is_ready:
        client.query_event("ready", True)

    if client.lobbypls:
        print("Host: " + client.lobbypls[0][0])
        for n, (name, ready) in enumerate(client.lobbypls):
            if ready:
                print(str(n + 1) + ": " + name + f" {fg(82)}(ready){attr('reset')}")
            else:
                print(str(n + 1) + ": " + name + f" {fg(196)}(not ready){attr('reset')}")
    else:
        print("Connecting...")

    if client.lastwinner is not None:
        print("Last winner: " + client.lastwinner)

def gametick():
    # TODO tomorrow
    # do a fancy thing that shows the cards, the table, the players, etc.
    # the ai will be made later
    pass

logdir = Path(__file__).parent / 'bot_logs'
logdir.mkdir(exist_ok=True, parents=True)

print("Please input the server address:")

client = Client(input("> "), version, settings)
client.start()

while True:
    clear()
    try:
        if state == 'wait':
            waitroomtick()
        else:
            gametick()

    except KeyboardInterrupt:
        client.stop()
        break

