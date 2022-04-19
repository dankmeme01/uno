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

CARD_AMOUNT = 7

Card = namedtuple("Card", ["color", "type"])

cards: list[Card] = []
colors = ['red', 'blue', 'yellow', 'green']

# XXX we will need zeros but theyre not in the sheet fsr
#for i in colors:
#    cards.append(Card(i, '0'))

for x in range(0,2):
    for i in range(1,10):
        for color in colors:
            cards.append(Card(color, str(i)))
    for color in colors:
        cards.append(Card(color, 'block'))
        cards.append(Card(color, 'reverse'))
        cards.append(Card(color, '+2'))
    for i in range(0,4):
        cards.append(Card('wild', ['color', '+4'][x]))

# cards is a full deck of uno, 108 cards
# i need to clean this up though
# alot of garbage-

def card_to_id(card: Card) -> str:
    if type(card) == list:
        card = Card(*card)
    return card.color + '_' + str(card.type)

def id_to_card(id: str) -> Card:
    return Card(*id.split('_'))

class Player:
    def __init__(self, name):
        self.deck : list[Card] = []
        self.name = name
        self.ready = False
        self.waiting_action = False

    def getdeck(self):
        return self.deck

    def getname(self):
        return self.name

    def hascard(self, search):
        for card in self.deck:
            if card.color == search.color \
            or card.type == search.type \
            or card.color == 'wild' \
            or search.color == 'wild' \
            or card.type == 'color' \
            or card.type == '+4':
                return True
        return False

    def removecard(self, search):
        for n, card in enumerate(self.deck):
            if (card.color == search.color or search.type in ('+4', 'color')) and card.type == search.type:
                self.deck.pop(n)
                return True
        return False

class Table:
    def __init__(self):
        self.players: list[Player] = []
        self.clockwise = True
        self.deck = []
        # moving is index of player who is yet to place a card.
        self.moving = None
        self.started = False
        self.lastwinner = None

    def add_player(self, playername):
        if self.started:
            raise ValueError("Game has already started.")
        self.players.append(Player(playername))

    def remove_player(self, playername):
        player = self.getplayer(playername)
        pindex = self.players.index(player)
        cachemoving = False
        if self.moving == pindex:
            cachemoving = True

        self.players.pop(pindex)
        if cachemoving:
            self.nextmoving()

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

    def check_cards(self):
        if len(self.deck) == 0:
            self.deck = self.placedeck.copy()
            self.deck.remove(self.topcard)
            random.shuffle(self.deck)
            for n, card in enumerate(self.deck):
                if card.type in ('color', '+4'):
                    self.deck[n] = Card('wild', card.type)
            self.placedeck.clear()
            self.placedeck.append(self.topcard)

    def start(self):
        self.clockwise = True
        self.deck = cards.copy()
        topcard = random.choice(self.deck)
        self.deck.remove(topcard)
        random.shuffle(self.deck)

        if topcard.color == 'wild':
            topcard = Card(random.choice(colors), topcard.type)
        self.topcard = topcard

        self.placedeck = [topcard]

        for player in self.players:
            player.ready = False
            player.waiting_action = False
            player.deck = []

            for _ in range(0, CARD_AMOUNT):
                player.deck.append(self.deck.pop())
                self.check_cards()

        self.moving = random.randrange(0, len(self.players))
        self.started = True

    def can_place(self, card):
        return card.color == self.topcard.color \
            or card.type == self.topcard.type \
            or card.color == 'wild' \
            or self.topcard.color == 'wild' \
            or card.type == 'color' \
            or card.type == '+4'

    def validate_move(self, player: Player, card):
        return self.can_place(card) and player.hascard(card)

    def nextmoving(self):
        self.moving = self.moving + (1 if self.clockwise else -1)
        if self.moving >= len(self.players):
            self.moving = 0
        elif self.moving == -1:
            self.moving = len(self.players) - 1

    def place(self, player: Player, card):
        # no checks because we assume server is good :)
        player.removecard(card)
        self.placedeck.append(card)

        if card.color == 'wild':
            ccolor = random.choice(colors) # XXX ask the player
        else:
            ccolor = card.color

        self.topcard = Card(ccolor, card.type)

        nextplayer = self.moving + (1 if self.clockwise else -1)
        if nextplayer == len(self.players):
            nextplayer = 0
        elif nextplayer == -1:
            nextplayer = len(self.players) - 1

        if '+' in card.type: # +4 or +2
            pl = self.players[nextplayer]
            for _ in range(0,int(card.type[1:])):
                self.check_cards()
                pl.deck.append(self.deck.pop())
            self.nextmoving()
        elif card.type == 'reverse':
            self.clockwise = not self.clockwise
            # official uno rules state that with 2 players, a reverse is same as block.
            if len(self.players) == 2:
                self.nextmoving()
        elif card.type == 'block':
            self.nextmoving()

        self.nextmoving()

        for i in self.players:
            if len(i.deck) == 0:
                self.started = False
                self.lastwinner = i.name
                break

    def draw(self, player: Player) -> Card:
        self.check_cards()
        card = self.deck.pop()
        if not self.can_place(card):
            player.deck.append(card)
            self.nextmoving()
            return False
        return card

    def getplayer(self, name):
        plnames = [i.name for i in self.players]
        if name in plnames:
            for i in self.players:
                if i.name == name:
                    return i

        else:
            return None