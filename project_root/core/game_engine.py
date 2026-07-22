import pygame
import sys
import random
import os

from ui.animations import play_splash_screen
from utils.utils import Config, sc
from resources import load_settings, save_settings, load_progress, save_progress, set_language, Assets
from scenes.menu_scene import MenuScene
from scenes.blackjack_scene import BlackjackScene
from scenes.fool_scene import FoolScene
from scenes.poker_scene import PokerScene
from scenes.shop_scene import ShopScene
from utils.utils import Config, sc, resource_path

class GameEngine:
    def __init__(self):
        Config.init()

        self.MUSIC_END_EVENT = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)

        self.clock = pygame.time.Clock()
        info = pygame.display.Info()
        self.WIDTH, self.HEIGHT = info.current_w, info.current_h

        self.current_settings = load_settings()
        self.current_progress = load_progress()
        self.current_vsync = self.current_settings.get("vsync", False)
        set_language(self.current_settings.get("language", "en"))

        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
        if self.current_vsync:
            try:
                self.WINDOW = pygame.display.set_mode((self.WIDTH, self.HEIGHT), flags | pygame.SCALED, vsync=1)
            except Exception:
                self.WINDOW = pygame.display.set_mode((self.WIDTH, self.HEIGHT), flags)
        else:
            self.WINDOW = pygame.display.set_mode((self.WIDTH, self.HEIGHT), flags)

        pygame.display.set_caption("Velaris")
        pygame.mouse.set_visible(False)
        pygame.display.flip()

        Assets.init()
        self.current_emoji_pack = self.current_settings.get("emoji_pack", "Standard")
        Assets.load_emojis(self.current_emoji_pack)

        self.current_skip_splash = self.current_settings.get("skip_splash", False)
        if not self.current_skip_splash:
            logo_img = Assets.images.get('logo', pygame.Surface((int(sc(300)), int(sc(300)))))
            if not play_splash_screen(self.WINDOW, self.clock, self.current_vsync, logo_img):
                pygame.quit()
                sys.exit()

        self.current_emotion = "main"
        self.current_theme = self.current_settings.get("current_theme", "red")
        self.current_bg_index = self.current_settings.get("current_bg_index", 1)
        self.current_companion = self.current_settings.get("companion", "blond")
        self.current_music_mode = "menu"
        self.current_track_index = 0
        self.volume = self.current_settings.get("volume", 0.4)
        self.muting_music = self.current_settings.get("muting_music", False)
        self.sfx_volume = self.current_settings.get("sfx_volume", 0.2)
        self.muting_sfx = self.current_settings.get("muting_sfx", False)
        self.brightness = self.current_settings.get("brightness", 1.0)
        self.nickname_text = self.current_settings.get("nickname", "Player")

        self.server = None
        self.client = None
        self.my_id = 0
        self.target_players = 2

        self.mx, self.my = 0, 0
        self.running = True

        self.MUSIC_PLAYLISTS = {
            "red": {"menu": ["red_menu1.mp3", "red_menu2.mp3", "red_menu3.mp3"], "game": ["red_game1.mp3", "red_game2.mp3"]},
            "green": {"menu": ["green_menu1.mp3", "green_menu2.mp3", "green_menu3.mp3"], "game": ["green_game1.mp3", "green_game2.mp3"]},
            "blue": {"menu": ["blue_menu1.mp3", "blue_menu2.mp3", "blue_menu3.mp3"], "game": ["blue_game1.mp3", "blue_game2.mp3"]},
            "gold": {"menu": ["gold_menu1.mp3", "gold_menu2.mp3", "gold_menu3.mp3", "gold_menu4.mp3"], "game": ["gold_game1.mp3", "gold_game2.mp3"]},
            "cyberpunk": {"menu": ["cyberpunk_menu1.mp3", "cyberpunk_menu2.mp3", "cyberpunk_menu3.mp3"], "game": ["cyberpunk_game1.mp3", "cyberpunk_game2.mp3"]}
        }

        self.update_sfx_volume()
        self.set_theme_and_bg(self.current_theme, self.current_bg_index)

        self.play_track()

        self.scenes = {
            "menu": MenuScene(self),
            "blackjack": BlackjackScene(self),
            "fool": FoolScene(self),
            "poker": PokerScene(self),
            "shop": ShopScene(self)
        }
        self.current_scene = None
        self.switch_scene("menu")

    def switch_scene(self, scene_name, **kwargs):
        if scene_name in self.scenes:
            self.current_scene = self.scenes[scene_name]
            self.current_scene.on_enter(**kwargs)

    def pick_random_emotion(self):
        if self.current_companion == "blond":
            self.current_emotion = random.choice(["main", "arrogance", "idea"])
        elif self.current_companion == "gold":
            self.current_emotion = random.choice(["main", "arrogance", "kiss", "think", "wink"])
        elif self.current_companion == "cyberpunk":
            self.current_emotion = random.choice(["main", "kiss", "think", "wink", "happy"])
        else:
            self.current_emotion = random.choice(["main", "arrogance", "kiss", "wink"])

    def unlock_title(self, title_id):
        if "titles_unlocked" not in self.current_progress:
            self.current_progress["titles_unlocked"] = ["Новичок"]
        if title_id not in self.current_progress["titles_unlocked"]:
            self.current_progress["titles_unlocked"].append(title_id)
            save_progress(self.current_progress)

    def update_sfx_volume(self):
        v = 0 if self.muting_sfx else self.sfx_volume
        for snd in Assets.sounds.values():
            snd.set_volume(float(v))

    def play_track(self):
        try:
            track = self.MUSIC_PLAYLISTS[self.current_theme][self.current_music_mode][self.current_track_index]
            raw_path = os.path.join("sound", "music", "game" if self.current_music_mode == "game" else "menu", track)

            path = resource_path(raw_path)

            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(float(self.volume))
            pygame.mixer.music.play(0)
            if self.muting_music: pygame.mixer.music.pause()
        except Exception: pass

    def switch_music(self, new_theme, new_mode):
        if new_theme != self.current_theme or new_mode != self.current_music_mode:
            self.current_theme = new_theme
            self.current_music_mode = new_mode
            self.current_track_index = 0
            self.play_track()

    def set_theme_and_bg(self, new_theme, bg_idx):
        Assets.sounds['enter'].play()
        self.switch_music(new_theme, self.current_music_mode)
        self.current_theme = new_theme
        self.current_bg_index = bg_idx
        self.pick_random_emotion()

        Config.chip_theme = "cyberpunk" if self.current_theme == "cyberpunk" else "default"
        Assets.images['all_chips'] = Assets.images.get(f'all_chips_{Config.chip_theme}', Assets.images.get('all_chips_default'))

        if self.current_theme == "green":
            self.current_cursor = Assets.images['c2']
            self.cursor_offset = (self.current_cursor.get_width() // 2, self.current_cursor.get_height() // 2)
            self.current_bg = Assets.images.get(f'bg_green{self.current_bg_index}')
            self.thumb_color = (78, 123, 50)
        elif self.current_theme == "blue":
            self.current_cursor = Assets.images['c3']
            self.cursor_offset = (self.current_cursor.get_width() // 2, self.current_cursor.get_height() // 2)
            self.current_bg = Assets.images.get(f'bg_blue{self.current_bg_index}')
            self.thumb_color = (44, 72, 160)
        elif self.current_theme == "gold":
            self.current_cursor = Assets.images.get('c_gold', Assets.images['c1'])
            self.cursor_offset = (self.current_cursor.get_width() // 5, self.current_cursor.get_height() // 5)
            self.current_bg = Assets.images.get(f'bg_gold{self.current_bg_index}')
            self.thumb_color = (255, 215, 0)
        elif self.current_theme == "cyberpunk":
            self.current_cursor = Assets.images.get('c_cyberpunk', Assets.images.get('c1'))
            self.cursor_offset = (self.current_cursor.get_width() // 5, self.current_cursor.get_height() // 5)
            self.current_bg = Assets.images.get(f'bg_cyberpunk{self.current_bg_index}')
            self.thumb_color = (0, 255, 255)
        else:
            self.current_cursor = Assets.images['c1']
            self.cursor_offset = (self.current_cursor.get_width() // 5, self.current_cursor.get_height() // 5)
            self.current_bg = Assets.images.get(f'bg_red{self.current_bg_index}')
            self.thumb_color = (135, 23, 5)

        self.current_settings["current_theme"] = self.current_theme
        self.current_settings["current_bg_index"] = self.current_bg_index
        save_settings(self.current_settings)

    def run(self):
        while self.running:
            self.mx, self.my = pygame.mouse.get_pos()
            events = pygame.event.get()

            for event in events:
                if event.type == self.MUSIC_END_EVENT:
                    self.current_track_index = (self.current_track_index + 1) % len(self.MUSIC_PLAYLISTS[self.current_theme][self.current_music_mode])
                    self.play_track()

                if event.type == pygame.QUIT:
                    self.running = False
                    if self.server: self.server.stop()
                    if self.client: self.client.disconnect()

            if self.current_scene:
                self.current_scene.handle_events(events)
                self.current_scene.update()
                self.current_scene.draw(self.WINDOW)

            if self.brightness < 1.0:
                alpha = int(220 * (1.0 - self.brightness))
                if alpha > 0:
                    dark_overlay = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
                    dark_overlay.fill((0, 0, 0, alpha))
                    self.WINDOW.blit(dark_overlay, (0, 0))

            if sys.platform not in ("android", "ios"):
                self.WINDOW.blit(self.current_cursor, (int(self.mx - self.cursor_offset[0]), int(self.my - self.cursor_offset[1])))

            pygame.display.flip()

            if self.current_vsync:
                self.clock.tick(float(60))
            else:
                self.clock.tick(float(120))