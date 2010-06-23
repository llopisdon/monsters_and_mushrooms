#!/usr/bin/env python
import os
import pygame
import random
import sys

def load_image(name):
    fullname = os.path.join("data", name)
    img = pygame.image.load(fullname)
    return img.convert(img)

class Actor(pygame.sprite.Sprite):

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

        self.frames = []
        self.frames.append( load_image("sprites/exp0.png") )
        self.frames.append( load_image("sprites/exp1.png") )

        self.x = 0
        self.y = 0
        self.frame = 0
        self.max_frames = len(self.frames)
        self.ttl = pygame.time.get_ticks()
        img = self.frames[0]
        self.rect = img.get_rect()
        self.rect.topleft = self.x, self.y

    def update(self, frame_delay, keys):
        dt = pygame.time.get_ticks() - self.ttl
        if dt > frame_delay:
            self.ttl = pygame.time.get_ticks()
            self.frame += 1
            if self.frame == self.max_frames:
                self.frame = 0
        if keys[0]:
            self.x -= 5
        if keys[1]:
            self.x += 5
        if keys[2]:
            self.y -= 5
        if keys[3]:
            self.y += 5

        if self.x < 0:
            self.x = 0
        elif self.x > 640:
            self.x = 640

        if self.y < 0:
            self.y = 0
        elif self.y > 480:
            self.y = 480
        
        self.rect.topleft = self.x, self.y

    def draw(self, buffer):
        buffer.blit(self.frames[self.frame], self.rect)
        
def main():

    pygame.init()
    clock = pygame.time.Clock()
    system_font = pygame.font.get_default_font()
    font = pygame.font.SysFont(None, 24)
    res = (640, 480)
    screen = pygame.display.set_mode(res)
    background = pygame.Surface(res)
    background.fill([0,0,0])
    screen.blit(background, [0,0])

#pygame.time.Clock()
# pygame.time.get_ticks()

    keys = [False, False, False, False, False]

    actor = Actor()


    frame_delay = 250

    while True:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    keys[0] = True
                elif event.key == pygame.K_RIGHT:
                    keys[1] = True
                elif event.key == pygame.K_UP:
                    keys[2] = True
                elif event.key == pygame.K_DOWN:
                    keys[3] = True
                elif (event.key == pygame.K_SPACE) or \
                 (event.key == pygame.K_LCTRL):
                    keys[4] = True
                elif event.key == pygame.K_ESCAPE:
                    sys.exit()
                elif event.key == pygame.K_a:
                    frame_delay += 1
                elif event.key == pygame.K_z:
                    frame_delay -= 1
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    keys[0] = False
                elif event.key == pygame.K_RIGHT:
                    keys[1] = False
                elif event.key == pygame.K_UP:
                    keys[2] = False
                elif event.key == pygame.K_DOWN:
                    keys[3] = False
                elif event.key == pygame.K_SPACE or \
                 (event.key == pygame.K_LCTRL):
                    keys[4] = False


        screen.blit(background, [0,0])
        
        str = "Frame Delay: %d" % frame_delay
        text = font.render(str, 1, (255,255,255))
        screen.blit(text, [0,460])

        actor.update(frame_delay, keys)
        actor.draw(screen)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
