from pygame.locals import *
from classes import *
from networking import Client, LocalPlayer, Server
from unoengine import card_to_id, id_to_card, Card
import pygame
import socket

__version__ = "1.8.1"

SCREENSIZE = (1000, 600)
screen = pygame.display.set_mode(SCREENSIZE)
clock = pygame.time.Clock()

settingpath = Path(__file__).parent / '.settings'
settings = Settings(settingpath, name=socket.gethostname(), saveaddr=[])

global_server = None
global_client = None

game_on = True

state = 'menu'

def connect_to_game(addr):
    global global_client, ipaddrentry
    if not global_client:
        try:
            global_client = Client(addr, __version__, settings)
            global_client.start()
            if not addr in settings.get('saveaddr'):
                settings.run_on('saveaddr', 'append', addr)
        except Exception as e:
            global_client = None
            print(e)
            ipaddrentry.set('')


def host_game():
    global global_server
    if not global_server:
        global_server = Server(__version__, settings)
        global_server.start()
        while not global_server.address:
            pass
        connect_to_game(global_server.address)

def set_state(state2: str):
    global state
    state = state2

def switch_ip():
    global menuipindex
    if not menuipindex:
        menuipindex = len(settings.get('saveaddr'))

    menuipindex -= 1
    if menuipindex < 0:
        menuipindex = 0

    ipaddrentry.set(settings.get('saveaddr')[menuipindex])

#menu
hostbtn = Button(None, None, 500, 170, host_game, Text(48, "Host Game", (127, 127, 127), (255, 255, 255)))
ipaddrentry = Entry(200, 50, 500, 300, maxchars=15, bgcolor=(127, 127, 127), fgcolor=(165, 165, 165), textcolor=(255, 255, 255), emptytext="IP Address", fontsize=24)
clientbtn = Button(None, None, 500, 380, lambda: connect_to_game(ipaddrentry.get()), Text(48, "Connect", (127, 127, 127), (255, 255, 255)))
lhostbtn = Button(None, None, 950, 575, lambda: ipaddrentry.set(socket.gethostbyname(socket.gethostname())), Text(24, "Localhost", (127, 127, 127), (255, 255, 255)))
open_settings = Button(None, None, 50, 575, lambda: set_state('settings'), Text(24, "Settings", (127, 127, 127), (255, 255, 255)))
recentip_btn = Button(None, None, 940, 25, switch_ip, Text(24, "Insert last IP", (127, 127, 127), (255, 255, 255)))
menuipindex = None

#waitroom
readybtn = Button(None, None, 500, 500, lambda: global_client.ready(), Text(32, "Ready", (127, 127, 127), (255, 255, 255)))
infomsg = Label(None, None, 500, 110, Text(32, "Connecting...", None, (255, 255, 255)))
readystatus = Label(None, None, 500, 450, Text(32, "Not ready", None, (255, 0, 0)))
set_other_waitroom_title = False

def set_shownaddr():
    global shown_addr, iplbl, global_client
    shown_addr = True
    addrlbl.set_display(Text(28, "Server IP: " + global_client.serv_addr, None, (255, 255, 255)))

hostlbl = Label(None, None, 500, 160, Text(28, "Host:", None, (255, 255, 255)))
iplbl = Button(None, None, 500, 195, set_shownaddr, Text(28, "Click to show address", (127, 127, 127), (255, 255, 255)))
addrlbl = Label(None, None, 500, 195, Text(28, "Server IP:", None, (255, 255, 255)))
totalplbl = Label(None, None, 500, 260, Text(28, "Players", None, (255, 255, 255)))

shown_addr = False
localready = False

#game
cardsheet = Spritesheet(str(Path(__file__).parent / 'cards.png'), 50)
drawbtn = Button(None, None, 930, 465, lambda: global_client.draw(), Text(30, "Draw", (127, 127, 127), (255, 255, 255)))
draw_take = Button(None, None, 870, 450, lambda: global_client.draw_take(), Text(30, "Take", (127, 127, 127), (255, 255, 255)))
draw_place = Button(None, None, 960, 450, lambda: global_client.draw_place(), Text(30, "Place", (127, 127, 127), (255, 255, 255)))
card_back = pygame.image.load(str(Path(__file__).parent / 'cardback.png'))
card_back = pygame.transform.scale(card_back, (50, 282 * (50 / 188)))
topcard_cache = None
topcard_saved = None
topcard_cachetimer = None
deck_cachelen = None
deck_cachesaved = None
deck_cachetimer = None
anim_state = {}
animbuffer = []
drewncards = []
drewnplayers = []

#settings
curname = Label(None, None, 500, 100, Text(32, "Current name:", None, (255, 255, 255)))
name_entry = Entry(200, 50, 500, 300, maxchars=24, bgcolor=(127, 127, 127), fgcolor=(165, 165, 165), textcolor=(255, 255, 255), emptytext="Type new name here", fontsize=24)
set_name = Button(None, None, 500, 360, lambda: set_my_name(name_entry.get()), Text(36, "Set name", (127, 127, 127), (255, 255, 255)))
default_name = Button(None, None, 500, 440, lambda: set_my_name(socket.gethostname()), Text(36, "Set default name", (127, 127, 127), (255, 255, 255)))
close_settings = Button(None, None, 40, 575, lambda: set_state('menu'), Text(24, "Back", (127, 127, 127), (255, 255, 255)))
version_lbl = Label(None, None, 500, 575, Text(24, "Version: " + __version__, None, (255, 255, 255)))

def stop_game():
    global game_on, global_client, global_server
    game_on = False
    if global_client and not global_client.stopped:
        global_client.stop()
        global_client = None
    if global_server and not global_server.stopped:
        global_server.stop()
        global_server = None

    pygame.quit()
    print("Bye!")
    exit(0)

def set_my_name(name: str):
    settings.set('name', name)

def pass_event(event, *objects):
    for obj in objects:
        if obj:
            obj.on_event(event)

def update_objects(*objects):
    for obj in objects:
        obj.update()
        obj.draw(screen)

def menutick():
    global game_on, global_client, state
    for event in pygame.event.get():
        if event.type == QUIT:
            return stop_game()

        pass_event(event, hostbtn, ipaddrentry, clientbtn, lhostbtn, open_settings, recentip_btn)

    update_objects(hostbtn, ipaddrentry, clientbtn, lhostbtn, open_settings, recentip_btn)

    if global_client:
        state = 'wait'

def waitroomtick():
    global game_on, global_client, localready, state, set_other_waitroom_title
    for event in pygame.event.get():
        if event.type == QUIT:
            return stop_game()

        pass_event(event, readybtn, iplbl if not shown_addr else addrlbl)

    cl: Client = global_client

    if cl.stopped:
        print("Connection to the server has been ended. If this is shouldn't have happened, check the 'client.log' file for the error.")
        return stop_game()

    if not cl.in_menu:
        state = 'game'
        return

    if cl.is_ready != localready:
        localready = cl.is_ready
    if localready:
        readystatus.set_display(Text(24, "Ready", None, (0, 255, 0)))
    else:
        readystatus.set_display(Text(24, "Not ready", None, (255, 0, 0)))

    if cl.lobbypls:
        if not set_other_waitroom_title:
            set_other_waitroom_title = True
            infomsg.set_display(Text(32, "Waiting for other players...", None, (255, 255, 255)))
        hostlbl.set_display(Text(28, "Host: " + cl.lobbypls[0][0], None, (255, 255, 255)))
        for n, (name, ready) in enumerate(cl.lobbypls):
            # display each of the names with a distance of 40 pixels vertically
            x = 500
            y = 290 + 20 * n
            text = Text(24, name, None, (0, 255, 0) if ready else (255, 0, 0))
            screen.blit(text.surface, text.surface.get_rect(center=(x, y)))

    if cl.lastwinner is not None:
        txt = Text(32, "Last winner: " + cl.lastwinner, None, (255, 255, 0))
        screen.blit(txt.surface, txt.surface.get_rect(center=(500, 70)))

    update_objects(readybtn, infomsg, readystatus, hostlbl, totalplbl, iplbl if not shown_addr else addrlbl)

def gametick():
    global global_client, drewncards, state, anim_state, animbuffer, drewnplayers
    cl: Client = global_client

    def draw_players():
        drewnplayers.clear()
        thisone = 0
        playersfixed = []
        more = []
        less = []
        myindex = cl.myindex
        indextable = {}

        for player in cl.players:
            indextable[player.index] = player
            if player.index > myindex:
                more.append(player.index)
            elif player.index < myindex:
                less.append(player.index)
        more.sort()
        less.sort()
        playersfixed = [indextable[player] for player in (more + less)]

        for p in playersfixed:
            midindex = (len(cl.players) - 1) // 2

            px = SCREENSIZE[0] / 2 + (thisone - midindex) * (SCREENSIZE[0] / (len(cl.players) - 1))
            py = 50
            # draw their name

            namewidth = SCREENSIZE[0] / 4
            if len(playersfixed) % 2 == 0:
                px += namewidth

            if len(playersfixed) <= 3:
                fontsize = 24
            elif len(playersfixed) == 4:
                fontsize = 20
            elif len(playersfixed) == 5:
                fontsize = 18
            elif len(playersfixed) == 6:
                fontsize = 16
            elif len(playersfixed) == 7:
                fontsize = 14
            elif len(playersfixed) == 8:
                fontsize = 12
            else:
                fontsize = 8

            name = Text(fontsize, p.name, None, (255, 255, 255) if p.index != cl.moving else (0, 255, 0))
            screen.blit(name.surface, name.surface.get_rect(center=(px, py)))
            # draw their card amount

            card = Text(fontsize, f"{p.cards} cards", None, (255, 255, 255))
            screen.blit(card.surface, card.surface.get_rect(center=(px, py + 30)))
            drewnplayers.append((name, p.index, p.cards, px, py))
            thisone += 1

    def draw_deck():
        global deck_cachesaved, deck_cachelen, deck_cachetimer
        drewncards.clear()
        if deck_cachelen is None:
            deck_cachelen = len(cl.deck)
            deck_cachesaved = len(cl.deck)

        elif len(cl.deck) > deck_cachelen:
            cardmod = 5 * (len(cl.deck) - deck_cachelen - 1)
            if deck_cachesaved and len(cl.deck) != deck_cachesaved:
                deck_cachesaved = len(cl.deck)
                deck_cachetimer = 25 + cardmod

            elif deck_cachetimer == None:
                deck_cachesaved = len(cl.deck)
                deck_cachetimer = 25 + cardmod

            deck_cachetimer -= 1
            if deck_cachetimer == 0:
                deck_cachelen = deck_cachesaved
                deck_cachetimer = None
            elif deck_cachetimer <= cardmod and deck_cachetimer % 5 == 0:
                deck_cachelen += 1

        diff = deck_cachesaved - deck_cachelen
        animcardlist = cl.deck[:-diff] if diff > 0 else cl.deck

        for n, c in enumerate(animcardlist):
            card = cardsheet.get_sprite(card_to_id(c))
            midindex = len(animcardlist) // 2
            cardwidth = card.get_rect().width

            if len(animcardlist) > 1:
                diff = ((SCREENSIZE[0] - 2*cardwidth) / (len(animcardlist) - 1))
                if diff > cardwidth:
                    diff = cardwidth
                x = SCREENSIZE[0] / 2 + (n - midindex) * diff
                if len(animcardlist) % 2 == 0:
                    x += cardwidth / 2
            else:
                x = SCREENSIZE[0] / 2

            y = SCREENSIZE[1] - 50
            rect = card.get_rect(center=(x, y))
            drewncards.append( (card_to_id(c), rect) )
            screen.blit(card, rect)

    def draw_topcard_indicators():
        global topcard_cache, topcard_cachetimer, topcard_saved

        # this is very weird but it works (?)
        if not topcard_cache:
            topcard_cache = cl.topcard

        elif cl.topcard != topcard_cache:
            if topcard_saved and cl.topcard != topcard_saved:
                topcard_saved = cl.topcard
                topcard_cachetimer = 30

            elif topcard_cachetimer == None:
                topcard_saved = cl.topcard
                topcard_cachetimer = 30

            topcard_cachetimer -= 1
            if topcard_cachetimer == 0:
                topcard_cache = topcard_saved
                topcard_cachetimer = None

        # now draw the topcard
        topcard = cardsheet.get_sprite(card_to_id(topcard_cache))
        if not topcard:
            print("Card not found:", card_to_id(topcard_cache))
        screen.blit(topcard, topcard.get_rect(center=(SCREENSIZE[0] / 2, SCREENSIZE[1] / 2)))


        # if we are moving, say that to the player
        if cl.moving == cl.myindex:
            infot = Text(36, "It's your turn!", None, (255, 0, 99))
            screen.blit(infot.surface, infot.surface.get_rect(center=(SCREENSIZE[0] / 2, SCREENSIZE[1] / 2 + 150)))

        # if we are currently drawing a card, draw that to the screen
        if global_client.showdraw:
            card = cardsheet.get_sprite(card_to_id(global_client.showdraw))
            screen.blit(card, card.get_rect(center=(915, 400)))

        if not not cl.waiting_color:
            # draw four squares for color selection in a 2x2 square
            colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
            for n, color in enumerate(colors):
                x = 890 if n % 2 == 1 else 940
                y = 400 + n // 2 * 50
                surf = pygame.Surface((45, 45))
                surf.fill(color)
                screen.blit(surf, surf.get_rect(center=(x, y)))

    def draw_drawbtn():
        if cl.showdraw:
            update_objects(draw_take, draw_place)
        elif not cl.waiting_color and cl.moving == cl.myindex:
            update_objects(drawbtn)

    def update_color_choice():
        colors = ("red","green","blue","yellow")
        crects = {}
        for n, color in enumerate(colors):
            x = 890 if n % 2 == 1 else 940
            y = 400 + n // 2 * 50
            crects[color] = pygame.Surface((45, 45)).get_rect(center=(x, y))

        for color, rect in crects.items():
            if rect.collidepoint(pygame.mouse.get_pos()):
                cl.place_card(Card(color, cl.waiting_color.type))
                cl.waiting_color = False
                break

    def update_card_choice():
        for cardid, rect in drewncards[::-1]: # reverse the list so it works better if you have too many cards
            mpos = pygame.mouse.get_pos()
            if rect.collidepoint(mpos):
                if id_to_card(cardid).color == 'wild':
                    cl.waiting_color = id_to_card(cardid)
                    break
                cl.place_card(cardid)
                break

    def update_draw_check_mousebtn():
        for event in pygame.event.get():
            if event.type == QUIT:
                return stop_game()

            if cl.showdraw:
                pass_event(event, draw_place, draw_take)
                return
            elif not cl.waiting_color and cl.moving == cl.myindex:
                pass_event(event, drawbtn)

            if event.type == MOUSEBUTTONUP:
                if cl.moving == cl.myindex and not cl.waiting_color:
                    update_card_choice()

                elif cl.moving == cl.myindex and not not cl.waiting_color:
                    update_color_choice()

    def draw_clockwise():
        # draw the base lines for arrow
        pygame.draw.lines(screen, (255, 0, 25), False,
            ((SCREENSIZE[0] / 2 - 20, SCREENSIZE[1] / 2 - 65), # above the card
             (SCREENSIZE[0] / 2 - 55, SCREENSIZE[1] / 2 - 65), # left top of the card
             (SCREENSIZE[0] / 2 - 55, SCREENSIZE[1] / 2 + 65), # left bottom of the card
             (SCREENSIZE[0] / 2 - 20, SCREENSIZE[1] / 2 + 65)) # below the card
        , 4)

        # now the right side
        pygame.draw.lines(screen, (255, 0, 25), False,
            ((SCREENSIZE[0] / 2 + 20, SCREENSIZE[1] / 2 - 65), # above the card
             (SCREENSIZE[0] / 2 + 55, SCREENSIZE[1] / 2 - 65), # right top of the card
             (SCREENSIZE[0] / 2 + 55, SCREENSIZE[1] / 2 + 65), # right bottom of the card
             (SCREENSIZE[0] / 2 + 20, SCREENSIZE[1] / 2 + 65)) # below the card
        , 4)

        if cl.clockwise:
            # draw the arrow on the left
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 - 20, SCREENSIZE[1] / 2 - 65), (SCREENSIZE[0] / 2 - 30, SCREENSIZE[1] / 2 - 75), 4)
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 - 20, SCREENSIZE[1] / 2 - 65), (SCREENSIZE[0] / 2 - 30, SCREENSIZE[1] / 2 - 55), 4)
            # draw the arrow on the right
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 + 20, SCREENSIZE[1] / 2 + 65), (SCREENSIZE[0] / 2 + 30, SCREENSIZE[1] / 2 + 75), 4)
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 + 20, SCREENSIZE[1] / 2 + 65), (SCREENSIZE[0] / 2 + 30, SCREENSIZE[1] / 2 + 55), 4)
        else:
            # draw the arrow on the left
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 - 20, SCREENSIZE[1] / 2 + 65), (SCREENSIZE[0] / 2 - 30, SCREENSIZE[1] / 2 + 75), 4)
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 - 20, SCREENSIZE[1] / 2 + 65), (SCREENSIZE[0] / 2 - 30, SCREENSIZE[1] / 2 + 55), 4)
            # draw the arrow on the right
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 + 20, SCREENSIZE[1] / 2 - 65), (SCREENSIZE[0] / 2 + 30, SCREENSIZE[1] / 2 - 75), 4)
            pygame.draw.line(screen, (255, 0, 25), (SCREENSIZE[0] / 2 + 20, SCREENSIZE[1] / 2 - 65), (SCREENSIZE[0] / 2 + 30, SCREENSIZE[1] / 2 - 55), 4)

    def collect_anim_state():
        return {
            'topcard': cl.topcard,
            'clockwise': cl.clockwise,
            'moving': cl.moving,
            'players': cl.players
        }

    def anim_tick():
        global anim_state, animbuffer
        newstate = collect_anim_state()
        if newstate != anim_state:
            cardcache = {}
            # if a player took +2 or +4, display that
            for old_p, new_p in zip(anim_state['players'], newstate['players']):
                cardcache[old_p.index] = (old_p.cards, new_p.cards)
                old_p: LocalPlayer
                new_p: LocalPlayer

                if old_p.cards < new_p.cards:
                    amount = new_p.cards - old_p.cards
                    if new_p.index == cl.myindex:
                        px, py = (SCREENSIZE[0] / 2, SCREENSIZE[1] - 50)
                    else:
                        for name, index, cards, px, py in drewnplayers:
                            if index == new_p.index:
                                break
                        else:
                            raise ValueError('Player not found with index %s' % new_p.index)

                    for i in range(amount):
                        animbuffer.append([ tuple(drawbtn.pos), (px, py), card_back, 30, 30, 3 * i])
            # detect the change
            prev_moving = anim_state['moving']
            if prev_moving == cl.myindex:
                old_cards, new_cards = cardcache[prev_moving]
                if old_cards >= new_cards:
                    surf = cardsheet.get_sprite(card_to_id(newstate['topcard']))
                    animbuffer.append([ (SCREENSIZE[0] / 2, SCREENSIZE[1] - 50 ), (SCREENSIZE[0] / 2, SCREENSIZE[1] / 2), surf, 30, 30, 0 ])
                else:
                    # we drew the card
                    animbuffer.append([ tuple(drawbtn.pos), (SCREENSIZE[0] / 2, SCREENSIZE[1] - 50), card_back, 30, 30, 0 ])
            else:
                for name, index, cards, px, py in drewnplayers:
                    if index == prev_moving:
                        # if the topcard changed they placed it
                        if newstate['topcard'] != anim_state['topcard']:
                            # get topcard as surface, from the spritesheet
                            surf = cardsheet.get_sprite(card_to_id(newstate['topcard']))
                            animbuffer.append([ (px, py), (SCREENSIZE[0] / 2, SCREENSIZE[1] / 2), surf, 30, 30, 0 ])
                        else:
                            # they drew the card
                            animbuffer.append([ tuple(drawbtn.pos), (px, py), card_back, 30, 30, 0 ])

            anim_state = newstate

        animbuffer = [[s,d,r,t,st,w] for (s,d,r,t,st,w) in animbuffer if t > 0]

        for index, (source, dest, surface, tick, start_tick, wait_ticks) in enumerate(animbuffer):
            if wait_ticks > 0:
                wait_ticks -= 1
            else:
                tick -= 1
                diff = (dest[0] - source[0], dest[1] - source[1]) # also divide by the tick difference
                pos = (diff[0] / start_tick * (start_tick - tick), diff[1] / start_tick * (start_tick - tick))
                screen.blit(surface, surface.get_rect(center=(source[0] + pos[0], source[1] + pos[1])))
            animbuffer[index] = (source, dest, surface, tick, start_tick, wait_ticks)

    if not cl.topcard:
        if len(animbuffer) > 0:
            anim_tick()
        elif topcard_cachetimer and topcard_cachetimer > 0:
            pass
        else:
            state = "wait"
        return

    if cl.stopped:
        print("Connection to the server has been ended. If this is shouldn't have happened, check the 'client.log' file for the error.")
        return stop_game()


    if not anim_state:
        draw_players()
        anim_state = collect_anim_state()

    draw_topcard_indicators()

    anim_tick()

    draw_players()
    draw_deck()


    draw_drawbtn()

    # we don't need the arrows if there are 2 people.
    if len(cl.players) > 2:
        draw_clockwise()

    update_draw_check_mousebtn()


def settingstick():
    for event in pygame.event.get():
        if event.type == QUIT:
            return stop_game()

        elif event.type == KEYDOWN and event.key == K_ESCAPE:
            return set_state('menu')

        pass_event(event, name_entry, set_name, default_name, close_settings)

    curname.set_display(Text(32, "Current name: %s" % settings.get('name'), None, (255, 255, 255)))
    update_objects(curname, name_entry, set_name, default_name, close_settings, version_lbl)

print("Starting up UNO version", __version__)
logdir = Path(__file__).parent / 'logs'
logdir.mkdir(exist_ok=True, parents=True)

while game_on:
    try:
        screen.fill((0, 0, 0))
        if state == 'menu':
            menutick()
        elif state == 'wait':
            waitroomtick()
        elif state == 'settings':
            settingstick()
        else:
            gametick()

        clock.tick(60)
        pygame.display.flip()
    except KeyboardInterrupt:
        stop_game()
