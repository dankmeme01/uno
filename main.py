from pygame.locals import *
from classes import *
from networking import Client, Server
from unoengine import card_to_id, id_to_card, Card
import pygame
import socket

__version__ = "1.6-pre5"
# i don't know if this bug still exists, but i wont remove this yet
# +4 sometimes gives 12 cards (lmao)

SCREENSIZE = (1000, 600)
screen = pygame.display.set_mode(SCREENSIZE)
clock = pygame.time.Clock()

settingpath = Path(__file__).parent / '.settings'
if settingpath.exists():
    settings = Settings.load(settingpath)
else:
    settings = Settings(name=socket.gethostname())
    settings.save(settingpath)

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

#menu
hostbtn = Button(None, None, 500, 170, host_game, Text(48, "Host Game", (127, 127, 127), (255, 255, 255)))
ipaddrentry = Entry(200, 50, 500, 300, maxchars=15, bgcolor=(127, 127, 127), fgcolor=(165, 165, 165), textcolor=(255, 255, 255), emptytext="IP Address", fontsize=24)
clientbtn = Button(None, None, 500, 380, lambda: connect_to_game(ipaddrentry.get()), Text(48, "Connect", (127, 127, 127), (255, 255, 255)))
lhostbtn = Button(None, None, 950, 575, lambda: ipaddrentry.set(socket.gethostbyname(socket.gethostname())), Text(24, "Localhost", (127, 127, 127), (255, 255, 255)))
open_settings = Button(None, None, 50, 575, lambda: set_state('settings'), Text(24, "Settings", (127, 127, 127), (255, 255, 255)))

#waitroom
readybtn = Button(None, None, 500, 500, lambda: global_client.ready(), Text(32, "Ready", (127, 127, 127), (255, 255, 255)))
infomsg = Label(None, None, 500, 110, Text(32, "Waiting for other players...", None, (255, 255, 255)))
readystatus = Label(None, None, 500, 450, Text(32, "Not ready", None, (255, 0, 0)))

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
drewncards = []

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
    settings.save(settingpath)

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

        pass_event(event, hostbtn, ipaddrentry, clientbtn, lhostbtn, open_settings)

    update_objects(hostbtn, ipaddrentry, clientbtn, lhostbtn, open_settings)

    if global_client:
        state = 'wait'

def waitroomtick():
    global game_on, global_client, localready, state
    for event in pygame.event.get():
        if event.type == QUIT:
            return stop_game()

        pass_event(event, readybtn, iplbl if not shown_addr else addrlbl)

    cl: Client = global_client
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
    global global_client, drewncards, state
    cl: Client = global_client
    if not cl.topcard:
        state = "wait"
        return

    if cl.stopped:
        print("Connection to the server has been ended.")
        return stop_game()

    def draw_players():
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

            match len(playersfixed):
                case 1 | 2 | 3:
                    fontsize = 24
                case 4:
                    fontsize = 20
                case 5:
                    fontsize = 18
                case 6:
                    fontsize = 16
                case 7:
                    fontsize = 14
                case 8:
                    fontsize = 12
                case _:
                    fontsize = 8

            name = Text(fontsize, p.name, None, (255, 255, 255) if p.index != cl.moving else (0, 255, 0))
            screen.blit(name.surface, name.surface.get_rect(center=(px, py)))
            # draw their card amount

            card = Text(fontsize, f"{p.cards} cards", None, (255, 255, 255))
            screen.blit(card.surface, card.surface.get_rect(center=(px, py + 30)))
            thisone += 1

    def draw_deck():
        drewncards.clear()
        for n, c in enumerate(cl.deck):
            card = cardsheet.get_sprite(card_to_id(c))
            midindex = len(cl.deck) // 2
            cardwidth = card.get_rect().width

            if len(cl.deck) > 1:
                diff = ((SCREENSIZE[0] - 2*cardwidth) / (len(cl.deck) - 1))
                if diff > cardwidth:
                    diff = cardwidth
                x = SCREENSIZE[0] / 2 + (n - midindex) * diff
                if len(cl.deck) % 2 == 0:
                    x += cardwidth / 2
            else:
                x = SCREENSIZE[0] / 2

            y = SCREENSIZE[1] - 50
            rect = card.get_rect(center=(x, y))
            drewncards.append( (card_to_id(c), rect) )
            screen.blit(card, rect)

    def draw_topcard_indicators():
        # now draw the topcard
        topcard = cardsheet.get_sprite(card_to_id(cl.topcard))
        if not topcard:
            print("Card not found:", card_to_id(cl.topcard))
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

            elif event.type == MOUSEBUTTONUP:
                if cl.moving == cl.myindex and not cl.waiting_color:
                    update_card_choice()

                elif cl.moving == cl.myindex and not not cl.waiting_color:
                    update_color_choice()
            
            if cl.showdraw:
                pass_event(event, draw_place, draw_take)
            elif not cl.waiting_color and cl.moving == cl.myindex:
                pass_event(event, drawbtn)

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


    draw_players()
    draw_deck()
    draw_topcard_indicators()
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
