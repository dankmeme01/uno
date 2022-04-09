# uhh

# this file will have all the defined stuff
# so you can access it from both main and networking
# like the table class
# it will have info about all players
# i will copy it from my previous uno
# and change a bit
# one moment please  щл 

from collections import namedtuple
import random

Card = namedtuple("Card", ["color", "type"])

cards: list[Card] = []
colors = ['red', 'blue', 'yellow', 'green']

for i in colors:
    cards.append(Card(i, 0))

for x in range(0,2):
    for i in range(1,10):
        for color in colors:
            cards.append(Card(color, i))
    for color in colors:
        cards.append(Card(color, 'block'))
        cards.append(Card(color, 'reverse'))
        cards.append(Card(color, '+2'))
    for i in range(0,4):
        cards.append(Card('wild', ['color', '+4'][x]))

# cards is a full deck of uno, 108 cards
# i need to clean this up though
# alot of garbage-

class Player:
    def __init__(self, name):
        self.deck : list[Card] = []
        self.name = name
        self.ready = False

    def getdeck(self):
        return self.deck

    def getname(self):
        return self.name
    
    def hascard(self, search):
        for card in self.deck:
            if card.color == search.color and card.type == search.type:
                return True
        return False

    def removecard(self, search):
        for n, card in self.deck:
            if card.color == search.color and card.type == search.type:
                self.deck.pop(n)
                return True
        return False 

class Table:
    def __init__(self):
        self.players = []
        self.clockwise = True
        # moving is index of player who is yet to place a card.
        self.moving = None
        self.deck = cards.copy()
        self.started = False
        self.lastwinner = None
        random.shuffle(self.deck)

    def add_player(self, playername):
        if self.started:
            raise ValueError("Game has already started.")
        self.players.append(Player(playername))

    def get_ready_players(self):
        n = 0
        for p in self.players:
            if p.ready:
                n += 1
        return n

    def check_all_ready(self):
        return self.get_ready_players() == len(self.players)

    def get_player(self, name):
        for i in self.players:
            if i.name == name:
                return i
        return None

    def indexof(self, name):
        for i in self.players:
            if i.name == name:
                return self.players.index(i)
        return None

    def start(self):
        topcard = random.choice(self.deck)
        self.topcard = topcard

        self.placedeck = [topcard]
        self.deck.remove(topcard)
        
        self.moving = random.randrange(0, len(self.players))
        self.started = True

    def can_place(self, card):
        return card.color == self.topcard.color or card.type == self.topcard.type or card.color == 'wild' or self.topcard.color == 'wild'

    def validate_move(self, player: Player, cardcolor, cardtype):
        card = Card(cardcolor, cardtype)
        return self.can_place(card) and player.hascard(card)
    
    def nextmoving(self):
        self.moving = self.moving + (1 if self.clockwise else -1)
        if self.moving == len(self.players):
            self.moving = 0
        elif self.moving == -1:
            self.moving = len(self.players) - 1

    def place(self, player: Player, cardcolor, cardtype):
        # no checks because we assume server is good :)
        card = Card(cardcolor, cardtype)
        player.removecard(card)
        self.placedeck.append(card)
        self.topcard = Card(ccolor, card.type)

        if card.color == 'wild':
            ccolor = random.choice(('red', 'blue', 'yellow', 'green')) # XXX ask the player
        else:
            ccolor = card.color
        
        nextplayer = self.moving + (1 if self.clockwise else -1)
        if nextplayer == len(self.players):
            nextplayer = 0
        elif nextplayer == -1:
            nextplayer = len(self.players) - 1

        if '+' in cardtype: # +4 or +2
            pl = self.players[nextplayer]
            for _ in range(0,int(cardtype[1:])):
                if len(self.deck) == 0:
                    self.deck = self.placedeck.copy()
                    random.shuffle(self.deck)
                    self.placedeck.clear()
                pl.deck.append(self.deck.pop())
            self.nextmoving()
        elif card['type'] == 'reverse':
            self.clockwise = not self.clockwise
        elif card['type'] == 'block':
            self.nextmoving()

        self.nextmoving()

        for i in self.players:
            if len(i.deck) == 0:
                self.started = False
                self.lastwinner = i.name
                break

    def draw(self, player: Player):
        if len(self.deck) == 0:
            self.deck = self.placedeck.copy()
            random.shuffle(self.deck)
            self.placedeck.clear()

        player.deck.append(self.deck.pop())
        self.nextmoving()

    def getplayer(self, name):
        plnames = [i.name for i in self.players]
        if name in plnames:
            for i in self.players:
                if i.name == name:
                    return i

        else:
            return None