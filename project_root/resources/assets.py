import pygame
import os
from utils.utils import sc, load_img, Config

class Assets:
    fonts = {}
    sounds = {}
    images = {}
    companions = {}
    emojis = []
    current_pack = None

    @classmethod
    def init(cls):
        try:
            cls.fonts['f10'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(10))
            cls.fonts['f15'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(15))
            cls.fonts['f18'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(18))
            cls.fonts['f20'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(20))
            cls.fonts['f25'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(25))
            cls.fonts['f30'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(30))
            cls.fonts['f40'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(40))
            cls.fonts['f50'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(65))
            cls.fonts['f60'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(75))
            cls.fonts['f80'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(100))
            cls.fonts['f100'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(120))
            cls.fonts['f150'] = pygame.font.Font(os.path.join("fonts", "PlayfairDisplaySC-Italic.ttf"), sc(180))
            cls.fonts['text10'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(10))
            cls.fonts['text15'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(15))
            cls.fonts['text20'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(20))
            cls.fonts['text25'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(30))
            cls.fonts['text30'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(40))
            cls.fonts['text40'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(50))
            cls.fonts['text50'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(60))
            cls.fonts['text60'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(70))
            cls.fonts['text70'] = pygame.font.Font(os.path.join("fonts", "Kuhlenbach.ttf"), sc(80))
        except Exception:
            sys_font = "arial"
            cls.fonts['f10'] = pygame.font.SysFont(sys_font, sc(10))
            cls.fonts['f15'] = pygame.font.SysFont(sys_font, sc(15))
            cls.fonts['f20'] = pygame.font.SysFont(sys_font, sc(20))
            cls.fonts['f25'] = pygame.font.SysFont(sys_font, sc(25))
            cls.fonts['f30'] = pygame.font.SysFont(sys_font, sc(30))
            cls.fonts['f40'] = pygame.font.SysFont(sys_font, sc(40))
            cls.fonts['f50'] = pygame.font.SysFont(sys_font, sc(65))
            cls.fonts['f60'] = pygame.font.SysFont(sys_font, sc(75))
            cls.fonts['f80'] = pygame.font.SysFont(sys_font, sc(100))
            cls.fonts['f100'] = pygame.font.SysFont(sys_font, sc(120))
            cls.fonts['f150'] = pygame.font.SysFont(sys_font, sc(180))
            cls.fonts['text25'] = pygame.font.SysFont(sys_font, sc(30))
            cls.fonts['text30'] = pygame.font.SysFont(sys_font, sc(40))
            cls.fonts['text40'] = pygame.font.SysFont(sys_font, sc(50))
            cls.fonts['text50'] = pygame.font.SysFont(sys_font, sc(60))
            cls.fonts['text60'] = pygame.font.SysFont(sys_font, sc(70))
            cls.fonts['text70'] = pygame.font.SysFont(sys_font, sc(80))

        class DummySound:
            def play(self): pass
            def set_volume(self, v): pass

        for s in ["back", "enter", "scroll", "card", "chip"]:
            try:
                cls.sounds[s] = pygame.mixer.Sound(os.path.join("sound", "sounds", f"{s}.mp3"))
            except:
                cls.sounds[s] = DummySound()

        def _load_s(p, f):
            i = load_img(os.path.join(*p))
            return pygame.transform.smoothscale(i, (int(i.get_width()*f), int(i.get_height()*f)))

        cls.companions = {'girl_blond': {'red': {}, 'green': {}, 'blue': {}, 'gold': {}, 'white': {}}, 'girl_red': {}, 'girl_gold': {}}
        emotions = ['kiss', 'main', 'wink', 'arrogance', 'idea', 'think']

        for theme in ['red', 'green', 'blue', 'gold', 'white']:
            for emo in emotions:
                try:
                    cls.companions['girl_blond'][theme][emo] = _load_s(["textures", "companions", "girl_blond", theme, f"{emo}.png"], 0.7)
                except Exception:
                    pass

            if cls.companions['girl_blond'][theme]:
                first_img = list(cls.companions['girl_blond'][theme].values())[0]
                if 'main' not in cls.companions['girl_blond'][theme]:
                    cls.companions['girl_blond'][theme]['main'] = first_img
                for emo in emotions:
                    if emo not in cls.companions['girl_blond'][theme]:
                        cls.companions['girl_blond'][theme][emo] = cls.companions['girl_blond'][theme]['main']

        for emo in emotions:
            try:
                cls.companions['girl_red'][emo] = _load_s(["textures", "companions", "girl_red", f"{emo}.png"], 0.71)
            except Exception:
                pass

        for emo in emotions:
            try:
                cls.companions['girl_gold'][emo] = _load_s(["textures", "companions", "girl_gold", f"{emo}.png"], 0.71)
            except Exception:
                pass

        cls.images['bg_red1'] = load_img(os.path.join("textures", "backgrounds", "red", "bg_red1.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_red2'] = load_img(os.path.join("textures", "backgrounds", "red", "bg_red2.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_green1'] = load_img(os.path.join("textures", "backgrounds", "green", "bg_green1.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_green2'] = load_img(os.path.join("textures", "backgrounds", "green", "bg_green2.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_blue1'] = load_img(os.path.join("textures", "backgrounds", "blue", "bg_blue1.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_blue2'] = load_img(os.path.join("textures", "backgrounds", "blue", "bg_blue2.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_gold1'] = load_img(os.path.join("textures", "backgrounds", "gold", "bg_gold1.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_gold2'] = load_img(os.path.join("textures", "backgrounds", "gold", "bg_gold2.png"), (Config.WIDTH, Config.HEIGHT))

        cls.images['player_menu'] = load_img(os.path.join("textures", "different", "1player.png"))
        cls.images['players_img'] = load_img(os.path.join("textures", "different", "2players.png"))

        cls.images['blackjack_choice'] = load_img(os.path.join("textures", "different", "blackjack.png"), (int(sc(500)), int(sc(350))))
        cls.images['fool_choice'] = load_img(os.path.join("textures", "different", "fool.png"), (int(sc(430)), int(sc(350))))
        cls.images['poker_choice'] = load_img(os.path.join("textures", "different", "poker.png"), (int(sc(430)), int(sc(350))))

        cls.images['gold_blackjack_choice'] = load_img(os.path.join("textures", "different", "gold_blackjack.png"), (int(sc(500)), int(sc(350))))
        cls.images['gold_fool_choice'] = load_img(os.path.join("textures", "different", "gold_fool.png"), (int(sc(430)), int(sc(350))))
        cls.images['gold_poker_choice'] = load_img(os.path.join("textures", "different", "gold_poker.png"), (int(sc(430)), int(sc(350))))

        cls.images['raccoonka'] = load_img(os.path.join("textures", "authors", "raccoonka.png"))
        cls.images['muteTexture'] = load_img(os.path.join("textures", "sound", "playmusic.png"))
        cls.images['unmuteTexture'] = load_img(os.path.join("textures", "sound", "mutemusic.png"))
        cls.images['logo'] = load_img(os.path.join("textures", "different", "logo.png"))
        cls.images['gold_preview'] = load_img(os.path.join("textures", "different", "gold.png"))
        cls.images['lei'] = load_img(os.path.join("textures", "different", "lei.png"))

        cls.images['logo_blond'] = load_img(os.path.join("textures", "companions", "logo_girls", "blond.png"))
        cls.images['logo_red'] = load_img(os.path.join("textures", "companions", "logo_girls", "red.png"))
        cls.images['logo_gold'] = load_img(os.path.join("textures", "companions", "logo_girls", "gold.png"))

        card_w, card_h = sc(190), sc(250)
        cls.images['shirt_red'] = load_img(os.path.join("textures", "cards", "shirts", "shirtred.png"), (card_w, card_h))
        cls.images['shirt_green'] = load_img(os.path.join("textures", "cards", "shirts", "shirtgreen.png"), (card_w, card_h))
        cls.images['shirt_blue'] = load_img(os.path.join("textures", "cards", "shirts", "shirtblue.png"), (card_w, card_h))
        cls.images['shirt_gold'] = load_img(os.path.join("textures", "cards", "shirts", "shirtgold.png"), (card_w, card_h))

        c1 = load_img(os.path.join("textures", "cursors", "cursor1.png"))
        c2 = load_img(os.path.join("textures", "cursors", "cursor2.png"))
        c3 = load_img(os.path.join("textures", "cursors", "cursor3.png"))

        try:
            c_gold = load_img(os.path.join("textures", "cursors", "gold_cursor.png"))
        except Exception:
            c_gold = c1

        if c1.get_width() > 1:
            cls.images['c1'] = pygame.transform.smoothscale(c1, (int(c1.get_width() * 0.028), int(c1.get_height() * 0.028)))
            cls.images['c2'] = pygame.transform.smoothscale(c2, (int(c2.get_width() * 0.028), int(c2.get_height() * 0.028)))
            cls.images['c3'] = pygame.transform.smoothscale(c3, (int(c3.get_width() * 0.028), int(c3.get_height() * 0.028)))
            cls.images['c_gold'] = pygame.transform.smoothscale(c_gold, (int(c_gold.get_width() * 0.028), int(c_gold.get_height() * 0.028)))
        else:
            cls.images['c1'] = c1; cls.images['c2'] = c2; cls.images['c3'] = c3; cls.images['c_gold'] = c_gold

        cls.companions['girl_cyberpunk'] = {}
        for emo in emotions + ['happy']:
            try:
                cls.companions['girl_cyberpunk'][emo] = _load_s(["textures", "companions", "girl_cyberpunk", f"{emo}.png"], 0.71)
            except Exception:
                pass

        cls.images['bg_cyberpunk1'] = load_img(os.path.join("textures", "backgrounds", "cyberpunk", "bg_cyberpunk1.png"), (Config.WIDTH, Config.HEIGHT))
        cls.images['bg_cyberpunk2'] = load_img(os.path.join("textures", "backgrounds", "cyberpunk", "bg_cyberpunk2.png"), (Config.WIDTH, Config.HEIGHT))

        cls.images['cyberpunk_1player'] = load_img(os.path.join("textures", "different", "cyberpunk_1player.png"))
        cls.images['cyberpunk_2players'] = load_img(os.path.join("textures", "different", "cyberpunk_2players.png"))

        cls.images['cyberpunk_blackjack_choice'] = load_img(os.path.join("textures", "different", "cyberpunk_blackjack.png"), (int(sc(500)), int(sc(350))))
        cls.images['cyberpunk_fool_choice'] = load_img(os.path.join("textures", "different", "cyberpunk_fool.png"), (int(sc(430)), int(sc(350))))
        cls.images['cyberpunk_poker_choice'] = load_img(os.path.join("textures", "different", "cyberpunk_poker.png"), (int(sc(430)), int(sc(350))))

        cls.images['cyberpunk_preview'] = load_img(os.path.join("textures", "different", "cyberpunk.png"))

        try:
            cls.images['logo_cyberpunk'] = load_img(os.path.join("textures", "companions", "logo_girls", "cyberpunk.png"))
        except Exception:
            cls.images['logo_cyberpunk'] = pygame.Surface((int(sc(200)), int(sc(200))), pygame.SRCALPHA)

        try:
            raw_cyber_shirt = load_img(os.path.join("textures", "cards", "shirts", "cybershirt.png"))
            cyber_bbox = raw_cyber_shirt.get_bounding_rect()
            cropped_cyber_shirt = raw_cyber_shirt.subsurface(cyber_bbox)
            cls.images['shirt_cyberpunk'] = pygame.transform.smoothscale(cropped_cyber_shirt, (sc(160), sc(220)))
        except Exception:
            cls.images['shirt_cyberpunk'] = cls.images.get('shirt_red')

        try:
            c_cyberpunk = load_img(os.path.join("textures", "cursors", "cyber_cursor.png"))
            if c_cyberpunk.get_width() > 1:
                cls.images['c_cyberpunk'] = pygame.transform.smoothscale(c_cyberpunk, (int(c_cyberpunk.get_width() * 0.028), int(c_cyberpunk.get_height() * 0.028)))
            else:
                cls.images['c_cyberpunk'] = c_cyberpunk
        except Exception:
            cls.images['c_cyberpunk'] = cls.images.get('c1')

        for t_chip in ["default", "cyberpunk"]:
            try:
                raw = pygame.image.load(os.path.join("textures", "chips", t_chip, "all_chips.png")).convert_alpha()
                cls.images[f'all_chips_{t_chip}'] = pygame.transform.smoothscale(raw, (int(raw.get_width() * Config.SCALE * 0.5), int(raw.get_height() * Config.SCALE * 0.5)))
            except Exception:
                cls.images[f'all_chips_{t_chip}'] = pygame.Surface((sc(200), sc(200)), pygame.SRCALPHA)

        cls.images['all_chips'] = cls.images.get('all_chips_default')

        try:
            cls.images['logo_Standard'] = load_img(os.path.join("textures", "emotions", "emoji", "logo_emojis.png"), (int(sc(300)), int(sc(300))))
        except Exception:
            cls.images['logo_Standard'] = pygame.Surface((int(sc(300)), int(sc(300))), pygame.SRCALPHA)

        for p_name in ["Skull", "Cyberpunk", "Raccoon"]:
            try:
                if p_name == "Skull":
                    folder = "skull"
                    filename = "logo_skull.png"
                else:
                    folder = p_name.lower()
                    filename = f"logo_{folder}.png"

                cls.images[f'logo_{p_name}'] = load_img(os.path.join("textures", "emotions", folder, filename), (int(sc(300)), int(sc(300))))
            except Exception:
                cls.images[f'logo_{p_name}'] = pygame.Surface((int(sc(300)), int(sc(300))), pygame.SRCALPHA)

        try:
            cls.images['logo_emoji'] = load_img(os.path.join("textures", "emotions", "logo_emoji.png"), (int(sc(80)), int(sc(80))))
        except Exception:
            cls.images['logo_emoji'] = pygame.Surface((int(sc(80)), int(sc(80))), pygame.SRCALPHA)

        cls.load_emojis("Standard")

    @classmethod
    def load_emojis(cls, pack_name):
        if cls.current_pack == pack_name:
            return

        cls.current_pack = pack_name
        cls.emojis.clear()

        if pack_name == "Standard":
            folder = "emoji"
        elif pack_name == "Skull":
            folder = "skull"
        else:
            folder = pack_name.lower()

        for i in range(1, 9):
            try:
                img = load_img(os.path.join("textures", "emotions", folder, f"{i}.png"), (int(sc(140)), int(sc(140))))
                cls.emojis.append(img)
            except Exception:
                cls.emojis.append(pygame.Surface((int(sc(140)), int(sc(140))), pygame.SRCALPHA))