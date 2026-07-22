import pygame
import random
import os
import math

from scenes.base_scene import BaseScene
from core.models import Player, Deck, Card, Chip
from ui.ui import Button
from ui.animations import Animator
from utils.utils import sc, load_img, draw_alpha_rect, draw_text_centered
from resources import save_progress, t, Assets

def ease_out_bounce(t):
    n1 = 7.5625
    d1 = 2.75

    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375

class BlackjackScene(BaseScene):
    def __init__(self, engine):
        super().__init__(engine)
        self.mode = "singleplayer"
        self.animator = Animator()
        self.players = {}
        self.money = {}
        self.results = {}
        self.placed_chips = []
        self.card_visuals = {}
        self.texture_cache = {}
        self.player_titles = {}
        self.player_nicknames = {}
        self.ready_to_play = set()
        self.game_phase = "betting"
        self.current_turn_index = 0
        self.dealer_hidden = False
        self.start_size = 52
        self.dealer_delay_timer = 0
        self.money_notice_timer = 0
        self.dealer = Player(True)
        self.deck = Deck()

        self.card_w, self.card_h = sc(190), sc(250)
        self.cx, self.cy = int(self.engine.WIDTH // 2), int(self.engine.HEIGHT // 2)
        self.deck_pos = (int(self.engine.WIDTH - sc(200)), int(self.cy - sc(100)))

        self._init_ui()

    def _init_ui(self):
        self.get_btn_rect = pygame.Rect(int(sc(30)), int(self.engine.HEIGHT - sc(150)), int(sc(240)), int(sc(85)))
        self.pass_btn_rect = pygame.Rect(int(sc(270)), int(self.engine.HEIGHT - sc(150)), int(sc(240)), int(sc(85)))
        self.restart_btn_rect = pygame.Rect(0, 0, int(sc(380)), int(sc(100))); self.restart_btn_rect.center = (self.cx, int(self.cy + sc(50)))
        self.exit_game_btn = pygame.Rect(int(self.engine.WIDTH - sc(350)), int(self.engine.HEIGHT - sc(170)), int(sc(300)), int(sc(110)))
        self.enough_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(125))); self.enough_btn.center = (self.cx, int(self.engine.HEIGHT - sc(200)))

        self.mountain_pos = (int(sc(-15)), int(self.cy - Assets.images['all_chips'].get_height() // 2))
        self.w_c = int(sc(120)); self.cw, self.ch = int(self.w_c * 1.7), int(self.w_c * 0.9)
        mc_x, mc_y = int(self.mountain_pos[0] + Assets.images['all_chips'].get_width() // 2), self.cy
        rx, ry = int(Assets.images['all_chips'].get_width() // 2 + self.cw // 2 + sc(-110)), int(Assets.images['all_chips'].get_height() // 2 + self.ch // 2 + sc(15))

        pos = []
        for a in [-80, -48, -16, 16, 48, 80]:
            rad = math.radians(a)
            pos.append((int(mc_x + math.cos(rad) * rx - self.cw // 2), int(mc_y + math.sin(rad) * ry - self.ch // 2)))

        theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"

        self.set_bet_100 = Button(pos[0][0], pos[0][1], self.cw, self.ch, self.engine.WINDOW); self.set_bet_100.set_button_texture(os.path.join("textures", "chips", theme, "100.png"))
        self.set_bet_250 = Button(pos[1][0], pos[1][1], self.cw, self.ch, self.engine.WINDOW); self.set_bet_250.set_button_texture(os.path.join("textures", "chips", theme, "250.png"))
        self.set_bet_500 = Button(pos[2][0], pos[2][1], self.cw, self.ch, self.engine.WINDOW); self.set_bet_500.set_button_texture(os.path.join("textures", "chips", theme, "500.png"))
        self.set_bet_1000 = Button(pos[3][0], pos[3][1], self.cw, self.ch, self.engine.WINDOW); self.set_bet_1000.set_button_texture(os.path.join("textures", "chips", theme, "1000.png"))
        self.set_bet_2500 = Button(pos[4][0], pos[4][1], self.cw, self.ch, self.engine.WINDOW); self.set_bet_2500.set_button_texture(os.path.join("textures", "chips", theme, "2500.png"))
        self.set_bet_10000 = Button(pos[5][0], pos[5][1], self.cw, self.ch, self.engine.WINDOW); self.set_bet_10000.set_button_texture(os.path.join("textures", "chips", theme, "10000.png"))

        self.emoji_btn_size = int(sc(80))
        self.emoji_panel_open = False
        self.emoji_panel_anim_start = 0
        self.active_emojis = {}
        self.emoji_display_time = 3000

    def _show_emoji(self, pid, idx):
        self.active_emojis[pid] = {
            "idx": idx,
            "timer": pygame.time.get_ticks() + self.emoji_display_time,
            "start_time": pygame.time.get_ticks()
        }

    def on_enter(self, mode="singleplayer"):
        self.mode = mode
        self.engine.switch_music(self.engine.current_theme, "game")
        self.reset_game_state(full_reset=True)

        if self.mode in ["singleplayer", "multiplayer_host"]:
            self.engine.my_id = 0
            self.init_player(self.engine.my_id)
            self.player_titles[self.engine.my_id] = self.engine.current_progress.get("current_title", "Новичок")
            self.player_nicknames[self.engine.my_id] = getattr(self.engine, "nickname_text", "Player")

    def init_player(self, pid):
        self.players[pid] = Player(False)
        if pid not in self.money:
            self.money[pid] = self.engine.current_progress.get("money", 10000)

    def reset_game_state(self, full_reset=False):
        for p in self.players.values():
            p.set_bet(0); p.clear_deck()
        self.dealer.clear_deck(); self.placed_chips.clear()
        self.card_visuals.clear()
        self.game_phase = "betting"
        self.current_turn_index = 0
        self.ready_to_play.clear()
        self.results.clear()
        self.dealer_hidden = False
        self.animator.clear()
        self.active_emojis.clear()
        self.emoji_panel_open = False
        self.emoji_panel_anim_start = 0
        if full_reset:
            for pid in list(self.money.keys()):
                self.money[pid] = self.engine.current_progress.get("money", 10000)

    def get_player_center(self, pid):
        sorted_ids = sorted(list(self.players.keys()))
        if pid not in sorted_ids: return self.cx
        idx = sorted_ids.index(pid)
        spacing = int(self.engine.WIDTH // (len(sorted_ids) + 1))
        return spacing * (idx + 1)

    def get_title_color(self, title):
        if title in ["Разработчик", "Developer", "Millionaire", "Миллионер", "Крути-вези!", "I got lucky!"]:
            t_ms = pygame.time.get_ticks()
            glow = int((math.sin(t_ms / 150.0) + 1) / 2 * 100)
            return (255, 255 - glow, 0)
        return (255, 215, 0)

    def _get_cached_texture(self, path, size):
        if self.engine.current_theme == "cyberpunk":
            path = path.replace("cards_wood", "cards_cyberpunk")

        if path not in self.texture_cache:
            if self.engine.current_theme == "cyberpunk":
                raw_img = load_img(path)
                img_w, img_h = raw_img.get_size()
                target_w, target_h = size

                ratio = max(target_w / img_w, target_h / img_h)
                new_w = int(img_w * ratio)
                new_h = int(img_h * ratio)

                scaled_img = pygame.transform.smoothscale(raw_img, (new_w, new_h))
                final_img = pygame.Surface(size, pygame.SRCALPHA)

                offset_x = (target_w - new_w) // 2
                offset_y = (target_h - new_h) // 2
                final_img.blit(scaled_img, (offset_x, offset_y))

                self.texture_cache[path] = final_img
            else:
                self.texture_cache[path] = load_img(path, size)

        return self.texture_cache[path]

    def _deal_animated(self, c, end_x, end_y, on_finish, img=None):
        if img is None:
            img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
        angle = 0 if random.random() < 0.2 else random.randint(-12, 12)
        offset_x = random.randint(int(sc(-10)), int(sc(10)))
        offset_y = random.randint(int(sc(-10)), int(sc(10)))
        self.card_visuals[c] = {"offset": (offset_x, offset_y), "angle": angle}

        target_x = end_x + offset_x
        target_y = end_y + offset_y
        start_angle = angle + random.choice([-180, 180])

        self.animator.add(img=img, start_pos=self.deck_pos, end_pos=(target_x, target_y), on_finish=on_finish, frames=15, start_angle=start_angle, end_angle=angle)

    def _update_achievements(self, res, bet):
        if "titles_unlocked" not in self.engine.current_progress:
            self.engine.current_progress["titles_unlocked"] = ["Новичок"]
        if res in ["win", "blackjack"]:
            self.engine.current_progress["win_count"] = self.engine.current_progress.get("win_count", 0) + 1
            if self.engine.current_progress["win_count"] >= 100:
                self.engine.unlock_title("Коллектор")
            if bet >= 100000:
                self.engine.unlock_title("Крупье на пенсии")
        if res == "blackjack":
            self.engine.current_progress["blackjack_count"] = self.engine.current_progress.get("blackjack_count", 0) + 1
            if self.engine.current_progress["blackjack_count"] >= 21:
                self.engine.unlock_title("Шулер")
        save_progress(self.engine.current_progress)

    def update(self):
        self.animator.update()
        if self.mode == "multiplayer_host" and getattr(self.engine, 'server', None):
            self._handle_server()
        elif self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
            self._handle_client()

        if self.mode in ["singleplayer", "multiplayer_host"]:
            self._update_game_logic()

    def handle_events(self, events):
        mx, my = self.engine.mx, self.engine.my
        px_my = self.get_player_center(self.engine.my_id)

        emoji_btn_rect = pygame.Rect(int(px_my + sc(200)), int(self.engine.HEIGHT - sc(115)), self.emoji_btn_size, self.emoji_btn_size)
        reset_rect = pygame.Rect(int(self.mountain_pos[0] + sc(90)), int(self.mountain_pos[1] - sc(160)), int(sc(300)), int(sc(40)))
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and (event.button == 3 or (event.button == 1 and reset_rect.collidepoint(mx, my))):
                if self.game_phase == "betting" and self.engine.my_id not in self.ready_to_play:
                    current_bet = self.players[self.engine.my_id].get_bet().get_value() if self.engine.my_id in self.players else 0
                    if current_bet > 0:
                        if self.mode == "multiplayer_client":
                            if getattr(self.engine, 'client', None):
                                self.engine.client.send_data({"action": "cancel_bet"})
                        else:
                            Assets.sounds['chip'].play()
                            self.money[self.engine.my_id] += current_bet
                            self.players[self.engine.my_id].get_bet().value = 0
                            self.engine.current_progress["money"] = self.money[self.engine.my_id]
                            save_progress(self.engine.current_progress)
                            self.rebuild_placed_chips()
                            if getattr(self.engine, 'server', None):
                                self.engine.server.broadcast({"action": "cancel_bet", "id": self.engine.my_id})

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.animator.queue: return

                if self.emoji_panel_open:
                    panel_rect = pygame.Rect(int(px_my + sc(200)), int(self.engine.HEIGHT - sc(300)), int(sc(350)), int(sc(180)))
                    if panel_rect.collidepoint(mx, my):
                        rel_x = mx - panel_rect.x - sc(15)
                        rel_y = my - panel_rect.y - sc(15)
                        col = int(rel_x // sc(80))
                        row = int(rel_y // sc(80))
                        if 0 <= col < 4 and 0 <= row < 2:
                            idx = row * 4 + col
                            self._show_emoji(self.engine.my_id, idx)
                            if self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
                                self.engine.client.send_data({"action": "emoji", "idx": idx})
                            elif getattr(self.engine, 'server', None):
                                self.engine.server.broadcast({"action": "emoji", "id": self.engine.my_id, "idx": idx})
                        return
                    else:
                        if not emoji_btn_rect.collidepoint(mx, my):
                            self.emoji_panel_open = False

                if emoji_btn_rect.collidepoint(mx, my):
                    Assets.sounds['enter'].play()
                    self.emoji_panel_open = not self.emoji_panel_open
                    if self.emoji_panel_open:
                        self.emoji_panel_anim_start = pygame.time.get_ticks()
                    return

                has_bet = self.players[self.engine.my_id].get_bet().get_value() > 0 if self.engine.my_id in self.players else False
                can_exit = (self.game_phase == "game_over") or (self.game_phase == "betting" and not has_bet)

                if can_exit and self.exit_game_btn.collidepoint((mx, my)):
                    Assets.sounds['back'].play()
                    if getattr(self.engine, 'server', None): self.engine.server.stop(); self.engine.server = None
                    if getattr(self.engine, 'client', None): self.engine.client.disconnect(); self.engine.client = None
                    if self.engine.my_id in self.money:
                        self.engine.current_progress["money"] = self.money[self.engine.my_id]
                        save_progress(self.engine.current_progress)
                    self.engine.switch_scene("menu")
                    return

                if self.game_phase == "betting":
                    if self.mode == "multiplayer_client" and self.engine.my_id not in self.ready_to_play:
                        if self.players[self.engine.my_id].get_bet().get_value() > 0 and self.enough_btn.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "enough"})
                        elif self.money[self.engine.my_id] >= 100:
                            self._handle_chip_click(mx, my)

                    elif self.mode in ["singleplayer", "multiplayer_host"]:
                        if (self.mode == "multiplayer_host") and len(self.players) < getattr(self.engine, 'target_players', 2): pass
                        elif self.players[self.engine.my_id].get_bet().get_value() > 0 and self.enough_btn.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if self.mode == "singleplayer":
                                self.game_phase = "dealing"
                                self.dealer_hidden = True
                                self.deck.fill_in_order(self.start_size)
                            else:
                                self.ready_to_play.add(self.engine.my_id)
                                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "ready", "id": self.engine.my_id})
                        elif self.engine.my_id not in self.ready_to_play and self.money[self.engine.my_id] >= 100:
                            self._handle_chip_click(mx, my)

                elif self.game_phase == "playing":
                    sorted_ids = sorted(list(self.players.keys()))
                    if self.current_turn_index < len(sorted_ids) and sorted_ids[self.current_turn_index] == self.engine.my_id:
                        if self.get_btn_rect.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if self.mode == "multiplayer_client":
                                if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "get"})
                            else:
                                c = self.deck.erase(random.randint(0, len(self.deck) - 1))
                                p_len = len(self.players[self.engine.my_id].get_deck()) + 1
                                end_x = int(px_my - (self.card_w + (p_len - 1) * sc(40)) // 2 + (p_len - 1) * sc(40))
                                end_y = int(self.engine.HEIGHT - sc(250))
                                self._deal_animated(c, end_x, end_y, lambda card=c: [Assets.sounds['card'].play(), self.players[self.engine.my_id].take_card(card)])
                                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "deal", "target": self.engine.my_id, "val": c.value, "suit": c.suit})

                        if self.pass_btn_rect.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if self.mode == "multiplayer_client":
                                if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "pass"})
                            else:
                                self.current_turn_index += 1
                                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "phase", "phase": "playing", "turn": self.current_turn_index})

                elif self.game_phase == "game_over":
                    if self.restart_btn_rect.collidepoint((mx, my)) and self.engine.my_id not in self.ready_to_play:
                        Assets.sounds['enter'].play()
                        if self.mode == "singleplayer":
                            self.reset_game_state()
                        elif self.mode == "multiplayer_client":
                            if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "restart"})
                        elif self.mode == "multiplayer_host":
                            self.ready_to_play.add(self.engine.my_id)
                            if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "ready", "id": self.engine.my_id})

    def rebuild_placed_chips(self):
        self.placed_chips.clear()
        for pid, p in self.players.items():
            val = p.get_bet().get_value()
            if val <= 0:
                continue
            px = self.get_player_center(pid)

            chips = [10000] * (val // 10000)
            rem = val % 10000

            if rem > 0:
                denoms = [2500, 1000, 500, 250, 100]
                queue = [(rem, [])]
                visited = {rem}
                found = False
                while queue:
                    current_rem, path = queue.pop(0)
                    if current_rem == 0:
                        chips.extend(path)
                        found = True
                        break
                    for d in denoms:
                        if current_rem >= d:
                            next_rem = current_rem - d
                            if next_rem not in visited:
                                visited.add(next_rem)
                                queue.append((next_rem, path + [d]))
                if not found:
                    for d in [2500, 1000, 500, 250, 100]:
                        chips.extend([d] * (rem // d))
                        rem %= d

            chips.reverse()
            theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
            for i, c in enumerate(chips):
                img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{c}.png"), (self.cw, self.ch))
                self.placed_chips.append((img, (int(px - self.w_c // 2), int(self.cy - self.w_c // 2 - i * sc(8)))))

    def _handle_chip_click(self, mx, my):
        current_bet = self.players[self.engine.my_id].get_bet().get_value()
        bet_val = 0
        if self.set_bet_10000.rect.collidepoint(mx, my) and self.money[self.engine.my_id] >= 10000: bet_val = 10000
        elif self.set_bet_2500.rect.collidepoint(mx, my) and self.money[self.engine.my_id] >= 2500: bet_val = 2500
        elif self.set_bet_1000.rect.collidepoint(mx, my) and self.money[self.engine.my_id] >= 1000: bet_val = 1000
        elif self.set_bet_500.rect.collidepoint(mx, my) and self.money[self.engine.my_id] >= 500: bet_val = 500
        elif self.set_bet_250.rect.collidepoint(mx, my) and self.money[self.engine.my_id] >= 250: bet_val = 250
        elif self.set_bet_100.rect.collidepoint(mx, my) and self.money[self.engine.my_id] >= 100: bet_val = 100

        if bet_val > 0:
            if current_bet + bet_val > 100000:
                return
            if self.mode == "multiplayer_client":
                if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "bet", "val": bet_val})
            else:
                Assets.sounds['chip'].play()
                self.players[self.engine.my_id].get_bet().value += bet_val
                self.money[self.engine.my_id] -= bet_val
                self.engine.current_progress["money"] = self.money[self.engine.my_id]
                save_progress(self.engine.current_progress)
                theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{bet_val}.png"), (self.cw, self.ch))
                px = self.get_player_center(self.engine.my_id)
                anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                temp_val = self.players[self.engine.my_id].get_bet().get_value()
                count = sum(temp_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                anim_end = (int(px - self.cw // 2), int(self.cy - self.ch // 2 - max(0, count - 1) * sc(8)))
                self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)
                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "bet", "id": self.engine.my_id, "val": bet_val})

    def _update_game_logic(self):
        if self.game_phase == "betting":
            if self.mode == "multiplayer_host" and len(self.players) > 0 and len(self.ready_to_play) == len(self.players):
                self.game_phase = "dealing"
                self.ready_to_play.clear()
                self.dealer_hidden = True
                self.deck.fill_in_order(self.start_size)

        elif self.game_phase == "dealing" and not self.animator.queue:
            for pid in sorted(list(self.players.keys())):
                c = self.deck.erase(random.randint(0, len(self.deck) - 1))
                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "deal", "target": pid, "val": c.value, "suit": c.suit})
                px = self.get_player_center(pid)
                end_x = int(px - self.card_w // 2)
                if pid == self.engine.my_id:
                    end_y = int(self.engine.HEIGHT - sc(250))
                else:
                    end_y = int(sc(150))
                self._deal_animated(c, end_x, end_y, lambda card=c, p_id=pid: [Assets.sounds['card'].play(), self.players[p_id].take_card(card)])

            c_d1 = self.deck.erase(random.randint(0, len(self.deck) - 1))
            if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "deal", "target": "dealer", "val": c_d1.value, "suit": c_d1.suit, "hidden": True})
            shirt = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])
            self._deal_animated(c_d1, int(self.cx - self.card_w // 2), int(sc(70)), lambda card=c_d1: [Assets.sounds['card'].play(), self.dealer.take_card(card)], img=shirt)

            for pid in sorted(list(self.players.keys())):
                c = self.deck.erase(random.randint(0, len(self.deck) - 1))
                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "deal", "target": pid, "val": c.value, "suit": c.suit})
                px = self.get_player_center(pid)
                end_x = int(px - (self.card_w + sc(40)) // 2 + sc(40))
                if pid == self.engine.my_id:
                    end_y = int(self.engine.HEIGHT - sc(250))
                else:
                    end_y = int(sc(150))
                self._deal_animated(c, end_x, end_y, lambda card=c, p_id=pid: [Assets.sounds['card'].play(), self.players[p_id].take_card(card)])

            c_d2 = self.deck.erase(random.randint(0, len(self.deck) - 1))
            if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "deal", "target": "dealer", "val": c_d2.value, "suit": c_d2.suit, "hidden": False})
            self._deal_animated(c_d2, int(self.cx - (self.card_w + sc(40)) // 2 + sc(40)), int(sc(50)), lambda card=c_d2: [Assets.sounds['card'].play(), self.dealer.take_card(card)])

            self.game_phase = "playing"
            self.current_turn_index = 0
            if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "phase", "phase": "playing", "turn": self.current_turn_index})

        elif self.game_phase == "playing" and not self.animator.queue:
            sorted_ids = sorted(list(self.players.keys()))
            if self.current_turn_index < len(sorted_ids):
                active_id = sorted_ids[self.current_turn_index]
                p_val = self.players[active_id].check_value_in_hand()
                if p_val >= 21:
                    self.current_turn_index += 1
                    if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "phase", "phase": "playing", "turn": self.current_turn_index})
            else:
                self.game_phase = "dealer_turn"
                if self.dealer_hidden:
                    self.dealer_hidden = False
                    if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "reveal"})

        elif self.game_phase == "dealer_turn" and not self.animator.queue:
            d_val = self.dealer.check_value_in_hand()
            if d_val < 17 and any(self.players[p].check_value_in_hand() <= 21 for p in self.players):
                if self.dealer_delay_timer == 0:
                    self.dealer_delay_timer = pygame.time.get_ticks() + 600
                elif pygame.time.get_ticks() >= self.dealer_delay_timer:
                    self.dealer_delay_timer = 0
                    c = self.deck.erase(random.randint(0, len(self.deck) - 1))
                    d_len = len(self.dealer.get_deck()) + 1
                    end_x = int(self.cx - (self.card_w + (d_len - 1) * sc(40)) // 2 + (d_len - 1) * sc(40))
                    self._deal_animated(c, end_x, int(sc(70)), lambda card=c: [Assets.sounds['card'].play(), self.dealer.take_card(card)])
                    if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "deal", "target": "dealer", "val": c.value, "suit": c.suit, "hidden": False})
            else:
                for pid, p in self.players.items():
                    p_val = p.check_value_in_hand()
                    if p_val > 21: self.results[pid] = "lose"
                    elif d_val > 21: self.results[pid] = "win"
                    elif p_val == d_val: self.results[pid] = "push"
                    elif p_val > d_val: self.results[pid] = "win"
                    else: self.results[pid] = "lose"
                    if self.results[pid] == "win" and p_val == 21 and len(p.get_deck()) == 2:
                        self.results[pid] = "blackjack"

                for pid, res in self.results.items():
                    bet = self.players[pid].get_bet().get_value()
                    if res == "blackjack": self.money[pid] += int(bet * 2.5)
                    elif res == "win": self.money[pid] += bet * 2
                    elif res == "push": self.money[pid] += bet

                if self.engine.my_id in self.money:
                    self.engine.current_progress["money"] = self.money[self.engine.my_id]
                    save_progress(self.engine.current_progress)

                self.game_phase = "game_over"
                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "game_over", "results": self.results})

        elif self.game_phase == "game_over" and not self.animator.queue:
            if not getattr(self, "stats_saved_for_this_round", False):
                if self.engine.my_id in self.results:
                    self._update_achievements(self.results[self.engine.my_id], self.players[self.engine.my_id].get_bet().get_value())
                self.stats_saved_for_this_round = True

            if self.mode == "multiplayer_host" and len(self.players) > 0 and len(self.ready_to_play) == len(self.players):
                self.reset_game_state()
                self.stats_saved_for_this_round = False
                self.engine.server.broadcast({"action": "phase", "phase": "betting"})

    def _handle_server(self):
        while not self.engine.server.message_queue.empty():
            msg_obj = self.engine.server.message_queue.get()
            data = msg_obj["data"]
            action = data.get("action")
            cid = data.get("client_id")

            if action == "internal_player_joined":
                self.init_player(cid)
                profiles = {p: {"title": self.player_titles.get(p, "Новичок"), "nickname": self.player_nicknames.get(p, f"Player {p+1}")} for p in self.players}
                self.engine.server.broadcast({"action": "profiles_sync", "profiles": profiles})
                continue
            elif action == "internal_player_left":
                self.players.pop(cid, None)
                self.money.pop(cid, None)
                self.ready_to_play.discard(cid)
                continue

            if action == "set_profile":
                self.player_titles[cid] = data.get("title", "Новичок")
                self.player_nicknames[cid] = data.get("nickname", "Player")
                profiles = {p: {"title": self.player_titles.get(p, "Новичок"), "nickname": self.player_nicknames.get(p, f"Player {p+1}")} for p in self.players}
                self.engine.server.broadcast({"action": "profiles_sync", "profiles": profiles})
            elif action == "bet" and self.game_phase == "betting":
                bet_val = data.get("val")
                current_bet = self.players[cid].get_bet().get_value()
                if self.money.get(cid, 0) >= bet_val and cid not in self.ready_to_play and current_bet + bet_val <= 100000:
                    Assets.sounds['chip'].play()
                    self.players[cid].get_bet().value += bet_val
                    self.money[cid] -= bet_val
                    if cid == self.engine.my_id:
                        self.engine.current_progress["money"] = self.money[self.engine.my_id]
                        save_progress(self.engine.current_progress)
                    theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                    c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{bet_val}.png"), (self.cw, self.ch))
                    px = self.get_player_center(cid)
                    anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                    temp_val = self.players[cid].get_bet().get_value()
                    count = sum(temp_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                    anim_end = (int(px - self.cw // 2), int(self.cy - self.ch // 2 - max(0, count - 1) * sc(8)))
                    self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)
                    self.engine.server.broadcast({"action": "bet", "id": cid, "val": bet_val})
            elif action == "cancel_bet" and self.game_phase == "betting":
                current_bet = self.players[cid].get_bet().get_value()
                if current_bet > 0 and cid not in self.ready_to_play:
                    Assets.sounds['chip'].play()
                    self.money[cid] += current_bet
                    self.players[cid].get_bet().value = 0
                    if cid == self.engine.my_id:
                        self.engine.current_progress["money"] = self.money[self.engine.my_id]
                        save_progress(self.engine.current_progress)
                    self.rebuild_placed_chips()
                    self.engine.server.broadcast({"action": "cancel_bet", "id": cid})
            elif action == "enough" and self.game_phase == "betting":
                if self.players[cid].get_bet().get_value() > 0:
                    Assets.sounds['enter'].play()
                    self.ready_to_play.add(cid)
                    self.engine.server.broadcast({"action": "ready", "id": cid})
            elif action == "get" and self.game_phase == "playing":
                sorted_ids = sorted(list(self.players.keys()))
                if self.current_turn_index < len(sorted_ids) and sorted_ids[self.current_turn_index] == cid:
                    c = self.deck.erase(random.randint(0, len(self.deck) - 1))
                    p_len = len(self.players[cid].get_deck()) + 1
                    px = self.get_player_center(cid)
                    end_x = int(px - (self.card_w + (p_len - 1) * sc(40)) // 2 + (p_len - 1) * sc(40))
                    if cid == self.engine.my_id:
                        end_y = int(self.engine.HEIGHT - sc(250))
                    else:
                        end_y = int(sc(150))
                    self._deal_animated(c, end_x, end_y, lambda card=c, pid=cid: [Assets.sounds['card'].play(), self.players[pid].take_card(card)])
                    self.engine.server.broadcast({"action": "deal", "target": cid, "val": c.value, "suit": c.suit})
            elif action == "pass" and self.game_phase == "playing":
                sorted_ids = sorted(list(self.players.keys()))
                if self.current_turn_index < len(sorted_ids) and sorted_ids[self.current_turn_index] == cid:
                    self.current_turn_index += 1
                    self.engine.server.broadcast({"action": "phase", "phase": "playing", "turn": self.current_turn_index})
            elif action == "restart" and self.game_phase == "game_over":
                self.ready_to_play.add(cid)
                self.engine.server.broadcast({"action": "ready", "id": cid})
            elif action == "emoji":
                idx = data.get("idx")
                self._show_emoji(cid, idx)
                self.engine.server.broadcast({"action": "emoji", "id": cid, "idx": idx})

    def _handle_client(self):
        while not self.engine.client.message_queue.empty():
            msg_obj = self.engine.client.message_queue.get()
            action = msg_obj.get("action")

            if action == "init":
                self.engine.my_id = msg_obj["id"]
                self.engine.target_players = msg_obj.get("target_players", 2)
                self.players.clear(); self.money.clear(); self.results.clear()
                for pid in msg_obj["players"]: self.init_player(pid)
                self.init_player(self.engine.my_id)
                self.engine.client.send_data({"action": "set_profile", "title": self.engine.current_progress.get("current_title", "Новичок"), "nickname": getattr(self.engine, "nickname_text", "Player")})
            elif action == "profiles_sync":
                for p_key, prof in msg_obj.get("profiles", {}).items():
                    try:
                        pid = int(p_key)
                        self.player_titles[pid] = prof["title"]
                        self.player_nicknames[pid] = prof["nickname"]
                    except ValueError:
                        pass
            elif action == "player_joined":
                self.init_player(msg_obj["id"])
            elif action == "player_left":
                self.players.pop(msg_obj["id"], None)
                self.money.pop(msg_obj["id"], None)
            elif action == "pity_money":
                self.money[msg_obj["id"]] = 2500
                if msg_obj["id"] == self.engine.my_id:
                    self.engine.current_progress["money"] = 2500
                    self.engine.unlock_title("Главный спонсор")
                    save_progress(self.engine.current_progress)
            elif action == "bet":
                cid = msg_obj["id"]
                bet_val = msg_obj["val"]
                Assets.sounds['chip'].play()
                self.players[cid].get_bet().value += bet_val
                self.money[cid] -= bet_val
                if cid == self.engine.my_id:
                    self.engine.current_progress["money"] = self.money[self.engine.my_id]
                    save_progress(self.engine.current_progress)
                theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{bet_val}.png"), (self.cw, self.ch))
                px = self.get_player_center(cid)
                anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                temp_val = self.players[cid].get_bet().get_value()
                count = sum(temp_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                anim_end = (int(px - self.cw // 2), int(self.cy - self.ch // 2 - max(0, count - 1) * sc(8)))
                self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)
            elif action == "cancel_bet":
                cid = msg_obj["id"]
                current_bet = self.players[cid].get_bet().get_value()
                Assets.sounds['chip'].play()
                self.money[cid] += current_bet
                self.players[cid].get_bet().value = 0
                if cid == self.engine.my_id:
                    self.engine.current_progress["money"] = self.money[self.engine.my_id]
                    save_progress(self.engine.current_progress)
                self.rebuild_placed_chips()
            elif action == "ready":
                self.ready_to_play.add(msg_obj["id"])
            elif action == "deal":
                target = msg_obj["target"]
                val = msg_obj["val"]
                suit = msg_obj.get("suit", "hearts")
                hidden = msg_obj.get("hidden", False)
                c = Card(val, suit)
                if target == "dealer":
                    d_len = len(self.dealer.get_deck()) + 1
                    end_x = int(self.cx - (self.card_w + (d_len - 1) * sc(40)) // 2 + (d_len - 1) * sc(40))
                    shirt = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])
                    img = shirt if hidden else None
                    if hidden: self.dealer_hidden = True
                    self._deal_animated(c, end_x, int(sc(70)), lambda card=c: [Assets.sounds['card'].play(), self.dealer.take_card(card)], img=img)
                else:
                    p_len = len(self.players[target].get_deck()) + 1
                    px = self.get_player_center(target)
                    end_x = int(px - (self.card_w + (p_len - 1) * sc(40)) // 2 + (p_len - 1) * sc(40))
                    if target == self.engine.my_id:
                        end_y = int(self.engine.HEIGHT - sc(250))
                    else:
                        end_y = int(sc(150))
                    self._deal_animated(c, end_x, end_y, lambda card=c, pid=target: [Assets.sounds['card'].play(), self.players[pid].take_card(card)])
            elif action == "reveal":
                self.dealer_hidden = False
            elif action == "phase":
                self.game_phase = msg_obj["phase"]
                if "turn" in msg_obj: self.current_turn_index = msg_obj["turn"]
                if self.game_phase == "betting":
                    self.reset_game_state()
                    self.stats_saved_for_this_round = False
            elif action == "game_over":
                self.results = {int(k): v for k, v in msg_obj["results"].items()}
                self.game_phase = "game_over"
                if self.engine.my_id in self.results:
                    res = self.results[self.engine.my_id]
                    bet = self.players[self.engine.my_id].get_bet().get_value()
                    if res == "blackjack": self.money[self.engine.my_id] += int(bet * 2.5)
                    elif res == "win": self.money[self.engine.my_id] += bet * 2
                    elif res == "push": self.money[self.engine.my_id] += bet
                    self.engine.current_progress["money"] = self.money[self.engine.my_id]
                    self._update_achievements(res, bet)
            elif action == "emoji":
                self._show_emoji(msg_obj["id"], msg_obj["idx"])

    def draw(self, window):
        mx, my = self.engine.mx, self.engine.my
        window.blit(self.engine.current_bg, (0, 0))

        current_time = pygame.time.get_ticks()
        expired = [pid for pid, data in self.active_emojis.items() if current_time > data["timer"]]
        for pid in expired:
            del self.active_emojis[pid]

        shirt = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])
        for i in range(5): window.blit(shirt, (self.deck_pos[0] - i * 2, self.deck_pos[1] - i * 2))

        sorted_ids = sorted(list(self.players.keys()))
        for pid in sorted_ids:
            p = self.players[pid]; px = self.get_player_center(pid); p_len = len(p.get_deck())

            if p_len > 0:
                start_x = int(px - (self.card_w + (p_len - 1) * sc(40)) // 2)
                for i, c in enumerate(p.get_deck()):
                    img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
                    visuals = self.card_visuals.get(c, {"offset": (0, 0), "angle": 0})
                    target_x = int(start_x + i * sc(40)) + visuals["offset"][0]
                    if pid == self.engine.my_id:
                        target_y = int(self.engine.HEIGHT - sc(360)) + visuals["offset"][1]
                    else:
                        target_y = int(sc(100)) + visuals["offset"][1]

                    if visuals["angle"] != 0:
                        img = pygame.transform.rotozoom(img, visuals["angle"], 1.0)
                        rect = img.get_rect(center=(target_x + self.card_w//2, target_y + self.card_h//2))
                        window.blit(img, rect.topleft)
                    else:
                        window.blit(img, (target_x, target_y))

            p_text = self.engine.nickname_text if pid == self.engine.my_id else self.player_nicknames.get(pid, f"Player {pid+1}" if self.mode != "singleplayer" else "Bot")
            p_title = self.player_titles.get(pid, "Крупье на пенсии") if pid != self.engine.my_id else self.engine.current_progress.get("current_title", "Новичок")

            if pid == self.engine.my_id:
                text_y = int(self.engine.HEIGHT - sc(95))
            else:
                text_y = int(sc(360))

            draw_text_centered(window, f"[{t(p_title)}]", Assets.fonts['text30'], self.get_title_color(p_title), (0, 0, 0), (int(px - sc(100)), text_y, int(sc(200)), int(sc(30))), int(sc(2)))
            draw_text_centered(window, p_text, Assets.fonts['text30'], (255,255,255), (0,0,0), (int(px - sc(100)), text_y + int(sc(35)), int(sc(200)), int(sc(30))), int(sc(2)))
            draw_text_centered(window, f"{t('Bet:')} {p.get_bet().get_value()}", Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (int(px - sc(100)), text_y + int(sc(65)), int(sc(200)), int(sc(30))), int(sc(2)))

            p_val = p.check_value_in_hand()
            if p_len > 0:
                val_y = int(self.engine.HEIGHT - sc(420)) if pid == self.engine.my_id else int(sc(40))
                draw_alpha_rect(window, (0, 0, 0, 160), (int(px - sc(40)), val_y, int(sc(80)), int(sc(40))), (218, 165, 32), int(sc(2)), int(sc(10)))
                draw_text_centered(window, f"{p_val}", Assets.fonts['text30'], (255,255,255), (0,0,0), (int(px - sc(40)), val_y, int(sc(80)), int(sc(40))))

            if pid in self.active_emojis:
                emo_data = self.active_emojis[pid]
                idx = emo_data["idx"]
                if idx < len(Assets.emojis):
                    emoji_img = Assets.emojis[idx]

                    time_alive = current_time - emo_data["start_time"]
                    anim_duration = 600
                    if time_alive <= anim_duration:
                        t_anim = time_alive / anim_duration
                        scale = ease_out_bounce(t_anim)
                        scaled_w = int(emoji_img.get_width() * scale)
                        scaled_h = int(emoji_img.get_height() * scale)
                        if scaled_w > 0 and scaled_h > 0:
                            current_img = pygame.transform.smoothscale(emoji_img, (scaled_w, scaled_h))
                        else:
                            current_img = pygame.Surface((1, 1), pygame.SRCALPHA)
                    else:
                        current_img = emoji_img

                    if pid == self.engine.my_id:
                        emoji_x = int(px - sc(250))
                        emoji_y = int(self.engine.HEIGHT - sc(300))
                    else:
                        emoji_x = int(px + sc(150))
                        emoji_y = int(sc(380))

                    img_rect = current_img.get_rect(center=(emoji_x, emoji_y))
                    window.blit(current_img, img_rect.topleft)

            if pid == self.engine.my_id:
                emoji_btn_rect = pygame.Rect(int(px + sc(200)), int(self.engine.HEIGHT - sc(115)), self.emoji_btn_size, self.emoji_btn_size)

                draw_alpha_rect(window, (0, 0, 0, 160), emoji_btn_rect, (218, 165, 32), int(sc(2)), int(sc(10)))
                window.blit(Assets.images['logo_emoji'], emoji_btn_rect.topleft)

                if self.emoji_panel_open:
                    panel_rect = pygame.Rect(int(px + sc(200)), int(self.engine.HEIGHT - sc(300)), int(sc(350)), int(sc(180)))

                    anim_progress = min(1.0, (current_time - self.emoji_panel_anim_start) / 250.0)
                    t_anim = 1 - (1 - anim_progress) ** 5

                    anim_h = int(panel_rect.height * t_anim)
                    anim_rect = pygame.Rect(panel_rect.x, panel_rect.bottom - anim_h, panel_rect.width, anim_h)

                    if anim_h > 0:
                        draw_alpha_rect(window, (0, 0, 0, 160), anim_rect, (218, 165, 32), int(sc(2)), int(sc(10)))

                        old_clip = window.get_clip()
                        window.set_clip(anim_rect)

                        for i, emoji_img in enumerate(Assets.emojis):
                            col = i % 4
                            row = i // 4
                            small_emoji = pygame.transform.smoothscale(emoji_img, (int(sc(70)), int(sc(70))))

                            ex = panel_rect.x + sc(15) + col * sc(80)
                            ey = panel_rect.y + sc(15) + row * sc(80)
                            window.blit(small_emoji, (int(ex), int(ey)))

                            if pygame.Rect(ex, ey, sc(70), sc(70)).collidepoint(mx, my):
                                draw_alpha_rect(window, (255, 255, 255, 100), (int(ex - sc(5)), int(ey - sc(5)), int(sc(80)), int(sc(80))), (0, 0, 0), 1, int(sc(5)))

                        window.set_clip(old_clip)

        d_len = len(self.dealer.get_deck())
        if d_len > 0:
            start_x = int(self.cx - (self.card_w + (d_len - 1) * sc(40)) // 2)
            for i, c in enumerate(self.dealer.get_deck()):
                visuals = self.card_visuals.get(c, {"offset": (0, 0), "angle": 0})
                target_x = int(start_x + i * sc(40)) + visuals["offset"][0]
                target_y = int(sc(70)) + visuals["offset"][1]

                img = shirt if i == 0 and self.dealer_hidden else self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
                if visuals["angle"] != 0:
                    img = pygame.transform.rotozoom(img, visuals["angle"], 1.0)
                    rect = img.get_rect(center=(target_x + self.card_w//2, target_y + self.card_h//2))
                    window.blit(img, rect.topleft)
                else:
                    window.blit(img, (target_x, target_y))

            vis_val = sum(c.get_value() for c in self.dealer.get_deck()[1:]) if self.dealer_hidden and d_len > 1 else self.dealer.check_value_in_hand()
            if vis_val > 0:
                draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(40)), int(sc(10)), int(sc(80)), int(sc(40))), (218, 165, 32), int(sc(2)), int(sc(10)))
                draw_text_centered(window, f"{vis_val}", Assets.fonts['text30'], (255,255,255), (0,0,0), (int(self.cx - sc(40)), int(sc(10)), int(sc(80)), int(sc(40))))

        for chip_img, chip_pos in self.placed_chips: window.blit(chip_img, chip_pos)
        self.animator.draw(window)

        if self.engine.my_id in self.players:
            draw_alpha_rect(window, (0, 0, 0, 160), (int(sc(20)), int(sc(20)), int(sc(350)), int(sc(50))), (218, 165, 32), int(sc(2)), int(sc(10)))
            draw_text_centered(window, f"{t('Money:')} {self.money[self.engine.my_id]}$", Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (int(sc(20)), int(sc(20)), int(sc(350)), int(sc(50))))

            if self.game_phase == "betting":
                if (self.mode == "multiplayer_host" or self.mode == "multiplayer_client") and len(self.players) < getattr(self.engine, 'target_players', 2):
                    draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))), (218, 165, 32), int(sc(2)), int(sc(15)))
                    draw_text_centered(window, t("Waiting for players..."), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))))
                elif self.engine.my_id not in self.ready_to_play:
                    if self.players[self.engine.my_id].get_bet().get_value() == 0:
                        draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(200)), int(self.cy - sc(30)), int(sc(400)), int(sc(60))), (218, 165, 32), int(sc(2)), int(sc(15)))
                        draw_text_centered(window, t("Choose your bet!"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(200)), int(self.cy - sc(30)), int(sc(400)), int(sc(60))))

                    window.blit(Assets.images['all_chips'], self.mountain_pos)

                    if self.money[self.engine.my_id] >= 100: self.set_bet_100.draw()
                    if self.money[self.engine.my_id] >= 250: self.set_bet_250.draw()
                    if self.money[self.engine.my_id] >= 500: self.set_bet_500.draw()
                    if self.money[self.engine.my_id] >= 1000: self.set_bet_1000.draw()
                    if self.money[self.engine.my_id] >= 2500: self.set_bet_2500.draw()
                    if self.money[self.engine.my_id] >= 10000: self.set_bet_10000.draw()

                    if self.players[self.engine.my_id].get_bet().get_value() > 0:
                        reset_rect = pygame.Rect(int(self.mountain_pos[0] + sc(90)), int(self.mountain_pos[1] - sc(160)), int(sc(300)), int(sc(40)))
                        h_res = reset_rect.collidepoint(mx, my)
                        b_color = (255, 100, 100) if h_res else (200, 50, 50)
                        draw_alpha_rect(window, (0, 0, 0, 160), reset_rect, b_color, int(sc(3)) if h_res else int(sc(2)), int(sc(10)))
                        draw_text_centered(window, t("Reset Bet"), Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), reset_rect)

                        h_en = self.enough_btn.collidepoint(mx, my)
                        b_col = (255, 215, 0) if h_en else (218, 165, 32)
                        draw_alpha_rect(window, (0, 0, 0, 160), self.enough_btn, b_col, int(sc(3)) if h_en else int(sc(2)), int(sc(15)))
                        draw_text_centered(window, t("Enough"), Assets.fonts['f60'] if h_en else Assets.fonts['f50'], "gradient" if h_en else (255, 255, 255), (0, 0, 0), self.enough_btn)
                else:
                    if self.mode != "singleplayer":
                        draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))), (218, 165, 32), int(sc(2)), int(sc(15)))
                        draw_text_centered(window, t("Waiting for others..."), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))))

            elif self.game_phase == "playing":
                if self.current_turn_index < len(sorted_ids):
                    active_id = sorted_ids[self.current_turn_index]
                    if active_id == self.engine.my_id:
                        h_g = self.get_btn_rect.collidepoint(mx, my)
                        b_col = (255, 215, 0) if h_g else (218, 165, 32)
                        draw_alpha_rect(window, (0, 0, 0, 160), self.get_btn_rect, b_col, int(sc(3)) if h_g else int(sc(2)), int(sc(15)))
                        draw_text_centered(window, t("Get"), Assets.fonts['f60'] if h_g else Assets.fonts['f50'], "gradient" if h_g else (255, 255, 255), (0, 0, 0), self.get_btn_rect)

                        h_p = self.pass_btn_rect.collidepoint(mx, my)
                        b_col = (255, 215, 0) if h_p else (218, 165, 32)
                        draw_alpha_rect(window, (0, 0, 0, 160), self.pass_btn_rect, b_col, int(sc(3)) if h_p else int(sc(2)), int(sc(15)))
                        draw_text_centered(window, t("Pass"), Assets.fonts['f60'] if h_p else Assets.fonts['f50'], "gradient" if h_p else (255, 255, 255), (0, 0, 0), self.pass_btn_rect)
                    else:
                        if self.mode != "singleplayer":
                            draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))), (218, 165, 32), int(sc(2)), int(sc(15)))
                            draw_text_centered(window, f"{t('Player ')}{active_id + 1}{t('''s Turn''')}", Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))))

        if self.engine.my_id in self.money and self.game_phase == "betting" and self.money[self.engine.my_id] < 100 and self.players[self.engine.my_id].get_bet().get_value() == 0:
            if self.money_notice_timer == 0: self.money_notice_timer = pygame.time.get_ticks() + 2500
            lose_rect = pygame.Rect(0, 0, int(sc(700)), int(sc(180))); lose_rect.center = (self.cx, self.cy - sc(300))
            draw_alpha_rect(window, (0, 0, 0, 160), lose_rect, (218, 165, 32), int(sc(2)), int(sc(15)))
            draw_text_centered(window, t("You lose all your money!"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (lose_rect.x, lose_rect.y, lose_rect.width, int(sc(60))), 0)
            draw_text_centered(window, t("So, to prevent you from leaving,"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (lose_rect.x, int(lose_rect.y + sc(60)), lose_rect.width, int(sc(60))), 0)
            draw_text_centered(window, t("we gave you some money."), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (lose_rect.x, int(lose_rect.y + sc(120)), lose_rect.width, int(sc(60))), 0)

            if pygame.time.get_ticks() >= self.money_notice_timer:
                self.money[self.engine.my_id] = 2500
                self.engine.current_progress["money"] = 2500
                self.engine.unlock_title("Главный спонсор")
                save_progress(self.engine.current_progress)
                self.money_notice_timer = 0
                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "pity_money", "id": self.engine.my_id})
                elif getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "pity_money", "id": self.engine.my_id})

        if self.game_phase == "game_over" and not self.animator.queue and self.engine.my_id in self.results:
            res = self.results[self.engine.my_id]
            msg = "Blackjack!" if res == "blackjack" else ("You win!" if res == "win" else ("You lose!" if res == "lose" else "Push!"))
            w = int(sc(480)) if msg == "Blackjack!" else (int(sc(580)) if res == "win" else (int(sc(650)) if res == "lose" else int(sc(300))))
            draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - w//2), int(self.cy - sc(100)), w, int(sc(80))), (218, 165, 32), int(sc(2)), int(sc(15)))
            draw_text_centered(window, t(msg), Assets.fonts['f60'], (255, 255, 255), (0, 0, 0), (int(self.cx - w // 2), int(self.cy - sc(100)), w, int(sc(80))), 0)

            if self.mode == "singleplayer" or self.engine.my_id not in self.ready_to_play:
                hovered = self.restart_btn_rect.collidepoint(mx, my)
                b_col = (255, 215, 0) if hovered else (218, 165, 32)
                draw_alpha_rect(window, (0, 0, 0, 160), self.restart_btn_rect, b_col, int(sc(3)) if hovered else int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Restart"), Assets.fonts['f60'] if hovered else Assets.fonts['f50'], "gradient" if hovered else (255, 255, 255), (0, 0, 0), self.restart_btn_rect, 0)
            else:
                draw_alpha_rect(window, (0, 0, 0, 160), self.restart_btn_rect, (218, 165, 32), int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Waiting for players..."), Assets.fonts['text40'], (255, 255, 255), (0, 0, 0), self.restart_btn_rect, 0)

        has_bet = self.players[self.engine.my_id].get_bet().get_value() > 0 if self.engine.my_id in self.players else False
        can_exit = (self.game_phase == "game_over") or (self.game_phase == "betting" and not has_bet)

        if can_exit:
            h_e = self.exit_game_btn.collidepoint(mx, my)
            b_col = (255, 215, 0) if h_e else (218, 165, 32)
            draw_alpha_rect(window, (0, 0, 0, 160), self.exit_game_btn, b_col, int(sc(3)) if h_e else int(sc(2)), int(sc(15)))
            draw_text_centered(window, t("Exit"), Assets.fonts['f60'] if h_e else Assets.fonts['f50'], "gradient" if h_e else (255, 255, 255), (0, 0, 0), self.exit_game_btn)