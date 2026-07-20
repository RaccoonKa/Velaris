import pygame
import os
import yaml
import random
import math
from scenes.base_scene import BaseScene
from utils.utils import sc, draw_alpha_rect, draw_text_centered, draw_text
from resources import t, Assets, save_progress

class ShopScene(BaseScene):
    def __init__(self, engine):
        super().__init__(engine)
        self.cx = int(self.engine.WIDTH // 2)
        self.cy = int(self.engine.HEIGHT // 2)

        self.back_btn = pygame.Rect(0, 0, int(sc(240)), int(sc(80)))
        self.back_btn.bottomright = (int(self.engine.WIDTH - sc(20)), int(self.engine.HEIGHT - sc(20)))

        self.store_data = {"skins": [], "titles": [], "emoticons": []}
        self._load_store()

        self.item_w, self.item_h = int(sc(400)), int(sc(200))
        self.spacing = self.item_w + int(sc(60))

        self.carousels = {
            "skins & themes": {"scroll_x": 0, "dragging": False, "velocity": 0, "zoom_amp": 0.0, "y": int(self.engine.HEIGHT * 0.35), "items": self.store_data.get("skins", [])},
            "titles": {"scroll_x": 0, "dragging": False, "velocity": 0, "zoom_amp": 0.0, "y": int(self.engine.HEIGHT * 0.62), "items": self.store_data.get("titles", [])},
            "emoticons": {"scroll_x": 0, "dragging": False, "velocity": 0, "zoom_amp": 0.0, "y": int(self.engine.HEIGHT * 0.89), "items": self.store_data.get("emoticons", [])}
        }

        self.last_mx = 0
        self.click_start_pos = (0, 0)

        self.show_popup = False
        self.selected_category = None
        self.selected_item = None

        self.popup_rect = pygame.Rect(0, 0, int(sc(950)), int(sc(500)))
        self.popup_rect.center = (self.cx, self.cy)

        self.buy_btn = pygame.Rect(0, 0, int(sc(420)), int(sc(70)))
        self.buy_btn.center = (self.cx - int(sc(230)), self.cy + int(sc(180)))

        self.popup_back_btn = pygame.Rect(0, 0, int(sc(420)), int(sc(70)))
        self.popup_back_btn.center = (self.cx + int(sc(230)), self.cy + int(sc(180)))

        self.particles = []

    def _load_store(self):
        try:
            path = os.path.join("configs", "store.yaml")
            if not os.path.exists(path):
                if not os.path.exists("configs"):
                    os.makedirs("configs")
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump({
                        "skins": [{"name": "Lei", "price": 10000}, {"name": "Cyberpunk", "price": 60000}, {"name": "Golden", "price": 60000}],
                        "titles": [{"name": "Volcano of Luck", "price": 30000}, {"name": "High roller", "price": 50000}, {"name": "Bluff master", "price": 50000}, {"name": "Millionaire", "price": 1000000}],
                        "emoticons": [{"name": "Skull", "price": 40000}, {"name": "Cyberpunk", "price": 40000}, {"name": "Raccoon", "price": 40000}]
                    }, f)
            with open(path, "r", encoding="utf-8") as f:
                self.store_data = yaml.safe_load(f)

            has_golden = any(skin.get("name") == "Golden" for skin in self.store_data.get("skins", []))
            if not has_golden:
                if "skins" not in self.store_data:
                    self.store_data["skins"] = []
                self.store_data["skins"].append({"name": "Golden", "price": 60000})
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(self.store_data, f)

        except Exception as e:
            print(e)

    def on_enter(self, **kwargs):
        self.engine.switch_music(self.engine.current_theme, "menu")

    def _get_item_at_pos(self, mx, my):
        for key, data in self.carousels.items():
            items = data["items"]
            if not items: continue
            y = data["y"]

            center_i = -int(round(data["scroll_x"] / self.spacing))

            idx = center_i % len(items)
            item = items[idx]
            card_cx = self.cx + center_i * self.spacing + data["scroll_x"]
            dist = abs(self.cx - card_cx)

            zoom_factor = 1.0
            center_factor = max(0.0, 1.0 - dist / self.spacing)
            zoom_factor = 1.0 + (0.14 * center_factor * data["zoom_amp"])

            final_w = int(self.item_w * zoom_factor)
            final_h = int(self.item_h * zoom_factor)
            card_x = int(card_cx - final_w / 2)
            card_y = int(y - final_h / 2)

            rect = pygame.Rect(card_x, card_y, final_w, final_h)
            if rect.collidepoint(mx, my):
                return key, item

        return None, None

    def spawn_particles(self):
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 12)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            color = random.choice([(255, 215, 0), (255, 255, 255), (255, 250, 200)])
            size = random.uniform(sc(4), sc(10))
            lifetime = random.randint(40, 80)
            self.particles.append([self.cx, self.cy, dx, dy, lifetime, color, size, lifetime])

    def handle_events(self, events):
        mx, my = self.engine.mx, self.engine.my

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.show_popup:
                    if self.buy_btn.collidepoint(mx, my):
                        price = self.selected_item["price"]
                        name = self.selected_item["name"]
                        money = self.engine.current_progress.get("money", 10000)

                        if self.selected_category == "titles":
                            unlocked = self.engine.current_progress.get("titles_unlocked", ["Новичок"])
                            if name not in unlocked and money >= price:
                                Assets.sounds['enter'].play()
                                self.engine.current_progress["money"] -= price
                                self.engine.unlock_title(name)
                                self.spawn_particles()
                        elif self.selected_category == "emoticons":
                            unlocked = self.engine.current_progress.get("emojis_unlocked", ["Standard"])
                            if name not in unlocked and money >= price:
                                Assets.sounds['enter'].play()
                                self.engine.current_progress["money"] -= price
                                unlocked.append(name)
                                self.engine.current_progress["emojis_unlocked"] = unlocked
                                save_progress(self.engine.current_progress)
                                self.spawn_particles()
                        elif self.selected_category == "skins & themes":
                            unlocked = self.engine.current_progress.get("skins_unlocked", ["Musa"])
                            if name not in unlocked and money >= price:
                                Assets.sounds['enter'].play()
                                self.engine.current_progress["money"] -= price
                                unlocked.append(name)
                                self.engine.current_progress["skins_unlocked"] = unlocked
                                save_progress(self.engine.current_progress)
                                self.spawn_particles()

                    elif self.popup_back_btn.collidepoint(mx, my):
                        Assets.sounds['back'].play()
                        self.show_popup = False
                else:
                    if self.back_btn.collidepoint(mx, my):
                        Assets.sounds['back'].play()
                        self.engine.switch_scene("menu")
                        return

                    self.click_start_pos = (mx, my)
                    for key, data in self.carousels.items():
                        if not data["items"]: continue
                        hitbox = pygame.Rect(0, data["y"] - self.item_h // 2, self.engine.WIDTH, self.item_h)
                        if hitbox.collidepoint(mx, my):
                            data["dragging"] = True
                            data["velocity"] = 0
                            self.last_mx = mx
                            break

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not self.show_popup:
                    dist = math.hypot(mx - self.click_start_pos[0], my - self.click_start_pos[1])
                    if dist < sc(15):
                        cat, item = self._get_item_at_pos(mx, my)
                        if item:
                            Assets.sounds['enter'].play()
                            self.selected_category = cat
                            self.selected_item = item
                            self.show_popup = True

                    for data in self.carousels.values():
                        data["dragging"] = False

            elif event.type == pygame.MOUSEMOTION:
                if not self.show_popup:
                    for data in self.carousels.values():
                        if data["dragging"]:
                            dx = mx - self.last_mx
                            data["scroll_x"] += dx
                            data["velocity"] = dx

                    if any(d["dragging"] for d in self.carousels.values()):
                        self.last_mx = mx

    def update(self):
        mx, my = self.engine.mx, self.engine.my

        if self.show_popup:
            return

        for data in self.carousels.values():
            hitbox = pygame.Rect(0, data["y"] - self.item_h // 2, self.engine.WIDTH, self.item_h)
            is_hovered = hitbox.collidepoint(mx, my)

            if not data["dragging"]:
                data["scroll_x"] += data["velocity"]
                data["velocity"] *= 0.92

                target_scroll = round(data["scroll_x"] / self.spacing) * self.spacing
                diff = target_scroll - data["scroll_x"]

                if abs(data["velocity"]) < 3:
                    data["scroll_x"] += diff * 0.15

                if is_hovered and abs(data["scroll_x"] - target_scroll) < sc(5) and abs(data["velocity"]) < 1.5:
                    data["zoom_amp"] = min(1.0, data["zoom_amp"] + 0.12)
                else:
                    data["zoom_amp"] = max(0.0, data["zoom_amp"] - 0.12)
            else:
                data["zoom_amp"] = max(0.0, data["zoom_amp"] - 0.15)

    def draw(self, window):
        window.blit(self.engine.current_bg, (0, 0))
        draw_alpha_rect(window, (0, 0, 0, 180), (0, 0, self.engine.WIDTH, self.engine.HEIGHT), (0, 0, 0), 0, 0)
        draw_text_centered(window, t("Luck Shop"), Assets.fonts['f150'], (255, 215, 0), (0, 0, 0), (self.cx, int(sc(80)), 0, 0), int(sc(5)))

        for key, data in self.carousels.items():
            items = data["items"]
            if not items: continue

            y = data["y"]
            draw_text_centered(window, t(key), Assets.fonts['f40'], (255, 255, 255), (0, 0, 0), (self.cx, y - self.item_h // 2 - int(sc(40)), 0, 0), int(sc(2)))

            center_i = -int(round(data["scroll_x"] / self.spacing))

            for i in range(center_i - 3, center_i + 4):
                idx = i % len(items)
                item = items[idx]

                card_cx = self.cx + i * self.spacing + data["scroll_x"]
                dist = abs(self.cx - card_cx)

                if dist < self.spacing * 0.7:
                    alpha = 255
                else:
                    fade_range = self.spacing * 0.8
                    alpha = max(0, min(255, int(255 * (1 - (dist - self.spacing * 0.7) / fade_range))))

                if alpha <= 0: continue

                zoom_factor = 1.0
                color = (40, 40, 40, 230)

                if i == center_i:
                    center_factor = max(0.0, 1.0 - dist / self.spacing)
                    zoom_factor = 1.0 + (0.14 * center_factor * data["zoom_amp"])
                    if data["dragging"]:
                        color = (60, 60, 60, 230)

                card_surf = pygame.Surface((self.item_w, self.item_h), pygame.SRCALPHA)
                local_rect = pygame.Rect(0, 0, self.item_w, self.item_h)
                r_radius = int(sc(15))

                pygame.draw.rect(card_surf, color, local_rect, border_radius=r_radius)
                pygame.draw.rect(card_surf, (200, 200, 200), local_rect, width=int(sc(2)), border_radius=r_radius)

                is_bought = False
                if key == "titles":
                    is_bought = item["name"] in self.engine.current_progress.get("titles_unlocked", ["Новичок"])
                elif key == "emoticons":
                    is_bought = item["name"] in self.engine.current_progress.get("emojis_unlocked", ["Standard"])
                elif key == "skins & themes":
                    is_bought = item["name"] in self.engine.current_progress.get("skins_unlocked", ["Musa"])

                draw_text_centered(card_surf, item["name"], Assets.fonts['text50'], (255, 255, 255), (0,0,0), (0, int(sc(40)), self.item_w, 0))

                if is_bought:
                    draw_text_centered(card_surf, t("Bought"), Assets.fonts['text30'], (100, 200, 100), (0,0,0), (0, self.item_h - int(sc(50)), self.item_w, 0))
                else:
                    draw_text_centered(card_surf, f"{item['price']} $", Assets.fonts['text30'], (255, 215, 0), (0,0,0), (0, self.item_h - int(sc(50)), self.item_w, 0))

                final_w = int(self.item_w * zoom_factor)
                final_h = int(self.item_h * zoom_factor)
                scaled_surf = pygame.transform.smoothscale(card_surf, (final_w, final_h))

                scaled_surf.set_alpha(alpha)

                card_x = int(card_cx - final_w / 2)
                card_y = int(y - final_h / 2)
                window.blit(scaled_surf, (card_x, card_y))

        if not self.show_popup:
            hovered = self.back_btn.collidepoint(self.engine.mx, self.engine.my)
            draw_text_centered(window, t("Back"), Assets.fonts['f60'] if hovered else Assets.fonts['f50'], "gradient" if hovered else (245, 245, 245), (0, 0, 0), self.back_btn, int(sc(4)) if hovered else int(sc(3)))

        if self.show_popup and self.selected_item:
            draw_alpha_rect(window, (0, 0, 0, 200), (0, 0, self.engine.WIDTH, self.engine.HEIGHT), (0, 0, 0), 0, 0)

            skin_name = self.selected_item.get('name') if self.selected_category == "skins & themes" else ""

            if skin_name == "Golden":
                popup_surf = pygame.Surface((self.popup_rect.width, self.popup_rect.height), pygame.SRCALPHA)

                r_radius = int(sc(20))
                pygame.draw.rect(popup_surf, (255, 255, 255, 255), (0, 0, self.popup_rect.width, self.popup_rect.height), border_radius=r_radius)

                gold_img = Assets.images.get('gold_preview')
                if gold_img:
                    ow, oh = gold_img.get_width(), gold_img.get_height()
                    scale = max(self.popup_rect.width / ow, self.popup_rect.height / oh)
                    nw, nh = int(ow * scale), int(oh * scale)
                    gold_scaled = pygame.transform.smoothscale(gold_img, (nw, nh))

                    crop_x = (nw - self.popup_rect.width) // 2
                    crop_y = (nh - self.popup_rect.height) // 2

                    popup_surf.blit(gold_scaled, (0, 0), pygame.Rect(crop_x, crop_y, self.popup_rect.width, self.popup_rect.height), special_flags=pygame.BLEND_RGBA_MIN)

                window.blit(popup_surf, self.popup_rect.topleft)

                description_lines = [
                    t("• New outfit for Musa"),
                    t("• New card shirt"),
                    t("• New backgrounds"),
                    t("• New music"),
                    t("• New cursor")
                ]

                start_x = self.popup_rect.left + int(sc(50))
                start_y = self.popup_rect.top + int(sc(140))
                line_height = int(sc(40))

                text_bg_rect = pygame.Rect(start_x - int(sc(20)), start_y - int(sc(10)), int(sc(360)), len(description_lines) * line_height + int(sc(15)))
                draw_alpha_rect(window, (0, 0, 0, 110), text_bg_rect, (0, 0, 0), 0, int(sc(10)))

                for idx, line in enumerate(description_lines):
                    pos_y = start_y + idx * line_height
                    draw_text(window, line, Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (start_x, pos_y), int(sc(2)))
            else:
                pygame.draw.rect(window, (30, 30, 30), self.popup_rect, border_radius=int(sc(20)))

            draw_alpha_rect(window, (0, 0, 0, 0), self.popup_rect, (200, 200, 200), int(sc(3)), int(sc(20)))
            draw_text_centered(window, t("Preview"), Assets.fonts['f60'], (255, 255, 255), (0, 0, 0), (self.cx, self.popup_rect.top + int(sc(60)), 0, 0), int(sc(3)))

            is_bought = False

            if self.selected_category == "titles":
                title_name = self.selected_item['name']
                t_color = (255, 215, 0)
                if title_name in ["Разработчик", "Миллионер", "Millionaire"]:
                    t_ms = pygame.time.get_ticks()
                    glow = int((math.sin(t_ms / 150.0) + 1) / 2 * 100)
                    t_color = (255, 255 - glow, 0)

                title_str = f"[{t(title_name)}]"
                draw_text_centered(window, title_str, Assets.fonts['text50'], t_color, (0, 0, 0), (self.cx, self.cy - int(sc(50)), 0, 0), int(sc(2)))
                draw_text_centered(window, self.engine.nickname_text, Assets.fonts['text60'], (255, 255, 255), (0, 0, 0), (self.cx, self.cy + int(sc(10)), 0, 0), int(sc(3)))

                unlocked = self.engine.current_progress.get("titles_unlocked", ["Новичок"])
                is_bought = self.selected_item["name"] in unlocked

            elif self.selected_category == "emoticons":
                emo_name = self.selected_item['name']
                try:
                    emo_img = Assets.images.get(f'logo_{emo_name}', Assets.images.get('logo_Standard'))
                except:
                    emo_img = None

                if emo_img:
                    img_rect = emo_img.get_rect(center=(self.cx, self.cy - int(sc(20))))
                    window.blit(emo_img, img_rect.topleft)

                unlocked = self.engine.current_progress.get("emojis_unlocked", ["Standard"])
                is_bought = self.selected_item["name"] in unlocked

            elif self.selected_category == "skins & themes":
                unlocked = self.engine.current_progress.get("skins_unlocked", ["Musa"])
                is_bought = skin_name in unlocked

                if skin_name == "Lei":
                    lei_img = Assets.images.get('lei')
                    if lei_img:
                        ow, oh = lei_img.get_width(), lei_img.get_height()
                        max_h = int(sc(260))
                        if oh > max_h:
                            scale = max_h / oh
                            lei_img = pygame.transform.smoothscale(lei_img, (int(ow * scale), max_h))

                        img_rect = lei_img.get_rect(center=(self.cx, self.cy - int(sc(20))))
                        window.blit(lei_img, img_rect.topleft)

            price = self.selected_item["price"]
            money = self.engine.current_progress.get("money", 10000)
            can_afford = money >= price

            if is_bought:
                draw_text_centered(window, t("Bought"), Assets.fonts['text50'], (100, 200, 100), (0, 0, 0), (self.cx, self.cy + int(sc(90)), 0, 0), int(sc(2)))
                btn_color = (100, 100, 100)
                btn_txt = "Bought"
            else:
                shadow_offset = int(sc(3)) if skin_name == "Golden" else int(sc(2))
                draw_text_centered(window, f"{price} $", Assets.fonts['text50'], (255, 215, 0), (0, 0, 0), (self.cx, self.cy + int(sc(90)), 0, 0), shadow_offset)
                if can_afford:
                    btn_color = (50, 150, 50)
                    btn_txt = "Buy"
                else:
                    btn_color = (150, 50, 50)
                    btn_txt = "Not enough money"

            h_buy = self.buy_btn.collidepoint(self.engine.mx, self.engine.my) and not is_bought and can_afford
            draw_alpha_rect(window, (0, 0, 0, 160), self.buy_btn, "gradient" if h_buy else btn_color, int(sc(3)), int(sc(15)))
            draw_text_centered(window, t(btn_txt), Assets.fonts['f30'], (255, 255, 255), (0, 0, 0), self.buy_btn, int(sc(2)))

            h_back = self.popup_back_btn.collidepoint(self.engine.mx, self.engine.my)
            draw_alpha_rect(window, (0, 0, 0, 160), self.popup_back_btn, "gradient" if h_back else (245, 245, 245), int(sc(3)), int(sc(15)))
            draw_text_centered(window, t("Back"), Assets.fonts['f30'], "gradient" if h_back else (255, 255, 255), (0, 0, 0), self.popup_back_btn, int(sc(2)))

            for p in self.particles[:]:
                p[0] += p[2]
                p[1] += p[3]
                p[4] -= 1
                if p[4] <= 0:
                    self.particles.remove(p)
                else:
                    alpha = int((p[4] / p[7]) * 255)
                    surf = pygame.Surface((int(p[6]*2), int(p[6]*2)), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (*p[5], alpha), (int(p[6]), int(p[6])), int(p[6]))
                    window.blit(surf, (int(p[0]-p[6]), int(p[1]-p[6])))
