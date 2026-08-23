import pygame
import random
import os
import math

from scenes.base_scene import BaseScene
from core.models import Player, Deck, Card
from ui.ui import Button
from ui.animations import Animator
from utils.utils import sc, load_img, draw_alpha_rect, draw_text_centered
from resources import save_progress, t, Assets

def cv(card):
    v = card.get_value()
    return 14 if v == 1 else v

def can_beat(attack_card, defend_card, trump_suit):
    av = cv(attack_card)
    dv = cv(defend_card)
    if defend_card.suit == attack_card.suit:
        return dv > av
    if defend_card.suit == trump_suit:
        return True
    return False

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

class FoolScene(BaseScene):
    def __init__(self, engine):
        super().__init__(engine)
        self.mode = "singleplayer"
        self.animator = Animator()
        self.players = {}
        self.money = {}
        self.player_titles = {}
        self.player_nicknames = {}
        self.placed_chips = []
        self.card_visuals = {}
        self.ready_to_play = set()
        self.game_phase = "betting"
        self.deck = Deck()
        self.trump_card = None
        self.table_cards = []
        self.current_turn_pid = None
        self.attacker_pid = None
        self.defender_pid = None
        self.taking = False
        self.fool_id = None

        self.card_w, self.card_h = sc(190), sc(250)
        self.cx, self.cy = int(self.engine.WIDTH // 2), int(self.engine.HEIGHT // 2)
        self.deck_pos = (int(self.engine.WIDTH - sc(200)), int(self.cy - sc(100)))

        self.texture_cache = {}
        self.bot_timer = 0
        self.hovered_card = None
        self.shuffle_count = 0
        self.deal_queue = []

        self.emoji_btn_size = int(sc(80))
        self.emoji_panel_open = False
        self.emoji_panel_anim_start = 0
        self.active_emojis = {}
        self.emoji_display_time = 3000

        self._init_ui()

    def _init_ui(self):
        self.take_btn = pygame.Rect(int(sc(30)), int(self.engine.HEIGHT - sc(150)), int(sc(260)), int(sc(90)))
        self.pass_btn = pygame.Rect(int(sc(270)), int(self.engine.HEIGHT - sc(150)), int(sc(260)), int(sc(90)))
        self.restart_btn = pygame.Rect(0, 0, int(sc(380)), int(sc(100))); self.restart_btn.center = (self.cx, int(self.cy + sc(80)))
        self.exit_btn = pygame.Rect(int(self.engine.WIDTH - sc(350)), int(self.engine.HEIGHT - sc(170)), int(sc(300)), int(sc(110)))
        self.enough_btn = pygame.Rect(0, 0, int(sc(350)), int(sc(125))); self.enough_btn.center = (self.cx, int(self.engine.HEIGHT - sc(100)))

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

        if self.engine.current_theme == "cyberpunk":
            self.w_c = int(sc(150))
        else:
            self.w_c = int(sc(120))

        self.cw, self.ch = int(self.w_c * 1.7), int(self.w_c * 0.9)

    def get_title_color(self, title):
        if title in ["Разработчик", "Developer", "Millionaire", "Миллионер", "Крути-вези!", "I got lucky!"]:
            t_ms = pygame.time.get_ticks()
            glow = int((math.sin(t_ms / 150.0) + 1) / 2 * 100)
            return (255, 255 - glow, 0)
        return (255, 215, 0)

    def _show_emoji(self, pid, idx):
        self.active_emojis[pid] = {
            "idx": idx,
            "timer": pygame.time.get_ticks() + self.emoji_display_time,
            "start_time": pygame.time.get_ticks()
        }

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

    def on_enter(self, mode="singleplayer"):
        self.mode = mode
        self.engine.switch_music(self.engine.current_theme, "game")
        self.reset_game_state(full_reset=True)

        theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
        self.set_bet_100.set_button_texture(os.path.join("textures", "chips", theme, "100.png"))
        self.set_bet_250.set_button_texture(os.path.join("textures", "chips", theme, "250.png"))
        self.set_bet_500.set_button_texture(os.path.join("textures", "chips", theme, "500.png"))
        self.set_bet_1000.set_button_texture(os.path.join("textures", "chips", theme, "1000.png"))
        self.set_bet_2500.set_button_texture(os.path.join("textures", "chips", theme, "2500.png"))
        self.set_bet_10000.set_button_texture(os.path.join("textures", "chips", theme, "10000.png"))

        if self.mode in ["singleplayer", "multiplayer_host"]:
            self.engine.my_id = 0
            self.init_player(self.engine.my_id)
            self.player_titles[self.engine.my_id] = self.engine.current_progress.get("current_title", "Новичок")
            self.player_nicknames[self.engine.my_id] = getattr(self.engine, "nickname_text", "Player")
            if self.mode == "singleplayer":
                self.init_player(1)
                self.player_titles[1] = "Крупье на пенсии"
                self.player_nicknames[1] = "Bot"

    def init_player(self, pid):
        self.players[pid] = Player(False)
        if pid not in self.money:
            self.money[pid] = self.engine.current_progress.get("money", 10000)

    def reset_game_state(self, full_reset=False):
        for p in self.players.values():
            p.set_bet(0); p.clear_deck()
        self.deck.clear_deck()
        self.table_cards.clear()
        self.ready_to_play.clear()
        self.placed_chips.clear()
        self.card_visuals.clear()
        self.trump_card = None
        self.fool_id = None
        self.game_phase = "betting"
        self.animator.clear()
        self.taking = False
        self.bot_timer = 0
        self.attacker_pid = None
        self.defender_pid = None
        self.current_turn_pid = None
        self.active_emojis.clear()
        self.emoji_panel_open = False
        if full_reset:
            self.players.clear()
            self.money.clear()
            self.player_titles.clear()
            self.player_nicknames.clear()

    def start_game(self):
        self.deck.clear_deck()
        for suit in ["clubs", "diamonds", "hearts", "spades"]:
            for val in [6, 7, 8, 9, 10, 11, 12, 13, 1]:
                self.deck.add_card_by_value(val, suit)
        random.shuffle(self.deck.cards)

        self.start_shuffling()

    def start_shuffling(self):
        self.game_phase = "shuffling"
        self.shuffle_count = 0
        if self.mode == "multiplayer_host" and self.engine.server:
            self.engine.server.broadcast({"action": "shuffle_anim"})
        self.do_shuffle_anim()

    def do_shuffle_anim(self):
        shirt = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])
        start_pos = self.deck_pos
        end_pos = (self.deck_pos[0] - sc(80), self.deck_pos[1])
        if self.shuffle_count % 2 != 0:
            start_pos, end_pos = end_pos, start_pos
        self.animator.add(img=shirt, start_pos=start_pos, end_pos=end_pos, on_finish=self.on_shuffle_step_done, frames=6)

    def on_shuffle_step_done(self):
        self.shuffle_count += 1
        if self.shuffle_count >= 6:
            if self.mode != "multiplayer_client":
                self.start_dealing()
        else:
            Assets.sounds['card'].play()
            self.do_shuffle_anim()

    def start_dealing(self):
        self.game_phase = "dealing"
        self.deal_queue = []
        for _ in range(6):
            for pid in sorted(self.players.keys()):
                self.deal_queue.append(pid)
        self.deal_queue.append("trump")
        self.deal_next_card()

    def deal_next_card(self):
        if not self.deal_queue:
            if self.mode == "multiplayer_client":
                return

            if self.attacker_pid is None:
                first_attacker = None
                lowest_trump = 15
                for pid, p in self.players.items():
                    for c in p.get_deck().cards:
                        if c.suit == self.trump_card.suit:
                            val = cv(c)
                            if val < lowest_trump:
                                lowest_trump = val
                                first_attacker = pid

                if first_attacker is None:
                    first_attacker = random.choice(list(self.players.keys()))

                self.attacker_pid = first_attacker
                self.defender_pid = self.get_next_player(self.attacker_pid)

            self.current_turn_pid = self.attacker_pid
            self.game_phase = "attack"
            self.bot_timer = pygame.time.get_ticks() + 1000
            if getattr(self.engine, 'server', None):
                self._broadcast_state()
            return

        target = self.deal_queue.pop(0)
        if target == "trump":
            c = self.deck.cards[0]
            self.trump_card = c
            if self.mode == "multiplayer_host" and self.engine.server:
                self.engine.server.broadcast({"action": "deal_anim", "target": "trump", "val": c.value, "suit": c.suit})
            img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
            self._deal_animated(c, self.deck_pos[0] - sc(50), self.deck_pos[1] + sc(20), self.deal_next_card, img=img)
        else:
            c = self.deck.erase(-1)
            if self.mode == "multiplayer_host" and self.engine.server:
                self.engine.server.broadcast({"action": "deal_anim", "target": target, "val": c.value, "suit": c.suit})
            px, py = self.get_player_hand_pos(target)
            self._deal_animated(c, px, py, lambda card=c, pid=target: [Assets.sounds['card'].play(), self.players[pid].take_card(card) if pid in self.players else None, self.deal_next_card()])

    def get_player_hand_pos(self, pid):
        if pid == self.engine.my_id:
            return self.cx, int(self.engine.HEIGHT - sc(250))
        else:
            return self.get_player_center(pid), int(sc(100))

    def get_player_center(self, pid):
        if pid == self.engine.my_id:
            return self.cx
        opponents = [p for p in sorted(list(self.players.keys())) if p != self.engine.my_id]
        if pid not in opponents:
            return self.cx
        idx = opponents.index(pid)
        spacing = int(self.engine.WIDTH // (len(opponents) + 1))
        return spacing * (idx + 1)

    def update(self):
        self.animator.update()
        if self.mode == "multiplayer_host" and getattr(self.engine, 'server', None):
            self._handle_server()
        elif self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
            self._handle_client()

        if self.mode in ["singleplayer", "multiplayer_host"]:
            self._update_game_logic()

    def _update_game_logic(self):
        if self.game_phase == "betting":
            if self.mode == "singleplayer":
                if len(self.ready_to_play) == 1:
                    self.players[1].get_bet().value = self.players[0].get_bet().get_value()
                    self.start_game()
            elif self.mode == "multiplayer_host":
                if len(self.players) > 1 and len(self.ready_to_play) == len(self.players):
                    self.start_game()
        elif self.mode == "singleplayer" and self.current_turn_pid == 1 and not self.animator.queue:
            self.bot_play()
        elif self.game_phase == "game_over":
            if self.mode == "multiplayer_host" and len(self.players) > 0 and len(self.ready_to_play) == len(self.players):
                self.reset_game_state()
                self._broadcast_state()

    def bot_play(self):
        if pygame.time.get_ticks() < self.bot_timer:
            return

        bot_hand = self.players[1].get_deck().cards
        if not bot_hand:
            if self.game_phase in ["attack", "take_add"]:
                self.action_pass(1)
            return

        if self.game_phase == "attack":
            valid = self.get_valid_attack_cards(bot_hand)
            defended_count = len([c for c in self.table_cards if c['defend']])
            def_hand_size = len(self.players[self.defender_pid].get_deck().cards) if self.defender_pid in self.players else 0
            max_attacks = min(6, def_hand_size + defended_count)

            if valid and len(self.table_cards) < max_attacks:
                valid.sort(key=lambda c: (c.suit == self.trump_card.suit, cv(c)))
                self.action_play_card(1, valid[0])
            else:
                if self.table_cards:
                    self.action_pass(1)

        elif self.game_phase == "defend":
            unbeaten = [c for c in self.table_cards if not c['defend']]
            if unbeaten:
                target = unbeaten[0]['attack']
                valid = self.get_valid_defend_cards(bot_hand, target)
                if valid:
                    valid.sort(key=lambda c: (c.suit == self.trump_card.suit, cv(c)))
                    self.action_beat_card(1, valid[0])
                else:
                    self.action_take(1)

        elif self.game_phase == "take_add":
            valid = self.get_valid_attack_cards(bot_hand)
            defended_count = len([c for c in self.table_cards if c['defend']])
            def_hand_size = len(self.players[self.defender_pid].get_deck().cards) if self.defender_pid in self.players else 0
            max_attacks = min(6, def_hand_size + defended_count)

            if valid and len(self.table_cards) < max_attacks:
                valid.sort(key=lambda c: (c.suit == self.trump_card.suit, cv(c)))
                self.action_play_card(1, valid[0])
            else:
                self.action_pass(1)

    def get_valid_attack_cards(self, hand):
        if not self.table_cards:
            return hand
        ranks_on_table = set()
        for pair in self.table_cards:
            ranks_on_table.add(cv(pair['attack']))
            if pair['defend']:
                ranks_on_table.add(cv(pair['defend']))
        return [c for c in hand if cv(c) in ranks_on_table]

    def get_valid_defend_cards(self, hand, attack_card):
        return [c for c in hand if can_beat(attack_card, c, self.trump_card.suit)]

    def rebuild_placed_chips(self):
        self.placed_chips.clear()
        total_val = sum(p.get_bet().get_value() for p in self.players.values())
        if total_val <= 0:
            return
        px = self.deck_pos[0] - sc(250)

        chips = [10000] * (total_val // 10000)
        rem = total_val % 10000

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
            self.placed_chips.append((img, (int(px), int(self.deck_pos[1] + sc(30) - i * sc(8)))))

    def _handle_chip_click(self, mx, my):
        current_bet = self.players[self.engine.my_id].get_bet().get_value()
        bet_val = 0
        if self.set_bet_10000.rect.collidepoint(mx, my) and self.money.get(self.engine.my_id, 0) >= 10000: bet_val = 10000
        elif self.set_bet_2500.rect.collidepoint(mx, my) and self.money.get(self.engine.my_id, 0) >= 2500: bet_val = 2500
        elif self.set_bet_1000.rect.collidepoint(mx, my) and self.money.get(self.engine.my_id, 0) >= 1000: bet_val = 1000
        elif self.set_bet_500.rect.collidepoint(mx, my) and self.money.get(self.engine.my_id, 0) >= 500: bet_val = 500
        elif self.set_bet_250.rect.collidepoint(mx, my) and self.money.get(self.engine.my_id, 0) >= 250: bet_val = 250
        elif self.set_bet_100.rect.collidepoint(mx, my) and self.money.get(self.engine.my_id, 0) >= 100: bet_val = 100

        if bet_val > 0:
            if current_bet + bet_val > 100000:
                return
            if self.mode == "multiplayer_client":
                if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "bet", "val": bet_val})
            else:
                Assets.sounds['chip'].play()
                self.players[self.engine.my_id].get_bet().value += bet_val
                self.money[self.engine.my_id] -= bet_val
                self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                save_progress(self.engine.current_progress)
                theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{bet_val}.png"), (self.cw, self.ch))
                px = self.deck_pos[0] - sc(250)
                anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                total_val = sum(p.get_bet().get_value() for p in self.players.values())
                count = sum(total_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                anim_end = (int(px - self.cw // 2), int(self.cy - self.ch // 2 - max(0, count - 1) * sc(8)))
                self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)
                if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "bet", "id": self.engine.my_id, "val": bet_val})

    def handle_events(self, events):
        mx, my = self.engine.mx, self.engine.my

        emoji_btn_rect = pygame.Rect(int(self.cx + sc(280)), int(self.engine.HEIGHT - sc(200)), self.emoji_btn_size, self.emoji_btn_size)
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
                            self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                            save_progress(self.engine.current_progress)
                            self.rebuild_placed_chips()
                            if getattr(self.engine, 'server', None):
                                self.engine.server.broadcast({"action": "cancel_bet", "id": self.engine.my_id})

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.animator.queue and self.game_phase != "betting": return

                if self.emoji_panel_open:
                    panel_rect = pygame.Rect(int(self.cx + sc(280)), int(self.engine.HEIGHT - sc(390)), int(sc(350)), int(sc(180)))
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

                if self.exit_btn.collidepoint((mx, my)):
                    Assets.sounds['back'].play()
                    if getattr(self.engine, 'server', None): self.engine.server.stop(); self.engine.server = None
                    if getattr(self.engine, 'client', None): self.engine.client.disconnect(); self.engine.client = None
                    if self.engine.my_id in self.money:
                        self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                        save_progress(self.engine.current_progress)
                    self.engine.switch_scene("menu")
                    return

                if self.game_phase == "betting":
                    if self.mode == "multiplayer_client" and self.engine.my_id not in self.ready_to_play:
                        if self.players[self.engine.my_id].get_bet().get_value() > 0 and self.enough_btn.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "enough"})
                        elif self.money.get(self.engine.my_id, 0) >= 100:
                            self._handle_chip_click(mx, my)

                    elif self.mode in ["singleplayer", "multiplayer_host"]:
                        if (self.mode == "multiplayer_host") and len(self.players) < getattr(self.engine, 'target_players', 2): pass
                        elif self.players[self.engine.my_id].get_bet().get_value() > 0 and self.enough_btn.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            self.ready_to_play.add(self.engine.my_id)
                            if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "ready", "id": self.engine.my_id})
                        elif self.engine.my_id not in self.ready_to_play and self.money.get(self.engine.my_id, 0) >= 100:
                            self._handle_chip_click(mx, my)

                elif self.game_phase == "game_over":
                    if self.restart_btn.collidepoint((mx, my)) and self.engine.my_id not in self.ready_to_play:
                        Assets.sounds['enter'].play()
                        if self.mode == "singleplayer":
                            self.reset_game_state()
                        elif self.mode == "multiplayer_client":
                            if getattr(self.engine, 'client', None): self.engine.client.send_data({"action": "restart"})
                        elif self.mode == "multiplayer_host":
                            self.ready_to_play.add(self.engine.my_id)
                            if getattr(self.engine, 'server', None):
                                self.engine.server.broadcast({"action": "ready", "id": self.engine.my_id})

                elif self.current_turn_pid == self.engine.my_id:
                    if self.game_phase in ["attack", "take_add"]:
                        if self.table_cards and self.pass_btn.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if self.mode == "multiplayer_client":
                                getattr(self.engine, 'client', None).send_data({"action": "pass"})
                            else:
                                self.action_pass(self.engine.my_id)
                            return

                    if self.game_phase == "defend":
                        if self.take_btn.collidepoint((mx, my)):
                            Assets.sounds['enter'].play()
                            if self.mode == "multiplayer_client":
                                getattr(self.engine, 'client', None).send_data({"action": "take"})
                            else:
                                self.action_take(self.engine.my_id)
                            return

                    my_hand = self.players[self.engine.my_id].get_deck().cards
                    card_spacing = min(sc(40), sc(320) / max(1, len(my_hand)))
                    shift_x = max(0, (len(my_hand) - 6) * sc(18))
                    for i, c in reversed(list(enumerate(my_hand))):
                        cx = int(self.cx - shift_x - (len(my_hand) * card_spacing) // 2 + i * card_spacing)
                        cy = int(self.engine.HEIGHT - sc(250))
                        if self.hovered_card == c:
                            cy -= sc(20)
                        rect = pygame.Rect(cx, cy, self.card_w, self.card_h)
                        if rect.collidepoint(mx, my):
                            self.try_play_card(c)
                            break

            elif event.type == pygame.MOUSEMOTION:
                if self.game_phase not in ["waiting", "game_over", "betting", "shuffling", "dealing"]:
                    my_hand = self.players[self.engine.my_id].get_deck().cards if self.engine.my_id in self.players else []
                    self.hovered_card = None
                    card_spacing = min(sc(40), sc(320) / max(1, len(my_hand)))
                    shift_x = max(0, (len(my_hand) - 6) * sc(18))
                    for i, c in reversed(list(enumerate(my_hand))):
                        cx = int(self.cx - shift_x - (len(my_hand) * card_spacing) // 2 + i * card_spacing)
                        cy = int(self.engine.HEIGHT - sc(250))
                        rect = pygame.Rect(cx, cy, self.card_w, self.card_h)
                        if rect.collidepoint(mx, my):
                            self.hovered_card = c
                            break

    def try_play_card(self, card):
        hand = self.players[self.engine.my_id].get_deck().cards
        if self.game_phase in ["attack", "take_add"]:
            valid = self.get_valid_attack_cards(hand)
            defended_count = len([c for c in self.table_cards if c['defend']])
            def_hand_size = len(self.players[self.defender_pid].get_deck().cards) if self.defender_pid in self.players else 0
            max_attacks = min(6, def_hand_size + defended_count)

            if card in valid and len(self.table_cards) < max_attacks:
                if self.mode == "multiplayer_client":
                    getattr(self.engine, 'client', None).send_data({"action": "play_card", "val": card.value, "suit": card.suit})
                else:
                    self.action_play_card(self.engine.my_id, card)
        elif self.game_phase == "defend":
            unbeaten = [c for c in self.table_cards if not c['defend']]
            if unbeaten:
                target = unbeaten[0]['attack']
                valid = self.get_valid_defend_cards(hand, target)
                if card in valid:
                    if self.mode == "multiplayer_client":
                        getattr(self.engine, 'client', None).send_data({"action": "beat_card", "val": card.value, "suit": card.suit})
                    else:
                        self.action_beat_card(self.engine.my_id, card)

    def action_play_card(self, pid, card):
        if pid not in self.players: return
        if card in self.players[pid].get_deck().cards:
            self.players[pid].get_deck().cards.remove(card)

        if self.mode == "multiplayer_host" and getattr(self.engine, 'server', None):
            self.engine.server.broadcast({"action": "play_card_anim", "pid": pid, "val": card.value, "suit": card.suit})

        idx = len(self.table_cards)
        target_x = self.cx - sc(200) + idx * sc(85)
        target_y = self.cy - sc(100)

        c_img = self._get_cached_texture(card.get_texture_path(), (self.card_w, self.card_h))
        px, py = self.get_player_hand_pos(pid)

        def finish():
            if not any(p['attack'].value == card.value and p['attack'].suit == card.suit for p in self.table_cards):
                self.table_cards.append({"attack": card, "defend": None})
            Assets.sounds['card'].play()
            if self.mode != "multiplayer_client":
                if self.taking:
                    self.game_phase = "take_add"
                    self.current_turn_pid = self.attacker_pid
                else:
                    self.game_phase = "defend"
                    self.current_turn_pid = self.defender_pid
                self.bot_timer = pygame.time.get_ticks() + random.randint(800, 1500)
                if getattr(self.engine, 'server', None): self._broadcast_state()

        self.animator.add(c_img, (px, py), (target_x, target_y), finish, frames=10)

    def action_beat_card(self, pid, card):
        if pid not in self.players: return
        if card in self.players[pid].get_deck().cards:
            self.players[pid].get_deck().cards.remove(card)

        if self.mode == "multiplayer_host" and getattr(self.engine, 'server', None):
            self.engine.server.broadcast({"action": "beat_card_anim", "pid": pid, "val": card.value, "suit": card.suit})

        target_idx = 0
        for i, pair in enumerate(self.table_cards):
            if not pair['defend']:
                target_idx = i
                break

        target_x = self.cx - sc(200) + target_idx * sc(85) + sc(20)
        target_y = self.cy - sc(80)

        c_img = self._get_cached_texture(card.get_texture_path(), (self.card_w, self.card_h))
        px, py = self.get_player_hand_pos(pid)

        def finish():
            if target_idx < len(self.table_cards) and self.table_cards[target_idx]['defend'] is None:
                self.table_cards[target_idx]['defend'] = card
            Assets.sounds['card'].play()

            if self.mode != "multiplayer_client":
                if len(self.table_cards) == 6 or len(self.players[pid].get_deck().cards) == 0:
                    self.do_bito()
                else:
                    self.game_phase = "attack"
                    self.current_turn_pid = self.attacker_pid
                    self.bot_timer = pygame.time.get_ticks() + random.randint(800, 1500)
                    if getattr(self.engine, 'server', None): self._broadcast_state()

        self.animator.add(c_img, (px, py), (target_x, target_y), finish, frames=10)

    def action_take(self, pid):
        self.taking = True
        self.game_phase = "take_add"
        self.current_turn_pid = self.attacker_pid
        self.bot_timer = pygame.time.get_ticks() + random.randint(800, 1500)
        if getattr(self.engine, 'server', None): self._broadcast_state()

    def action_pass(self, pid):
        if self.taking:
            self.do_take()
        else:
            self.do_bito()

    def do_take(self):
        for pair in self.table_cards:
            if self.defender_pid in self.players:
                self.players[self.defender_pid].take_card(pair['attack'])
                if pair['defend']:
                    self.players[self.defender_pid].take_card(pair['defend'])
        self.table_cards.clear()
        self.taking = False

        self.deal_queue = []
        order = [self.attacker_pid, self.defender_pid]
        for pid in order:
            if pid in self.players:
                while len(self.players[pid].get_deck().cards) + self.deal_queue.count(pid) < 6 and (len(self.deck) - self.deal_queue.count("trump") - len(self.deal_queue)) > 0:
                    self.deal_queue.append(pid)

        self.attacker_pid = self.get_next_player(self.defender_pid)
        self.defender_pid = self.get_next_player(self.attacker_pid)
        self.current_turn_pid = self.attacker_pid

        if self.deal_queue:
            self.game_phase = "dealing"
            self.deal_next_card()
        else:
            self.game_phase = "attack"
            self.bot_timer = pygame.time.get_ticks() + random.randint(800, 1500)
            self.check_game_over()
            if getattr(self.engine, 'server', None): self._broadcast_state()

    def do_bito(self):
        self.table_cards.clear()
        self.deal_queue = []
        order = [self.attacker_pid, self.defender_pid]
        for pid in order:
            if pid in self.players:
                while len(self.players[pid].get_deck().cards) + self.deal_queue.count(pid) < 6 and (len(self.deck) - self.deal_queue.count("trump") - len(self.deal_queue)) > 0:
                    self.deal_queue.append(pid)

        self.attacker_pid = self.defender_pid
        self.defender_pid = self.get_next_player(self.attacker_pid)
        self.current_turn_pid = self.attacker_pid

        if self.deal_queue:
            self.game_phase = "dealing"
            self.deal_next_card()
        else:
            self.game_phase = "attack"
            self.bot_timer = pygame.time.get_ticks() + random.randint(800, 1500)
            self.check_game_over()
            if getattr(self.engine, 'server', None): self._broadcast_state()

    def get_next_player(self, pid):
        sorted_ids = sorted(list(self.players.keys()))
        if not sorted_ids: return pid
        if pid not in sorted_ids: return sorted_ids[0]
        idx = sorted_ids.index(pid)
        return sorted_ids[(idx + 1) % len(sorted_ids)]

    def check_game_over(self):
        if self.game_phase == "game_over":
            return

        if self.mode != "singleplayer" and len(self.players) <= 1 and self.game_phase != "betting":
            self.game_phase = "game_over"
            self.ready_to_play.clear()
            self.fool_id = None
            if self.engine.my_id in self.players:
                bet = self.players[self.engine.my_id].get_bet().get_value()
                self.money[self.engine.my_id] = self.money.get(self.engine.my_id, 0) + bet * 2
                self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                save_progress(self.engine.current_progress)
            return

        active_players = [pid for pid, p in self.players.items() if len(p.get_deck().cards) > 0]
        if len(self.deck) == 0 and len(active_players) <= 1:
            self.game_phase = "game_over"
            self.ready_to_play.clear()
            self.fool_id = active_players[0] if active_players else None
            if self.fool_id != self.engine.my_id:
                bet = self.players[self.engine.my_id].get_bet().get_value() if self.engine.my_id in self.players else 0
                self.money[self.engine.my_id] = self.money.get(self.engine.my_id, 0) + bet * 2
                self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                save_progress(self.engine.current_progress)

    def draw(self, window):
        mx, my = self.engine.mx, self.engine.my
        window.blit(self.engine.current_bg, (0, 0))

        current_time = pygame.time.get_ticks()
        expired = [pid for pid, data in self.active_emojis.items() if current_time > data["timer"]]
        for pid in expired:
            del self.active_emojis[pid]

        shirt = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])

        if self.trump_card and len(self.deck.cards) > 0:
            trump_img = self._get_cached_texture(self.trump_card.get_texture_path(), (self.card_w, self.card_h))
            visuals = self.card_visuals.get(self.trump_card, {"offset": (0, 0), "angle": 0})
            if visuals["angle"] != 0:
                trump_rotated = pygame.transform.rotozoom(trump_img, 90 + visuals["angle"], 1.0)
                rect = trump_rotated.get_rect(center=(self.deck_pos[0] - sc(50) + self.card_w//2, self.deck_pos[1] + sc(20) + self.card_h//2))
                window.blit(trump_rotated, rect.topleft)
            else:
                trump_rotated = pygame.transform.rotate(trump_img, 90)
                window.blit(trump_rotated, (self.deck_pos[0] - sc(50), self.deck_pos[1] + sc(20)))

        if len(self.deck) > 0 and self.game_phase not in ["betting"]:
            for i in range(min(5, len(self.deck))):
                window.blit(shirt, (self.deck_pos[0] - i * 2, self.deck_pos[1] - i * 2))
            draw_text_centered(window, str(len(self.deck)), Assets.fonts['text50'], (255,255,255), (0,0,0), (self.deck_pos[0], self.deck_pos[1] - sc(60), self.card_w, sc(30)))

        for i, pair in enumerate(self.table_cards):
            ax = self.cx - sc(200) + i * sc(85)
            ay = self.cy - sc(100)
            a_img = self._get_cached_texture(pair['attack'].get_texture_path(), (self.card_w, self.card_h))
            window.blit(a_img, (ax, ay))

            if pair['defend']:
                d_img = self._get_cached_texture(pair['defend'].get_texture_path(), (self.card_w, self.card_h))
                window.blit(d_img, (ax + sc(20), ay + sc(20)))

        for pid, p in self.players.items():
            hand = p.get_deck().cards

            if pid == self.engine.my_id:
                px = self.cx
            else:
                px = self.get_player_center(pid)

            if pid == self.engine.my_id:
                p_text = getattr(self.engine, "nickname_text", "Player")
            elif self.mode == "singleplayer":
                p_text = "Bot"
            else:
                p_text = self.player_nicknames.get(pid, f"{t('Player ')}{pid + 1}")

            p_title = self.player_titles.get(pid, "Новичок") if pid != self.engine.my_id else self.engine.current_progress.get("current_title", "Новичок")

            if pid == self.engine.my_id:
                text_y_start = int(self.engine.HEIGHT - sc(360))
            else:
                text_y_start = int(sc(280))

            draw_text_centered(window, f"[{t(p_title)}]", Assets.fonts['text30'], self.get_title_color(p_title), (0, 0, 0), (int(px - sc(100)), text_y_start, int(sc(200)), int(sc(30))), int(sc(2)))
            draw_text_centered(window, p_text, Assets.fonts['text30'], (255,255,255), (0,0,0), (int(px - sc(100)), text_y_start + int(sc(35)), int(sc(200)), int(sc(30))), int(sc(2)))
            draw_text_centered(window, f"{t('Bet:')} {p.get_bet().get_value()}", Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (int(px - sc(100)), text_y_start + int(sc(70)), int(sc(200)), int(sc(30))), int(sc(2)))

            if getattr(self.engine, 'server', None):
                ping_val = self.engine.server.pings.get(pid, 0)
            elif getattr(self.engine, 'client', None):
                ping_val = self.engine.client.pings.get(pid, 0)
            else:
                ping_val = 0

            if ping_val < 50:
                p_col, p_bars = (0, 255, 0), 4
            elif ping_val < 150:
                p_col, p_bars = (173, 255, 47), 3
            elif ping_val < 300:
                p_col, p_bars = (255, 165, 0), 2
            else:
                p_col, p_bars = (255, 0, 0), 1

            ping_x = int(px + sc(110))
            ping_y = int(text_y_start + sc(35))

            for b in range(4):
                bw = int(sc(4))
                bh = int(sc(6 + b * 4))
                bx = ping_x + b * int(sc(6))
                by = ping_y - bh
                c = p_col if b < p_bars else (100, 100, 100)
                pygame.draw.rect(window, c, (bx, by, bw, bh))
            
            if pid == self.engine.my_id:
                card_spacing = min(sc(40), sc(320) / max(1, len(hand)))
                shift_x = max(0, (len(hand) - 6) * sc(18))
                for i, c in enumerate(hand):
                    cx = int(px - shift_x - (len(hand) * card_spacing) // 2 + i * card_spacing)
                    cy = int(self.engine.HEIGHT - sc(250))
                    if self.hovered_card == c and not self.animator.queue:
                        cy -= sc(20)
                    img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
                    window.blit(img, (cx, cy))
            else:
                for i in range(len(hand)):
                    cx = int(px - (len(hand) * sc(40)) // 2 + i * sc(40))
                    cy = int(sc(20))
                    window.blit(shirt, (cx, cy))

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

                    emoji_x = int(px - sc(270))
                    emoji_y = int(self.engine.HEIGHT - sc(320)) if pid == self.engine.my_id else int(sc(100))
                    img_rect = current_img.get_rect(center=(emoji_x, emoji_y))
                    window.blit(current_img, img_rect.topleft)

        for chip_img, chip_pos in self.placed_chips: window.blit(chip_img, chip_pos)
        self.animator.draw(window)

        if self.engine.my_id in self.players:
            draw_alpha_rect(window, (0, 0, 0, 160), (int(sc(20)), int(sc(20)), int(sc(350)), int(sc(50))), (218, 165, 32), int(sc(2)), int(sc(10)))
            draw_text_centered(window, f"{t('Money:')} {self.money.get(self.engine.my_id, 0)}$", Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), (int(sc(20)), int(sc(20)), int(sc(350)), int(sc(50))))

            emoji_btn_rect = pygame.Rect(int(self.cx + sc(280)), int(self.engine.HEIGHT - sc(200)), self.emoji_btn_size, self.emoji_btn_size)
            draw_alpha_rect(window, (0, 0, 0, 160), emoji_btn_rect, (218, 165, 32), int(sc(2)), int(sc(10)))
            window.blit(Assets.images['logo_emoji'], emoji_btn_rect.topleft)

            if self.emoji_panel_open:
                panel_rect = pygame.Rect(int(self.cx + sc(280)), int(self.engine.HEIGHT - sc(390)), int(sc(350)), int(sc(180)))
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

        if self.game_phase == "betting":
            if (self.mode == "multiplayer_host" or self.mode == "multiplayer_client") and len(self.players) < getattr(self.engine, 'target_players', 2):
                draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))), (218, 165, 32), int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Waiting for players..."), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))))
            elif self.engine.my_id not in self.ready_to_play:
                if self.players[self.engine.my_id].get_bet().get_value() == 0:
                    draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(200)), int(self.cy - sc(30)), int(sc(400)), int(sc(70))), (218, 165, 32), int(sc(2)), int(sc(15)))
                    draw_text_centered(window, t("Choose your bet!"), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(200)), int(self.cy - sc(30)), int(sc(400)), int(sc(60))))

                window.blit(Assets.images['all_chips'], self.mountain_pos)

                if self.money.get(self.engine.my_id, 0) >= 100: self.set_bet_100.draw()
                if self.money.get(self.engine.my_id, 0) >= 250: self.set_bet_250.draw()
                if self.money.get(self.engine.my_id, 0) >= 500: self.set_bet_500.draw()
                if self.money.get(self.engine.my_id, 0) >= 1000: self.set_bet_1000.draw()
                if self.money.get(self.engine.my_id, 0) >= 2500: self.set_bet_2500.draw()
                if self.money.get(self.engine.my_id, 0) >= 10000: self.set_bet_10000.draw()

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

        elif self.game_phase == "game_over":
            res_text = t("You win!") if getattr(self, 'fool_id', None) != self.engine.my_id else t("You're a fool!")
            text_w = max(int(sc(580)), Assets.fonts['f60'].size(res_text)[0] + int(sc(70)))

            res_rect = pygame.Rect(0, 0, text_w, int(sc(100)))
            res_rect.center = (self.cx, int(self.cy - sc(60)))

            draw_alpha_rect(window, (0, 0, 0, 160), res_rect, (218, 165, 32), int(sc(2)), int(sc(15)))
            draw_text_centered(window, res_text, Assets.fonts['f60'], (255, 255, 255), (0, 0, 0), res_rect)

            if self.mode == "singleplayer" or self.engine.my_id not in self.ready_to_play:
                h = self.restart_btn.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), self.restart_btn, (255, 215, 0) if h else (218, 165, 32), int(sc(3)) if h else int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Restart"), Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (255, 255, 255), (0, 0, 0), self.restart_btn)
            else:
                draw_alpha_rect(window, (0, 0, 0, 160), self.restart_btn, (218, 165, 32), int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Waiting for players..."), Assets.fonts['text40'], (255, 255, 255), (0, 0, 0), self.restart_btn)

        elif self.game_phase in ["attack", "defend", "take_add"]:
            if self.current_turn_pid == self.engine.my_id:
                if self.game_phase == "defend":
                    h = self.take_btn.collidepoint(mx, my)
                    draw_alpha_rect(window, (0, 0, 0, 160), self.take_btn, (255, 215, 0) if h else (218, 165, 32), int(sc(3)) if h else int(sc(2)), int(sc(15)))
                    draw_text_centered(window, t("Take"), Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (255, 255, 255), (0, 0, 0), self.take_btn)
                elif self.game_phase in ["attack", "take_add"] and self.table_cards:
                    h = self.pass_btn.collidepoint(mx, my)
                    draw_alpha_rect(window, (0, 0, 0, 160), self.pass_btn, (255, 215, 0) if h else (218, 165, 32), int(sc(3)) if h else int(sc(2)), int(sc(15)))
                    draw_text_centered(window, t("Done"), Assets.fonts['f60'] if h else Assets.fonts['f50'], "gradient" if h else (255, 255, 255), (0, 0, 0), self.pass_btn)
            else:
                msg = t("Opponent's turn")
                draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(200)), int(self.cy), sc(420), int(sc(70))), (218, 165, 32), int(sc(2)), int(sc(15)))
                draw_text_centered(window, msg, Assets.fonts['f40'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(200)), int(self.cy), sc(420), int(sc(70))))

        has_bet = self.players[self.engine.my_id].get_bet().get_value() > 0 if self.engine.my_id in self.players else False
        can_exit = (self.game_phase == "game_over") or (self.game_phase == "betting" and not has_bet)

        if can_exit:
            h_e = self.exit_btn.collidepoint(mx, my)
            draw_alpha_rect(window, (0, 0, 0, 160), self.exit_btn, (255, 215, 0) if h_e else (218, 165, 32), int(sc(3)) if h_e else int(sc(2)), int(sc(15)))
            draw_text_centered(window, t("Exit"), Assets.fonts['f60'] if h_e else Assets.fonts['f50'], "gradient" if h_e else (255, 255, 255), (0, 0, 0), self.exit_btn)

    def _broadcast_state(self):
        state = {
            "action": "sync",
            "phase": self.game_phase,
            "turn": self.current_turn_pid,
            "attacker": self.attacker_pid,
            "defender": self.defender_pid,
            "taking": self.taking,
            "deck_count": len(self.deck),
            "trump": {"val": self.trump_card.value, "suit": self.trump_card.suit} if self.trump_card else None,
            "table": [
                {
                    "attack": {"val": p['attack'].value, "suit": p['attack'].suit},
                    "defend": {"val": p['defend'].value, "suit": p['defend'].suit} if p['defend'] else None
                } for p in self.table_cards
            ],
            "fool_id": getattr(self, 'fool_id', None)
        }
        self.engine.server.broadcast(state)
        for pid, p in self.players.items():
            self.engine.server.broadcast({"action": "hand", "pid": pid, "cards": [{"val": c.value, "suit": c.suit} for c in p.get_deck().cards]})

    def _handle_server(self):
        while not self.engine.server.message_queue.empty():
            msg = self.engine.server.message_queue.get()
            data = msg["data"]
            action = data.get("action")
            cid = data.get("client_id")

            if action == "internal_player_joined":
                self.init_player(cid)
                profiles = {pid: {"title": self.player_titles.get(pid, "Новичок"), "nickname": self.player_nicknames.get(pid, f"Player {pid+1}")} for pid in self.players}
                self.engine.server.broadcast({"action": "profiles_sync", "profiles": profiles})
                self._broadcast_state()
                continue
            elif action == "internal_player_left":
                is_turn = (self.current_turn_pid == cid)

                self.players.pop(cid, None)
                self.money.pop(cid, None)
                self.ready_to_play.discard(cid)
                self.player_titles.pop(cid, None)
                self.player_nicknames.pop(cid, None)

                if self.game_phase in ["attack", "defend", "take_add"]:
                    if is_turn:
                        if self.taking:
                            self.do_take()
                        else:
                            self.do_bito()

                    if self.attacker_pid not in self.players:
                        self.attacker_pid = self.get_next_player(self.attacker_pid)
                    if self.defender_pid not in self.players or self.defender_pid == self.attacker_pid:
                        self.defender_pid = self.get_next_player(self.attacker_pid)
                    if self.current_turn_pid not in self.players:
                        self.current_turn_pid = self.attacker_pid if self.game_phase in ["attack", "take_add"] else self.defender_pid

                self.rebuild_placed_chips()
                self.check_game_over()
                if getattr(self.engine, 'server', None):
                    self._broadcast_state()
                continue

            if action == "set_profile":
                self.player_titles[cid] = data.get("title", "Новичок")
                self.player_nicknames[cid] = data.get("nickname", "Player")
                if "money" in data:
                    self.money[cid] = data["money"]
                profiles = {p: {"title": self.player_titles.get(p, "Новичок"), "nickname": self.player_nicknames.get(p, f"Player {p+1}")} for p in self.players}
                self.engine.server.broadcast({"action": "profiles_sync", "profiles": profiles})
            elif action == "bet" and self.game_phase == "betting":
                if cid in self.players:
                    parsed_val = data.get("val")
                    current_bet = self.players[cid].get_bet().get_value()
                    if self.money.get(cid, 0) >= parsed_val and cid not in self.ready_to_play and current_bet + parsed_val <= 100000:
                        Assets.sounds['chip'].play()
                        self.players[cid].get_bet().value += parsed_val
                        self.money[cid] -= parsed_val
                        if cid == self.engine.my_id:
                            self.engine.current_progress["money"] = self.money[self.engine.my_id]
                            save_progress(self.engine.current_progress)
                        theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                        c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{parsed_val}.png"), (self.cw, self.ch))
                        px = self.deck_pos[0] - sc(250)
                        anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                        total_val = sum(p.get_bet().get_value() for p in self.players.values())
                        count = sum(total_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                        anim_end = (int(px - self.cw // 2), int(self.cy - self.ch // 2 - max(0, count - 1) * sc(8)))
                        self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)
                        self.engine.server.broadcast({"action": "bet", "id": cid, "val": parsed_val})
            elif action == "cancel_bet" and self.game_phase == "betting":
                if cid in self.players:
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
                if cid in self.players and self.players[cid].get_bet().get_value() > 0:
                    Assets.sounds['enter'].play()
                    self.ready_to_play.add(cid)
                    self.engine.server.broadcast({"action": "ready", "id": cid})
            elif action == "play_card":
                if not self.animator.queue and cid in self.players and self.current_turn_pid == cid and self.game_phase in ["attack", "take_add"]:
                    c = next((card for card in self.players[cid].get_deck().cards if card.value == data['val'] and card.suit == data['suit']), None)
                    if c:
                        valid = self.get_valid_attack_cards(self.players[cid].get_deck().cards)
                        defended_count = len([p for p in self.table_cards if p['defend']])
                        def_hand_size = len(self.players[self.defender_pid].get_deck().cards) if self.defender_pid in self.players else 0
                        max_attacks = min(6, def_hand_size + defended_count)
                        if c in valid and len(self.table_cards) < max_attacks:
                            self.action_play_card(cid, c)
            elif action == "beat_card":
                if not self.animator.queue and cid in self.players and self.current_turn_pid == cid and self.game_phase == "defend":
                    c = next((card for card in self.players[cid].get_deck().cards if card.value == data['val'] and card.suit == data['suit']), None)
                    if c:
                        unbeaten = [p for p in self.table_cards if not p['defend']]
                        if unbeaten:
                            target = unbeaten[0]['attack']
                            valid = self.get_valid_defend_cards(self.players[cid].get_deck().cards, target)
                            if c in valid:
                                self.action_beat_card(cid, c)
            elif action == "pass":
                if not self.animator.queue and cid in self.players and self.current_turn_pid == cid and self.game_phase in ["attack", "take_add"]:
                    self.action_pass(cid)
            elif action == "take":
                if not self.animator.queue and cid in self.players and self.current_turn_pid == cid and self.game_phase == "defend":
                    self.action_take(cid)
            elif action == "restart":
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
                self.players.clear()
                self.money.clear()
                for pid in msg_obj["players"]: self.init_player(pid)
                self.init_player(self.engine.my_id)
                self.engine.client.send_data({"action": "set_profile", "title": self.engine.current_progress.get("current_title", "Новичок"), "nickname": getattr(self.engine, "nickname_text", "Player"), "money": self.engine.current_progress.get("money", 10000)})
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
                self.player_titles.pop(msg_obj["id"], None)
                self.player_nicknames.pop(msg_obj["id"], None)
                self.ready_to_play.discard(msg_obj["id"])
                if self.game_phase == "betting":
                    self.rebuild_placed_chips()
            elif action == "shuffle_anim":
                self.game_phase = "shuffling"
                self.shuffle_count = 0
                self.deck.cards = [Card(1, "hearts")] * 36
                self.do_shuffle_anim()
            elif action == "deal_anim":
                self.game_phase = "dealing"
                target = msg_obj["target"]
                c = Card(msg_obj["val"], msg_obj["suit"])
                if target == "trump":
                    self.trump_card = c
                    img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
                    self._deal_animated(c, self.deck_pos[0] - sc(50), self.deck_pos[1] + sc(20), lambda: None, img=img)
                else:
                    if self.deck.cards:
                        self.deck.erase(-1)
                    px, py = self.get_player_hand_pos(target)
                    self._deal_animated(c, px, py, lambda card=c, pid=target: [Assets.sounds['card'].play(), self.players[pid].take_card(card) if pid in self.players else None])
            elif action == "play_card_anim":
                pid = msg_obj["pid"]
                if pid not in self.players: continue
                c = Card(msg_obj["val"], msg_obj["suit"])
                hand = self.players[pid].get_deck().cards
                card_to_remove = next((card for card in hand if card.value == c.value and card.suit == c.suit), None)
                if not card_to_remove and hand:
                    card_to_remove = hand[0]
                if card_to_remove:
                    hand.remove(card_to_remove)

                idx = len(self.table_cards)
                target_x = self.cx - sc(200) + idx * sc(85)
                target_y = self.cy - sc(100)
                px, py = self.get_player_hand_pos(pid)
                c_img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))

                def finish_play():
                    if not any(p['attack'].value == c.value and p['attack'].suit == c.suit for p in self.table_cards):
                        self.table_cards.append({"attack": c, "defend": None})
                    Assets.sounds['card'].play()

                self.animator.add(c_img, (px, py), (target_x, target_y), finish_play, frames=10)
            elif action == "beat_card_anim":
                pid = msg_obj["pid"]
                if pid not in self.players: continue
                c = Card(msg_obj["val"], msg_obj["suit"])
                hand = self.players[pid].get_deck().cards
                card_to_remove = next((card for card in hand if card.value == c.value and card.suit == c.suit), None)
                if not card_to_remove and hand:
                    card_to_remove = hand[0]
                if card_to_remove:
                    hand.remove(card_to_remove)

                target_idx = 0
                for i, pair in enumerate(self.table_cards):
                    if not pair['defend']:
                        target_idx = i
                        break

                target_x = self.cx - sc(200) + target_idx * sc(85) + sc(20)
                target_y = self.cy - sc(80)
                px, py = self.get_player_hand_pos(pid)
                c_img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))

                def finish_beat():
                    if target_idx < len(self.table_cards) and self.table_cards[target_idx]['defend'] is None:
                        self.table_cards[target_idx]['defend'] = c
                    Assets.sounds['card'].play()

                self.animator.add(c_img, (px, py), (target_x, target_y), finish_beat, frames=10)
            elif action == "bet":
                cid = msg_obj["id"]
                if cid in self.players:
                    bet_val = msg_obj["val"]
                    Assets.sounds['chip'].play()
                    self.players[cid].get_bet().value += bet_val
                    self.money[cid] -= bet_val
                    if cid == self.engine.my_id:
                        self.engine.current_progress["money"] = self.money[self.engine.my_id]
                        save_progress(self.engine.current_progress)
                    theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                    c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{bet_val}.png"), (self.cw, self.ch))
                    px = self.deck_pos[0] - sc(250)
                    anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                    total_val = sum(p.get_bet().get_value() for p in self.players.values())
                    count = sum(total_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                    anim_end = (int(px - self.cw // 2), int(self.cy - self.ch // 2 - max(0, count - 1) * sc(8)))
                    self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)
            elif action == "cancel_bet":
                cid = msg_obj["id"]
                if cid in self.players:
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
            elif action == "sync":
                old_phase = getattr(self, 'game_phase', None)
                self.game_phase = msg_obj["phase"]
                if self.game_phase == "betting" and old_phase != "betting":
                    self.reset_game_state()

                self.fool_id = msg_obj.get("fool_id")

                if self.game_phase == "game_over" and old_phase != "game_over":
                    self.ready_to_play.clear()
                    if self.fool_id != self.engine.my_id:
                        bet = self.players[self.engine.my_id].get_bet().get_value() if self.engine.my_id in self.players else 0
                        self.money[self.engine.my_id] = self.money.get(self.engine.my_id, 0) + bet * 2
                        self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                        save_progress(self.engine.current_progress)

                self.current_turn_pid = msg_obj["turn"]
                self.attacker_pid = msg_obj["attacker"]
                self.defender_pid = msg_obj["defender"]
                self.taking = msg_obj["taking"]

                self.deck.cards = [Card(1, "hearts")] * msg_obj["deck_count"]
                if msg_obj["trump"]:
                    self.trump_card = Card(msg_obj["trump"]["val"], msg_obj["trump"]["suit"])
                else:
                    self.trump_card = None

                self.table_cards = []
                for p in msg_obj["table"]:
                    pair = {"attack": Card(p["attack"]["val"], p["attack"]["suit"]), "defend": None}
                    if p["defend"]:
                        pair["defend"] = Card(p["defend"]["val"], p["defend"]["suit"])
                    self.table_cards.append(pair)
            elif action == "hand":
                pid = msg_obj["pid"]
                if pid in self.players:
                    self.players[pid].clear_deck()
                    for c_data in msg_obj["cards"]:
                        self.players[pid].take_card(Card(c_data["val"], c_data["suit"]))
            elif action == "emoji":
                self._show_emoji(msg_obj["id"], msg_obj["idx"])