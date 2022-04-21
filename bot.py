# This script is not recommended to use in actual games (because it's cheating duh)
# Originally created only for testing. The server knows if you're a bot or not. You can obviously change it but you will be an asshole then.

from networking import Client, LocalPlayer
from unoengine import Card
from pathlib import Path
from colored import bg, fg, attr
import random
import time
import json
import sys
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
        state = 'game'
        return

    if not client.is_ready:
        client.is_ready = client.query_event("ready", True)

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
    global state
    if not client.topcard:
        state = "wait"
        return

    more = []
    less = []
    myindex = client.myindex
    indextable = {}

    for player in client.players:
        indextable[player.index] = player
        if player.index > myindex:
            more.append(player.index)
        elif player.index < myindex:
            less.append(player.index)

    more.sort()
    less.sort()
    playersfixed: list[LocalPlayer] = [indextable[player] for player in (more + less)]
    tc = client.topcard
    print("Players:", ', '.join(f'{fg(82) if player.index == client.moving else ""}{player.name} ({player.cards} cards){attr("reset")}' for player in playersfixed), flush=False)
    print("Topcard:", tc[0], tc[1], flush=False)
    print("Clockwise:", client.clockwise, flush=False)
    print("Your deck:", ', '.join(' '.join(card) for card in client.deck), flush=False)

    sys.stdout.flush()

    if client.moving == client.myindex:
        time.sleep(0.65)
        BotAI.action_v2(client)

class BotAI:
    def can_place(topcard: Card, card: Card):
        """Returns whether or not a card can be placed on top of the topcard"""
        return card.color == topcard.color \
            or card.type == topcard.type \
            or card.color == 'wild' \
            or topcard.color == 'wild' \
            or card.type == 'color' \
            or card.type == '+4'

    def action_v1(client: Client):
        """First version of action function, not used anymore because a better ai is made in action_v2, this one just randomly draws cards"""
        assert client.moving == client.myindex
        matches = []
        mycolors = dict.fromkeys(('red', 'green', 'blue', 'yellow', 'wild'), 0)
        for card in client.deck:
            mycolors[card.color] += 1
            if BotAI.can_place(client.topcard, card):
                matches.append(card)

        mycolors = {k: v for k, v in sorted(mycolors.items(), key=lambda item: item[1])}

        if client.showdraw:
            client.draw_place()
            return

        if client.waiting_color:
            color = list(mycolors.keys())[-1]
            client.place_card(Card(color, client.waiting_color.type))
            client.waiting_color = False
            return

        if not matches:
            if client.moving == client.myindex:
                return client.draw()

        else:
            pick = random.choice(matches)
            if pick.color == 'wild':
                color = list(mycolors.keys())[-1]
                client.place_card(Card(color, pick.type))
            else:
                client.place_card(pick)

    def deck_to_colors(deck: list[Card]):
        """Get the dict of how many cards of each color are in the deck"""
        colors = dict.fromkeys(('red', 'green', 'blue', 'yellow', 'wild'), 0)
        for card in deck:
            colors[card.color] += 1
        return dict(sorted(colors.items(), key=lambda item: item[1]))

    def card_match_topcard(card: Card, topcard: Card, mydeck: list[Card]):
        """Returns a ratio (0, 1) of how good the move will be not taking in account other players, but only your deck and topcard. Will return 0 if the card can't be placed at all."""
        if not BotAI.can_place(topcard, card):
            return 0

        mycolors = BotAI.deck_to_colors(client.deck)
        # if we are switching color, then return a different ratio depending on how many cards do you have of that color
        if card.color != topcard.color and card.color != 'wild':
            return mycolors[card.color] / len(mydeck)

        if card.color == 'wild':
            # since we are putting a wild, we need to check if we could place a different card.
            # if we could not, then significantly increase the ratio
            could_place = 0
            for x in mydeck:
                if BotAI.can_place(topcard, x):
                    could_place += 1

            could_place -= 1 # remove this card itself

            # we don't want to return more than 1, so use a min function
            return min(0.33 + (1 / (could_place + 1)) * 1.1, 1)

        return 0.33

    def card_match_player(card: Card, nextplayer: LocalPlayer):
        """Returns a ratio (0, 1) of how good the card will be to play against the next player. If they have low cards, and a card either blocks them or gives them more cards, the ratio will be high."""
        # if its a block/reverse then return a ratio of 0.5 + (6 - nextplayer.cards) / 11
        if card.type == 'reverse' or card.type == 'block':
            return min(0.5 + (6 - nextplayer.cards) / 11, 1)

        # if its a +2 or a +4 then return a ratio of 0.6 + (6 - nextplayer.cards) / 10
        if card.type == '+2' or card.type == '+4':
            return min(0.6 + (6 - nextplayer.cards) / 10, 1)

        # NOTE: the values above may need some balancing. i just took random numbers that looked good.
        # if the card is a color card, return 0.4
        if card.type == 'color':
            return 0.4

        # if the card is none of the above, this
        return 0.2

    def card_match_ratio(card, topcard, nextplayer, mydeck):
        """Returns a value calculated by card_match_topcard and card_match_player"""
        v1 = BotAI.card_match_topcard(card, topcard, mydeck)
        v2 = BotAI.card_match_player(card, nextplayer)

        if v1 == 0:
            return 0

        product = v1 * v2
        sum = v1 + v2
        return product * sum + max(v1, v2) / 2 # idk why lol XXX

    def action_v2(client: Client):
        """Second version of action function, this one is more intelligent and tries to play the best card possible"""
        assert client.moving == client.myindex

        # g
        mycolors = BotAI.deck_to_colors(client.deck)

        # this is the next player after us
        nextp = client.players[(client.myindex + (1 if client.clockwise else -1)) % len(client.players)]

        best_match = (0, None)
        for card in client.deck:
            match = BotAI.card_match_ratio(card, client.topcard, nextp, client.deck)
            if match > best_match[0]:
                best_match = (match, card)

        # do stuff
        if client.showdraw:
            client.draw_place()
            return

        if client.waiting_color:
            color = list(mycolors.keys())[-1]
            client.place_card(Card(color, client.waiting_color.type))
            client.waiting_color = False
            return

        if not best_match[1]:
            # a guard just in case, might be unnecessary
            if client.moving == client.myindex:
                return client.draw()

        else:
            card = best_match[1]
            if card.color == 'wild':
                color = list(mycolors.keys())[-1]
                client.place_card(Card(color, card.type))
            else:
                client.place_card(card)

logdir = Path(__file__).parent / 'bot_logs'
logdir.mkdir(exist_ok=True, parents=True)

print("Please input the server address:")

client = Client(input("> "), version, settings, bot=True)
client.start()

while True:
    clear()
    #print('\n', flush=False)
    try:
        if state == 'wait':
            waitroomtick()
        else:
            gametick()

        time.sleep(0.2)
    except KeyboardInterrupt:
        client.stop()
        break

