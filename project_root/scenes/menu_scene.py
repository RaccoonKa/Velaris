import pygame
import math
import random
import os
from scenes.base_scene import BaseScene
from utils.utils import sc, draw_alpha_rect, draw_text_centered, draw_gradient_circle, draw_text
from resources import save_settings, save_progress, t, set_language, get_language, Assets
from network.network import GameServer, GameClient

class MenuScene(BaseScene):
    def __init__(self, engine):
        super().__init__(engine)
        self._init_ui()
        self.hovered_button = None
        self.showPlay = False
        self.showGameChoice = False
        self.game_choice = "blackjack"
        self.showSettings = False
        self.showAuthors = False
        self.showGameTypeMenu = False
        self.showHostJoinMenu = False
        self.showHostPlayersMenu = False
        self.showIPInput = False
        self.showBonusInput = False
        self.settings_tab = "menu"
        self.visual_sub_tab = "bg"
        self.dropdown_open = None
        self.network_mode = ""
        self.ip_text = ""
        self.bonus_text = ""
        self.bonus_message = ""
        self.bonus_message_timer = 0
        self.nickname_input_active = False

        self.music_slider_dragging = False
        self.sfx_slider_dragging = False
        self.brightness_slider_dragging = False

        self.ALL_TITLES = ["Новичок", "Главный спонсор", "Шулер", "Крупье на пенсии", "Коллектор", "Крути-вези!", "Разработчик"]
        self.TITLE_CONDITIONS = {
            "Новичок": "Выдаётся сразу каждому.",
            "Главный спонсор": "Проиграть все деньги.",
            "Шулер": "Получить BlackJack! 21 раз.",
            "Крупье на пенсии": "Поставить 100000 и выиграть.",
            "Коллектор": "Выиграть 100 раз.",
            "Крути-вези!": "Выиграть в Колесе Фортуны.",
            "Разработчик": "Стань разработчиком!)"
        }
        self.update_titles()

        self.wheel_box = pygame.Rect(int(sc(20)), int(self.engine.HEIGHT - sc(460)), int(sc(450)), int(sc(280)))
        self.reel_rect = pygame.Rect(int(sc(40)), int(self.engine.HEIGHT - sc(380)), int(sc(210)), int(sc(180)))
        self.spin_btn_rect = pygame.Rect(int(sc(280)), int(self.engine.HEIGHT - sc(330)), int(sc(150)), int(sc(80)))

        self.reel_y = 0.0
        self.reel_y_start = 0.0
        self.wheel_state = "idle"
        self.wheel_target_idx = 0
        self.reel_y_target = 0.0
        self.wheel_spin_start = 0
        self.wheel_pool = []
        self._build_wheel_pool()

        self.particles = []

        try:
            self.wheel_sound = pygame.mixer.Sound(os.path.join("sound", "sounds", "wheel.mp3"))
        except:
            self.wheel_sound = None

    def _build_wheel_pool(self):
        self.wheel_pool = []
        for _ in range(4):
            self.wheel_pool.append({"type": "money", "val": 1000, "name": "1000 $"})
        for _ in range(2):
            self.wheel_pool.append({"type": "money", "val": 2500, "name": "2500 $"})
        self.wheel_pool.append({"type": "money", "val": 5000, "name": "5000 $"})
        for _ in range(2):
            self.wheel_pool.append({"type": "money", "val": 10000, "name": "10000 $"})
        self.wheel_pool.append({"type": "money", "val": 100000, "name": "100000 $"})

        unlocked = self.engine.current_progress.get("titles_unlocked", ["Новичок"])
        if "Крути-вези!" not in unlocked:
            self.wheel_pool.append({"type": "title", "val": "Крути-вези!", "name": "Крути-вези!"})

        random.shuffle(self.wheel_pool)

    def spawn_win_particles(self):
        px = self.wheel_box.x + self.wheel_box.width // 2
        py = self.wheel_box.y + self.wheel_box.height // 2
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 12)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            color = random.choice([(255, 215, 0), (255, 255, 255), (255, 250, 200), (255, 100, 100)])
            size = random.uniform(sc(4), sc(10))
            lifetime = random.randint(40, 80)
            self.particles.append([px, py, dx, dy, lifetime, color, size, lifetime])

    def localize_title(self, title_name):
        if title_name in ["Крути-вези!", "I got lucky!"]:
            return "Крути-вези!" if get_language() == "ru" else "I got lucky!"
        return t(title_name)

    def update_titles(self):
        self.VISIBLE_TITLES = list(self.ALL_TITLES)
        for unlocked_title in self.engine.current_progress.get("titles_unlocked", []):
            if unlocked_title not in self.VISIBLE_TITLES:
                self.VISIBLE_TITLES.append(unlocked_title)
        if "Разработчик" in self.engine.current_progress.get("titles_unlocked", []):
            self.VISIBLE_TITLES.append("Разработчик")
        try:
            self.viewing_title_idx = self.VISIBLE_TITLES.index(self.engine.current_progress.get("current_title", "Новичок"))
        except ValueError:
            self.viewing_title_idx = 0

    def get_title_color(self, title):
        if title in ["Разработчик", "Developer", "Millionaire", "Миллионер", "Крути-вези!", "I got lucky!"]:
            t_ms = pygame.time.get_ticks()
            glow = int((math.sin(t_ms / 150.0) + 1) / 2 * 100)
            return (255, 255 - glow, 0)
        return (255, 215, 0)

    def _init_ui(self):
        self.cx, self.cy = int(self.engine.WIDTH // 2), int(self.engine.HEIGHT // 2)

        self.play_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.play_btn.center = (self.cx, int(self.cy - sc(130)))
        self.shop_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.shop_btn.center = (self.cx, int(self.cy - sc(40)))
        self.set_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.set_btn.center = (self.cx, int(self.cy + sc(50)))
        self.auth_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.auth_btn.center = (self.cx, int(self.cy + sc(140)))
        self.exit_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.exit_btn.center = (self.cx, int(self.cy + sc(230)))

        self.back_btn = pygame.Rect(0, 0, int(sc(320)), int(sc(80))); self.back_btn.bottomright = (int(self.engine.WIDTH - sc(50)), int(self.engine.HEIGHT - sc(50)))

        self.bj_btn = pygame.Rect(0, 0, int(sc(400)), int(sc(400)))
        self.bj_btn.center = (int(self.cx - sc(250)), self.cy)
        self.fool_btn = pygame.Rect(0, 0, int(sc(400)), int(sc(400)))
        self.fool_btn.center = (int(self.cx + sc(250)), self.cy)

        self.player_menu = pygame.transform.smoothscale(Assets.images['player_menu'], (int(sc(290)), int(sc(250))))
        self.players_img = pygame.transform.smoothscale(Assets.images['players_img'], (int(sc(290)), int(sc(250))))

        mode_btn_w = max(self.player_menu.get_width(), self.players_img.get_width())
        mode_btn_h = max(self.player_menu.get_height(), self.players_img.get_height())
        self.mode1_btn = pygame.Rect(0, 0, int(mode_btn_w), int(mode_btn_h)); self.mode1_btn.center = (int(self.cx - sc(250)), self.cy)
        self.mode2_btn = pygame.Rect(0, 0, int(mode_btn_w), int(mode_btn_h)); self.mode2_btn.center = (int(self.cx + sc(250)), self.cy)

        self.local_btn_rect = pygame.Rect(0, 0, int(sc(750)), int(sc(120))); self.local_btn_rect.center = (self.cx, int(self.cy - sc(80)))
        self.online_btn_rect = pygame.Rect(0, 0, int(sc(750)), int(sc(120))); self.online_btn_rect.center = (self.cx, int(self.cy + sc(80)))
        self.host_btn_rect = pygame.Rect(0, 0, int(sc(750)), int(sc(120))); self.host_btn_rect.center = (self.cx, int(self.cy - sc(80)))
        self.join_btn_rect = pygame.Rect(0, 0, int(sc(750)), int(sc(120))); self.join_btn_rect.center = (self.cx, int(self.cy + sc(80)))

        self.p2_btn = pygame.Rect(0, 0, int(sc(410)), int(sc(110))); self.p2_btn.center = (self.cx, int(self.cy - sc(130)))
        self.p3_btn = pygame.Rect(0, 0, int(sc(410)), int(sc(110))); self.p3_btn.center = (self.cx, self.cy)
        self.p4_btn = pygame.Rect(0, 0, int(sc(410)), int(sc(110))); self.p4_btn.center = (self.cx, int(self.cy + sc(130)))

        self.ip_input_rect = pygame.Rect(0, 0, int(sc(500)), int(sc(80))); self.ip_input_rect.center = (self.cx, int(self.cy - sc(20)))
        self.connect_btn_rect = pygame.Rect(0, 0, int(sc(350)), int(sc(65))); self.connect_btn_rect.center = (self.cx, int(self.cy + sc(80)))

        self.gen_tab_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.gen_tab_btn.center = (self.cx, int(self.cy - sc(135)))
        self.theme_tab_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.theme_tab_btn.center = (self.cx, int(self.cy - sc(45)))
        self.tut_tab_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.tut_tab_btn.center = (self.cx, int(self.cy + sc(45)))
        self.bonus_tab_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.bonus_tab_btn.center = (self.cx, int(self.cy + sc(135)))

        self.bonus_input_rect = pygame.Rect(0, 0, int(sc(400)), int(sc(80))); self.bonus_input_rect.center = (self.cx, self.cy)
        self.bonus_back_btn = pygame.Rect(0, 0, int(sc(200)), int(sc(60))); self.bonus_back_btn.center = (self.cx, int(self.cy + sc(150)))

        self.slider_bg = pygame.Rect(0, 0, int(sc(500)), int(sc(30))); self.slider_bg.center = (int(self.cx + sc(50)), int(self.cy - sc(180)))
        self.slider_thumb = pygame.Rect(0, 0, int(sc(40)), int(sc(40)))
        self.btn_mute = pygame.Rect(0, 0, Assets.images['muteTexture'].get_width(), Assets.images['muteTexture'].get_height()); self.btn_mute.midleft = (int(self.slider_bg.right + sc(60)), self.slider_bg.centery)

        self.sfx_slider_bg = pygame.Rect(0, 0, int(sc(500)), int(sc(30))); self.sfx_slider_bg.center = (int(self.cx + sc(50)), int(self.cy - sc(100)))
        self.sfx_slider_thumb = pygame.Rect(0, 0, int(sc(40)), int(sc(40)))
        self.btn_sfx_mute = pygame.Rect(0, 0, Assets.images['muteTexture'].get_width(), Assets.images['muteTexture'].get_height()); self.btn_sfx_mute.midleft = (int(self.sfx_slider_bg.right + sc(60)), self.sfx_slider_bg.centery)

        self.brightness_slider_bg = pygame.Rect(0, 0, int(sc(500)), int(sc(30))); self.brightness_slider_bg.center = (int(self.cx + sc(50)), int(self.cy - sc(20)))
        self.brightness_slider_thumb = pygame.Rect(0, 0, int(sc(40)), int(sc(40)))

        self.btn_lang_en = pygame.Rect(self.slider_bg.left, int(self.cy + sc(50)), int(sc(160)), int(sc(55)))
        self.btn_lang_ru = pygame.Rect(int(self.slider_bg.left + sc(180)), int(self.cy + sc(50)), int(sc(160)), int(sc(55)))
        self.btn_vsync = pygame.Rect(self.slider_bg.left, int(self.cy + sc(120)), int(sc(160)), int(sc(45)))
        self.btn_skip_splash = pygame.Rect(self.slider_bg.left, int(self.cy + sc(190)), int(sc(160)), int(sc(45)))

        self.nickname_input_rect = pygame.Rect(self.slider_bg.left, int(self.cy + sc(260)), int(sc(280)), int(sc(45)))
        self.btn_save_nick = pygame.Rect(int(self.nickname_input_rect.right + sc(20)), int(self.cy + sc(260)), int(sc(170)), int(sc(45)))

        self.title_left_btn = pygame.Rect(self.slider_bg.left, int(self.cy + sc(330)), int(sc(40)), int(sc(45)))
        self.title_display_rect = pygame.Rect(int(self.slider_bg.left + sc(50)), int(self.cy + sc(330)), int(sc(320)), int(sc(45)))
        self.title_right_btn = pygame.Rect(int(self.slider_bg.left + sc(380)), int(self.cy + sc(330)), int(sc(40)), int(sc(45)))
        self.btn_equip_title = pygame.Rect(int(self.title_right_btn.right + sc(20)), int(self.cy + sc(330)), int(sc(140)), int(sc(45)))

        self.title_hint_rect = pygame.Rect(0, 0, int(sc(600)), int(sc(30)))
        self.title_hint_rect.centerx = self.title_display_rect.centerx
        self.title_hint_rect.y = int(self.cy + sc(385))

        self.v_tab_bg = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.v_tab_bg.center = (int(self.cx - sc(370)), int(self.engine.HEIGHT * 0.25))
        self.v_tab_comp = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.v_tab_comp.center = (self.cx, int(self.engine.HEIGHT * 0.25))
        self.v_tab_emoji = pygame.Rect(0, 0, int(sc(350)), int(sc(70))); self.v_tab_emoji.center = (int(self.cx + sc(370)), int(self.engine.HEIGHT * 0.25))

        self.btn_red = pygame.Rect(0, 0, int(sc(250)), int(sc(70))); self.btn_red.center = (int(self.cx - sc(300)), int(self.cy))
        self.btn_green = pygame.Rect(0, 0, int(sc(250)), int(sc(70))); self.btn_green.center = (self.cx, int(self.cy))
        self.btn_blue = pygame.Rect(0, 0, int(sc(250)), int(sc(70))); self.btn_blue.center = (int(self.cx + sc(300)), int(self.cy))

        self.btn_red_bg1 = pygame.Rect(self.btn_red.x, int(self.btn_red.bottom + sc(5)), self.btn_red.width, int(sc(60)))
        self.btn_red_bg2 = pygame.Rect(self.btn_red.x, int(self.btn_red_bg1.bottom + sc(5)), self.btn_red.width, int(sc(60)))
        self.btn_green_bg1 = pygame.Rect(self.btn_green.x, int(self.btn_green.bottom + sc(5)), self.btn_green.width, int(sc(60)))
        self.btn_green_bg2 = pygame.Rect(self.btn_green.x, int(self.btn_green_bg1.bottom + sc(5)), self.btn_green.width, int(sc(60)))
        self.btn_blue_bg1 = pygame.Rect(self.btn_blue.x, int(self.btn_blue.bottom + sc(5)), self.btn_blue.width, int(sc(60)))
        self.btn_blue_bg2 = pygame.Rect(self.btn_blue.x, int(self.btn_blue_bg1.bottom + sc(5)), self.btn_blue.width, int(sc(60)))

        self.btn_comp_blond = pygame.Rect(0, 0, int(sc(200)), int(sc(200))); self.btn_comp_blond.center = (int(self.cx - sc(200)), int(self.cy + sc(50)))
        self.btn_comp_red = pygame.Rect(0, 0, int(sc(200)), int(sc(200))); self.btn_comp_red.center = (int(self.cx + sc(200)), int(self.cy + sc(50)))

    def get_emoji_pack_rects(self):
        unlocked_packs = self.engine.current_progress.get("emojis_unlocked", ["Standard"])
        rects = []
        pack_w, pack_h = int(sc(250)), int(sc(250))
        spacing = int(sc(320))
        total_w = len(unlocked_packs) * spacing - (spacing - pack_w)
        start_x = self.cx - total_w // 2
        for i, pack_name in enumerate(unlocked_packs):
            ex = start_x + pack_w // 2 + i * spacing
            ey = int(self.cy + sc(50))
            rect = pygame.Rect(0, 0, pack_w, pack_h)
            rect.center = (ex, ey)
            rects.append((pack_name, rect))
        return rects

    def on_enter(self, **kwargs):
        self.engine.switch_music(self.engine.current_theme, "menu")
        if self.engine.muting_music:
            pygame.mixer.music.pause()
        self.update_titles()
        self._build_wheel_pool()

        if not hasattr(self.engine, 'brightness'):
            self.engine.brightness = self.engine.current_settings.get("brightness", 1.0)

        self.slider_thumb.center = (int(self.slider_bg.x + self.slider_bg.width * self.engine.volume), self.slider_bg.centery)
        self.sfx_slider_thumb.center = (int(self.sfx_slider_bg.x + self.sfx_slider_bg.width * self.engine.sfx_volume), self.sfx_slider_bg.centery)
        self.brightness_slider_thumb.center = (int(self.brightness_slider_bg.x + self.brightness_slider_bg.width * self.engine.brightness), self.brightness_slider_bg.centery)

    def draw_aligned_label(self, text, right_x, center_y, font_obj, window):
        txt_surf = font_obj.render(text, True, (255, 255, 255))
        w, h = txt_surf.get_size()
        draw_text(window, text, font_obj, (255, 255, 255), (0, 0, 0), (int(right_x - w), int(center_y - h // 2)), int(sc(2)))

    def _draw_overlay_message(self, message, window):
        window.blit(self.engine.current_bg, (0, 0))
        draw_alpha_rect(window, (0, 0, 0, 160), (0, 0, self.engine.WIDTH, self.engine.HEIGHT), (0, 0, 0), 0, 0)
        draw_text_centered(window, message, Assets.fonts['f100'], (255, 255, 255), (0, 0, 0), (0, 0, self.engine.WIDTH, self.engine.HEIGHT), int(sc(4)))
        pygame.display.flip()

    def on_wheel_stop(self):
        win_item = self.wheel_pool[self.wheel_target_idx]
        if win_item["type"] == "money":
            self.engine.current_progress["money"] = self.engine.current_progress.get("money", 10000) + win_item["val"]
            save_progress(self.engine.current_progress)
            if win_item["val"] >= 10000:
                self.spawn_win_particles()
                Assets.sounds['enter'].play()
        elif win_item["type"] == "title":
            self.engine.unlock_title(win_item["val"])
            self.spawn_win_particles()
            Assets.sounds['enter'].play()
            self._build_wheel_pool()
            self.update_titles()

    def update(self):
        mx, my = self.engine.mx, self.engine.my
        current_hover = None

        for p in self.particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
            if p[4] <= 0:
                self.particles.remove(p)

        if self.wheel_state == "spinning":
            elapsed = pygame.time.get_ticks() - self.wheel_spin_start
            if elapsed >= 4000:
                self.reel_y = self.reel_y_target
                self.wheel_state = "idle"
                self.on_wheel_stop()
            else:
                u = elapsed / 4000.0
                ease_out = 1.0 - (1.0 - u) ** 4
                self.reel_y = self.reel_y_start + (self.reel_y_target - self.reel_y_start) * ease_out

        if not (self.showPlay or self.showSettings or self.showAuthors or self.showGameTypeMenu or self.showHostJoinMenu or self.showHostPlayersMenu or self.showIPInput or getattr(self, "showGameChoice", False)):
            for b in [self.play_btn, self.shop_btn, self.set_btn, self.auth_btn, self.exit_btn]:
                if b.collidepoint((mx, my)): current_hover = b
            if self.wheel_state == "idle" and self.spin_btn_rect.collidepoint((mx, my)):
                current_hover = self.spin_btn_rect
        elif getattr(self, "showGameChoice", False):
            for b in [self.bj_btn, self.fool_btn, self.back_btn]:
                if b.collidepoint((mx, my)): current_hover = b
        elif self.showPlay:
            for b in [self.mode1_btn, self.mode2_btn, self.back_btn]:
                if b.collidepoint((mx, my)): current_hover = b
        elif self.showGameTypeMenu:
            for b in [self.local_btn_rect, self.online_btn_rect, self.back_btn]:
                if b.collidepoint((mx, my)): current_hover = b
        elif self.showHostJoinMenu:
            for b in [self.host_btn_rect, self.join_btn_rect, self.back_btn]:
                if b.collidepoint((mx, my)): current_hover = b
        elif self.showHostPlayersMenu:
            for b in [self.p2_btn, self.p3_btn, self.p4_btn, self.back_btn]:
                if b.collidepoint((mx, my)): current_hover = b
        elif self.showIPInput:
            for b in [self.connect_btn_rect, self.back_btn]:
                if b.collidepoint((mx, my)): current_hover = b
        elif self.showSettings:
            if getattr(self, "showBonusInput", False):
                if self.bonus_back_btn.collidepoint((mx, my)): current_hover = self.bonus_back_btn
            else:
                if self.settings_tab == "menu":
                    for b in [self.gen_tab_btn, self.theme_tab_btn, self.tut_tab_btn, self.bonus_tab_btn, self.back_btn]:
                        if b.collidepoint((mx, my)): current_hover = b
                elif self.settings_tab == "general":
                    t_id = self.VISIBLE_TITLES[self.viewing_title_idx]
                    unlocked = t_id in self.engine.current_progress.get("titles_unlocked", ["Новичок"])
                    btns = [self.btn_mute, self.btn_sfx_mute, self.btn_lang_en, self.btn_lang_ru, self.btn_vsync, self.btn_skip_splash, self.btn_save_nick, self.title_left_btn, self.title_right_btn, self.back_btn]
                    if unlocked and t_id != self.engine.current_progress.get("current_title", "Новичок"):
                        btns.append(self.btn_equip_title)
                    for b in btns:
                        if b.collidepoint((mx, my)): current_hover = b
                    if self.slider_bg.collidepoint((mx, my)) or self.slider_thumb.collidepoint((mx, my)): current_hover = self.slider_bg
                    if self.sfx_slider_bg.collidepoint((mx, my)) or self.sfx_slider_thumb.collidepoint((mx, my)): current_hover = self.sfx_slider_bg
                    if self.brightness_slider_bg.collidepoint((mx, my)) or self.brightness_slider_thumb.collidepoint((mx, my)): current_hover = self.brightness_slider_bg
                elif self.settings_tab == "themes":
                    for b in [self.v_tab_bg, self.v_tab_comp, self.v_tab_emoji, self.back_btn]:
                        if b.collidepoint((mx, my)): current_hover = b

                    if self.visual_sub_tab == "bg":
                        for b in [self.btn_red, self.btn_green, self.btn_blue]:
                            if b.collidepoint((mx, my)): current_hover = b
                        if self.dropdown_open == "red":
                            for b in [self.btn_red_bg1, self.btn_red_bg2]:
                                if b.collidepoint((mx, my)): current_hover = b
                        elif self.dropdown_open == "green":
                            for b in [self.btn_green_bg1, self.btn_green_bg2]:
                                if b.collidepoint((mx, my)): current_hover = b
                        elif self.dropdown_open == "blue":
                            for b in [self.btn_blue_bg1, self.btn_blue_bg2]:
                                if b.collidepoint((mx, my)): current_hover = b
                    elif self.visual_sub_tab == "comp":
                        for b in [self.btn_comp_blond, self.btn_comp_red]:
                            if b.collidepoint((mx, my)): current_hover = b
                    elif self.visual_sub_tab == "emoji":
                        for pack_name, b in self.get_emoji_pack_rects():
                            if b.collidepoint((mx, my)): current_hover = b

                elif self.settings_tab == "tutorial":
                    if self.back_btn.collidepoint((mx, my)): current_hover = self.back_btn
        elif self.showAuthors:
            if self.back_btn.collidepoint((mx, my)): current_hover = self.back_btn

        if current_hover != self.hovered_button:
            if current_hover is not None and not self.music_slider_dragging and not self.sfx_slider_dragging and not getattr(self, 'brightness_slider_dragging', False):
                Assets.sounds['scroll'].play()
            self.hovered_button = current_hover

    def _check_bonus_code(self):
        code = self.bonus_text
        redeemed = self.engine.current_progress.get("redeemed_codes", [])
        if code in redeemed:
            self.bonus_message = t("Invalid code!")
        elif code == "X7A9BQ2M":
            self.engine.unlock_title("Разработчик")
            redeemed.append(code)
            self.engine.current_progress["redeemed_codes"] = redeemed
            save_progress(self.engine.current_progress)
            self.bonus_message = t("Code activated!")
            self.update_titles()
        elif code == "P9D3K6W1":
            self.engine.current_progress["money"] = self.engine.current_progress.get("money", 10000) + 10000
            redeemed.append(code)
            self.engine.current_progress["redeemed_codes"] = redeemed
            save_progress(self.engine.current_progress)
            self.bonus_message = t("Code activated!")
        else:
            self.bonus_message = t("Invalid code!")
        self.bonus_message_timer = pygame.time.get_ticks() + 2000
        self.bonus_text = ""

    def handle_events(self, events):
        mx, my = self.engine.mx, self.engine.my
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.showIPInput:
                    if event.key == pygame.K_BACKSPACE:
                        self.ip_text = self.ip_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        ip_target = self.ip_text.strip() if self.ip_text.strip() else '127.0.0.1'
                        Assets.sounds['enter'].play()
                        self._draw_overlay_message(t("Connecting to server..."), self.engine.WINDOW)
                        self.engine.client = GameClient(host=ip_target)
                        self.engine.client.connect()
                        if self.engine.client.connected:
                            self.engine.switch_scene(self.game_choice, mode="multiplayer_client")
                        else:
                            self._draw_overlay_message(t("Connection error"), self.engine.WINDOW)
                            pygame.time.wait(3000)
                    else:
                        if len(self.ip_text) < 15 and event.unicode in "0123456789.":
                            self.ip_text += event.unicode
                elif self.showSettings and getattr(self, "showBonusInput", False):
                    if event.key == pygame.K_ESCAPE:
                        Assets.sounds['back'].play(); self.showBonusInput = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.bonus_text = self.bonus_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        Assets.sounds['enter'].play(); self._check_bonus_code()
                    else:
                        if len(self.bonus_text) < 8 and event.unicode.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
                            self.bonus_text += event.unicode.upper()
                elif self.showSettings and self.settings_tab == "general" and self.nickname_input_active:
                    if event.key == pygame.K_BACKSPACE:
                        self.engine.nickname_text = self.engine.nickname_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        Assets.sounds['enter'].play()
                        self.nickname_input_active = False
                        self.engine.current_settings["nickname"] = self.engine.nickname_text
                        save_settings(self.engine.current_settings)
                    else:
                        if len(self.engine.nickname_text) < 15 and event.unicode.isprintable():
                            self.engine.nickname_text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                in_submenu = (self.showPlay or self.showSettings or self.showAuthors or
                              self.showGameTypeMenu or self.showHostJoinMenu or
                              self.showHostPlayersMenu or self.showIPInput or getattr(self, "showGameChoice", False))

                if in_submenu and self.back_btn.collidepoint(mx, my) and not getattr(self, "showBonusInput", False):
                    Assets.sounds['back'].play()
                    self.engine.pick_random_emotion()
                    if getattr(self, "showGameChoice", False) or self.showAuthors:
                        self.showGameChoice = self.showAuthors = False
                    elif self.showPlay:
                        self.showPlay = False
                        self.showGameChoice = True
                    elif self.showGameTypeMenu:
                        self.showGameTypeMenu = False
                        self.showPlay = True
                    elif self.showHostJoinMenu:
                        self.showHostJoinMenu = False
                        self.showGameTypeMenu = True
                    elif self.showHostPlayersMenu:
                        self.showHostPlayersMenu = False
                        self.showHostJoinMenu = True
                    elif self.showIPInput:
                        self.showIPInput = False
                        self.showHostJoinMenu = True
                    elif self.showSettings:
                        if self.settings_tab == "menu":
                            self.showSettings = False
                        else:
                            self.settings_tab = "menu"

                elif not in_submenu:
                    if self.exit_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.running = False
                    elif self.play_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.showGameChoice = True
                    elif self.shop_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.engine.switch_scene("shop")
                    elif self.set_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.showSettings = True
                    elif self.auth_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.showAuthors = True
                    elif self.wheel_state == "idle" and self.spin_btn_rect.collidepoint(mx, my):
                        if self.wheel_sound:
                            v = 0.0 if self.engine.muting_sfx else self.engine.sfx_volume
                            self.wheel_sound.set_volume(v)
                            self.wheel_sound.play()
                        self._build_wheel_pool()
                        self.wheel_target_idx = random.randrange(len(self.wheel_pool))
                        self.wheel_spin_start = pygame.time.get_ticks()
                        self.wheel_state = "spinning"
                        self.reel_y_start = self.reel_y

                        item_h = sc(60)
                        total_h = len(self.wheel_pool) * item_h

                        align_y = self.wheel_target_idx * item_h - (self.reel_rect.height - item_h) // 2
                        current_mod = self.reel_y_start % total_h
                        diff = (align_y - current_mod) % total_h
                        self.reel_y_target = self.reel_y_start + (6 * total_h) + diff

                elif getattr(self, "showGameChoice", False):
                    if self.bj_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play()
                        self.game_choice = "blackjack"
                        self.showGameChoice = False
                        self.showPlay = True
                    elif self.fool_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play()
                        self.game_choice = "fool"
                        self.showGameChoice = False
                        self.showPlay = True

                elif self.showPlay:
                    if self.mode1_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play()
                        self.engine.pick_random_emotion()
                        self.engine.switch_scene(self.game_choice, mode="singleplayer")
                    elif self.mode2_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.showPlay = False; self.showGameTypeMenu = True

                elif self.showGameTypeMenu:
                    if self.local_btn_rect.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.network_mode = "local"; self.showGameTypeMenu = False; self.showHostJoinMenu = True
                    elif self.online_btn_rect.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.network_mode = "online"; self.showGameTypeMenu = False; self.showHostJoinMenu = True

                elif self.showHostJoinMenu:
                    if self.host_btn_rect.collidepoint(mx, my):
                        Assets.sounds['enter'].play(); self.engine.pick_random_emotion(); self.showHostJoinMenu = False; self.showHostPlayersMenu = True
                    elif self.join_btn_rect.collidepoint(mx, my):
                        Assets.sounds['enter'].play()
                        self.engine.pick_random_emotion()
                        self.showHostJoinMenu = False
                        self.showIPInput = True
                        self.ip_text = ""

                elif self.showHostPlayersMenu:
                    count = 0
                    if self.p2_btn.collidepoint(mx, my): count = 2
                    elif self.p3_btn.collidepoint(mx, my): count = 3
                    elif self.p4_btn.collidepoint(mx, my): count = 4

                    if count > 0:
                        Assets.sounds['enter'].play()
                        self.engine.target_players = count
                        self.showHostPlayersMenu = False
                        self.engine.server = GameServer(target_players=count)
                        self.engine.server.start()
                        if self.engine.server.running:
                            self.engine.switch_scene(self.game_choice, mode="multiplayer_host")

                elif self.showIPInput:
                    if self.connect_btn_rect.collidepoint(mx, my):
                        ip_target = self.ip_text.strip() if self.ip_text.strip() else '127.0.0.1'
                        Assets.sounds['enter'].play()
                        self._draw_overlay_message(t("Connecting to server..."), self.engine.WINDOW)
                        self.engine.client = GameClient(host=ip_target)
                        self.engine.client.connect()
                        if self.engine.client.connected:
                            self.engine.switch_scene(self.game_choice, mode="multiplayer_client")
                        else:
                            self._draw_overlay_message(t("Connection error"), self.engine.WINDOW)
                            pygame.time.wait(3000)

                elif self.showSettings:
                    if getattr(self, "showBonusInput", False):
                        if self.bonus_back_btn.collidepoint(mx, my):
                            Assets.sounds['back'].play(); self.showBonusInput = False
                    else:
                        if self.settings_tab == "menu":
                            if self.gen_tab_btn.collidepoint(mx, my): Assets.sounds['enter'].play(); self.settings_tab = "general"
                            elif self.theme_tab_btn.collidepoint(mx, my): Assets.sounds['enter'].play(); self.settings_tab = "themes"
                            elif self.tut_tab_btn.collidepoint(mx, my): Assets.sounds['enter'].play(); self.settings_tab = "tutorial"
                            elif self.bonus_tab_btn.collidepoint(mx, my): Assets.sounds['enter'].play(); self.showBonusInput = True; self.bonus_text = ""; self.bonus_message_timer = 0
                        elif self.settings_tab == "general":
                            self.nickname_input_active = self.nickname_input_rect.collidepoint(mx, my)

                            if self.btn_save_nick.collidepoint(mx, my):
                                Assets.sounds['enter'].play(); self.nickname_input_active = False
                                self.engine.current_settings["nickname"] = self.engine.nickname_text
                                save_settings(self.engine.current_settings)

                            elif self.title_left_btn.collidepoint(mx, my):
                                Assets.sounds['enter'].play(); self.viewing_title_idx = (self.viewing_title_idx - 1) % len(self.VISIBLE_TITLES)
                            elif self.title_right_btn.collidepoint(mx, my):
                                Assets.sounds['enter'].play(); self.viewing_title_idx = (self.viewing_title_idx + 1) % len(self.VISIBLE_TITLES)
                            elif self.btn_equip_title.collidepoint(mx, my):
                                t_id = self.VISIBLE_TITLES[self.viewing_title_idx]
                                if t_id in self.engine.current_progress.get("titles_unlocked", ["Новичок"]):
                                    Assets.sounds['enter'].play()
                                    self.engine.current_progress["current_title"] = t_id
                                    save_progress(self.engine.current_progress)

                            elif self.slider_bg.collidepoint(mx, my) or self.slider_thumb.collidepoint(mx, my):
                                self.music_slider_dragging = True
                                slider_x = max(0, min(mx - self.slider_bg.x, self.slider_bg.width))
                                self.engine.volume = slider_x / self.slider_bg.width
                                self.slider_thumb.centerx = int(self.slider_bg.x + slider_x)
                                pygame.mixer.music.set_volume(float(self.engine.volume))
                            elif self.btn_mute.collidepoint(mx, my):
                                Assets.sounds['enter'].play()
                                self.engine.muting_music = not self.engine.muting_music
                                pygame.mixer.music.pause() if self.engine.muting_music else pygame.mixer.music.unpause()
                                self.engine.current_settings["muting_music"] = self.engine.muting_music
                                save_settings(self.engine.current_settings)
                            elif self.sfx_slider_bg.collidepoint(mx, my) or self.sfx_slider_thumb.collidepoint((mx, my)):
                                self.sfx_slider_dragging = True
                                slider_x = max(0, min(mx - self.sfx_slider_bg.x, self.sfx_slider_bg.width))
                                self.engine.sfx_volume = slider_x / self.sfx_slider_bg.width
                                self.sfx_slider_thumb.centerx = int(self.sfx_slider_bg.x + slider_x)
                                self.engine.update_sfx_volume()
                            elif self.btn_sfx_mute.collidepoint(mx, my):
                                Assets.sounds['enter'].play()
                                self.engine.muting_sfx = not self.engine.muting_sfx
                                self.engine.update_sfx_volume()
                                self.engine.current_settings["muting_sfx"] = self.engine.muting_sfx
                                save_settings(self.engine.current_settings)
                            elif getattr(self, 'brightness_slider_bg', None) and (self.brightness_slider_bg.collidepoint(mx, my) or self.brightness_slider_thumb.collidepoint(mx, my)):
                                self.brightness_slider_dragging = True
                                slider_x = max(0, min(mx - self.brightness_slider_bg.x, self.brightness_slider_bg.width))
                                self.engine.brightness = slider_x / self.brightness_slider_bg.width
                                self.brightness_slider_thumb.centerx = int(self.brightness_slider_bg.x + slider_x)
                            elif self.btn_lang_en.collidepoint(mx, my):
                                Assets.sounds['enter'].play()
                                set_language("en"); self.engine.current_settings["language"] = "en"; save_settings(self.engine.current_settings)
                            elif self.btn_lang_ru.collidepoint(mx, my):
                                Assets.sounds['enter'].play()
                                set_language("ru"); self.engine.current_settings["language"] = "ru"; save_settings(self.engine.current_settings)
                            elif self.btn_vsync.collidepoint(mx, my):
                                Assets.sounds['enter'].play()
                                self.engine.current_vsync = not self.engine.current_vsync
                                self.engine.current_settings["vsync"] = self.engine.current_vsync
                                save_settings(self.engine.current_settings)
                            elif self.btn_skip_splash.collidepoint(mx, my):
                                Assets.sounds['enter'].play()
                                self.engine.current_skip_splash = not self.engine.current_skip_splash
                                self.engine.current_settings["skip_splash"] = self.engine.current_skip_splash
                                save_settings(self.engine.current_settings)
                        elif self.settings_tab == "themes":
                            if self.v_tab_bg.collidepoint(mx, my): Assets.sounds['enter'].play(); self.visual_sub_tab = "bg"; self.dropdown_open = None
                            elif self.v_tab_comp.collidepoint(mx, my): Assets.sounds['enter'].play(); self.visual_sub_tab = "comp"; self.dropdown_open = None
                            elif self.v_tab_emoji.collidepoint(mx, my): Assets.sounds['enter'].play(); self.visual_sub_tab = "emoji"; self.dropdown_open = None

                            if self.visual_sub_tab == "bg":
                                clicked_dropdown = False
                                if self.dropdown_open == "red":
                                    if self.btn_red_bg1.collidepoint(mx, my): self.engine.set_theme_and_bg("red", 1); self.dropdown_open = None; clicked_dropdown = True
                                    elif self.btn_red_bg2.collidepoint(mx, my): self.engine.set_theme_and_bg("red", 2); self.dropdown_open = None; clicked_dropdown = True
                                elif self.dropdown_open == "green":
                                    if self.btn_green_bg1.collidepoint(mx, my): self.engine.set_theme_and_bg("green", 1); self.dropdown_open = None; clicked_dropdown = True
                                    elif self.btn_green_bg2.collidepoint(mx, my): self.engine.set_theme_and_bg("green", 2); self.dropdown_open = None; clicked_dropdown = True
                                elif self.dropdown_open == "blue":
                                    if self.btn_blue_bg1.collidepoint(mx, my): self.engine.set_theme_and_bg("blue", 1); self.dropdown_open = None; clicked_dropdown = True
                                    elif self.btn_blue_bg2.collidepoint(mx, my): self.engine.set_theme_and_bg("blue", 2); self.dropdown_open = None; clicked_dropdown = True

                                if not clicked_dropdown:
                                    if self.btn_red.collidepoint(mx, my): Assets.sounds['enter'].play(); self.dropdown_open = "red" if self.dropdown_open != "red" else None
                                    elif self.btn_green.collidepoint(mx, my): Assets.sounds['enter'].play(); self.dropdown_open = "green" if self.dropdown_open != "green" else None
                                    elif self.btn_blue.collidepoint(mx, my): Assets.sounds['enter'].play(); self.dropdown_open = "blue" if self.dropdown_open != "blue" else None
                                    else: self.dropdown_open = None

                            elif self.visual_sub_tab == "comp":
                                if self.btn_comp_blond.collidepoint(mx, my):
                                    Assets.sounds['enter'].play(); self.engine.current_companion = "blond"; self.engine.pick_random_emotion()
                                    self.engine.current_settings["companion"] = self.engine.current_companion; save_settings(self.engine.current_settings)
                                elif self.btn_comp_red.collidepoint(mx, my):
                                    Assets.sounds['enter'].play(); self.engine.current_companion = "red"; self.engine.pick_random_emotion()
                                    self.engine.current_settings["companion"] = self.engine.current_companion; save_settings(self.engine.current_settings)

                            elif self.visual_sub_tab == "emoji":
                                for pack_name, rect in self.get_emoji_pack_rects():
                                    if rect.collidepoint(mx, my):
                                        Assets.sounds['enter'].play()
                                        self.engine.current_emoji_pack = pack_name
                                        Assets.load_emojis(pack_name)
                                        self.engine.current_settings["emoji_pack"] = pack_name
                                        save_settings(self.engine.current_settings)
                                        break

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.music_slider_dragging:
                    self.engine.current_settings["volume"] = self.engine.volume; save_settings(self.engine.current_settings)
                if self.sfx_slider_dragging:
                    self.engine.current_settings["sfx_volume"] = self.engine.sfx_volume; save_settings(self.engine.current_settings)
                if getattr(self, 'brightness_slider_dragging', False):
                    self.engine.current_settings["brightness"] = self.engine.brightness; save_settings(self.engine.current_settings)
                self.music_slider_dragging = self.sfx_slider_dragging = False
                if hasattr(self, 'brightness_slider_dragging'): self.brightness_slider_dragging = False

            if event.type == pygame.MOUSEMOTION:
                if self.music_slider_dragging:
                    slider_x = max(0, min(mx - self.slider_bg.x, self.slider_bg.width))
                    self.engine.volume = slider_x / self.slider_bg.width
                    self.slider_thumb.centerx = int(self.slider_bg.x + slider_x)
                    pygame.mixer.music.set_volume(float(self.engine.volume))
                if self.sfx_slider_dragging:
                    slider_x = max(0, min(mx - self.sfx_slider_bg.x, self.sfx_slider_bg.width))
                    self.engine.sfx_volume = slider_x / self.sfx_slider_bg.width
                    self.sfx_slider_thumb.centerx = int(self.sfx_slider_bg.x + slider_x)
                    self.engine.update_sfx_volume()
                if getattr(self, 'brightness_slider_dragging', False):
                    slider_x = max(0, min(mx - self.brightness_slider_bg.x, self.brightness_slider_bg.width))
                    self.engine.brightness = slider_x / self.brightness_slider_bg.width
                    self.brightness_slider_thumb.centerx = int(self.brightness_slider_bg.x + slider_x)

    def draw(self, window):
        mx, my = self.engine.mx, self.engine.my
        window.blit(self.engine.current_bg, (0, 0))

        if getattr(self, "showGameChoice", False):
            draw_text_centered(window, t("Select Game"), Assets.fonts['f150'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))

            for btn, img_key, label in [(self.bj_btn, 'blackjack_choice', t("BlackJack")), (self.fool_btn, 'fool_choice', t("Durak"))]:
                h = btn.collidepoint(mx, my)
                bg_rect = btn.inflate(int(sc(20)), int(sc(20)))
                draw_alpha_rect(window, (0, 0, 0, 160), bg_rect, "gradient" if h else (245, 245, 245), int(sc(3)), int(sc(15)))

                img = Assets.images[img_key]
                img_rect = img.get_rect(center=btn.center)
                window.blit(img, img_rect.topleft)
                draw_text_centered(window, label, Assets.fonts['f60'], (255,255,255), (0,0,0), (btn.x, int(btn.bottom + sc(40)), btn.width, 0), int(sc(2)))

            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showPlay:
            emo = self.engine.current_emotion
            theme = self.engine.current_theme
            if self.engine.current_companion == "blond" : active_devushka = Assets.companions['girl_blond'][theme].get(emo, Assets.companions['girl_blond'][theme].get('main'))
            else: active_devushka = Assets.companions['girl_red'].get(emo, Assets.companions['girl_red'].get('main'))
            if active_devushka:
                offset_x = sc(5) if self.engine.current_companion == "blond" else sc(20)
                window.blit(active_devushka, (int(self.engine.WIDTH - active_devushka.get_width() - offset_x), int(self.engine.HEIGHT - active_devushka.get_height())))

            for btn, img in [(self.mode1_btn, self.player_menu), (self.mode2_btn, self.players_img)]:
                bg_rect = btn.inflate(int(sc(30)), int(sc(30)))
                draw_alpha_rect(window, (0, 0, 0, 160), bg_rect, "gradient", int(sc(3)), int(sc(15)))
                img_rect = img.get_rect(center=btn.center)
                window.blit(img, img_rect.topleft)
            draw_text_centered(window, t("Single play"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (self.mode1_btn.x, int(self.mode1_btn.bottom + sc(60)), self.mode1_btn.width, 0), int(sc(2)))
            draw_text_centered(window, t("Multiplayer"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (self.mode2_btn.x, int(self.mode2_btn.bottom + sc(60)), self.mode2_btn.width, 0), int(sc(2)))
            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showGameTypeMenu:
            draw_text_centered(window, t("Network Type"), Assets.fonts['f150'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))
            for btn, txt in [(self.local_btn_rect, t("Local Game")), (self.online_btn_rect, t("Online Game"))]:
                h = btn.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), btn, "gradient" if h else (245,245,245), int(sc(3)), int(sc(15)))
                draw_text_centered(window, txt, Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (245,245,245), (0,0,0), btn, int(sc(4)) if h else int(sc(3)))
            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showHostJoinMenu:
            header_text = t("Local Game") if self.network_mode == "local" else t("Online Game")
            draw_text_centered(window, header_text, Assets.fonts['f150'], (255,255,255), (0,0,0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))
            for btn, txt in [(self.host_btn_rect, t("Host Game")), (self.join_btn_rect, t("Join Game"))]:
                h = btn.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), btn, "gradient" if h else (245,245,245), int(sc(3)), int(sc(15)))
                draw_text_centered(window, txt, Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (245,245,245), (0,0,0), btn, int(sc(4)) if h else int(sc(3)))
            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showHostPlayersMenu:
            draw_text_centered(window, t("Select Players"), Assets.fonts['f150'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))
            for btn, txt in [(self.p2_btn, t("2 Players")), (self.p3_btn, t("3 Players")), (self.p4_btn, t("4 Players"))]:
                h = btn.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), btn, "gradient" if h else (245,245,245), int(sc(3)), int(sc(15)))
                draw_text_centered(window, txt, Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (245,245,245), (0,0,0), btn, int(sc(4)) if h else int(sc(3)))
            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showIPInput:
            draw_text_centered(window, t("Enter Host IP"), Assets.fonts['f150'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))
            pygame.draw.rect(window, (30,30,30), self.ip_input_rect, border_radius=int(sc(15)))
            draw_alpha_rect(window, (0,0,0,0), self.ip_input_rect, "gradient", int(sc(3)), int(sc(15)))
            cursor_str = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
            draw_text_centered(window, self.ip_text + cursor_str, Assets.fonts['text50'], (255,255,255), (0,0,0), self.ip_input_rect)
            h = self.connect_btn_rect.collidepoint(mx, my)
            draw_alpha_rect(window, (0, 0, 0, 160), self.connect_btn_rect, "gradient" if h else (245,245,245), int(sc(3)), int(sc(15)))
            draw_text_centered(window, t("Connect"), Assets.fonts['f40'] if h else Assets.fonts['f30'], "gradient" if h else (245, 245, 245), (0, 0, 0), self.connect_btn_rect, int(sc(4)) if h else int(sc(3)))
            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showSettings:
            if getattr(self, "showBonusInput", False):
                draw_alpha_rect(window, (0, 0, 0, 200), (0, 0, self.engine.WIDTH, self.engine.HEIGHT), (0, 0, 0), 0, 0)
                draw_text_centered(window, t("Enter code:"), Assets.fonts['f60'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.cy - sc(120)), 0, 0), 0)
                pygame.draw.rect(window, (30, 30, 30), self.bonus_input_rect, border_radius=int(sc(15)))
                draw_alpha_rect(window, (0, 0, 0, 0), self.bonus_input_rect, (245, 245, 245), int(sc(3)), int(sc(15)))
                cursor_str = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
                draw_text_centered(window, self.bonus_text + cursor_str, Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), self.bonus_input_rect)
                if pygame.time.get_ticks() < getattr(self, "bonus_message_timer", 0):
                    draw_text_centered(window, self.bonus_message, Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.cy + sc(80)), 0, 0), 0)
                h_b = self.bonus_back_btn.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), self.bonus_back_btn, "gradient" if h_b else (245,245,245), int(sc(3)), int(sc(15)))
                draw_text_centered(window, t("Back"), Assets.fonts['f40'] if h_b else Assets.fonts['f30'], "gradient" if h_b else (245, 245, 245), (0, 0, 0), self.bonus_back_btn, int(sc(3)) if h_b else int(sc(2)))
            else:
                draw_text_centered(window, t("Settings"), Assets.fonts['f150'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))
                if self.settings_tab == "menu":
                    for btn, txt in [(self.gen_tab_btn, t("General")), (self.theme_tab_btn, t("Themes")), (self.tut_tab_btn, t("Tutorial")), (self.bonus_tab_btn, t("Bonus Code"))]:
                        h = btn.collidepoint(mx, my)
                        draw_text_centered(window, txt, Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (245,245,245), (0,0,0), btn, int(sc(4)) if h else int(sc(3)))
                elif self.settings_tab == "general":

                    self.draw_aligned_label(t("Music:"), int(self.slider_bg.left - sc(20)), self.slider_bg.centery, Assets.fonts['text50'], window)
                    mute_rect = self.btn_mute.inflate(int(sc(20)), int(sc(20)))
                    draw_alpha_rect(window, (0, 0, 0, 160), mute_rect, "gradient", int(sc(3)), int(sc(15)))
                    window.blit(Assets.images['unmuteTexture'] if self.engine.muting_music else Assets.images['muteTexture'], self.btn_mute.topleft)

                    pygame.draw.rect(window, (30, 30, 30), self.slider_bg, border_radius=int(sc(15)))
                    fill_w = self.slider_thumb.centerx - self.slider_bg.x
                    if fill_w > 0: pygame.draw.rect(window, self.engine.thumb_color, pygame.Rect(self.slider_bg.x, self.slider_bg.y, fill_w, self.slider_bg.height), border_radius=int(sc(15)))
                    draw_alpha_rect(window, (0,0,0,0), self.slider_bg, "gradient", int(sc(3)), int(sc(15)))
                    pygame.draw.circle(window, (0,0,0), self.slider_thumb.center, int(sc(22))); draw_gradient_circle(window, self.slider_thumb.center, int(sc(20))); pygame.draw.circle(window, self.engine.thumb_color, self.slider_thumb.center, int(sc(15)))

                    self.draw_aligned_label(t("Sound effects:"), int(self.sfx_slider_bg.left - sc(20)), self.sfx_slider_bg.centery, Assets.fonts['text50'], window)
                    sfx_mute_rect = self.btn_sfx_mute.inflate(int(sc(20)), int(sc(20)))
                    draw_alpha_rect(window, (0, 0, 0, 160), sfx_mute_rect, "gradient", int(sc(3)), int(sc(15)))
                    window.blit(Assets.images['unmuteTexture'] if self.engine.muting_sfx else Assets.images['muteTexture'], self.btn_sfx_mute.topleft)

                    pygame.draw.rect(window, (30, 30, 30), self.sfx_slider_bg, border_radius=int(sc(15)))
                    fill_w_sfx = self.sfx_slider_thumb.centerx - self.sfx_slider_bg.x
                    if fill_w_sfx > 0: pygame.draw.rect(window, self.engine.thumb_color, pygame.Rect(self.sfx_slider_bg.x, self.sfx_slider_bg.y, fill_w_sfx, self.sfx_slider_bg.height), border_radius=int(sc(15)))
                    draw_alpha_rect(window, (0,0,0,0), self.sfx_slider_bg, "gradient", int(sc(3)), int(sc(15)))
                    pygame.draw.circle(window, (0,0,0), self.sfx_slider_thumb.center, int(sc(22))); draw_gradient_circle(window, self.sfx_slider_thumb.center, int(sc(20))); pygame.draw.circle(window, self.engine.thumb_color, self.sfx_slider_thumb.center, int(sc(15)))

                    self.draw_aligned_label(t("Brightness:"), int(self.brightness_slider_bg.left - sc(20)), self.brightness_slider_bg.centery, Assets.fonts['text50'], window)
                    pygame.draw.rect(window, (30, 30, 30), self.brightness_slider_bg, border_radius=int(sc(15)))
                    fill_w_br = self.brightness_slider_thumb.centerx - self.brightness_slider_bg.x
                    if fill_w_br > 0: pygame.draw.rect(window, self.engine.thumb_color, pygame.Rect(self.brightness_slider_bg.x, self.brightness_slider_bg.y, fill_w_br, self.brightness_slider_bg.height), border_radius=int(sc(15)))
                    draw_alpha_rect(window, (0,0,0,0), self.brightness_slider_bg, "gradient", int(sc(3)), int(sc(15)))
                    pygame.draw.circle(window, (0,0,0), self.brightness_slider_thumb.center, int(sc(22)))
                    draw_gradient_circle(window, self.brightness_slider_thumb.center, int(sc(20)))
                    pygame.draw.circle(window, self.engine.thumb_color, self.brightness_slider_thumb.center, int(sc(15)))

                    self.draw_aligned_label(t("Language:"), int(self.slider_bg.left - sc(20)), self.btn_lang_en.centery, Assets.fonts['text50'], window)
                    h_en = self.btn_lang_en.collidepoint(mx, my) or get_language() == "en"
                    draw_alpha_rect(window, (0,0,0,160), self.btn_lang_en, "gradient" if h_en else (245,245,245), int(sc(3)), int(sc(10)))
                    draw_text_centered(window, "English", Assets.fonts['text30'], "gradient" if h_en else (245,245,245), (0,0,0), self.btn_lang_en, int(sc(2)))

                    h_ru = self.btn_lang_ru.collidepoint(mx, my) or get_language() == "ru"
                    draw_alpha_rect(window, (0,0,0,160), self.btn_lang_ru, "gradient" if h_ru else (245,245,245), int(sc(3)), int(sc(10)))
                    draw_text_centered(window, "Русский", Assets.fonts['text30'], "gradient" if h_ru else (245,245,245), (0,0,0), self.btn_lang_ru, int(sc(2)))

                    self.draw_aligned_label(t("VSync:"), int(self.slider_bg.left - sc(20)), self.btn_vsync.centery, Assets.fonts['text50'], window)
                    h_v = self.btn_vsync.collidepoint(mx, my) or self.engine.current_vsync
                    draw_alpha_rect(window, (0,0,0,160), self.btn_vsync, "gradient" if h_v else (245,245,245), int(sc(3)), int(sc(10)))
                    draw_text_centered(window, t("On") if self.engine.current_vsync else t("Off"), Assets.fonts['text30'], "gradient" if h_v else (245, 245, 245), (0, 0, 0), self.btn_vsync, int(sc(2)))

                    self.draw_aligned_label(t("Skip Splash:"), int(self.slider_bg.left - sc(20)), self.btn_skip_splash.centery, Assets.fonts['text50'], window)
                    h_ss = self.btn_skip_splash.collidepoint(mx, my) or self.engine.current_skip_splash
                    draw_alpha_rect(window, (0,0,0,160), self.btn_skip_splash, "gradient" if h_ss else (245,245,245), int(sc(3)), int(sc(10)))
                    draw_text_centered(window, t("On") if self.engine.current_skip_splash else t("Off"), Assets.fonts['text30'], "gradient" if h_ss else (245, 245, 245), (0, 0, 0), self.btn_skip_splash, int(sc(2)))

                    self.draw_aligned_label(t("Nickname:"), int(self.slider_bg.left - sc(20)), self.nickname_input_rect.centery, Assets.fonts['text50'], window)
                    pygame.draw.rect(window, (30, 30, 30), self.nickname_input_rect, border_radius=int(sc(10)))
                    draw_alpha_rect(window, (0,0,0,0), self.nickname_input_rect, "gradient" if self.nickname_input_active else (245,245,245), int(sc(3)), int(sc(10)))
                    cursor_str = "_" if self.nickname_input_active and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
                    draw_text_centered(window, self.engine.nickname_text + cursor_str, Assets.fonts['text30'], (255,255,255), (0,0,0), self.nickname_input_rect)

                    h_sn = self.btn_save_nick.collidepoint(mx, my)
                    draw_alpha_rect(window, (0,0,0,160), self.btn_save_nick, "gradient" if h_sn else (245,245,245), int(sc(3)), int(sc(10)))
                    draw_text_centered(window, t("Save"), Assets.fonts['text30'], "gradient" if h_sn else (245, 245, 245), (0, 0, 0), self.btn_save_nick, int(sc(2)))

                    self.draw_aligned_label(t("Title:"), int(self.slider_bg.left - sc(20)), self.title_display_rect.centery, Assets.fonts['text50'], window)

                    h_tl = self.title_left_btn.collidepoint(mx, my)
                    draw_alpha_rect(window, (0,0,0,160), self.title_left_btn, "gradient" if h_tl else (245,245,245), int(sc(3)), int(sc(10)))
                    pygame.draw.polygon(window, (255, 215, 0), [
                        (self.title_left_btn.right - sc(15), self.title_left_btn.top + sc(12)),
                        (self.title_left_btn.right - sc(15), self.title_left_btn.bottom - sc(12)),
                        (self.title_left_btn.left + sc(12), self.title_left_btn.centery)
                    ])

                    pygame.draw.rect(window, (30, 30, 30), self.title_display_rect, border_radius=int(sc(10)))
                    draw_alpha_rect(window, (0,0,0,0), self.title_display_rect, (245,245,245), int(sc(3)), int(sc(10)))
                    title_id = self.VISIBLE_TITLES[self.viewing_title_idx]
                    draw_text_centered(window, self.localize_title(title_id), Assets.fonts['text30'], self.get_title_color(title_id), (0,0,0), self.title_display_rect)

                    h_tr = self.title_right_btn.collidepoint(mx, my)
                    draw_alpha_rect(window, (0,0,0,160), self.title_right_btn, "gradient" if h_tr else (245,245,245), int(sc(3)), int(sc(10)))
                    pygame.draw.polygon(window, (255, 215, 0), [
                        (self.title_right_btn.left + sc(15), self.title_right_btn.top + sc(12)),
                        (self.title_right_btn.left + sc(15), self.title_right_btn.bottom - sc(12)),
                        (self.title_right_btn.right - sc(12), self.title_right_btn.centery)
                    ])

                    unlocked = title_id in self.engine.current_progress.get("titles_unlocked", ["Новичок"])
                    if unlocked:
                        if title_id == self.engine.current_progress.get("current_title", "Новичок"):
                            draw_alpha_rect(window, (0,0,0,160), self.btn_equip_title, (100,100,100), int(sc(3)), int(sc(10)))
                            draw_text_centered(window, t("Equipped"), Assets.fonts['text30'], (150, 150, 150), (0, 0, 0), self.btn_equip_title, int(sc(2)))
                        else:
                            h_eq = self.btn_equip_title.collidepoint(mx, my)
                            draw_alpha_rect(window, (0,0,0,160), self.btn_equip_title, "gradient" if h_eq else (245,245,245), int(sc(3)), int(sc(10)))
                            draw_text_centered(window, t("Equip"), Assets.fonts['text30'], "gradient" if h_eq else (245, 245, 245), (0, 0, 0), self.btn_equip_title, int(sc(2)))
                    else:
                        hint = t(self.TITLE_CONDITIONS[title_id])
                        draw_text_centered(window, hint, Assets.fonts['text30'], (255, 255, 255), (0,0,0), self.title_hint_rect)

                elif self.settings_tab == "themes":
                    for t_id, btn, txt in [("bg", self.v_tab_bg, t("Themes & BG")), ("comp", self.v_tab_comp, t("Companions")), ("emoji", self.v_tab_emoji, t("Emojis"))]:
                        is_active = (self.visual_sub_tab == t_id)
                        h = btn.collidepoint(mx, my) or is_active
                        draw_alpha_rect(window, (0, 0, 0, 160), btn, "gradient" if is_active else ((245,245,245) if h else (150,150,150)), int(sc(3)) if is_active else int(sc(2)), int(sc(15)))
                        draw_text_centered(window, txt, Assets.fonts['text50'], "gradient" if is_active else ((255,255,255) if h else (180,180,180)), (0,0,0), btn, int(sc(2)))

                    if self.visual_sub_tab == "bg":
                        themes_btns = [("red", self.btn_red, t("Red")), ("green", self.btn_green, t("Green")), ("blue", self.btn_blue, t("Blue"))]
                        for t_id, btn, txt in themes_btns:
                            h = btn.collidepoint(mx, my) or self.dropdown_open == t_id
                            draw_alpha_rect(window, (0, 0, 0, 160), btn, "gradient" if h else (245,245,245), int(sc(3)), int(sc(10)))
                            draw_text_centered(window, txt, Assets.fonts['text50'], "gradient" if h else (255,255,255), (0,0,0), btn, int(sc(2)))

                        if self.dropdown_open == "red":
                            for b, txt in [(self.btn_red_bg1, t("Background 1")), (self.btn_red_bg2, t("Background 2"))]:
                                h = b.collidepoint(mx, my)
                                draw_alpha_rect(window, (0, 0, 0, 160), b, "gradient" if h else (245,245,245), int(sc(3)), int(sc(10)))
                                draw_text_centered(window, txt, Assets.fonts['text30'], "gradient" if h else (255,255,255), (0,0,0), b, int(sc(2)))
                        elif self.dropdown_open == "green":
                            for b, txt in [(self.btn_green_bg1, t("Background 1")), (self.btn_green_bg2, t("Background 2"))]:
                                h = b.collidepoint(mx, my)
                                draw_alpha_rect(window, (0, 0, 0, 160), b, "gradient" if h else (245,245,245), int(sc(3)), int(sc(10)))
                                draw_text_centered(window, txt, Assets.fonts['text30'], "gradient" if h else (255,255,255), (0,0,0), b, int(sc(2)))
                        elif self.dropdown_open == "blue":
                            for b, txt in [(self.btn_blue_bg1, t("Background 1")), (self.btn_blue_bg2, t("Background 2"))]:
                                h = b.collidepoint(mx, my)
                                draw_alpha_rect(window, (0, 0, 0, 160), b, "gradient" if h else (245,245,245), int(sc(3)), int(sc(10)))
                                draw_text_centered(window, txt, Assets.fonts['text30'], "gradient" if h else (255,255,255), (0,0,0), b, int(sc(2)))

                    elif self.visual_sub_tab == "comp":
                        h_b = self.btn_comp_blond.collidepoint(mx, my) or self.engine.current_companion == "blond"
                        bg_b = self.btn_comp_blond.inflate(int(sc(20)), int(sc(20)))
                        draw_alpha_rect(window, (0, 0, 0, 160), bg_b, "gradient" if h_b else (245,245,245), int(sc(3)), int(sc(15)))
                        blond_scaled = pygame.transform.smoothscale(Assets.images['logo_blond'], (self.btn_comp_blond.width, self.btn_comp_blond.height))
                        window.blit(blond_scaled, self.btn_comp_blond.topleft)
                        draw_text_centered(window, t("Lei"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (self.btn_comp_blond.x, int(self.btn_comp_blond.bottom + sc(40)), self.btn_comp_blond.width, 0), int(sc(2)))


                        h_r = self.btn_comp_red.collidepoint(mx, my) or self.engine.current_companion == "red"
                        bg_r = self.btn_comp_red.inflate(int(sc(20)), int(sc(20)))
                        draw_alpha_rect(window, (0, 0, 0, 160), bg_r, "gradient" if h_r else (245,245,245), int(sc(3)), int(sc(15)))
                        red_scaled = pygame.transform.smoothscale(Assets.images['logo_red'], (self.btn_comp_red.width, self.btn_comp_red.height))
                        window.blit(red_scaled, self.btn_comp_red.topleft)
                        draw_text_centered(window, t("Muse"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (self.btn_comp_red.x, int(self.btn_comp_red.bottom + sc(40)), self.btn_comp_red.width, 0), int(sc(2)))

                    elif self.visual_sub_tab == "emoji":
                        current_pack = self.engine.current_settings.get("emoji_pack", "Standard")
                        for pack_name, rect in self.get_emoji_pack_rects():
                            h = rect.collidepoint(mx, my)
                            is_selected = (pack_name == current_pack)
                            bg_rect = rect.inflate(int(sc(20)), int(sc(20)))
                            draw_alpha_rect(window, (0, 0, 0, 160), bg_rect, "gradient" if is_selected else ((245,245,245) if h else (100,100,100)), int(sc(3)) if is_selected else int(sc(2)), int(sc(15)))

                            logo_key = f'logo_{pack_name}'
                            if logo_key in Assets.images:
                                pack_img = Assets.images[logo_key]
                                p_rect = pack_img.get_rect(center=rect.center)
                                window.blit(pack_img, p_rect.topleft)

                if not getattr(self, "showBonusInput", False):
                    hovered = self.back_btn.collidepoint(mx, my)
                    draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        elif self.showAuthors:
            draw_text_centered(window, t("Authors"), Assets.fonts['f150'], (255, 255, 255), (0, 0, 0), (self.cx, int(self.engine.HEIGHT * 0.12), 0, 0), int(sc(5)))
            rac_rect = pygame.Rect(0, 0, Assets.images['raccoonka'].get_width(), Assets.images['raccoonka'].get_height()); rac_rect.center = (self.cx, int(self.cy - sc(50)))
            bg_rect = rac_rect.inflate(int(sc(30)), int(sc(30)))
            draw_alpha_rect(window, (0, 0, 0, 160), bg_rect, "gradient", int(sc(3)), int(sc(15)))
            window.blit(Assets.images['raccoonka'], rac_rect.topleft)
            draw_text_centered(window, t("Kravchuk Svetozar"), Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (rac_rect.x, int(rac_rect.bottom + sc(55)), rac_rect.width, 0), int(sc(2)))
            hovered = self.back_btn.collidepoint(mx, my)
            draw_text_centered(window, t("Back"), Assets.fonts['f100'] if hovered else Assets.fonts['f80'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))
        else:
            emo = self.engine.current_emotion
            theme = self.engine.current_theme
            if self.engine.current_companion == "blond": active_devushka = Assets.companions['girl_blond'][theme].get(emo, Assets.companions['girl_blond'][theme].get('main'))
            else: active_devushka = Assets.companions['girl_red'].get(emo, Assets.companions['girl_red'].get('main'))
            if active_devushka:
                offset_x = sc(5) if self.engine.current_companion == "blond" else sc(20)
                window.blit(active_devushka, (int(self.engine.WIDTH - active_devushka.get_width() - offset_x), int(self.engine.HEIGHT - active_devushka.get_height())))

            draw_text_centered(window, "Velaris", Assets.fonts['f150'], "animated_gradient", (0,0,0), (self.cx, int(self.engine.HEIGHT * 0.15), 0, 0), int(sc(5)), time_ms=pygame.time.get_ticks())

            info_rect = pygame.Rect(int(sc(20)), int(self.engine.HEIGHT - sc(160)), int(sc(450)), int(sc(140)))
            draw_alpha_rect(window, (0, 0, 0, 160), info_rect, "gradient", int(sc(3)), int(sc(15)))

            title_str = self.engine.current_progress.get("current_title", "Новичок")
            draw_text_centered(window, f"[{self.localize_title(title_str)}]", Assets.fonts['text30'], self.get_title_color(title_str), (0, 0, 0), (info_rect.x, info_rect.y + int(sc(10)), info_rect.width, int(sc(40))), int(sc(2)))

            draw_text_centered(window, f"{t('Nickname:')} {self.engine.nickname_text}", Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (info_rect.x, info_rect.y + int(sc(50)), info_rect.width, int(sc(40))), int(sc(2)))
            draw_text_centered(window, f"{t('Money:')} {self.engine.current_progress.get('money', 10000)}$", Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (info_rect.x, info_rect.y + int(sc(90)), info_rect.width, int(sc(40))), int(sc(2)))

            draw_alpha_rect(window, (0, 0, 0, 160), self.wheel_box, "gradient", int(sc(3)), int(sc(15)))
            wheel_header = "WHEEL OF FORTUNE" if get_language() == "en" else "КОЛЕСО УДАЧИ"
            draw_text_centered(window, wheel_header, Assets.fonts['text30'], (255, 215, 0), (0, 0, 0), (self.wheel_box.x, self.wheel_box.y + int(sc(10)), self.wheel_box.width, int(sc(30))), int(sc(2)))

            pygame.draw.rect(window, (20, 20, 20), self.reel_rect, border_radius=int(sc(10)))
            draw_alpha_rect(window, (0, 0, 0, 0), self.reel_rect, (255, 215, 0), int(sc(2)), int(sc(10)))

            old_clip = window.get_clip()
            window.set_clip(self.reel_rect)

            item_h = sc(60)
            total_h = len(self.wheel_pool) * item_h
            for i, item in enumerate(self.wheel_pool):
                draw_y = self.reel_rect.y + ((i * item_h - int(self.reel_y)) % total_h)
                if draw_y + item_h >= self.reel_rect.y and draw_y <= self.reel_rect.bottom:
                    item_center_y = draw_y + item_h // 2
                    is_centered = abs(item_center_y - self.reel_rect.centery) < (item_h // 2)

                    card_rect = pygame.Rect(self.reel_rect.x + sc(5), draw_y + sc(2), self.reel_rect.width - sc(10), item_h - sc(4))
                    bg_color = (60, 60, 60) if is_centered else (35, 35, 35)
                    border_color = (255, 215, 0) if is_centered else (100, 100, 100)
                    border_w = int(sc(2)) if is_centered else int(sc(1))

                    pygame.draw.rect(window, bg_color, card_rect, border_radius=int(sc(8)))
                    pygame.draw.rect(window, border_color, card_rect, width=border_w, border_radius=int(sc(8)))

                    if item["type"] == "title":
                        text_color = self.get_title_color("Крути-вези!")
                    elif item["val"] == 100000:
                        text_color = (255, 100, 100)
                    elif item["val"] == 10000:
                        text_color = (255, 215, 0)
                    else:
                        text_color = (255, 255, 255)

                    draw_text_centered(window, self.localize_title(item["name"]), Assets.fonts['text30'], text_color, (0, 0, 0), card_rect)

            window.set_clip(old_clip)

            lp1 = (self.reel_rect.x - sc(5), self.reel_rect.centery - sc(10))
            lp2 = (self.reel_rect.x - sc(5), self.reel_rect.centery + sc(10))
            lp3 = (self.reel_rect.x + sc(5), self.reel_rect.centery)
            pygame.draw.polygon(window, (255, 0, 0), [lp1, lp2, lp3])

            rp1 = (self.reel_rect.right + sc(5), self.reel_rect.centery - sc(10))
            rp2 = (self.reel_rect.right + sc(5), self.reel_rect.centery + sc(10))
            rp3 = (self.reel_rect.right - sc(5), self.reel_rect.centery)
            pygame.draw.polygon(window, (255, 0, 0), [rp1, rp2, rp3])

            if self.wheel_state == "idle":
                spin_lbl = "SPIN!" if get_language() == "en" else "КРУТИТЬ!"
                h = self.spin_btn_rect.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), self.spin_btn_rect, "gradient" if h else (245, 245, 245), int(sc(3)), int(sc(15)))
                draw_text_centered(window, spin_lbl, Assets.fonts['f20'] if h else Assets.fonts['f18'], "gradient" if h else (245, 245, 245), (0, 0, 0), self.spin_btn_rect, int(sc(3)) if h else int(sc(2)))
            else:
                spin_lbl = "SPINNING" if get_language() == "en" else "КРУТИМ"
                draw_alpha_rect(window, (0, 0, 0, 100), self.spin_btn_rect, (80, 80, 80), int(sc(1)), int(sc(15)))
                draw_text_centered(window, spin_lbl, Assets.fonts['text20'], (150, 150, 150), (0, 0, 0), self.spin_btn_rect)

            for btn, txt in [(self.play_btn, t("Play")), (self.shop_btn, t("Luck Shop")), (self.set_btn, t("Settings")), (self.auth_btn, t("Authors")), (self.exit_btn, t("Exit"))]:
                h = btn.collidepoint(mx, my)
                draw_text_centered(window, txt, Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (245,245,245), (0,0,0), btn, int(sc(4)) if h else int(sc(3)))

        for p in self.particles:
            alpha = int((p[4] / p[7]) * 255)
            surf = pygame.Surface((int(p[6]*2), int(p[6]*2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p[5], alpha), (int(p[6]), int(p[6])), int(p[6]))
            window.blit(surf, (int(p[0]-p[6]), int(p[1]-p[6])))