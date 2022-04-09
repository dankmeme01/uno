from pathlib import Path
import pygame
import sys, os

sys.path.insert(1, os.path.join(sys.path[0], '..')) 
from classes import Spritesheet

cardsheet = Spritesheet(str(Path(__file__).parent.parent / 'cards.png'))
outfolder = Path(__file__).parent / 'out'


for spkey, surf in cardsheet.get_sprites().items():
    outfile = outfolder / f'{spkey}.png'
    outfile.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(outfile))