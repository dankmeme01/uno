from pygame.locals import *
from classes import *
from networking import Client, Server
from threading import Thread
import pygame
import socket

SCREENSIZE = (1000, 600)
screen = pygame.display.set_mode(SCREENSIZE)
clock = pygame.time.Clock()

global_server = None
global_client = None

game_on = True

state = 'menu'

def connect_to_game(addr):
    global global_client
    if not global_client:
        global_client = Client(addr)
        global_client.start()

def host_game():
    global global_server
    if not global_server:
        global_server = Server()
        global_server.start()
        while not global_server.address:
            pass
        connect_to_game(global_server.address)

#menu
hostbtn = Button(None, None, 500, 170, host_game, Text(48, "Host Game", (127, 127, 127), (255, 255, 255)))
ipaddrentry = Entry(200, 50, 500, 300, maxchars=15, bgcolor=(127, 127, 127), fgcolor=(165, 165, 165), textcolor=(255, 255, 255), emptytext="IP Address", fontsize=24)
clientbtn = Button(None, None, 500, 380, lambda: connect_to_game(ipaddrentry.get()), Text(48, "Connect", (127, 127, 127), (255, 255, 255)))
lhostbtn = Button(None, None, 950, 575, lambda: ipaddrentry.set(socket.gethostbyname(socket.gethostname())), Text(24, "Localhost", (127, 127, 127), (255, 255, 255)))

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
cardsheet = Spritesheet(str(Path(__file__).parent / 'cards.png'))



def stop_game():
    global game_on, global_client, global_server
    game_on = False
    if global_client:
        global_client.stop()
        global_client = None
    if global_server:
        global_server.stop()
        global_server = None

def pass_event(event, *objects):
    for obj in objects:
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

        pass_event(event, hostbtn, ipaddrentry, clientbtn, lhostbtn)

    update_objects(hostbtn, ipaddrentry, clientbtn, lhostbtn)

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


    update_objects(readybtn, infomsg, readystatus, hostlbl, totalplbl, iplbl if not shown_addr else addrlbl)

def gametick():
    pass

while game_on:
    screen.fill((0, 0, 0))
    if state == 'menu':
        menutick()
    elif state == 'wait':
        waitroomtick()
    else:
        gametick()
    
    clock.tick(60)
    pygame.display.flip()
