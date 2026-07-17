import pygame
import ctypes
import sys

from core.game_engine import GameEngine

def main():
    try:
        # noinspection PyUnresolvedReferences
        ctypes.windll.user32.SetProcessDPIAware()
    except AttributeError:
        pass

    pygame.init()
    pygame.mixer.init() 

    game = GameEngine()
    game.run()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()