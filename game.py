#!/usr/bin/env python
# vim:set sts=4 et sw=4 ts=4 ci ai:
"""
Mushroom_and_Monsters -- a python+pygame based remake of the Atari
arcade version of Millipede.

Copyright 2007 Donald E. Llopis (thetofucube@gmail.com)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
USA
"""

import os
import pygame
import random
import sys

"""
millipede dimensions -- from atari acrcade version

total screen area 240x256

score area        (0,0)   - (239,7) 8 pixels
arena area        (0,8)   - (239,247) 240 pixels
player area       (0,200) - (239,247) 48 pixels
bottom score area (0,248) - (239,255) 8 pixles

this version

arena area        (0,0)   - (239,239) 240 pixels
player area       (0,192) - (239,239) 48 pixel 
bottom score area (0,240) - (239,255) 16 pixels

mushroom grid 30x29

mushroom grid 30x35
mushroom 8x8
player 7x7
player-missiler 5x7
ddt 16x8
1 millipede 8x8

Player Life Bonus @ every 20,000pts
Num Spiders on screen increases from 1 to n?
"""

DEBUG = False


class Game:

    FRAME_RATE = 60

    SCREEN_W = 360
    SCREEN_H = 376
    ARENA_W = 360
    ARENA_H = 360
    PLAYER_W = 360
    PLAYER_H = 72
    SCORE_W = 360
    SCORE_H = 16

    LIFE_BONUS = 20000

    MAX_DDTS = 5

    # delay times are in milliseconds 
    SLOW_DOWN_TIME_TTL = 5000
    SLOW_DOWN_TIME_TTL_DT = 125
    SWARM_STAGE_SPAWN_DELAY = 250
    SPAWN_QUEUE_DELAY = 100
    LEVEL_UP_DELAY = 1250
    START_RANDOM_EVENT_DELAY = 1000
    THE_NINTH_MILLIPEDE_DELAY = 750

    BEE_SWARM = 0
    DRAGONFLY_SWARM = 1 
    MOSQUITO_SWARM = 2
    BEEDRAGONFLY_SWARM = 3
    BEEDRAGONFLYMOSQUITO_SWARM = 4
    SWARM_BONUS_INC = 100
    SWARM_MAX_BONUS_POINTS = 1000
    START_PLAYER_LIVES = 3

    RANDOM_EVENT_FREQ = 50
 
    def __init__(self):
        max_columns = Game.SCREEN_W / MushroomField.MUSHROOM_WIDTH

        pygame.init()
        if not pygame.font: print "Warning: fonts disabled."
        mixer_init = pygame.mixer.get_init()
        if not mixer_init: print "Warning: mixer disabled."
        if mixer_init:
            print "Mixer available channels: ", \
            pygame.mixer.get_num_channels()

        pygame.display.set_caption('Monsters and Mushrooms')

        system_font = pygame.font.get_default_font()
        self.font = pygame.font.SysFont( None, 24 ) 
        
        # init joystick 0
        num_joystick = pygame.joystick.get_count()
        if num_joystick > 0:
            joy = pygame.joystick.Joystick( num_joystick - 1 )
            if not joy.init():
                print "Warning: could not initialize joystick(s)"
        
        # allocate backbuffer
        size = Game.SCREEN_W, Game.SCREEN_H
        #self.screen = pygame.display.set_mode(size,pygame.FULLSCREEN)
        self.screen = pygame.display.set_mode(size)
        self.background = pygame.Surface(size)
        self.background.fill([0,0,0])
        self.screen.blit(self.background, [0,0])
        
        # initialize sounds
        self.millipede_snd = load_sound("sounds/millipede.ogg")
        self.player_missile_snd = load_sound("sounds/shot1.ogg")
        self.player_hit_snd = load_sound("sounds/exp1.ogg")
        self.ddt_snd = load_sound("sounds/exp2.ogg")
        self.bee_snd = load_sound("sounds/bee1.ogg")
        self.mosquito_snd = load_sound("sounds/fly.ogg")
        self.spider_snd = load_sound("sounds/spider.ogg")
        self.dragonfly_snd = load_sound("sounds/bee2.ogg")

        # load main game static screens
        self.title_img = load_image("images/title.png")
        self.gameover_img = load_image("images/gameover.png")
        self.paused_img = load_image("images/paused.png")
        self.start_img = []
        self.start_img.append(load_image("images/start0.png"))
        self.start_img.append(load_image("images/start1.png"))
        self.start_img.append(load_image("images/start2.png"))

        self.init_vars()


    def init_vars(self):
        # init game objects
        self.keys = [False, False, False, False, False]
        self.score = 0
        self.prev_score = 0
        self.cur_level = 0
        self.p_table_idx = 0
        self.swarm_level = 0
        self.player_lives = Game.START_PLAYER_LIVES
        self.player_dead = False
        self.slow_down_time = False
        self.time_delay = 0
        self.repeat_level = False

        self.menu_delay = 0
        self.level_up_delay = 0

        self.clock = pygame.time.Clock()
        self.cur_tick = 0
        self.prev_tick = 0

        self.spawn_queue = {
            'bees' : 0,
            'beetles' : 0,
            'dragonflies' : 0,
            'earwigs' : 0,
            'inchworms' : 0,
            'mosquitos' : 0,
            'spiders' : 0,
            'ttl' : 0
        };

        self.actionfn = self.main_menu_init
        self.prev_actionfn = None

        self.swarmfn = None
        self.swarm_count = 0
        self.swarm_launch_delay = 0
        self.swarm_monster = None
        self.swarm_monster_lst = None
        self.swarm_points = 0
        self.swarm_next_monster = 0

        self.birthanddeathfn = None
        
        self.player = Player(self)
        self.players = pygame.sprite.Group()
        self.playerMissile = PlayerMissile(self)
        self.playerMissiles = pygame.sprite.Group()
        self.playerMissiles.add( self.playerMissile )

        self.popups = PopUps(self)
        self.particles = Particles(self)

        self.mushroom_field = MushroomField(self)

        self.millipedes = []

        self.spiders = pygame.sprite.Group()
        self.bees = pygame.sprite.Group()
        self.mosquitos = pygame.sprite.Group()
        self.beetles = pygame.sprite.Group()
        self.earwigs = pygame.sprite.Group()
        self.dragonflies = pygame.sprite.Group()
        self.inchworms = pygame.sprite.Group()
        self.monsters = pygame.sprite.Group()
        self.ddts = pygame.sprite.Group()

        self.damaged_mushrooms = []
        
        self.random_event_delay = 0
        self.cur_level_random_event_delay = Game.START_RANDOM_EVENT_DELAY

        # probability table for spawning monsters
        # (beetle,spider,bee,inchworm,mosquito,dragonfly,earwig)
        # seven types of monsters
        # one tuple per level example:
        self.p_table = (
        (25,-1,-1,-1,-1,-1,-1),
        (30,50,-1,52,-1,-1,54),
        (35,52,54,58,-1,-1,62),
        (40,54,56,60,-1,-1,64),
        (45,56,58,64,66,68,74),
        (50,58,60,66,68,70,76),
        (50,60,62,68,70,72,78),
        (50,62,64,70,72,74,80),
        (50,64,68,76,80,84,92),
        (50,66,70,78,82,86,94),
        (50,68,72,80,84,88,96),
        (50,70,76,84,88,92,98),
        (50,70,78,86,92,98,100) )

        # max beetle,spider,earwig,inchworm perl level
        self.max_table = (
        (2,0,0,0),
        (2,1,1,1),
        (2,1,1,1),
        (3,1,1,1),
        (3,2,1,1),
        (4,2,1,1),
        (4,2,1,1),
        (5,3,2,2),
        (5,4,2,2),
        (6,5,2,2),
        (6,6,2,2),
        (7,7,2,2),
        (8,8,2,2))


    def game_reset(self):
        """Reset game variables."""

        self.keys = [False, False, False, False, False]
        self.score = 0
        self.prev_score = 0

        self.slow_down_time = False
        self.time_delay = 0
        self.menu_delay = 0
        self.level_up_delay = 0

        # swarm stage variables
        self.swarmfn = None
        self.swarm_count = 0
        self.swarm_launch_delay = 0
        self.swarm_monster = None
        self.swarm_monster_lst = None
        self.swarm_next_monster = 0

        self.birthanddeathfn = None
 
        # Reset the stop-watch timer. 
        self.cur_tick = 0
        self.reset_ticks()
        
        # reset spawn queue
        self.spawn_queue_reset()

        # random events
        self.random_event_delay = 0
        self.cur_level_random_event_delay = Game.START_RANDOM_EVENT_DELAY

        # keep track of damaged mushrooms
        self.damaged_mushrooms = []
        
        #player info
        self.score = 0
        self.cur_level = 0
        self.swarm_level = 0
        self.player_lives = Game.START_PLAYER_LIVES
        self.player_dead = False
        self.slow_down_time = False
        self.time_delay = 0
        self.repeat_level = False

        self.menu_delay = 0
        self.level_up_delay = 0

        self.clock = pygame.time.Clock()
        self.cur_tick = 0
        self.prev_tick = 0

        for m in self.monsters:
           m.kill()
        self.ddts.empty()

        self.mushroom_field.reset()
        self.mushroom_field.populate_randomly()

        # special events
        self.the_ninth_millipede = False
        self.scroll_mushroomfield_delay = 0
        self.eight_spider_attack = False
 

    def spawn_queue_reset(self):
        """Reset the spawn queue."""
        self.spawn_queue['bees'] = 0
        self.spawn_queue['beetles'] = 0
        self.spawn_queue['dragonflies'] = 0
        self.spawn_queue['earwigs'] = 0
        self.spawn_queue['inchworms'] = 0
        self.spawn_queue['mosquitos'] = 0
        self.spawn_queue['spiders'] = 0
        self.spawn_queue['ttl'] = self.get_ticks()


    def level_reset(self):
        """Reset the current level."""
        # remove all actors from the game
        self.popups.clear()
        self.players.empty()
        self.playerMissiles.empty()
        self.millipedes = []
        for m in self.monsters:
            m.kill()
        for d in self.ddts:
            if d.active:
                d.kill()

        self.spawn_queue_reset()
        self.slow_down_time = False
        self.player_dead = False
        self.keys = [False, False, False, False, False]


    def level_init(self):
        """Setup current level data."""
        self.players.add( self.player )
        self.playerMissile.reset()
        self.playerMissiles.add( self.playerMissile )


    def get_ticks(self):
        """Return game clock ticks."""
        t = pygame.time.get_ticks()
        dt = t - self.prev_tick
        self.prev_tick = t
        self.cur_tick += dt
        return self.cur_tick


    def one_up_and_eight_spiders(self):
        """check for 1-UP and 8 spider attack."""
        event = False
        n = self.prev_score % Game.LIFE_BONUS
        m = self.score % Game.LIFE_BONUS
        # m will be less than n should a 1-UP occur
        if ((m-n) < 0):
            event = True
            self.player_lives += 1
            # play player_1_up sound here...
            if DEBUG:
                print "PLAYER 1-UP!!!!!"

        # check for 100,000 8 spider attack
        n = self.prev_score % 100000
        m = self.score % 100000
        if ((m-n) < 0):
            event = True
            self.spawn_queue['spiders'] += 8
            self.eight_spider_attack = True
            if DEBUG:
                print "Eight Spider Attack"

        # prevent multiple 1-ups or multiple 8 spider attacks
        if event:
            self.prev_score = self.score


    def reset_ticks(self):
        """Reset game tick counter. Must be called after a Pause."""
        self.prev_tick = pygame.time.get_ticks()


    def run(self):
        """Main game loop."""
        while True:
            self.actionfn()


    def main(self):
        """Game run."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.JOYAXISMOTION:
                #print "move pad: ", event.joy, event.axis, event.value
                if event.axis == 1:
                    if event.value == 0:
                        self.keys[2] = False 
                        self.keys[3] = False 
                    elif event.value == 1:
                        self.keys[3] = True
                    elif event.value == -1:
                        self.keys[2] = True
                elif event.axis == 0:
                    if event.value == 0:
                        self.keys[0] = False 
                        self.keys[1] = False 
                    elif event.value == 1:
                        self.keys[1] = True
                    elif event.value == -1:
                        self.keys[0] = True
            elif event.type == pygame.JOYBUTTONUP:
                #print "button up: ", event.joy, event.button
                if event.joy == 0 and event.button == 0:
                    self.keys[4] = False
            elif event.type == pygame.JOYBUTTONDOWN:
                #print "button down: ", event.joy, event.button
                if event.joy == 0 and event.button == 0:
                    self.keys[4] = True 
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.keys[0] = True
                elif event.key == pygame.K_RIGHT:
                    self.keys[1] = True
                elif event.key == pygame.K_UP:
                    self.keys[2] = True
                elif event.key == pygame.K_DOWN:
                    self.keys[3] = True
                elif (event.key == pygame.K_SPACE) or \
                 (event.key == pygame.K_LCTRL):
                    self.keys[4] = True
                elif event.key == pygame.K_ESCAPE:
                    sys.exit()
                elif event.key == pygame.K_p:
                    self.prev_actionfn = self.actionfn
                    self.menu_delay = self.get_ticks()
                    self.actionfn = self.pause
                    pygame.mixer.pause()
                elif event.key == pygame.K_m:
                    mushroom_field_print()
                elif event.key == pygame.K_g:
                    (x, y) = game.player.rect.topleft
                    gx = x / MushroomField.MUSHROOM_WIDTH
                    gy = y / MushroomField.MUSHROOM_HEIGHT
                    print "Player position: (%d, %d) : (%d, %d)" % \
                     (x, y, gx, gy)
                elif event.key == pygame.K_0:
                    self.swarm_init(Game.BEE_SWARM)
                elif event.key == pygame.K_1:
                    self.swarm_init(Game.DRAGONFLY_SWARM)
                elif event.key == pygame.K_2:
                    self.swarm_init(Game.MOSQUITO_SWARM)
                elif event.key == pygame.K_3:
                    self.swarm_init(Game.BEEDRAGONFLY_SWARM)
                elif event.key == pygame.K_4:
                    self.swarm_init(Game.BEEDRAGONFLYMOSQUITO_SWARM)
                elif event.key == pygame.K_l:
                    self.birthanddeathfn = self.birth_and_death_init
                elif event.key == pygame.K_r:
                    self.mushroom_field.populate_randomly()
                elif event.key == pygame.K_o:
                    self.mushroom_field.reset()
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    self.keys[0] = False
                elif event.key == pygame.K_RIGHT:
                    self.keys[1] = False
                elif event.key == pygame.K_UP:
                    self.keys[2] = False
                elif event.key == pygame.K_DOWN:
                    self.keys[3] = False
                elif event.key == pygame.K_SPACE or \
                 (event.key == pygame.K_LCTRL):
                    self.keys[4] = False

        # save current score -- used to check for player 1-UP
        self.prev_score = self.score

        # swarm stage?
        if self.swarmfn:
            self.swarmfn()

        # the 9th Millipede?
        if self.the_ninth_millipede:
            # scroll MushroomField by 1 row down each frame
            dt = self.get_ticks() - self.scroll_mushroomfield_delay
            if dt > Game.THE_NINTH_MILLIPEDE_DELAY:
                self.scroll_mushroomfield_delay = self.get_ticks()
                self.mushroom_field.row_down()
 
        # do not allow monsters to spawn before a level up
        # the millipede is king!
        if not self.level_up_delay:
            self.random_events()
            self.spawn_monsters()

        # do we need to planet some mushrooms?
        if self.birthanddeathfn:
            self.birthanddeathfn()

        # update actors - move player, update missile, move the milliepede
        # ddts, ddt collisions, millipedes, monsters, player, player-missle

        self.ddts.update()

        # check for ddt collisions
        self.ddt_collisions = True
        for d in self.ddts:
            if d.active:
                # check for millipede collisions
                for m in self.millipedes:
                    m.collision(d.rect)

                # check for collisions against all other monsters
                m_lst = pygame.sprite.spritecollide( d, self.monsters, False)
                for m in m_lst:
                    m.collision()
        self.ddt_collisions = False

        # check for time slow down
        if self.slow_down_time:
            cur_time = self.get_ticks()
            if (cur_time - self.slow_down_time_ttl) > Game.SLOW_DOWN_TIME_TTL:
                self.slow_down_time = False

            if (cur_time - self.time_delay) > Game.SLOW_DOWN_TIME_TTL_DT:
                for m in self.millipedes:
                    m.move()
                self.monsters.update()
                self.time_delay = cur_time
        else:
                for m in self.millipedes:
                    m.move()
                self.monsters.update()

        self.particles.update()
        self.players.update(self.keys, self.playerMissile)

        if self.playerMissile.active:
            self.playerMissile.move()


        """
        Check for:
        1 - player death
        2 - end of level
        3 - repeat current level
        """
        # player dead?
        if self.player_dead:
            # need to add a delay before this method is called....
            self.player_lives -= 1
            self.actionfn = self.player_die_init 
            # check to see if we need to repeat the level
            self.millipede_snd.stop()
            if len(self.millipedes) > 0:
                self.repeat_level = True
        # is end of level ?
        elif not self.repeat_level and \
            not self.swarmfn and \
            (len(self.millipedes) == 0):
            self.millipede_snd.stop()
            if self.level_up_delay:
                dt = self.get_ticks() - self.level_up_delay
                if dt > Game.LEVEL_UP_DELAY:
                    self.level_up_delay = 0
                    self.level_up()
            else:
                self.level_up_delay = self.get_ticks()
        # repeat current level?
        elif self.repeat_level:
            if self.level_up_delay:
                dt = self.get_ticks() - self.level_up_delay
                if dt > Game.LEVEL_UP_DELAY:
                    self.level_up_delay = 0
                    self.level_redo()
                    self.repeat_level = False
            else:
                self.level_up_delay = self.get_ticks()

        # check for 1-up
        self.one_up_and_eight_spiders()


        # start drawing a frame
        self.screen.blit(self.background, [0,0])

        # player area boundaries
        pygame.draw.line(self.screen,
                (0,0,128),
                (0,Game.ARENA_H-Game.PLAYER_H),
                (Game.ARENA_W,Game.ARENA_H-Game.PLAYER_H))
        pygame.draw.line(self.screen,
                (0,0,128),
                (0,Game.ARENA_H),
                (Game.ARENA_W,Game.ARENA_H))

        # draw actors
        self.players.draw(self.screen)

        if self.playerMissile.active:
            self.playerMissiles.draw(self.screen)

        self.mushroom_field.draw(self.screen)
        
        self.ddts.draw(self.screen)
        
        for m in self.millipedes:
            m.draw(self.screen)
            
        self.monsters.draw(self.screen)
        
        self.particles.draw(self.screen)
        
        self.popups.draw(self.screen)

        self.draw_score()

        pygame.display.flip()
        self.clock.tick(Game.FRAME_RATE)


    def main_menu_init(self):
        """Initialize main menu screen."""
        self.start_img_idx = 0
        self.start_img_delay = self.get_ticks()
        self.actionfn = self.main_menu


    def main_menu(self):
        """Main menu screen."""

        start = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.joy == 0 and event.button == 0:
                    start = True
            elif event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_SPACE) or \
                 (event.key == pygame.K_LCTRL):
                    start = True
                elif event.key == pygame.K_ESCAPE:
                    sys.exit()

        self.screen.blit(self.background, [0,0])
        self.screen.blit(self.title_img, [0,50])

        dt = self.get_ticks() - self.start_img_delay
        if dt > 275:
            self.start_img_delay = self.get_ticks()
            self.start_img_idx += 1
            if self.start_img_idx == len(self.start_img):
                self.start_img_idx = 0

        self.screen.blit(self.start_img[self.start_img_idx],\
        [Game.SCREEN_W/4,200])

        pygame.display.flip()
        self.clock.tick(Game.FRAME_RATE)

        if start:
            self.game_reset()
            self.level_reset()
            self.level_init()
            self.actionfn = self.main
            self.prev_actionfn = None
            self.game_start()
            self.reset_ticks()


    def pause(self):
        """Pause game loop."""

        for event in pygame.event.get():
            
            if event.type == pygame.QUIT:
                sys.exit()
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.actionfn = self.prev_actionfn
                    self.prev_actionfn = None
                    self.reset_ticks()
                    pygame.mixer.unpause()
                elif event.key == pygame.K_ESCAPE:
                    sys.exit()
        
        self.screen.blit(self.background, [0,0])
        #text = self.font.render("Paused", 1, (255,255,255))
        self.screen.blit(self.paused_img, [0,Game.SCREEN_H/3])

        pygame.display.flip()
        self.clock.tick(Game.FRAME_RATE)


    def game_over(self):
        """Game Over Screen."""
        GAME_OVER_DELAY = 2500
        quit = False
        for event in pygame.event.get():
            
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.joy == 0 and event.button == 0:
                    quit = True
            elif event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_SPACE) or \
                 (event.key == pygame.K_LCTRL) or \
                 (event.key == pygame.K_q):
                    quit = True
                elif event.key == pygame.K_ESCAPE:
                    sys.exit()

        self.screen.blit(self.background, [0,0])
        self.screen.blit(self.gameover_img, [0,Game.SCREEN_H/3])

        pygame.display.flip()
        self.clock.tick(Game.FRAME_RATE)
        
        dt = self.get_ticks() - self.menu_delay
        if (dt > GAME_OVER_DELAY) or quit:
            self.actionfn = self.main_menu_init
            self.prev_actionfn = None
            self.reset_ticks()


    def game_start(self):
        """Similar to Increment level but to start a new game."""
        self.cur_level += 1
        self.p_table_idx = (self.cur_level % len(self.p_table)) - 1
        self.swarm_level += 1
        #self.spawn_millipedes()
        self.millipedes.append(Millipede(self))
        self.millipede_snd.play(-1)

    def level_up(self):
        """Increment game level."""
        self.cur_level += 1
        self.p_table_idx = (self.cur_level % len(self.p_table)) - 1
        self.swarm_level += 1
        if self.swarm_level > 17:
            self.swarm_level = 1

        print "special level: ", self.swarm_level

        swarm_stage = None

        if self.swarm_level == 3:
            swarm_stage = Game.BEE_SWARM
        elif self.swarm_level == 8:
            swarm_stage = Game.DRAGONFLY_SWARM
        elif self.swarm_level == 11:
            swarm_stage = Game.MOSQUITO_SWARM
        elif self.swarm_level == 12:
            if DEBUG:
                print "SCROLL MUSHROOM FIELD NOW!!!!"
            self.the_ninth_millipede = True
            self.scroll_mushroomfield_delay = self.get_ticks()
        elif self.swarm_level == 13:
            self.the_ninth_millipede = False
            self.scroll_mushroomfield_delay = 0
        elif self.swarm_level == 14:
            swarm_stage = Game.BEEDRAGONFLY_SWARM
        elif self.swarm_level == 17:
            swarm_stage = Game.BEEDRAGONFLYMOSQUITO_SWARM

        # normal level
        if swarm_stage == None:
            # move mushroom field down by one row
            self.mushroom_field.row_down()
            # make some more millipedes...
            self.spawn_millipedes()
        # swarm stage
        else:
            self.swarm_init(swarm_stage)

        # remove time dilation effect
        self.slow_down_time = False

        # alternate mushroom field color
        self.mushroom_field.change_color()


    def level_redo(self):
        """Redo current level."""
        self.spawn_millipedes()


    def spawn_millipedes(self):
        """Used by level generators and level restart."""
        # generate a random list of x-positions
        start_x = range(0,MushroomField.FIELD_WIDTH)
        random.shuffle(start_x)
        # reduce Millipede segments by one each level
        # cycle repeats at Millipede.MAX_SEGMENTS
        if self.cur_level == 0:
            segments = Millipede.MAX_SEGMENTS
        else:
            segments = (self.cur_level - 1) % Millipede.MAX_SEGMENTS

        body_len = Millipede.MAX_SEGMENTS - segments
        if(body_len):
            xpos = start_x[0] * MushroomField.MUSHROOM_WIDTH
            self.millipedes.append(Millipede(self,body_len,(xpos,Millipede.start_y)))
        for i in range(segments):
            xpos = start_x[i+1] * MushroomField.MUSHROOM_WIDTH
            self.millipedes.append(Millipede(self,1,(xpos,Millipede.start_y)))
        
        self.millipede_snd.play(-1)



    def swarm_init(self, swarm_num):
        """Initialize Wave Stage."""

        self.swarm_count = 100
        self.swarm_next_monster = 0
        self.swarm_launch_delay = self.get_ticks()
        self.swarmfn = self.swarm_spawn

        self.swarm_points = Game.SWARM_BONUS_INC

        self.swarm_monster = []
        self.swarm_monster_lst = []
        self.swarm_snd = []

        # bee swarm
        if swarm_num == Game.BEE_SWARM:
            self.swarm_monster.append(Bee)
            self.swarm_monster_lst.append(self.bees)
            self.swarm_snd.append(self.bee_snd)
        # dragonfly swarm
        elif swarm_num == Game.DRAGONFLY_SWARM:
            self.swarm_monster.append(Dragonfly)
            self.swarm_monster_lst.append(self.dragonflies)
            self.swarm_snd.append(self.dragonfly_snd)
        # mosquito swarm
        elif swarm_num == Game.MOSQUITO_SWARM: 
            self.swarm_monster.append(Mosquito)
            self.swarm_monster_lst.append(self.mosquitos)
            self.swarm_snd.append(self.mosquito_snd)
        # bees and dragonflies
        elif swarm_num == Game.BEEDRAGONFLY_SWARM:
            self.swarm_monster.append(Bee)
            self.swarm_monster_lst.append(self.bees)
            self.swarm_snd.append(self.bee_snd)
            self.swarm_monster.append(Dragonfly)
            self.swarm_monster_lst.append(self.dragonflies)
            self.swarm_snd.append(self.dragonfly_snd)
        # bees, dragonflies, and mosquitos
        elif swarm_num == Game.BEEDRAGONFLYMOSQUITO_SWARM:
            self.swarm_monster.append(Bee)
            self.swarm_monster_lst.append(self.bees)
            self.swarm_snd.append(self.bee_snd)
            self.swarm_monster.append(Dragonfly)
            self.swarm_monster_lst.append(self.dragonflies)
            self.swarm_snd.append(self.dragonfly_snd)
            self.swarm_monster.append(Mosquito)
            self.swarm_monster_lst.append(self.mosquitos)
            self.swarm_snd.append(self.mosquito_snd)

        self.swarm_snd[0].play()
            
 
    def swarm_spawn(self):
        """Wave Stage loop."""
        i = self.swarm_next_monster
        if self.swarm_count > 0:
            dt = self.get_ticks() - self.swarm_launch_delay
            if dt > Game.SWARM_STAGE_SPAWN_DELAY:
                m = self.swarm_monster[i](self)
                m.add(self.monsters)
                m.add(self.swarm_monster_lst[i])
                self.swarm_count -= 1
                self.swarm_launch_delay = self.get_ticks()
                if (self.swarm_count % 10) == 0:
                    self.swarm_snd[i].play()
                if DEBUG:
                    print "WAVE SPAWN MONSTER"

                # make sure next group of monsters in the list spawns
                self.swarm_next_monster += 1
                if self.swarm_next_monster >= len(self.swarm_monster_lst):
                    self.swarm_next_monster = 0

        # wait until the last group of monsters are gone before
        # ending the swarm stage.
        n = len(self.swarm_monster) - 1
        if (self.swarm_count <= 0) and (len(self.swarm_monster_lst[n]) == 0):
            self.swarmfn = None
            # time to regrow or kill some mushrooms...
            self.birthanddeathfn = self.birth_and_death_init
            if DEBUG:
                print "WAVE STAGE END"

    def swarm_score_up(self, x, y):
        """Increment score during a swarm stage."""
        # any time a swarm stage monster is hit with a DDT
        # swarm_points are triple scored to a max of 1000 
        if self.ddt_collisions:
            tmp = self.swarm_points
            self.swarm_points = self.swarm_points * 3
            if self.swarm_points > Game.SWARM_MAX_BONUS_POINTS:
                self.swarm_points = Game.SWARM_MAX_BONUS_POINTS

        self.score += self.swarm_points
        self.popups.add(x, y, self.swarm_points)
        self.swarm_points += Game.SWARM_BONUS_INC
        if self.swarm_points > Game.SWARM_MAX_BONUS_POINTS:
            self.swarm_points = Game.SWARM_MAX_BONUS_POINTS

        if self.ddt_collisions:
            # restore points
            self.swarm_points = tmp


    def stop_ninth_millipede(self):
        """Stop scrolling mushroom field stage."""
        self.the_ninth_millipede = False
        self.scroll_mushroomfield_delay = 0
 

    def birth_and_death_init(self):
        """Initialize the Mushroom Birth and Death loop."""
        self.birth_and_death_ttl = self.get_ticks()
        self.birthanddeathfn = self.birth_and_death
        self.birth_and_death_trigger = self.get_ticks()

    
    def birth_and_death(self):
        """Mushroom Birth and Death loop."""
        dt = self.get_ticks() - self.birth_and_death_ttl
        if dt > 1000:
            self.birthanddeathfn = None
        else:
            dt = self.get_ticks() - self.birth_and_death_trigger
            if dt > 250:
                self.mushroom_field.birth_and_death()
                self.birth_and_death_trigger = self.get_ticks()

    
    def player_die_init(self):
        """Initliaze Player death sequence."""

        """ 
        remove any monsters from the screen 
        and setup mushroom regrowth sequence.
        """
        self.level_reset()
        self.player_die_mushroom_count = len(self.damaged_mushrooms)
        self.player_die_delay = 0
        self.actionfn = self.player_die


    def player_die(self):
        """Player death loop."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.prev_actionfn = self.actionfn
                    self.menu_delay = self.get_ticks()
                    self.actionfn = self.pause
                    pygame.mixer.pause()
                elif event.key == pygame.K_ESCAPE:
                    sys.exit()
 
        """
        Restore any damaged mushrooms--one at a time--to full strength.
        Also, revert any flowers back to mushrooms.
        """

        if self.player_die_delay:
            dt = self.get_ticks() - self.player_die_delay
            if dt > 25:
                self.player_die_delay = 0
        elif len(self.damaged_mushrooms):
            index = self.damaged_mushrooms.pop()
            restore = self.mushroom_field.restore_mushroom(index)
            if restore:
                self.player_die_delay = self.get_ticks()
        else:
            if DEBUG:
                print "PLAYER DEATH SEQUENCE DONE!"
            if self.player_lives == 0:
                self.menu_delay = self.get_ticks()
                self.actionfn = self.game_over
            else:
                self.level_init()
                if DEBUG:
                    print "level init called"
                """
                check if we were in a swarm stage
                if so clear the swarm stage and increment
                the level.
                """

                if self.swarmfn:
                    self.swarmfn = None
                    self.birthanddeathfn = self.birth_and_death_init

                self.actionfn = self.main

        # start drawing a frame
        self.screen.blit(self.background, [0,0])

        # player area boundaries
        pygame.draw.line(self.screen,
                (0,0,128),
                (0,Game.ARENA_H-Game.PLAYER_H),
                (Game.ARENA_W,Game.ARENA_H-Game.PLAYER_H))
        pygame.draw.line(self.screen,
                (0,0,128),
                (0,Game.ARENA_H),
                (Game.ARENA_W,Game.ARENA_H))

        # draw actors
        self.mushroom_field.draw(self.screen)
        self.ddts.draw(self.screen)

        self.draw_score()

        pygame.display.flip()
        self.clock.tick(Game.FRAME_RATE)


    def draw_score(self):
        """draw game score to active screen buffer."""
        # draw text -- need to optimize this....
        score = "S: %d" % self.score
        text = self.font.render(score, 1, (255,255,255))
        self.screen.blit(text, [2,Game.SCREEN_H-Game.SCORE_H+1])
        lives = "P: %d" % self.player_lives
        text = self.font.render(lives, 1, (255,255,255))
        self.screen.blit(text, [Game.SCREEN_W/1.35,Game.SCREEN_H-Game.SCORE_H+1])

        if self.cur_level < 10:
            str = "L: 0%d" % self.cur_level
        else:
            str = "L: %d" % self.cur_level

        text = self.font.render(str, 1, (255,255,255))
        self.screen.blit(text, [Game.SCREEN_W/1.12,Game.SCREEN_H-Game.SCORE_H+1])


    def spawn_millipede_in_player_area(self):
        """Spawn a Millipede in the Player area."""
        # do not allow more than 10 millipedes
        # to spawn in the player area
        if len(self.millipedes) > 10:
            return

        if DEBUG:
            print "Millipede(s) spawned in player area."
        
        y = Game.ARENA_H - Game.PLAYER_H + Millipede.HEIGHT

        # 50/50 chance to spawn left or right side
        n = random.randint(0,9)
        if n < 5:
            x0 = -Millipede.WIDTH
            x1 = 0
            go_right = True 
        else:
            x0 = Game.ARENA_W - Millipede.WIDTH
            x1 = Game.ARENA_W - 1
            go_right = False 

        start_pos = (x0, y)

        # need to set direction here...
        # create a method to set the millipede
        # dir variables...
        m = Millipede(self, 1, start_pos)
        if go_right:
            m.go_right()
        else:
            m.go_left()
        m.set_waypoint( x1, 0 )
        self.millipedes.append(m)


    def spawn_monsters(self):
        """Generates monsters every SPAWN_QUEUE_DELAY milliseconds."""
        dt = self.get_ticks() - self.spawn_queue['ttl']

        if dt > Game.SPAWN_QUEUE_DELAY:

            if self.spawn_queue['bees']:
                if (self.spawn_queue['bees'] % 4) == 1:
                    self.bee_snd.play()
                self.spawn_queue['bees'] -= 1
                m = Bee(self)
                m.add(self.monsters)
                m.add(self.bees)

            max = self.max_table[self.p_table_idx]
            spawn = (len(self.beetles) < max[0])
            if spawn and self.spawn_queue['beetles']:
                self.spawn_queue['beetles'] -= 1
                m = Beetle(self)
                m.add(self.monsters)
                m.add(self.beetles)

            if not self.eight_spider_attack:
                max = self.max_table[self.p_table_idx]
                spawn = (len(self.spiders) < max[1])
                if spawn and self.spawn_queue['spiders']:
                    if len(self.spiders) == 0:
                        self.spider_snd.play(-1)
                    self.spawn_queue['spiders'] -= 1
                    m = Spider(self)
                    m.add(self.monsters)
                    m.add(self.spiders)
            else:
                if len(self.spiders) == 0:
                    self.spider_snd.play(-1)
                self.eight_spider_attack = False
                for i in range(0,8):
                    m = Spider(self)
                    m.add(self.monsters)
                    m.add(self.spiders)

                """
                max = self.max_table[self.p_table_idx]
                spawn = (len(self.spiders) < max[1])
                if spawn and self.spawn_queue['spiders']:
                    self.spawn_queue['spiders'] -= 1
                    m = Spider(self)
                    m.add(self.monsters)
                    m.add(self.spiders)
                """


            max = self.max_table[self.p_table_idx]
            spawn = (len(self.earwigs) < max[2])
            if spawn and self.spawn_queue['earwigs']:
                self.spawn_queue['earwigs'] -= 1
                m = Earwig(self)
                m.add(self.monsters)
                m.add(self.earwigs)

            max = self.max_table[self.p_table_idx]
            spawn = (len(self.inchworms) < max[3])
            if spawn and self.spawn_queue['inchworms']:
                self.spawn_queue['inchworms'] -= 1
                m = Inchworm(self)
                m.add(self.monsters)
                m.add(self.inchworms)
 
            if self.spawn_queue['dragonflies']:
                self.spawn_queue['dragonflies'] -= 1
                m = Dragonfly(self)
                m.add(self.monsters)
                m.add(self.dragonflies)
            
            if self.spawn_queue['mosquitos']:
                self.spawn_queue['mosquitos'] -= 1
                m = Mosquito(self)
                m.add(self.monsters)
                m.add(self.mosquitos)
                self.mosquito_snd.play()

            self.spawn_queue['ttl'] = self.get_ticks()


    def rng(self,start,end):
        # spin-up the rng a technique used in angband...
        random.randint(1,100)
        random.randint(1,100)
        random.randint(1,100)
        random.randint(1,100)
        return random.randint(1,100)


    def random_events(self):
        """Generate random Monster and Events."""

        # if there are 5 or less mushroom_field in the player area
        # then launch bees to grow more mushroom_field...
        if self.mushroom_field.total_player_area_mushrooms <= 5 and \
            (len(self.bees)==0) and (self.spawn_queue['bees'] == 0):
            n = random.randint(1,5)
            self.spawn_queue['bees'] += n

        if self.random_event_delay:
            dt = self.get_ticks() - self.random_event_delay
            if dt > self.cur_level_random_event_delay:
                self.random_event_delay = 0
        else:
            self.random_event_delay = self.get_ticks()
            # (beetle,spider,bee,inchworm,mosquito,dragonfly,earwig)
            prob = self.p_table[self.p_table_idx]

            p = self.rng(1,100)

            if p <= prob[0]:
                if DEBUG:
                    print "Spawn Beetle"
                self.spawn_queue['beetles'] += 1
                self.random_beetle_delay = self.get_ticks()

            elif p <= prob[1]:
                if DEBUG:
                    print "Spawn Spider"
                self.spawn_queue['spiders'] += 1

            elif p <= prob[2]:
                if DEBUG:
                    print "Spawn Bee"
                self.spawn_queue['bees'] += 1

            elif p <= prob[3]:
                if DEBUG:
                    print "Spawn Inchworm"
                self.spawn_queue['inchworms'] += 1

            elif p <= prob[4]:
                if DEBUG:
                    print "Spawn Mosquito"
                self.spawn_queue['mosquitos'] += 1

            elif p <= prob[5]:
                if DEBUG:
                    print "Spawn Dragonfly"
                self.spawn_queue['dragonflies'] += 1

            elif p <= prob[6]:
                if DEBUG:
                    print "Spawn Earwig"
                self.spawn_queue['earwigs'] += 1


#####################################################################

class Player(pygame.sprite.Sprite):
    """The Player."""

    HEIGHT = -1
    WIDTH = -1 
    image = None
    START_X = -1
    START_Y = -1
    x_max = -1
    y_min = -1
    y_max = -1
    X_INC = 3 
    Y_INC = 3 
    
    def __init__(self, game):
        pygame.sprite.Sprite.__init__(self)

        if Player.image == None:
            Player.image = load_image("sprites/player.png")
            Player.HEIGHT = Player.image.get_height()
            Player.WIDTH = Player.image.get_width()
            Player.START_X = (Game.SCREEN_W/2) - (Player.WIDTH/2)
            Player.START_Y = Game.ARENA_H - Player.HEIGHT
            Player.x_max = Game.ARENA_W - Player.WIDTH - 1
            Player.y_min = Game.ARENA_H - Game.PLAYER_H
            Player.y_max = Game.ARENA_H - Player.HEIGHT
        
        self.image = Player.image
        self.rect = self.image.get_rect()
        self.rect.topleft = Player.START_X, Player.START_Y
        self.rect.width = Player.WIDTH
        self.rect.height = Player.HEIGHT
        self.tmp_rect = self.image.get_rect()
        self.tmp_rect.width = Player.WIDTH
        self.tmp_rect.height = Player.HEIGHT 
        self.launch_delay = 0
        self.game = game

    def reset(self):
        self.rect.topleft = (Player.START_X, Player.START_Y)
        # stop all sounds
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        self.game.player_hit_snd.play()
        self.game.mushroom_field.clear_player_area()

    def update(self, keys, playerMissile):
        x, y = self.rect.topleft
        # check for collision against any monsters

        if not DEBUG:
            rect_list = []
            for m in self.game.millipedes:
                for b in m.body:
                    rect_list.append( b['rect'] )

            if self.rect.collidelist(rect_list) > -1:
                self.reset()
                self.game.player_dead = True
                self.game.stop_ninth_millipede()

            m_lst = pygame.sprite.spritecollide(self, self.game.monsters, False)
            if len(m_lst):
                self.reset()
                self.game.player_dead = True
                self.game.stop_ninth_millipede()
                return

        # update player position and launch missiles
        # LEFT
        if keys[0]:
            tmp_x = x - Player.X_INC
            self.tmp_rect.topleft = tmp_x, y
            if not self.game.mushroom_field.player_collision( self.tmp_rect ):
                x = x - Player.X_INC
        
        # RIGHT
        if keys[1]:
            tmp_x = x + Player.X_INC
            self.tmp_rect.topleft = tmp_x, y
            if not self.game.mushroom_field.player_collision( self.tmp_rect ):
                x = x + Player.X_INC

        # UP
        if keys[2]:
            tmp_y = y - Player.Y_INC
            self.tmp_rect.topleft = x, tmp_y
            if not self.game.mushroom_field.player_collision( self.tmp_rect ):
                y = y - Player.Y_INC

        # DOWN
        if keys[3]:
            tmp_y = y + Player.Y_INC
            self.tmp_rect.topleft = x, tmp_y
            if not self.game.mushroom_field.player_collision( self.tmp_rect ):
                y = y + Player.Y_INC

        # clamp player position to arena dimensions
        if x < 0:
            x = 0
        elif x > Player.x_max:
            x = Player.x_max

        if y < Player.y_min:
            y = Player.y_min
        elif y > Player.y_max:
            y = Player.y_max

        # update player rect
        self.rect.topleft = x, y
        
        # FIRE -- fire missle after position clamping has been done
        # there was an out of bounds error occuring when the
        # player would go too far to the left and a missle
        # was fired at the same time.
        if keys[4]:
            if self.launch_delay == 0:
                self.game.playerMissile.launch(x, y)
                self.launch_delay = self.game.get_ticks()

        # missile launch delay
        if self.launch_delay > 0:
            n = self.game.get_ticks() - self.launch_delay
            if n > 0:
                self.launch_delay = 0


#####################################################################


class PlayerMissile(pygame.sprite.Sprite):
    """The Player Missle."""

    WIDTH = 9
    HEIGHT = 11
    image = None
    Y_INC = 12 
    HALF_WIDTH = (WIDTH / 2) + 1
    
    def __init__(self, game):
        pygame.sprite.Sprite.__init__(self)
        if PlayerMissile.image == None:
            PlayerMissile.image = pygame.Surface([PlayerMissile.WIDTH,PlayerMissile.HEIGHT])
            PlayerMissile.image.fill([255,255,255])

        self.image = PlayerMissile.image
        self.rect = self.image.get_rect()
        self.rect.topleft = 0,0
        self.rect.width = PlayerMissile.WIDTH
        self.rect.height = PlayerMissile.HEIGHT
        self.x = 0
        self.y = 0
        self.active = False
        self.game = game

    def reset(self):
        self.active = False

    def launch(self,x,y):
        # adjust launching position
        if self.active == False:
            self.x = x + 1
            self.y = y - PlayerMissile.HEIGHT
            self.active = True
            self.game.player_missile_snd.play()

    def move(self):
        if self.active:
            # 1st -- check for collision again enemies in the 
            # enemy array
            # check for collision against mushroom
            self.rect.topleft = self.x, self.y

            for d in self.game.ddts:
                if d.collision(self.rect):
                    self.active = False
                    self.game.ddt_snd.play()
                    self.game.particles.add(self.x,self.y)
                    return

            if self.game.mushroom_field.missile_collision(self.rect):
                self.active = False
                self.game.particles.add(self.x,self.y)
                return

            # 2nd -- check for collision against monsters
            for m in self.game.millipedes:
                if m.collision(self.rect):
                    self.active = False
                    self.game.particles.add(self.x,self.y)
                    return

            m_lst = pygame.sprite.spritecollide(self,self.game.monsters,False)

            if len(m_lst):
                self.active = False
                for m in m_lst:
                    m.collision()
                    self.game.particles.add(self.x,self.y)
                return

            # 3rd -- move missile
            self.y -= PlayerMissile.Y_INC
            self.rect.topleft = self.x, self.y
            if self.y < (0 - PlayerMissile.HEIGHT):
                self.active = False


#####################################################################


class Millipede:
    """The Millipede."""

    # size of each segment of the millipede
    HEIGHT = -1
    WIDTH = -1
    frames = None
    max_frames = 0
    start_x = -1 
    start_y = -1 
    MAX_Y = -1

    # Millipede moves 3 pixels per frame
    MOVE_COUNT = 4
    move_inc = 3

    BODY_POINTS = 10
    HEAD_POINTS = 100

    MAX_SEGMENTS= 12

    
    def __init__(self, game, num_segments=12, start_pos=None):
        """game - reference to game object
        num_segments - starting number of segments
        start_pos - tuple (x,y) screen coordinates
        """

        self.game = game
        
        if Millipede.frames == None:
            Millipede.frames = []
            Millipede.frames.append(load_image("sprites/millipede0.png"))
            Millipede.frames.append(load_image("sprites/millipede1.png"))
            Millipede.max_frames = len(Millipede.frames)
            Millipede.HEIGHT = Millipede.frames[0].get_height()
            Millipede.WIDTH = Millipede.frames[0].get_width()
            Millipede.start_x = Game.ARENA_W / 2
            Millipede.start_y = 0 - Millipede.HEIGHT
            Millipede.MAX_Y = Game.ARENA_H - Game.PLAYER_H + Millipede.HEIGHT

        self.image = Millipede.frames[0]
        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0
 
        self.up = False
        self.down = True

        n = random.randint(0,10)
        if n < 5:
            self.left = True
            self.right = False
        else:
            self.left = False
            self.right = True

        self.change_row = False
        
        # max_y keeps track of max Y position of next row
        # that the Millipede is heading to
        self.max_y = 0
        
        # pa_spawned indicates that the Millipede spawned in the player
        # area
        self.pa_spawned = False
        self.poisoned = False

        self.move_count = Millipede.MOVE_COUNT

        if start_pos == None: 
            x = Millipede.start_x
            y = Millipede.start_y
        else:
            x, y = start_pos

        # millipede's body is an array of dictionaries
        # representing each segment of the body

        self.body = []

        for i in range(0,num_segments):
            # each segment of the millipede's body is
            # represented by a dictionary which holds
            # the segments position and heading
            m = {}
            if i == 0:
                m['head'] = True

            m['x_pos'] = x
            m['y_pos'] = y
            m['dx'] = 0
            m['dy'] = 0
            m['rect'] = pygame.Rect( x, y, Millipede.WIDTH, Millipede.HEIGHT )

            y = y - Millipede.HEIGHT

            self.body.append( m )

        self.x_inc = 0
        self.y_inc = Millipede.move_inc

        self.set_waypoint( x, 0 )


    def draw(self, buffer):
        """ update animation ... """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Millipede.max_frames:
                self.cur_frame = 0
            self.image = Millipede.frames[self.cur_frame]

        for m in self.body:
            buffer.blit( self.image, (m['x_pos'],m['y_pos']) )


    def __change_row(self, head):
        """Move the Millipede up or down."""
        if self.down:
            x = head['x_pos']
            y = head['y_pos'] + Millipede.HEIGHT
        elif self.up:
            x = head['x_pos']
            y = head['y_pos'] - Millipede.HEIGHT
        
        if y >= (Game.ARENA_H-Millipede.HEIGHT):
            self.down = False
            self.up = True
            y = head['y_pos'] + Millipede.HEIGHT
            self.max_y = Millipede.MAX_Y
            # trigger Millipede spawn in player area
            self.game.spawn_millipede_in_player_area()

        if y < self.max_y: 
            self.down = True
            self.up = False
            y = head['y_pos'] - Millipede.HIEGHT


    def move(self):
        # move head & move body
        head = self.body[0]

        if not head:
            return

        if self.move_count > 0:
            self.move_count -= 1

            for m in self.body:
                m['prev_x'] = m['x_pos']
                m['prev_y'] = m['y_pos']
                m['x_pos'] += m['dx']
                m['y_pos'] += m['dy']
                m['rect'].top = m['y_pos']
                m['rect'].left = m['x_pos']

        else:
            # reset movement counter
            self.move_count = Millipede.MOVE_COUNT

            # used to see if we need to change rows and/or alternate 
            # direction of movement
            alternate_dir = False
            random_dir = False

            x = head['x_pos']
            y = head['y_pos']

            # was moving left
            if self.left and not self.change_row:
                if head['x_pos'] > 0:
                    x = head['x_pos'] - Millipede.WIDTH
                    y = head['y_pos']

                elif head['x_pos'] == 0:
                    self.change_row = True

            # was moving right
            elif self.right and not self.change_row:
                x_max = Game.ARENA_W - Millipede.WIDTH
                if head['x_pos'] < x_max:
                    x = head['x_pos'] + Millipede.WIDTH
                    y = head['y_pos']
                elif head['x_pos'] == x_max:
                    self.change_row = True

            # change rows up or down if needed
            if self.change_row:
                if self.down:
                    x = head['x_pos']
                    y = head['y_pos'] + Millipede.HEIGHT
                elif self.up:
                    x = head['x_pos']
                    y = head['y_pos'] - Millipede.HEIGHT

                if y >= (Game.ARENA_H-Millipede.HEIGHT):
                    random_dir = True
                    self.down = False
                    self.up = True
                    y = head['y_pos'] + Millipede.HEIGHT
                    self.max_y = Millipede.MAX_Y
                    # trigger Millipede spawn in player area
                    self.game.spawn_millipede_in_player_area()
                    # Millipede is no longer poisoned when it
                    # reaches the bottom of the player area
                    if self.poisoned:
                        self.poisoned = False

                if y < self.max_y:
                    self.down = True
                    self.up = False
                    y = head['y_pos'] - Millipede.HEIGHT

                if not self.poisoned: 
                    self.change_row = False
                    alternate_dir = True

            # at this point the movement way point has been set
            # need to see if we can move into the desired grid point

            # check for mushroom collision
            collision = self.game.mushroom_field.millipede_collision(x, y)

            if not self.poisoned and not self.pa_spawned and collision:
                # collision has occured, change millipede direction
                # and move up or down a row depending on which way we
                # are going.

                # did we hit a poisoned mushroom?
                if self.game.mushroom_field.is_poisoned(x, y):
                    # poison the Millipede and make dive down
                    if DEBUG:
                        print "MILLIPEDE POISONED!!!!"
                    self.poisoned = True
                    alternate_dir = False
                    self.down = True
                    self.up = False

                self.change_row = True

            # make normal an Millipedes which spawned in player
            # area
            if self.pa_spawned:
                self.pa_spawned = False

            # alternate between left/right movement
            if alternate_dir:
                #n = random.randint(0,10)
                if self.left:
                    self.left = False
                    self.right = True
                else:
                    self.left = True
                    self.right = False

            # make Millipede more eratic if in player area
            if random_dir:
                n = random.randint(0,10)
                if n < 5:
                    self.left = True
                    self.right = False
                else:
                    self.left = False
                    self.right = True
            
            # keep track of head's current position before
            # waypoint change -- this is used by the body
            # to keep it moving along.
            #
            # move the head and propagate the waypoint change(s)
            # to the body
            #
            self.set_waypoint( x, y )

    def set_waypoint(self, x, y):
        """set target position for Millipede to move towards."""
        # need to handle special case where both dy and y are negative
        # ie. we are just starting to move into the board
        x0 = x
        y0 = y
        for m in self.body:
            x1 = m['x_pos']
            y1 = m['y_pos']
            if (y0 < 0) or (m['y_pos'] < 0):
                m['dx'] = 0
                m['dy'] = Millipede.move_inc
            else:
                dx = x0 - m['x_pos']
                dy = y0 - m['y_pos']

                if dx > 0:
                    m['dx'] = Millipede.move_inc
                elif dx < 0:
                    m['dx'] = -Millipede.move_inc
                else:
                    m['dx'] = 0
                
                if dy > 0:
                    m['dy'] = Millipede.move_inc
                elif dy < 0:
                    m['dy'] = -Millipede.move_inc
                else:
                    m['dy'] = 0
                    
            x0 = x1
            y0 = y1
    

    def collision(self, rect):
        """check for collision against other sprite."""
        m_rect = pygame.Rect(0,0,Millipede.WIDTH,Millipede.HEIGHT)
        hit = False
        for m in self.body:
            m_rect.left = m['x_pos']
            m_rect.top = m['y_pos']
            if m_rect.colliderect( rect ):

                self.game.stop_ninth_millipede()

                hit = True

                fx = m['x_pos'] / MushroomField.MUSHROOM_WIDTH
                fy = m['y_pos'] / MushroomField.MUSHROOM_WIDTH

                self.game.mushroom_field.add_mushroom( fx, fy )

                """ 
                split the millipede body at segment where collision
                occurrs and create a new instance of millipede
                """

                index = self.body.index( m )
                n = len(self.body)

                # determine score
                if index == 0:
                    self.game.score += Millipede.HEAD_POINTS
                    self.game.popups.add(
                    m['x_pos'],
                    m['y_pos'],
                    Millipede.HEAD_POINTS)
                else:
                    self.game.score += Millipede.BODY_POINTS

                # split Millipede if it has segments
                if n > 1:
                    # make millipede dive down if split
                    self.change_row = True
                    # split body into two parts 
                    n -= 1
                    body0 = self.body[0:index]
                    index += 1
                    body1 = self.body[index:n]
                    if (len(body0) == 0) and (len(body1) == 0):
                        self.game.millipedes.remove(self)
                        break

                    if body0 != []:
                        self.body = body0
                        n = len(body1)
                        if n > 0:
                            child = Millipede(self.game, -1)
                            child.body = body1
                            self.set_child_state( child )
                            self.game.millipedes.append( child )
                    else:
                        self.body = body1
                else:
                    # nothing of the Millipede remains kill it
                    self.game.millipedes.remove( self )
                break
            
        return hit

    
    def go_left(self):
        """make Millipede (which spawned in player area) go left."""
        self.change_row = False
        self.up = False
        self.down = True
        self.left = True
        self.right = False
        self.pa_spawned = True

    
    def go_right(self):
        """make Millipede (which spawned in player area) go right."""
        self.change_row = False
        self.up = False
        self.down = True
        self.left = False
        self.right = True
        self.pa_spawned = True


    def set_child_state(self, child):
        """ copy some parent state variables to the child."""
        child.move_count = self.move_count
        child.change_row = True
        child.max_y = self.max_y
        child.up = self.up
        child.down = self.down
        child.left = not self.right
        child.right = not self.left


#####################################################################

class MushroomField:
    """Mushrooms, Flowers, and DDTs oh my!"""

    images = None
    flower_img = None
    poisoned_img = None
    
    colors = ( ([0,128,0], [0,164,0], [0,198,0], [0,255,0]), \
    ([100,15,100], [127,30,127], [191,45,191], [255, 60, 255]), \
    ([25,39,75], [52, 77, 102], [77,115,153], [102,153,204]), \
    ([128,0,0], [164,0,0], [198,0,0], [255,0,0]), \
    ([88,0,117], [109,0,146], [131,0,179], [153,0,204]), \
    ([101,128,128], [119,164,164], [136,198,198], [153,255,255]), \
    ([0,0,128], [0,0,164], [0,0,198], [0,0,255]))

    poisoned_colors = ([0,27,128], [0,54,164], [0,81,198], [0,108,255])

    # mushroom field size is 30x30 mushrooms
    MUSHROOM_WIDTH = 12
    MUSHROOM_HEIGHT = 12
    MUSHROOM_HP = 4

    FIELD_WIDTH = Game.ARENA_W / MUSHROOM_WIDTH
    FIELD_HEIGHT = Game.ARENA_H / MUSHROOM_HEIGHT
    FIELD_PLAYER_Y = 24
    FIELD_PLAYER_Y_INDEX = FIELD_PLAYER_Y * MUSHROOM_WIDTH
    FIELD_PLAYER_Y_POS = FIELD_PLAYER_Y * MUSHROOM_WIDTH

    MAX_MUSHROOMS = FIELD_WIDTH * FIELD_HEIGHT

    MUSHROOM_POINTS = 1

    INITIAL_MUSHROOMS = 75

    MOVE_ROW_DOWN = 0 
    MOVE_ROW_UP = 1 

    def __init__(self, game):

        self.game = game

        self.cur_color_idx = 0
        self.cur_color = MushroomField.colors[self.cur_color_idx]

        # initialize mushroom images
        if MushroomField.images == None:

            MushroomField.flower_img = \
            pygame.Surface([MushroomField.MUSHROOM_WIDTH,\
            MushroomField.MUSHROOM_HEIGHT]) 
            
            tmp_rect = pygame.Rect(2,2,\
            MushroomField.MUSHROOM_WIDTH-4,\
            MushroomField.MUSHROOM_HEIGHT-4)

            MushroomField.flower_img = load_image("sprites/flower.png")

            MushroomField.poisoned_img = []

            for i in range(0,4):
                MushroomField.poisoned_img.append( \
                 pygame.Surface([MushroomField.MUSHROOM_WIDTH,\
                  MushroomField.MUSHROOM_HEIGHT])) 
                MushroomField.poisoned_img[i].fill( [0,255,255] )
                MushroomField.poisoned_img[i].fill( \
                MushroomField.poisoned_colors[i], tmp_rect )

            MushroomField.images = []

            self.tmp_rect = pygame.Rect(3,3,\
            MushroomField.MUSHROOM_WIDTH-3,\
            MushroomField.MUSHROOM_HEIGHT-3)

            for i in range(0,4):
                img = pygame.Surface([MushroomField.MUSHROOM_WIDTH,\
                MushroomField.MUSHROOM_HEIGHT])
                img.fill( [0,0,0] )
                img.fill( self.cur_color[i], self.tmp_rect )
                MushroomField.images.append(img)


        """
        Build the mushroom grid a dict of dicts representing 
        mushroom_field in their various states. To start make
        the grid empty of mushroom_field -- hp == 0

        hp - 'hit points'

        The hp also corresponds to the index of the mushroom
        image inside of the MushroomField.images array.
        """

        self.m_arr = []
        self.m_idx = []
        self.m_pos = []

        self.total_player_area_mushrooms = 0

        def __new_mushroom(index):
            """create mushroom dict entry."""
            # need to include x and y positions for collision
            # purposes

            assert (index > -1) and \
            (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index

            x = index % MushroomField.FIELD_WIDTH
            y = index / MushroomField.FIELD_WIDTH

            # calculate topleft x and y screen coordinates
            topleft = ( x * MushroomField.MUSHROOM_WIDTH,
                    y * MushroomField.MUSHROOM_WIDTH )

            #MushroomField.images[0] = img
            rect = pygame.Rect( 0, 0, 0, 0 )
            rect.width = MushroomField.MUSHROOM_WIDTH
            rect.height = MushroomField.MUSHROOM_HEIGHT
            rect.topleft = topleft

            m = { 'hp' : 0, \
            'rect': rect, \
            'poisoned': False, \
            'flower': False, \
            'ttl': 0,\
            'ddt': False }

            return m

        # initialize the mushroom field arrays
        for i in xrange(0,MushroomField.MAX_MUSHROOMS):
            m = __new_mushroom(i)
            self.m_arr.append( m )
            self.m_idx.append( i )
            self.m_pos.append( m['rect'] )


    def draw(self,buffer):
        """Draw the Mushroom Field."""

        for i in xrange(0,MushroomField.MAX_MUSHROOMS):
            index = self.m_idx[i]
            pos = self.m_pos[i]
            m = self.m_arr[index]
            if m['hp'] > 0:
                if m['poisoned']:
                    img = MushroomField.poisoned_img[m['hp']-1]
                else:
                    img = MushroomField.images[m['hp']-1]
                buffer.blit( img, pos )
            if m['flower']:
                img = MushroomField.flower_img
                buffer.blit( img, pos )


    def eat_mushroom(self, fx, fy):
        """Spider eats a mushroom or a flower."""
        if (fx > -1) and (fx < MushroomField.FIELD_WIDTH) \
                and (fy > -1) and (fy < MushroomField.FIELD_HEIGHT):
            index = (fy * MushroomField.FIELD_WIDTH) + fx
            assert (index > -1) and (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index
            m = self.m_arr[self.m_idx[index]]
            if (m['hp'] > 0) or m['flower']:
                self.__reset_mushroom( index )
                self.update_player_area_mushrooms(fy, -1)


    def mushroom_to_flower(self, fx, fy):
        """Turn a mushroom into a flower."""

        """ do not allow a flower to be placed in player area."""
        if fy == MushroomField.FIELD_HEIGHT - 1:
            return
        if (fx > -1) and (fx < MushroomField.FIELD_WIDTH) \
                and (fy > -1) and (fy < MushroomField.FIELD_HEIGHT):
            index = (fy * MushroomField.FIELD_WIDTH) + fx
            assert (index > -1) and (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index
            m = self.m_arr[self.m_idx[index]]
            if m['hp'] > 0:
                m['hp'] = 0
                m['poisoned'] = False
                m['flower'] = True
                m['ttl'] = self.game.get_ticks()
                self.update_player_area_mushrooms(fy, -1)
                # do not accidentally place a flower on top of the
                # player
                self.clear_player_area()
                self.game.damaged_mushrooms.append(index)

    
    def poison_mushroom(self, fx, fy):
        if (fx > -1) and (fx < MushroomField.FIELD_WIDTH) \
                and (fy > -1) and (fy < MushroomField.FIELD_HEIGHT):
            index = (fy * MushroomField.FIELD_WIDTH) + fx
            assert (index > -1) and (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index
            m = self.m_arr[self.m_idx[index]]
            if m['hp'] > 0:
                m['poisoned'] = True
                if index not in self.game.damaged_mushrooms:
                    self.game.damaged_mushrooms.append(index)


    def is_poisoned(self, x, y):
        """check to see if mushroom at x,y is posison."""
        x = x / MushroomField.MUSHROOM_WIDTH
        y = y / MushroomField.MUSHROOM_HEIGHT
        index = ( y * MushroomField.FIELD_WIDTH ) + x
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        m = self.m_arr[self.m_idx[index]]
        return m['poisoned']


    def wilt_flowers(self):
        """Remove flowers from the Mushroom Field."""
        cur_time = self.game.get_ticks()
        for i in xrange(0, MushroomField.MAX_MUSHROOMS):
            m = self.m_arr[self.m_idx[i]]
            if m['flower']:
                if (cur_time - m['ttl']) > 10000:
                    self.__reset_mushroom( i )


    def populate_randomly(self):
        """Populate the mushroom field randomly."""
        #return

        # populate the mushroom field with some mushrooms
        for i in xrange(MushroomField.INITIAL_MUSHROOMS):
            fx = random.randrange(0, MushroomField.FIELD_WIDTH)
            fy = random.randrange(0, MushroomField.FIELD_HEIGHT-1)
            index = (fy * MushroomField.FIELD_WIDTH) + fx
            assert (index > -1) and \
            (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index

            """
            must check to make sure we didn't already put down a
            mushroom. this was causing an over count bug. a mushroom
            could be placed on top of an existing mushroom and
            the count would not be properly decremented. This means
            that anywhere a mushroom is being added I must check to
            see if there is already a mushroom there, if there is
            then do not add a new mushroom otherwise this will
            result in incorrent mushroom counts.
            """

            i = self.m_idx[index]
            m = self.m_arr[i]

            if (m['hp'] == 0) and not m['ddt']:
                self.__reset_mushroom( index )
                m['hp'] = MushroomField.MUSHROOM_HP
                self.update_player_area_mushrooms(fy, 1) 

        # place an initial population of DDTs in the arena
        for i in range(0,Game.MAX_DDTS):
            while True:
                fx = random.randrange(0, MushroomField.FIELD_WIDTH-1)
                fy = random.randrange(0, MushroomField.FIELD_PLAYER_Y-1)
                #fy = MushroomField.FIELD_PLAYER_Y-1
                if not self.__has_ddt(fx, fy):
                    self.__add_ddt(fx, fy)
                    break


    def player_collision(self,player_rect):
        """Determine if player collided with one more more Mushrooms."""

        """ 
        determine which mushrooms need to be included in the rect
        list for colliding against the player 
        """

        x,y = player_rect.topleft

        x = x / MushroomField.MUSHROOM_WIDTH
        y = y / MushroomField.MUSHROOM_HEIGHT

        m_list = []

        index = (y * MushroomField.FIELD_WIDTH) + x
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        i = self.m_idx[index]
        m = self.m_arr[i]
        if (m['hp'] > 0) or (m['flower']):
            m_list.append(self.m_pos[index])

        x += 1
        if x < MushroomField.FIELD_WIDTH:
            index = (y * MushroomField.FIELD_WIDTH) + x
            i = self.m_idx[index]
            m = self.m_arr[i]
            if (m['hp'] > 0) or (m['flower']):
                m_list.append(self.m_pos[index])

            y += 1
            if y < MushroomField.FIELD_HEIGHT:
                index = (y * MushroomField.FIELD_WIDTH) + x
                i = self.m_idx[index]
                m = self.m_arr[i]
                if (m['hp'] > 0) or (m['flower']):
                    m_list.append(self.m_pos[index])
                x -= 1
                index = (y * MushroomField.FIELD_WIDTH) + x
                i = self.m_idx[index]
                m = self.m_arr[i]
                if (m['hp'] > 0) or (m['flower']):
                    m_list.append(self.m_pos[index])
        else:
            x -= 1
            y += 1
            if y < MushroomField.FIELD_HEIGHT:
                index = (y * MushroomField.FIELD_WIDTH) + x
                i = self.m_idx[index]
                m = self.m_arr[i]
                if (m['hp'] > 0) or (m['flower']):
                    m_list.append(self.m_pos[index])
              
        if player_rect.collidelist( m_list ) > -1:
            return True
        else:
            return False


    def millipede_collision(self, x, y):
        """check for Millipede vs Mushroom collision."""
        if (y < 0) or (y > (Game.SCREEN_H-Game.SCORE_H-1)):
            return False
        
        x = x / MushroomField.MUSHROOM_WIDTH
        y = y / MushroomField.MUSHROOM_HEIGHT

        index = (y * MushroomField.FIELD_WIDTH) + x
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        i = self.m_idx[index]
        m = self.m_arr[i]

        return (m['hp'] > 0) or m['flower']


    def missile_collision(self, missile_rect):
        """check for Player Missle vs Mushroom collision."""

        """
        this code needs to handle cases where there is
        greater overlap between neighbors
        could use Rect.collidelistall method 

        currently this code has a preference for the left most
        grid
        """

        grids = []

        x, y = missile_rect.topleft
        
        """
        check neighboring cells
        check current row left,right,center
        and below left,right,center
        """

        if (y < -MushroomField.MUSHROOM_HEIGHT):
            return False
        
        # below first row
        if (y > (MushroomField.MUSHROOM_HEIGHT - 1)):
            y0 = y / MushroomField.MUSHROOM_HEIGHT
        # first row -- clamp y grid value since we can go into y<0
        else:
            y0 = 0

        x0 = x / MushroomField.MUSHROOM_WIDTH

        # far right -- only need to consider 1 grid
        if (x > Game.ARENA_W):
            grids.append( (x0, y0) )
        else:
            # determine which grid must be checked first
            # the current one or the one to the right?

            index = ( y0 * MushroomField.FIELD_WIDTH ) + x0
            assert (index > -1) and \
            (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index
            i = self.m_idx[index]
            m = self.m_arr[i]
            #(tmp_x, tmp_y) = m['rect'].topleft
            (tmp_x, tmp_y) = self.m_pos[index].topleft
            dx = tmp_x + MushroomField.MUSHROOM_WIDTH - x
            # right grid first
            if dx < PlayerMissile.HALF_WIDTH:
                grids.append( (x0+1, y0) )
                grids.append( (x0, y0) )
            # left grid first
            else:
                grids.append( (x0, y0) )
                grids.append( (x0+1, y0) )

        missile_hit = False
        m_rect = pygame.Rect(0, 0, \
                MushroomField.MUSHROOM_WIDTH, \
                MushroomField.MUSHROOM_HEIGHT)

        for fx,fy in grids:
            index = ( fy * MushroomField.FIELD_WIDTH ) + fx
            assert (index > -1) and \
            (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index
            i = self.m_idx[index]
            m = self.m_arr[i]
            #m_rect.topleft = m['rect'].topleft
            m_rect.topleft = self.m_pos[index].topleft
            if (m['hp'] > 0) or m['flower']:
                if m_rect.colliderect(missile_rect):
                    missile_hit = True
                    if index not in self.game.damaged_mushrooms:
                        self.game.damaged_mushrooms.append(index)
                    if m['flower'] == False:
                        m['hp'] -= 1
                        if m['hp'] == 0:
                            self.game.score += \
                                    MushroomField.MUSHROOM_POINTS
                            self.update_player_area_mushrooms(fy, -1)
                    break

        return missile_hit


    def add_mushroom(self, fx=-1, fy=-1, index=-1):
        """add a mushroom at grid coordinates (fx, fy)"""
        # do not allow mushroom to be created in the players
        # grid position
        if index < 0:
            if (fx<0) or (fy<0) or \
                (fx>=MushroomField.FIELD_WIDTH) or \
                (fy>=MushroomField.FIELD_HEIGHT):
                return
            index = ( fy * MushroomField.FIELD_WIDTH ) + fx

        assert (index > -1) and\
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        i = self.m_idx[index]
        m = self.m_arr[i]

        # do not allow mushroom to appear on top of a DDT
        if m['ddt']:
            return

        # do not allow mushroom to appear on top of the player
        if self.game.player.rect.colliderect( self.m_pos[index] ):
            return

        # do not allow mushroom to appear in the player row
        if fy == (MushroomField.FIELD_HEIGHT-1):
            return

        # place a mushroom only if one does not already exist
        if m['hp'] == 0:
            self.__reset_mushroom( index )
            m['hp'] = MushroomField.MUSHROOM_HP
            self.update_player_area_mushrooms(fy,1)


    def __add_ddt(self, fx, fy):
        """add a ddt at grid coordinates (fx, fy)"""

        """
        NOTE: this method will overwrite what ever was in the
        current mushroom field grid for index and index+1
        """
        index = (fy * MushroomField.FIELD_WIDTH) + fx
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        self.__reset_mushroom(index)
        self.__reset_mushroom(index+1)
        ddt = DDT(self.game,fx*MushroomField.MUSHROOM_WIDTH, \
        fy*MushroomField.MUSHROOM_HEIGHT)
        if DEBUG:
            print "ADD DDT: ", index, fx, fy
        ddt.add(self.game.ddts)
        i = self.m_idx[index]
        j = self.m_idx[index+1]
        # a ddt takes up 2 squares, but we only want to keep
        # one reference otherwise a row shift would result
        # in the ddt going up twice
        self.m_arr[i]['ddt'] = True
        self.m_arr[j]['ddt'] = True


    def remove_ddt(self, fx, fy):
        """remove a ddt at grid coordinates (fx, fy)"""
        # called when DDT becomes active
        index = (fy * MushroomField.FIELD_WIDTH) + fx
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d (%d %d)" % (index, fx, fy)
        self.__reset_mushroom(index)
        self.__reset_mushroom(index+1)


    def __has_ddt(self, fx, fy):
        """check for a ddt at grid coordinates (fx, fy)"""
        index = (fy * MushroomField.FIELD_WIDTH) + fx
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        m0 = self.m_arr[self.m_idx[index]]
        m1 = self.m_arr[self.m_idx[index+1]]
        return (m0['ddt'] or m1['ddt'])


    def update_player_area_mushrooms(self, fy=-1, inc=0):
        """keep track of num mushrooms in player area."""
        # handle row down or up, just do a total count
        # once row change has taken place
        if inc == 0:
            self.total_player_area_mushrooms = 0
            for fy in xrange(MushroomField.FIELD_PLAYER_Y,
                    MushroomField.FIELD_HEIGHT):
                for fx in xrange(0, MushroomField.FIELD_WIDTH):
                    index = (MushroomField.FIELD_WIDTH * fy) + fx

                    assert (index > -1) and \
                    (index < MushroomField.MAX_MUSHROOMS), \
                    "Index out of bounds: %d" % index

                    m = self.m_arr[self.m_idx[index]]
                    if m['hp'] > 0:
                        self.total_player_area_mushrooms += 1
        # handle all other cases
        else:
            if fy >= MushroomField.FIELD_PLAYER_Y:
                self.total_player_area_mushrooms += inc


    def row_up(self):
        """move field row up and clear the last row."""
        # shift the rows up
        if DEBUG:
            print self.m_idx
        n = MushroomField.FIELD_WIDTH
        m = MushroomField.MAX_MUSHROOMS
        first_row = self.m_idx[0:n]
        self.m_idx = self.m_idx[n:m] + first_row
        if DEBUG:
            print self.m_idx
        
        # reset bottom-row of mushrooms
        n = MushroomField.MAX_MUSHROOMS - MushroomField.FIELD_WIDTH
        for i in range(n,m):
            self.__reset_mushroom(i)
       
        """ bookkeeping """
        # move the DDTs UP
        for d in self.game.ddts:
            d.update_position(MushroomField.MOVE_ROW_UP)
        self.clear_player_area()
        self.update_player_area_mushrooms()
        self.__update_damaged_mushrooms(-MushroomField.FIELD_WIDTH)
 

    def row_down(self):
        """move field row down and spawn a new row of fresh 
        mushrooms and ddts.""" 
 
        # shift the rows down
        n = MushroomField.MAX_MUSHROOMS - MushroomField.FIELD_WIDTH
        m = MushroomField.MAX_MUSHROOMS
        last_row = self.m_idx[n:m]
        self.m_idx = last_row + self.m_idx[0:n]

        # reset top-row of mushrooms
        for i in range(0,MushroomField.FIELD_WIDTH):
            self.__reset_mushroom(i)
       
        """ bookkeeping """
        def __clear_ddts():
            """remove ddts entering the player area."""
            start = (MushroomField.FIELD_WIDTH * MushroomField.FIELD_PLAYER_Y)
            end = start + MushroomField.FIELD_WIDTH
            if DEBUG:
                print "CLEAR DDTs ", start, end
            for i in xrange(start, end):
                ddt = self.m_arr[self.m_idx[i]]['ddt']
                if ddt:
                    if DEBUG:
                        print "REMOVING DDT in PLayer Area"
                    self.__reset_mushroom(i)


        def __row_spawn():
            """spawn a new row of mushrooms and ddts."""

            # generate n number of mushrooms
            n = random.randrange(0,MushroomField.MUSHROOM_WIDTH)
            for i in range(n):
                x = random.randrange(0,MushroomField.FIELD_WIDTH)
                self.add_mushroom(x, 0)

            n = len(self.game.ddts)
            if DEBUG:
                print "num ddts ", n
            if n < Game.MAX_DDTS:
                chance = (4-n) * 25
                r = random.randrange(0,100)
                # 25% chance to spawn a DDT
                if DEBUG:
                    print chance, r
                if r <= chance:
                    if DEBUG:
                        print "DDT spawned"
                    x = random.randrange(0,MushroomField.FIELD_WIDTH-1)
                    self.__add_ddt(x, 0)
            n = len(self.game.ddts)
            if DEBUG:
                print "num ddts ", n

        # move the DDTs down
        for d in self.game.ddts:
            d.update_position(MushroomField.MOVE_ROW_DOWN)
        self.clear_player_area()
        self.update_player_area_mushrooms()
        # bring in a new row of mushrooms and ddts
        __clear_ddts()
        __row_spawn()
        self.__update_damaged_mushrooms(MushroomField.FIELD_WIDTH)

        
    def __update_damaged_mushrooms(self, dy):
        """ updated damaged mushrooms list """
        n = len(self.game.damaged_mushrooms)
        m = 0
        for i in xrange(0,n):
            if DEBUG:
                print i, n
                print self.game.damaged_mushrooms[i]
            self.game.damaged_mushrooms[i] += dy
            if (self.game.damaged_mushrooms[i] > \
                (MushroomField.MAX_MUSHROOMS-1)) or \
                (self.game.damaged_mushrooms[i] < 0):
                self.game.damaged_mushrooms[i] = -1
                m += 1

        """ clear any mushrooms which have scrolled off the field """
        for i in xrange(0,m):
                if DEBUG:
                    print "Update Damaged Mushroom List: ", i
                self.game.damaged_mushrooms.remove(-1)

        if DEBUG:
            print "DAMAGED MUSHROOMS LIST"
            print self.game.damaged_mushrooms


    def __reset_mushroom(self, index):
        """reset mushroom grid entry."""

        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index
        i = self.m_idx[index]
        self.m_arr[i]['hp'] = 0
        self.m_arr[i]['poisoned'] = False
        self.m_arr[i]['flower'] = False
        self.m_arr[i]['ttl'] = False
        self.m_arr[i]['ddt'] = False


    def reset(self):
        """Clear the MushroomField."""
        # pick starting color
        n = len(MushroomField.colors)
        self.cur_color_idx = random.randrange(0,n)
        self.cur_color = MushroomField.colors[self.cur_color_idx]
        for i in range(0,4):
           img = MushroomField.images[i]
           img.fill([0,0,0])
           img.fill(self.cur_color[i], self.tmp_rect)
 
        # clear the field
        for i in xrange(0, MushroomField.MAX_MUSHROOMS):
            self.__reset_mushroom(i)
            self.game.ddts.empty()


    def restore_mushroom(self, index):
        """called by player death routine. Restore mushrooms."""

        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index

        i = self.m_idx[index]

        restore = False

        if self.m_arr[i]['flower']:
            fx = index % MushroomField.FIELD_WIDTH
            fy = index / MushroomField.FIELD_WIDTH
            self.__reset_mushroom(index)
            self.add_mushroom(fx, fy)
            self.update_player_area_mushrooms()
            restore = True
            if DEBUG:
                print "FLOWER RESTORED"

        #elif (self.m_arr[i]['hp'] > 0) and \
        #    (self.m_arr[i]['hp'] < MushroomField.MUSHROOM_HP):
        elif self.m_arr[i]['hp'] > 0:
            self.m_arr[i]['hp'] = MushroomField.MUSHROOM_HP
            self.m_arr[i]['poisoned'] = False
            restore = True
            if DEBUG:
                print "DAMAGED MUSHROOM RESTORED: %d " % self.m_arr[i]['hp']
                print MushroomField.MUSHROOM_HP

        if restore:
            if DEBUG:
                print "MUSHROOM RESTORED: %d " % index
            """ player restore sound here... """
            self.game.player_missile_snd.play()

        return restore


    def clear_player_area(self):
        """clear player area of mushrooms."""

        """
        there is a lot of duplicated code here... must refactor...
        but it works for now... 
        """

        """ first reset bottom most row in the
        original game there are no mushrooms present
        in the bottom most row. """
        n = MushroomField.MAX_MUSHROOMS-MushroomField.FIELD_WIDTH
        for i in xrange(n, MushroomField.MAX_MUSHROOMS):
            self.__reset_mushroom(i)

        """ now remove any mushrooms which may have collided
        or been placed ontop of the player. """

        x, y = self.game.player.rect.topleft
        fx = x / MushroomField.MUSHROOM_WIDTH
        fy = y / MushroomField.MUSHROOM_HEIGHT

        m_list = []

        index = (fy * MushroomField.FIELD_WIDTH) + fx
        assert (index > -1) and \
        (index < MushroomField.MAX_MUSHROOMS), \
        "Index out of bounds: %d" % index

        i = self.m_idx[index]

        m = self.m_arr[i]
        if (m['hp'] > 0) or (m['flower']):
            m_list.append(index)

        fx += 1
        if fx < MushroomField.FIELD_WIDTH:
            index = (fy * MushroomField.FIELD_WIDTH) + fx
            assert (index > -1) and \
            (index < MushroomField.MAX_MUSHROOMS), \
            "Index out of bounds: %d" % index
            i = self.m_idx[index]
            m = self.m_arr[i]
            if (m['hp'] > 0) or (m['flower']):
                m_list.append(index)

            fy += 1
            if fy < MushroomField.FIELD_HEIGHT:
                index = (fy * MushroomField.FIELD_WIDTH) + fx
                assert (index > -1) and \
                (index < MushroomField.MAX_MUSHROOMS), \
                "Index out of bounds: %d" % index 
                i = self.m_idx[index]
                m = self.m_arr[i]
                if (m['hp'] > 0) or (m['flower']):
                    m_list.append(index)
                fx -= 1
                index = (fy * MushroomField.FIELD_WIDTH) + fx
                i = self.m_idx[index]
                m = self.m_arr[i]
                if (m['hp'] > 0) or (m['flower']):
                    m_list.append(index)
        else:
            fx -= 1
            fy += 1
            if fy < MushroomField.FIELD_HEIGHT:
                index = (fy * MushroomField.FIELD_WIDTH) + fx
                assert (index > -1) and \
                (index < MushroomField.MAX_MUSHROOMS), \
                "Index out of bounds: %d" % index 
                i = self.m_idx[index]
                m = self.m_arr[i]
                if (m['hp'] > 0) or (m['flower']):
                    m_list.append(index)
              
        for i in m_list:
            m = self.m_arr[i]
            if self.game.player.rect.colliderect(m['rect']):
                fx = i % MushroomField.FIELD_WIDTH
                fy = i / MushroomField.FIELD_WIDTH
                # remember my friends, flowers do not count as
                # mushroom!
                if not m['flower']:
                    self.update_player_area_mushrooms( fy, -1 )
                self.__reset_mushroom(i)


    def change_color(self):
        self.cur_color_idx += 1
        if self.cur_color_idx == len(MushroomField.colors):
            self.cur_color_idx = 0

        self.cur_color = MushroomField.colors[self.cur_color_idx]

        for i in range(0,4):
           img = MushroomField.images[i]
           img.fill([0,0,0])
           img.fill(self.cur_color[i], self.tmp_rect)
 

    def birth_and_death(self):
        """Mushroom Field Birth and Death."""

        """
        From wikipedia:

        Conway's Game of Life Rules

        For each cell apply the following rules:

        1. Any live cell with fewer than two live neighbors dies, as
        if by loneliness.
        2. Any live cell with more than three live neighbors dies, as
        if by overcrowding.
        3. Any live cell with two or three live neighbors lives,
        unchanged, to the next generation.
        4. Any dead cell with exactly three live neighbors comes to
        life.

        """

        cells = [-1, -1, -1, -1, -1, -1, -1, -1]

        # last row is always empty
        n = MushroomField.MAX_MUSHROOMS - MushroomField.FIELD_WIDTH - 1

        for i in xrange(0,n):
            if i == 0:
                cells[0] = self.m_idx[i+1]
                cells[1] = self.m_idx[i+MushroomField.FIELD_WIDTH]
                cells[2] = self.m_idx[i+MushroomField.FIELD_WIDTH+1]
                count = 3
            elif i < MushroomField.FIELD_WIDTH:
                cells[0] = self.m_idx[i-1]
                cells[1] = self.m_idx[i+1]
                cells[2] = self.m_idx[i+MushroomField.FIELD_WIDTH-1]
                cells[3] = self.m_idx[i+MushroomField.FIELD_WIDTH]
                cells[4] = self.m_idx[i+MushroomField.FIELD_WIDTH+1]
                count = 5 
            else:
                cells[0] = self.m_idx[i-1-MushroomField.FIELD_WIDTH]
                cells[1] = self.m_idx[i-MushroomField.FIELD_WIDTH]
                cells[2] = self.m_idx[i-MushroomField.FIELD_WIDTH+1]
                cells[3] = self.m_idx[i-1]
                cells[4] = self.m_idx[i+1]
                cells[5] = self.m_idx[i+MushroomField.FIELD_WIDTH-1]
                cells[6] = self.m_idx[i+MushroomField.FIELD_WIDTH]
                cells[7] = self.m_idx[i+MushroomField.FIELD_WIDTH+1]
                count = 8

            neighbors = 0
            for j in range(0,count):
                m = self.m_arr[cells[j]]
                if (m['hp'] > 0) and not m['ddt']:
                    neighbors += 1

            if DEBUG:
                print "neighbors: ", neighbors

            m = self.m_arr[self.m_idx[i]]
            if DEBUG:
                print m['hp']
            # mushroom dies
            if m['hp'] and not m['ddt']:
                if (neighbors < 2) or (neighbors > 3):
                   self.__reset_mushroom(i)
            # mushroom regrows
            elif not m['ddt'] and (neighbors==3):
                self.add_mushroom(index=i) 
            
        self.update_player_area_mushrooms()

#####################################################################


class Bee(pygame.sprite.Sprite):
    """The Bee

    Leaves behind mushrooms when there are less than five
    mushroom in the player area. Number to trigger bee to arrive
    varies as level increases.
    """

    POINTS = 200
    HEIGHT = -1
    WIDTH = -1
    HP = 2
    frames = None
    max_frames = 0
    y_inc_slow = 4
    y_inc_fast = 5

    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)

        if Bee.frames == None:
            Bee.frames = []
            Bee.frames.append(load_image("sprites/bee0.png"))
            Bee.frames.append(load_image("sprites/bee1.png"))
            Bee.max_frames = len(Bee.frames)
            Bee.HEIGHT = Bee.frames[0].get_height()
            Bee.WIDTH = Bee.frames[0].get_width()

        self.image = Bee.frames[0]
        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0
        #self.rect = self.image.get_rect()

        start_x = (random.randrange(0,Game.SCREEN_W-1) / Bee.WIDTH) * Bee.WIDTH
        self.hp = Bee.HP
        self.dy = Bee.y_inc_slow
        self.column = start_x / MushroomField.MUSHROOM_WIDTH
       
        """ pick a column to spawn in...
        ok this could be really bad, but there is a limited
        number of Bees per frame so it should be a problem;
        however if the program ever goes into an infite
        loop this will be the first place to look! 
        """
        start_x = (random.randrange(0,Game.SCREEN_W-1) / Bee.WIDTH) * Bee.WIDTH
        self.column = start_x / MushroomField.MUSHROOM_WIDTH
        self.rect = pygame.Rect( start_x, 0, Bee.WIDTH, Bee.HEIGHT )
    
    def update(self):

        """ update animation ... """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Bee.max_frames:
                self.cur_frame = 0
            self.image = Bee.frames[self.cur_frame]


        gx = self.rect.left / MushroomField.MUSHROOM_WIDTH
        gy = self.rect.top / MushroomField.MUSHROOM_HEIGHT
        n = random.randrange(0,100)
        if self.rect.top < (Game.SCREEN_H - Game.SCORE_H):
            """ need better way of doing this ... """

            """ If not in swarm stage increase probability that
            a Bee will create a Mushroom. """
            if self.game.swarmfn == None:
                if gy < MushroomField.FIELD_PLAYER_Y:
                    # 2% chance
                    if n < 2:
                        #self.game.mushroom_field.grow_mushroom( gx, gy )
                        self.game.mushroom_field.add_mushroom( gx, gy )
                else:
                    # 10% chance
                    if n < 10:
                        #self.game.mushroom_field.grow_mushroom( gx, gy )
                        self.game.mushroom_field.add_mushroom( gx, gy )
            elif n < 1:
               """ In swarm stage decrease probability that a Bee 
               will create a Mushroom. """
               #self.game.mushroom_field.grow_mushroom( gx, gy )
               self.game.mushroom_field.add_mushroom( gx, gy )

        self.rect.top += self.dy
        if self.rect.top > Game.SCREEN_H:
            self.kill()
            self.game.bees.remove(self)

    def collision(self):
        self.hp -= 1
        if self.hp == 0:
            self.kill()
            self.game.bees.remove(self)
            if self.game.swarmfn:
                self.game.swarm_score_up(self.rect.left, self.rect.top)
            else:
                self.game.score += Bee.POINTS
                self.game.popups.add(self.rect.left, self.rect.top, Bee.POINTS)
        else:
            self.dy = Bee.y_inc_fast

    def draw(self, buffer):
        buffer.blit( Bee.image, self.rect )


#####################################################################


class Earwig(pygame.sprite.Sprite):
    """The Earwig.

    any mushroom it touches as it cross the screen is poisoned. if
    the millipede touches a poisoned mushroom it causes the millipede
    to hurl towards the player 

    NEED TO MAKE SURE EARWIG DOES NOT SPAWN IN SAME ROW AS MILLIPEDE
    """
    
    POINTS = 1000
    HEIGHT = -1
    WIDTH = -1
    l_frames = None
    r_frames = None
    max_frames = 0
    X_LEFT_INC = -1
    X_RIGHT_INC = 1

    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)

        if Earwig.l_frames == None:
            Earwig.l_frames = []
            Earwig.r_frames = []
            Earwig.l_frames.append(load_image("sprites/earwig-l-0.png"))
            Earwig.l_frames.append(load_image("sprites/earwig-l-1.png"))
            Earwig.r_frames.append(load_image("sprites/earwig-r-0.png"))
            Earwig.r_frames.append(load_image("sprites/earwig-r-1.png"))
            Earwig.max_frames = len(Earwig.l_frames)
            Earwig.HEIGHT = Earwig.l_frames[0].get_height()
            Earwig.WIDTH = Earwig.l_frames[0].get_width()

        n = self.game.rng(0,100)
        if n < 50:
            start_x = 0 - Earwig.WIDTH
            self.image = Earwig.r_frames[0]
            self.dx = Earwig.X_RIGHT_INC 
        else:
            start_x = Game.SCREEN_W
            self.image = Earwig.l_frames[0]
            self.dx = Earwig.X_LEFT_INC 
        
        start_y = (random.randrange(0,Game.ARENA_H-Game.PLAYER_H) / \
        MushroomField.MUSHROOM_HEIGHT) * MushroomField.MUSHROOM_HEIGHT
        self.rect = pygame.Rect( start_x, start_y, \
        Earwig.WIDTH, Earwig.HEIGHT )
        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0

    def update(self):
        """ Earwig moves from right to left. """

        """ update animation """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Earwig.max_frames:
                self.cur_frame = 0
            if self.dx == Earwig.X_LEFT_INC:
                self.image = Earwig.l_frames[self.cur_frame]
            else:
                self.image = Earwig.r_frames[self.cur_frame]

        gx = self.rect.left / MushroomField.MUSHROOM_WIDTH
        gy = self.rect.top / MushroomField.MUSHROOM_HEIGHT

        self.game.mushroom_field.poison_mushroom( gx, gy )

        self.rect.left += self.dx
        if (self.rect.left < (0-Earwig.WIDTH)) or \
            (self.rect.left >= (Game.SCREEN_W+Earwig.WIDTH)):
                if DEBUG:
                    print "EARWIG REMVOED!"
                self.kill()
                self.game.earwigs.remove(self)

    def collision(self):
        self.kill()
        self.game.earwigs.remove(self)
        self.game.score += Earwig.POINTS
        self.game.popups.add(self.rect.left,self.rect.top,Earwig.POINTS)

    def draw(self, buffer):
        buffer.blit( Earwig.__image, self.rect )


#####################################################################

class Inchworm(pygame.sprite.Sprite):
    """The Inchworm.
    
    If shot causes all enemies to slowdown for a period of time.
    """
    
    POINTS = 100
    HEIGHT = -1
    WIDTH = -1
    frames = None
    max_frames = 0
    X_INC = -1

    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)

        if Inchworm.frames == None:
            Inchworm.frames = []
            Inchworm.frames.append(load_image("sprites/inchworm0.png"))
            Inchworm.frames.append(load_image("sprites/inchworm1.png"))
            Inchworm.max_frames = len(Inchworm.frames)
            Inchworm.HEIGHT = Inchworm.frames[0].get_height()
            Inchworm.WIDTH = Inchworm.frames[0].get_width()

        self.image = Inchworm.frames[0]
        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0
        
        y = random.randrange(0, MushroomField.FIELD_PLAYER_Y)
        start_y = y * MushroomField.MUSHROOM_HEIGHT

        n = self.game.rng(0,100)
        if n < 50:
            start_x = Game.SCREEN_W
            self.dx = Inchworm.X_INC
        else:
            start_x = 0 - Inchworm.WIDTH
            self.dx = -Inchworm.X_INC

        self.rect = pygame.Rect(start_x, start_y, \
        Inchworm.WIDTH, Inchworm.HEIGHT )



    def update(self):
        """ Inchworm moves from right to left. """

        """ update animation """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Inchworm.max_frames:
                self.cur_frame = 0
            self.image = Inchworm.frames[self.cur_frame]

        self.rect.left += self.dx
        if (self.rect.left < (0-Inchworm.WIDTH)) or \
            (self.rect.left>=Game.SCREEN_W):
            self.kill()
            self.game.inchworms.remove(self)


    def collision(self):
        self.kill()
        self.game.inchworms.remove(self)
        self.game.score += Inchworm.POINTS
        self.game.popups.add(self.rect.left,self.rect.top,Inchworm.POINTS)
        """ make game time slow down """
        self.game.slow_down_time = True
        self.game.slow_down_time_ttl = self.game.get_ticks()
        self.game.time_delay = self.game.get_ticks()

    def draw(self, buffer):
        buffer.blit( Inchworm.__image, self.rect )


#####################################################################


class Beetle(pygame.sprite.Sprite):
    """The Beetle.

    turns mushroom_field into flowers, and if hit causes mushroom field
    to shift down by one row 
    """

    POINTS = 300
    HEIGHT = -1
    WIDTH = -1
    frames = None
    max_frames = 0
    x_inc = 2 
    y_inc = -2


    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)
        if Beetle.frames == None:
            Beetle.frames = []
            Beetle.frames.append(load_image("sprites/beetle0.png"))
            Beetle.frames.append(load_image("sprites/beetle1.png"))
            Beetle.max_frames = len(Beetle.frames)
            Beetle.HEIGHT = Beetle.frames[0].get_height()
            Beetle.WIDTH = Beetle.frames[0].get_width()

        self.image = Beetle.frames[0]
        self.rect = self.image.get_rect()

        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0
        
        n = random.randrange(0,10)

        if (n % 2):
            start_x = -Beetle.WIDTH
        else:
            start_x = Game.SCREEN_W

        y = random.randrange(Game.ARENA_H-Game.PLAYER_H, \
        (Game.ARENA_H - Beetle.HEIGHT), Beetle.HEIGHT)

        self.rect = pygame.Rect( start_x, y, Beetle.WIDTH, Beetle.HEIGHT )

        self.dest_x = random.randrange(0,\
        MushroomField.FIELD_WIDTH-1) * MushroomField.MUSHROOM_WIDTH
        self.dest_y = random.randrange(MushroomField.FIELD_HEIGHT/2,\
        MushroomField.FIELD_PLAYER_Y) * MushroomField.MUSHROOM_HEIGHT

        if self.dest_x == 0:
            self.dest_x = Beetle.WIDTH
        if self.dest_x == (Game.SCREEN_W - Beetle.WIDTH):
            self.dest_x = Game.SCREEN_W - Beetle.WIDTH - Beetle.WIDTH

        if start_x == -Beetle.WIDTH:
            self.dx = Beetle.x_inc
            self.dest_drop_x = 0
        else:
            self.dx = -Beetle.x_inc
            self.dest_drop_x = Game.SCREEN_W - Beetle.WIDTH

        self.dy = Beetle.y_inc
        self.go_drop_x = True
        self.go_drop_y = False
        self.go_to_dest_x = False
        self.go_to_dest_y = False
        self.go_home = False
        self.ttm = self.game.get_ticks()

        self.pause = False
        self.pause_ttl = 0
        self.tick = 0
        
    
    def update(self):

        """ update animation """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Beetle.max_frames:
                self.cur_frame = 0
            self.image = Beetle.frames[self.cur_frame]

        """ don't move if paused """
        if self.pause:
            n = self.game.get_ticks() - self.pause_ttl
            if n > 175:
                self.pause = False
            else:
                return

        """ delay movement of beetle by 25 ticks """
        cur_time = self.game.get_ticks()
        n = cur_time - self.ttm
        if (n<25):
            return
        else:
            self.ttm = cur_time

        """ turn mushroom_field into flowers """
        gx = self.rect.left / MushroomField.MUSHROOM_WIDTH
        gy = self.rect.top / MushroomField.MUSHROOM_HEIGHT
        self.game.mushroom_field.mushroom_to_flower(gx,gy)

        if self.go_drop_x:
            self.rect.left += self.dx
            if self.rect.left == self.dest_drop_x:
                self.go_drop_x = False
                self.go_drop_y = True

        elif self.go_drop_y:
            self.rect.top += -self.dy
            if self.rect.top == (Game.ARENA_H - Beetle.HEIGHT):
                self.go_drop_y = False
                self.go_to_dest_x = True
            
        elif self.go_to_dest_x:
            self.rect.left += self.dx
            if self.rect.left == self.dest_x:
                self.go_to_dest_x = False
                self.go_to_dest_y = True
                
        elif self.go_to_dest_y:
            self.rect.top += self.dy
            if self.rect.top == self.dest_y:
                self.go_to_dest_y = False
                self.go_home = True
                self.dx = -self.dx

        elif self.go_home:
            self.rect.left += self.dx
            if (self.rect.left < -Beetle.WIDTH) \
                    or (self.rect.left > Game.SCREEN_W-1):
                self.kill()

        """ the Beetle pauses as it moves up or down """
        if self.go_drop_y or self.go_to_dest_y:
            self.tick += 1
            if (self.tick % Beetle.HEIGHT) == 0:
                self.tick = 0
                self.pause = True
                self.pause_ttl = self.game.get_ticks()

    def collision(self):
        self.kill()
        self.game.popups.add(self.rect.left,self.rect.top,Beetle.POINTS)
        self.game.score += Beetle.POINTS
        self.game.mushroom_field.row_down()

    
#####################################################################


class Dragonfly(pygame.sprite.Sprite):
    """The Dragonfly.

    similar to bee, moves from side to side as it comes down the
    screen 
    """
    
    POINTS = 200
    HEIGHT = -1
    WIDTH = -1
    frames = None
    max_frames = 0
    x_inc = 4
    y_inc = 2 

    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)

        if Dragonfly.frames == None:
            Dragonfly.frames = []
            Dragonfly.frames.append(load_image("sprites/dragonfly0.png"))
            Dragonfly.frames.append(load_image("sprites/dragonfly1.png"))
            Dragonfly.frames.append(load_image("sprites/dragonfly2.png"))
            Dragonfly.max_frames = len(Dragonfly.frames)
            Dragonfly.HEIGHT = Dragonfly.frames[0].get_height()
            Dragonfly.WIDTH = Dragonfly.frames[0].get_width()

        self.image = Dragonfly.frames[0]
        self.cur_frame = 0
        self.frame_delay = self.game.get_ticks()
        
        start_x = (random.randrange(0,Game.SCREEN_W-1) / \
        MushroomField.MUSHROOM_WIDTH) * MushroomField.MUSHROOM_WIDTH
        self.rect = pygame.Rect( start_x, 0, Dragonfly.WIDTH, \
        Dragonfly.HEIGHT )
        
        self.dx = Dragonfly.x_inc
        self.dy = Dragonfly.y_inc
        
        n = random.randrange(0,10)
        if n < 5:
            self.dx = -self.dx
    
    def update(self):

        """ update aninamtion """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Dragonfly.max_frames:
                self.cur_frame = 0
            self.image = Dragonfly.frames[self.cur_frame]


        n = random.randrange(0,30)

        """ grow some mushrooms """

        gx = self.rect.left / MushroomField.MUSHROOM_WIDTH
        gy = self.rect.top / MushroomField.MUSHROOM_HEIGHT
        
        if self.rect.top < (Game.SCREEN_H - Game.SCORE_H):
            if gy < MushroomField.FIELD_PLAYER_Y:
                if (n == 67) or (n == 89):
                    #self.game.mushroom_field.grow_mushroom( gx, gy )
                    self.game.mushroom_field.add_mushroom( gx, gy )
            else:
                if (n == 98) or (n == 5) or (n == 23) \
                    or (n == 58) or (n == 75):
                    #self.game.mushroom_field.grow_mushroom( gx, gy )
                    self.game.mushroom_field.add_mushroom( gx, gy )

        self.rect.top += self.dy
        self.rect.left += self.dx

        if self.rect.left > (Game.SCREEN_W-Dragonfly.WIDTH):
            self.rect.left = (Game.SCREEN_W-Dragonfly.WIDTH)
            self.dx = self.dx * -1
        
        if self.rect.left < 0:
            self.rect.left = 0
            self.dx = self.dx * -1
        
        if self.rect.top > (Game.SCREEN_H-Game.SCORE_H-Dragonfly.HEIGHT):
            self.kill()

    def collision(self):
        self.kill()
        if self.game.swarmfn:
            self.game.swarm_score_up(self.rect.left,self.rect.top)
        else:
            self.game.score += Dragonfly.POINTS
            self.game.popups.add(self.rect.left,self.rect.top,Dragonfly.POINTS)

    def draw(self, buffer):
        buffer.blit( Dragonfly.image, self.rect )


#####################################################################


class Mosquito(pygame.sprite.Sprite):
    """The Mosquito.
    
    Zig-zags across screen. If hit causes field to scroll up.
    Moves diagnoally and changes direction when it hits the side
    of the sreen and moves the mushroom field up one row if hit 
    """

    POINTS = 400
    HEIGHT = -1
    WIDTH = -1
    frames = None
    max_frames = 0

    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)
        if Mosquito.frames == None:
            Mosquito.frames = []
            Mosquito.frames.append(load_image("sprites/mosquito0.png"))
            Mosquito.frames.append(load_image("sprites/mosquito1.png"))
            Mosquito.frames.append(load_image("sprites/mosquito2.png"))
            Mosquito.max_frames = len(Mosquito.frames)
            Mosquito.HEIGHT = Mosquito.frames[0].get_height()
            Mosquito.WIDTH = Mosquito.frames[0].get_width()

        self.image = Mosquito.frames[0]
        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0
        
        start_x = (random.randrange(0,Game.SCREEN_W-1) / \
        MushroomField.MUSHROOM_WIDTH) * MushroomField.MUSHROOM_WIDTH
        self.rect = pygame.Rect( start_x, 0, Mosquito.WIDTH, Mosquito.HEIGHT )

        n = random.randrange(0,10)
        if n < 5:
            self.dx = -2
        else:
            self.dx = 2
        
        self.dy = 4 

    def update(self):

        """ update animation """
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 250:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.cur_frame == Mosquito.max_frames:
                self.cur_frame = 0
            self.image = Mosquito.frames[self.cur_frame]

        n = random.randrange(0,30)

        if n==5:
            self.dx = -self.dx

        self.rect.top += self.dy
        self.rect.left += self.dx

        if self.rect.left > (Game.SCREEN_W-Mosquito.WIDTH):
            self.rect.left = (Game.SCREEN_W-Mosquito.WIDTH)
            self.dx = self.dx * -1
        
        if self.rect.left < 0:
            self.rect.left = 0
            self.dx = self.dx * -1
        
        if self.rect.top > (Game.SCREEN_H-Game.SCORE_H-Mosquito.HEIGHT):
            self.kill()
    
    def draw(self, buffer):
        buffer.blit( Mosquito.image, self.rect )
    
    def collision(self):
        self.kill()
        if self.game.swarmfn:
            self.game.swarm_score_up(self.rect.left,self.rect.top)
        else:
            self.game.popups.add(self.rect.left,self.rect.top,Mosquito.POINTS)
            self.game.score += Mosquito.POINTS
            self.game.mushroom_field.row_up()


#####################################################################


class Spider(pygame.sprite.Sprite):
    """The Spider.

    Attacks player from the bottom of the game field.

    Mutliple spiders appear in player area and zig-zag about.
    Spiders eat mushroom_field causing bees to spawn if there are 5 or less
    mushroom_field in the player area.

    Spiders have a peculiar motion. They move in a zig-zag motion, then 
    they stop, move in a straigt up and down motion, and then they
    zig-zag and leave.

    Also they spider does go about 1/2 outside the top of the player
    area. this is where the notion of points for spider distance to 
    player is calculated.
    """
    
    HEIGHT = -1
    WIDTH = -1
    frames = None
    max_frames = 0
    TTL = 5000
    POINTS_FAR = 300
    POINTS_MID = 600
    POINTS_CLOSE = 900
    POINTS_POINT_BLANK = 1200

    def __init__(self, game):
        self.game = game
        pygame.sprite.Sprite.__init__(self)
        if Spider.frames == None:
            Spider.frames = []
            Spider.frames.append(load_image("sprites/spider0.png"))
            Spider.frames.append(load_image("sprites/spider1.png"))
            Spider.frames.append(load_image("sprites/spider2.png"))
            Spider.max_frames = len(Spider.frames)
            Spider.HEIGHT = Spider.frames[0].get_height()
            Spider.WIDTH = Spider.frames[0].get_width()

        self.image = Spider.frames[0]
        self.rect = self.image.get_rect()
        self.frame_delay = self.game.get_ticks()
        self.cur_frame = 0

        n = random.randrange(0,10)
        # 50-50 choice in inital start side
        if n < 5:
            self.rect.left = 0 - Spider.WIDTH
            self.dx = 2
        else:
            self.rect.left = Game.SCREEN_W + Spider.WIDTH
            self.dx = -2

        self.rect.top = random.randrange((Game.ARENA_H - Game.PLAYER_H), 
                (Game.ARENA_H - Spider.HEIGHT))

        self.enter_arena = True
        self.leave_arena = False
        self.left_right = False
        self.eat_mushroom = False
        self.ttl = self.game.get_ticks()


    def update(self):

        cur_time = self.game.get_ticks()

        """ update animation """

        dt = cur_time - self.frame_delay
        if dt > 250:
            self.frame_delay = cur_time
            self.cur_frame += 1
            if self.cur_frame == Spider.max_frames:
                self.cur_frame = 0
            self.image = Spider.frames[self.cur_frame]

        if not self.enter_arena and not self.leave_arena:
            if (cur_time - self.ttl) > Spider.TTL:
                self.leave_arena = True
                self.enter_arean = False
                self.left_right = False

        if self.enter_arena:
            self.rect.left += self.dx
            if self.dx < 0:
                if self.rect.left < (Game.SCREEN_W-Spider.WIDTH):
                    self.enter_arena = False
                    self.left_right = True
                    self.dy = 2
            else:
                if self.rect.left > -1:
                    self.enter_arena = False
                    self.left_right = True
                    self.dy = 2

        elif self.leave_arena:
            self.rect.left += self.dx
            self.rect.top += self.dy
            if self.rect.top > (Game.ARENA_H - Spider.HEIGHT):
                self.rect.top = (Game.ARENA_H - Spider.HEIGHT)
                self.dy = -self.dy
            if self.rect.top < (Game.ARENA_H - Game.PLAYER_H):
                self.rect.top = (Game.ARENA_H - Game.PLAYER_H)
                self.dy = -self.dy
            if (self.rect.left < (-Spider.WIDTH)) or \
                (self.rect.left > (Game.ARENA_W + Spider.WIDTH)):
                self.game.spiders.remove(self)

        elif self.left_right:
            # random left-right motion
            n = random.randrange(0, 100)
            # 2% chance to change direction
            if n < 2:
                self.dx = -self.dx
            # 5% chance to go into up-down motion
            elif n < 5:
                self.left_right = False


            self.rect.top += self.dy
            self.rect.left += self.dx
            if self.rect.left > (Game.ARENA_W - Spider.WIDTH):
                self.rect.left = (Game.ARENA_W - Spider.WIDTH)
                self.dx = self.dx * -1
            
            if self.rect.left < 0:
                self.rect.left = 0
                self.dx = self.dx * -1
            
            if self.rect.top > (Game.ARENA_H - Spider.HEIGHT):
                self.rect.top = (Game.ARENA_H - Spider.HEIGHT)
                self.dy = -self.dy
            if self.rect.top < (Game.ARENA_H - Game.PLAYER_H):
                self.rect.top = (Game.ARENA_H - Game.PLAYER_H)
                self.dy = -self.dy
        else:
            n = random.randrange(0, 100)
            self.rect.top += self.dy
            if self.rect.top > (Game.ARENA_H - Spider.HEIGHT):
                self.rect.top = (Game.ARENA_H - Spider.HEIGHT)
                self.dy = -self.dy
            if self.rect.top < (Game.ARENA_H - Game.PLAYER_H - Game.SCORE_H):
                self.rect.top = (Game.ARENA_H - Game.PLAYER_H - Game.SCORE_H)
                self.dy = -self.dy
            # 2% chance spider will go back to zig-zag motiion
            if n < 2:
                self.left_right = True

        
        n = random.randrange(0, 100)
        # 5% chance spider eats a mushroom
        if n < 5:
            # eat mushroom if one is below spider
            gx = self.rect.left / MushroomField.MUSHROOM_WIDTH
            gy = self.rect.top / MushroomField.MUSHROOM_HEIGHT
            self.game.mushroom_field.eat_mushroom(gx, gy)

    
    def collision(self):
        self.kill()
        (x,y) = self.game.player.rect.topleft

        y0 = self.rect.top / MushroomField.MUSHROOM_HEIGHT
        y1 = y / MushroomField.MUSHROOM_HEIGHT

        d = y1 - y0
        """need to adjust these values..."""
        if d == 1:
            points = Spider.POINTS_POINT_BLANK
        elif d <= 3:
            points = Spider.POINTS_CLOSE
        elif d <= 4:
            points = Spider.POINTS_MID
        else:
            points = Spider.POINTS_FAR

        self.game.score += points
        self.game.popups.add(self.rect.left, self.rect.top, points)
        if len(self.game.spiders) == 0:
            self.game.spider_snd.stop()


#####################################################################


class DDT(pygame.sprite.Sprite):
    """The DDT.
    
    A potent insecticide. Creates a cloud of killer gas.

    Destroys everything in the area when shot -- there can only be
    four DDTs at a time on the board. DDTs are regenerted at the
    start of each new level, a new row may or may not bring in a new
    DDT canister(s). 
    
    According to the Millipede strategy guide there can only be
    4 DDTs at a time on the screen.

    Also, at least in the NES version, DDTs don't seem to be able
    to scroll into the player area.
    """

    WIDTH = 24
    HEIGHT = 12

    active_frames = None
    active_max_frames = 0

    inactive_frames = None
    inactive_max_frames = 0

    image_inactive = None
    image_active = None
    TTL = 3000

    def __init__(self, game, x, y):
        self.game = game
        pygame.sprite.Sprite.__init__(self)
        if DDT.active_frames == None:
            DDT.active_frames = []
            DDT.active_frames.append(load_image("sprites/ddt-active-0.png"))
            DDT.active_frames.append(load_image("sprites/ddt-active-1.png"))
            DDT.active_frames.append(load_image("sprites/ddt-active-2.png"))
            DDT.active_frames.append(load_image("sprites/ddt-active-3.png"))
            DDT.active_max_frames = len(DDT.active_frames)

            DDT.inactive_frames = []
            DDT.inactive_frames.append(load_image("sprites/ddt0.png"))
            DDT.inactive_frames.append(load_image("sprites/ddt1.png"))
            DDT.inactive_frames.append(load_image("sprites/ddt2.png"))
            DDT.inactive_frames.append(load_image("sprites/ddt3.png"))
            DDT.inactive_max_frames = len(DDT.inactive_frames)


        self.start_time = self.game.get_ticks()
        self.active = False

        self.rect_inactive = pygame.Rect( x, y, DDT.WIDTH, DDT.HEIGHT )
        self.rect_active = pygame.Rect( (x-(DDT.WIDTH/2)), \
        (y-(DDT.HEIGHT/2)), (DDT.WIDTH*2), (DDT.HEIGHT*2) )
        self.image = DDT.image_inactive
        self.rect = self.rect_inactive

        self.image = DDT.inactive_frames[0]
        self.cur_frame = 0
        self.frame_delay = self.game.get_ticks()


    def update_position(self, dir):
        """update DDT rects if its position has shifted up or down."""
        if not self.active:
            (x, y) = self.rect_inactive.topleft
            if dir:
                # up
                y -= DDT.HEIGHT
            else:
                # down
                y += DDT.HEIGHT
            self.rect_inactive.topleft = (x, y)
            x2 = x - (DDT.WIDTH/2)
            y2 = y - (DDT.HEIGHT/2)
            self.rect_active.topleft = (x2, y2)
            # remove DDT if goes above board or into player area
            if (y<0) or (y>=MushroomField.FIELD_PLAYER_Y_POS):
                self.kill()


    def update(self):
        """update animation."""
        dt = self.game.get_ticks() - self.frame_delay
        if dt > 300:
            self.frame_delay = self.game.get_ticks()
            self.cur_frame += 1
            if self.active:
                if self.cur_frame == DDT.active_max_frames:
                    self.cur_frame = 0
                self.image = DDT.active_frames[self.cur_frame]
            else: 
                #if self.cur_frame == DDT.inactive_max_frames:
                #    self.cur_frame = 0
                self.cur_frame = random.randrange(0,4)
                self.image = DDT.inactive_frames[self.cur_frame]

        if self.active:
            n = self.game.get_ticks() - self.start_time
            if n > DDT.TTL:
                self.kill()


    def collision(self,rect):
        if not self.active:
            hit = self.rect_inactive.colliderect( rect )
            if hit:
                self.active = True
                self.start_time = self.game.get_ticks()
                # remove the DDT from the mushroom field
                (x, y) = self.rect_inactive.topleft
                fx = x / MushroomField.MUSHROOM_WIDTH
                fy = y / MushroomField.MUSHROOM_HEIGHT
                if DEBUG:
                    print "DDT pos: ", x, y
                # DDT is removed from MushroomField entries
                # but Sprite is kept around until the 
                # explosion runs out
                self.game.mushroom_field.remove_ddt(fx, fy)
                # set rect for pygame collision
                self.image = DDT.active_frames[0]
                self.rect = self.rect_active
                self.game.stop_ninth_millipede()
            return hit
        else:
            return False


#####################################################################


class PopUps:
    """PopUps. 
    
    A class to display floating scores.
    """

    TTL = 1000

    scores = [1,10,100,200,300,400,500,600,700,800,900,1000,1200]

    def __init__(self, game):
        self.game = game
        self.popups = []
        self.scores = {}
        for s in PopUps.scores:
            self.scores[s] = \
            self.game.font.render(("%d" % s), 1, (255,255,255))


    def add(self,x,y,score):
        """Add a score to the game board."""
        p = {}
        #p['text'] = self.game.font.render( ("%d" % score), 1, (255,255,255))
        p['score'] = score #self.scores[score]
        (w,h) = self.scores[score].get_size()
        tmp_x = x + w
        if x < 0:
            p['x_pos'] = 0
        elif tmp_x > Game.SCREEN_W:
            p['x_pos'] = Game.SCREEN_W - w
        else:
            p['x_pos'] = x

        p['y_pos'] = y
        p['ttl'] = self.game.get_ticks()
        self.popups.append(p)


    def clear(self):
        self.popups = []


    def draw(self,background):
        cur_time = self.game.get_ticks()
        for p in self.popups:
            t = cur_time - p['ttl']
            if t < PopUps.TTL:
                background.blit(self.scores[p['score']],\
                [p['x_pos'], p['y_pos']])
            else:
                self.popups.remove(p)

#####################################################################

class Particles:
    """Particles. 
    
    A class to particle effects.
    """

    TTL = 250
    img = None
    MAX = 5

    def __init__(self, game):
        self.game = game
        self.particles = []

        if Particles.img == None:
            Particles.img = pygame.Surface([2,2])
            Particles.img.fill([255,255,255])

    def add(self,x,y):
        """Add n particles to the game board."""
        n = random.randrange(1,Particles.MAX+1)
        for i in range(0,n): 
            p = {}
            w = 5
            tmp_x = x + w
            if x < 0:
                p['x'] = 0
            elif tmp_x > Game.SCREEN_W:
                p['x'] = Game.SCREEN_W - w
            else:
                p['x'] = x
            p['y'] = y
            p['ttl'] = self.game.get_ticks()
            m = random.randrange(0,10)
            if m == 0:
                p['dx'] = 0
            elif m > 5:
                p['dx'] = random.randrange(1,3)
            else:
                p['dx'] = -random.randrange(1,3)

            m = random.randrange(0,10)
            if m == 0:
                p['dy'] = 0
            elif m > 5:
                p['dy'] = random.randrange(1,3) 
            else:
                p['dy'] = -random.randrange(1,3)
            self.particles.append(p)


    def clear(self):
        self.particles = []


    def update(self):
        for p in self.particles:
            p['x'] += p['dx']
            p['y'] += p['dy']


    def draw(self,background):
        cur_time = self.game.get_ticks()
        for p in self.particles:
            t = cur_time - p['ttl']
            if t < Particles.TTL:
                background.blit(Particles.img, [p['x'], p['y']])
            else:
                self.particles.remove(p)



#####################################################################

def load_sound(name):
    class NoneSound:
        def play(self,n=1): pass
        def stop(self): pass
    if not pygame.mixer:
        return NoneSound()
    #return NoneSound()
    fullname = os.path.join('data',name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except pygame.error, message:
        print "Error: can not load sound: ", fullname
        raise SystemExit, message
    return sound

def load_image(name):
    fullname = os.path.join("data", name)
    img = pygame.image.load(fullname)
    return img.convert(img)

def mushroom_field_print():
    print "Mushroom Field:"
    for i in xrange(0, MushroomField.FIELD_HEIGHT):
        str = ""
        for j in xrange(0, MushroomField.FIELD_WIDTH):
            index = ( i * MushroomField.FIELD_WIDTH ) + j
            k = game.mushroom_field.m_idx[index]
            m = game.mushroom_field.m_arr[k]
            if m['hp'] > 0:
                str += "m"
            elif m['flower']:
                str += "F"
            elif m['ddt']:
                str += "D"
            else:
                str += "."
        print str

#####################################################################

if __name__=='__main__':
    game = Game()
    game.run()
