import pygame
from pygame.locals import *
from pathlib import Path

pygame.font.init()



class PygameObject:
    def __init__(self, width, height, pos_x, pos_y, surface) -> None:
        self.size = (width, height)
        self.pos = [pos_x, pos_y]
        if not surface:
            surface = pygame.Surface((width, height))
        
        if width and height:
            self.surface = pygame.transform.scale(surface, self.size)
        else:
            self.surface = surface

    def update_rect(self):
        if not self.surface:
            raise NotImplementedError("surface is not defined")
        self.rect = self.surface.get_rect(center=tuple(self.pos))

    def on_event(self, event):
        pass

    def update(self):
        self.update_rect()

    def draw(self, surface):
        surface.blit(self.surface, self.rect)

class Display:
    def __init__(self, surface) -> None:
        self.surface = surface


class Text(Display):
    cached_fonts = {}
    @staticmethod
    def get_font(fontsize):
        if fontsize in Text.cached_fonts:
            return Text.cached_fonts[fontsize]
        else:
            font = pygame.font.SysFont(pygame.font.get_default_font(), fontsize)
            Text.cached_fonts[fontsize] = font
            return font

    def __init__(self, fontsize, text: str, bgcolor = None, fgcolor = (255,255,25)) -> None:
        self.font = Text.get_font(fontsize)
        self.bg = bgcolor
        text = self.font.render(text, True, fgcolor, bgcolor)
        super().__init__(text)


class Image(Display):
    def __init__(self, image_path) -> None:
        surface = pygame.image.load(image_path)
        super().__init__(surface)


class Label(PygameObject):
    def __init__(self, width, height, pos_x, pos_y, data: Display) -> None:
        super().__init__(width, height, pos_x, pos_y, data.surface)

    def set_display(self, data: Display):
        self.surface = data.surface

class Button(PygameObject):
    def __init__(self, width, height, pos_x, pos_y, on_press, label: Display):
        self.label = label
        self.pressed = False
        self.pressfunc = on_press
        # add 5 pixels on all sides to make it look better
        # for this, we make a new test surface that is 10 pixels bigger in both sides
        # and then we blit the label.surface onto the center
        if isinstance(label, Text):
            if not width or not height:
                rect = label.surface.get_rect()
                width, height = rect.width, rect.height
            testsurf = pygame.Surface((width + 10, height + 10))
            if label.bg:
                testsurf.fill(label.bg)
            testsurf.blit(label.surface, (5, 5))
            super().__init__(width + 10, height + 10, pos_x, pos_y, testsurf)
        else:
            super().__init__(width, height, pos_x, pos_y, label.surface)

    def on_event(self, event):
        if event.type == MOUSEBUTTONDOWN:
            point = pygame.mouse.get_pos()
            if self.rect.collidepoint(point):
                self.pressed = True
                self.pressfunc()

        elif event.type == MOUSEBUTTONUP and self.pressed == True:
            self.pressed = False


class Entry(PygameObject):
    def __init__(self, width, height, pos_x, pos_y, /, maxchars: int, bgcolor, fgcolor, textcolor, fontsize: int, emptytext: str) -> None:
        self.maxchars = maxchars
        self.bgcolor = bgcolor
        self.fgcolor = fgcolor
        self.emptytext = emptytext
        self.text = emptytext
        self.textcolor = textcolor
        self.focused = False
        self.prevstate = (False, "")
        self.fontsize = fontsize
        super().__init__(width, height, pos_x, pos_y, None)

    def update(self):
        if self.prevstate != (self.focused, self.text):
            self.surface.fill(self.bgcolor)
            if self.focused:
                if self.text == self.emptytext:
                    self.text = ''
                self.surface.fill(self.fgcolor)
            text = Text(self.fontsize, self.text, self.fgcolor if self.focused else self.bgcolor, self.textcolor)
            self.surface.blit(text.surface, text.surface.get_rect(center=self.surface.get_rect().center))
            self.prevstate = (self.focused, self.text)

        super().update()

    def get(self):
        return self.text
        
    def set(self, text):
        self.text = text
    
    def on_event(self, event):
        if event.type == MOUSEBUTTONDOWN:
            point = pygame.mouse.get_pos()
            if self.rect.collidepoint(point):
                self.focused = True
                self.text = ""
            else:
                self.focused = False

            if not self.text:
                self.text = self.emptytext
        if event.type == KEYDOWN:
            if self.focused:
                if event.key == K_BACKSPACE and len(self.text) > 0:
                    self.text = self.text[:-1]
                elif event.key == K_RETURN:
                    self.focused = False
                elif event.key == K_SPACE:
                    self.text += " "
                elif event.unicode and len(self.text) < self.maxchars:
                    self.text += event.unicode


class Spritesheet:
    def __init__(self, filename: str) -> None:
        self.sheet = pygame.image.load(filename)
        self.fname = filename
        self.sprites = {}
        self.load_sprites()

    def get_image(self, x, y, width, height):
        image = pygame.Surface((width, height))
        image.blit(self.sheet, (0, 0), (x, y, width, height))
        return image

    def get_sprites(self):
        return self.sprites

    def load_sprites(self):
        sheetfile = Path(self.fname + ".sheet")
        if sheetfile.is_file() and sheetfile.exists():
            with open(sheetfile, "r") as f:
                for line in f:
                    name, x, y, width, height = line.split()
                    self.sprites[name] = self.get_image(int(x), int(y), int(width), int(height))
        else:
            raise FileNotFoundError("No spritesheet file found for " + self.fname)
