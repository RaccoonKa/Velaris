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

def evaluate_hand(cards):
    if len(cards) < 5:
        return (-1, [])

    vals = [c.value if c.value != 1 else 14 for c in cards]
    suits = [c.suit for c in cards]

    flush_suit = None
    for s in set(suits):
        if suits.count(s) >= 5:
            flush_suit = s
            break

    flush_cards = sorted([v for i, v in enumerate(vals) if suits[i] == flush_suit], reverse=True) if flush_suit else []

    def get_straight(v_list):
        v_set = set(v_list)
        if 14 in v_set: v_set.add(1)
        sorted_v = sorted(list(v_set), reverse=True)
        for i in range(len(sorted_v) - 4):
            if sorted_v[i] - sorted_v[i+4] == 4:
                return sorted_v[i]
        if {14, 2, 3, 4, 5}.issubset(v_set):
            return 5
        return None

    straight_high = get_straight(vals)
    sf_high = get_straight(flush_cards) if flush_cards else None

    counts = {}
    for v in vals: counts[v] = counts.get(v, 0) + 1
    freqs = sorted([(c, v) for v, c in counts.items()], reverse=True)

    if sf_high: return (8, [sf_high])
    if freqs[0][0] == 4: return (7, [freqs[0][1], freqs[1][1] if len(freqs)>1 else 0])
    if freqs[0][0] == 3 and len(freqs) > 1 and freqs[1][0] >= 2: return (6, [freqs[0][1], freqs[1][1]])
    if flush_cards: return (5, flush_cards[:5])
    if straight_high: return (4, [straight_high])
    if freqs[0][0] == 3:
        kickers = sorted([v for v in vals if v != freqs[0][1]], reverse=True)[:2]
        return (3, [freqs[0][1]] + kickers)
    if freqs[0][0] == 2 and len(freqs) > 1 and freqs[1][0] == 2:
        kickers = sorted([v for v in vals if v != freqs[0][1] and v != freqs[1][1]], reverse=True)[:1]
        pair_high = max(freqs[0][1], freqs[1][1])
        pair_low = min(freqs[0][1], freqs[1][1])
        return (2, [pair_high, pair_low] + kickers)
    if freqs[0][0] == 2:
        kickers = sorted([v for v in vals if v != freqs[0][1]], reverse=True)[:3]
        return (1, [freqs[0][1]] + kickers)

    return (0, sorted(vals, reverse=True)[:5])


class PokerScene(BaseScene):
    def __init__(self, engine):
        super().__init__(engine)
        self.mode = "singleplayer"
        self.animator = Animator()

        self.players = {}
        self.money = {}
        self.player_titles = {}
        self.player_nicknames = {}
        self.active_players = set()
        self.acted_players = set()
        self.ready_to_play = set()

        self.deck = Deck()
        self.community_cards = []

        self.pot = 0
        self.current_bet = 0
        self.round_bets = {}

        self.game_phase = "waiting"
        self.dealer_idx = 0
        self.current_turn_idx = 0
        self.min_raise = 100
        self.staged_raise = 0
        self.bot_timer = 0
        self.last_winners = []

        self.card_visuals = {}
        self.texture_cache = {}
        self.placed_chips = []

        self.card_w, self.card_h = sc(140), sc(190)
        self.cx, self.cy = int(self.engine.WIDTH // 2), int(self.engine.HEIGHT // 2)
        self.deck_pos = (int(self.engine.WIDTH - sc(200)), int(self.cy - sc(100)))

        self.emoji_btn_size = int(sc(80))
        self.emoji_panel_open = False
        self.emoji_panel_anim_start = 0
        self.active_emojis = {}
        self.emoji_display_time = 3000

        self._init_ui()

    def _init_ui(self):
        btn_w, btn_h = sc(250), sc(100)
        btn_y = int(self.engine.HEIGHT - sc(120))
        self.fold_btn = pygame.Rect(int(self.engine.WIDTH - sc(790)), btn_y, btn_w, btn_h)
        self.call_btn = pygame.Rect(int(self.engine.WIDTH - sc(530)), btn_y, btn_w + sc(20), btn_h)
        self.raise_btn = pygame.Rect(int(self.engine.WIDTH - sc(250)), btn_y, btn_w, btn_h)

        self.exit_btn = pygame.Rect(int(self.engine.WIDTH - sc(280)), int(sc(30)), int(sc(270)), int(sc(100)))
        self.restart_btn = pygame.Rect(0, 0, int(sc(620)), int(sc(120))); self.restart_btn.center = (self.cx, int(self.cy + sc(200)))

        self.mountain_pos = (int(sc(-15)), int(self.cy - Assets.images['all_chips'].get_height() // 2 + sc(100)))
        self.w_c = int(sc(120)); self.cw, self.ch = int(self.w_c * 1.7), int(self.w_c * 0.9)
        mc_x, mc_y = int(self.mountain_pos[0] + Assets.images['all_chips'].get_width() // 2), int(self.cy + sc(100))
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

    def _show_emoji(self, pid, idx):
        self.active_emojis[pid] = {
            "idx": idx,
            "timer": pygame.time.get_ticks() + self.emoji_display_time,
            "start_time": pygame.time.get_ticks()
        }

    def init_player(self, pid):
        self.players[pid] = Player(False)
        if pid not in self.money:
            self.money[pid] = self.engine.current_progress.get("money", 10000)

    def on_enter(self, mode="singleplayer"):
        self.mode = mode
        self.engine.switch_music(self.engine.current_theme, "game")

        theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
        self.set_bet_100.set_button_texture(os.path.join("textures", "chips", theme, "100.png"))
        self.set_bet_250.set_button_texture(os.path.join("textures", "chips", theme, "250.png"))
        self.set_bet_500.set_button_texture(os.path.join("textures", "chips", theme, "500.png"))
        self.set_bet_1000.set_button_texture(os.path.join("textures", "chips", theme, "1000.png"))
        self.set_bet_2500.set_button_texture(os.path.join("textures", "chips", theme, "2500.png"))
        self.set_bet_10000.set_button_texture(os.path.join("textures", "chips", theme, "10000.png"))

        self.players.clear()
        self.money.clear()
        self.player_titles.clear()
        self.player_nicknames.clear()

        if self.mode in ["singleplayer", "multiplayer_host"]:
            self.engine.my_id = 0
            self.init_player(0)
            self.player_titles[0] = self.engine.current_progress.get("current_title", "Новичок")
            self.player_nicknames[0] = getattr(self.engine, "nickname_text", "Player")

            if self.mode == "singleplayer":
                for i in range(1, 4):
                    self.players[i] = Player(False)
                    self.money[i] = random.randint(5000, 20000)
                    self.player_titles[i] = "Шулер"
                    self.player_nicknames[i] = f"Bot {i}"
                self.start_hand()
            else:
                self.game_phase = "waiting"

    def _get_cached_texture(self, path, size):
        if self.engine.current_theme == "cyberpunk":
            path = path.replace("cards_wood", "cards_cyberpunk")
            if "cards_cyberpunk" in path or "cybershirt" in path:
                size = (sc(180), sc(215))

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

    def reset_game_state(self):
        for p in self.players.values():
            p.clear_deck()
        self.community_cards.clear()
        self.placed_chips.clear()
        self.card_visuals.clear()
        self.animator.clear()
        self.active_emojis.clear()
        self.emoji_panel_open = False
        self.emoji_panel_anim_start = 0

        self.pot = 0
        self.current_bet = 0
        self.round_bets = {pid: 0 for pid in self.players}
        self.staged_raise = 0
        self.last_winners = []

        self.active_players = set(self.players.keys())
        self.acted_players.clear()
        self.ready_to_play.clear()
        self.bot_timer = 0

        if self.mode == "singleplayer":
            broke = [pid for pid in self.players if self.money[pid] < 100 and pid != self.engine.my_id]
            for b in broke:
                self.players.pop(b, None)
                self.active_players.discard(b)

    def get_title_color(self, title):
        if title in ["Разработчик", "Developer", "Millionaire", "Миллионер", "Крути-вези!", "I got lucky!"]:
            t_ms = pygame.time.get_ticks()
            glow = int((math.sin(t_ms / 150.0) + 1) / 2 * 100)
            return (255, 255 - glow, 0)
        return (255, 215, 0)

    def start_hand(self):
        self.reset_game_state()
        if getattr(self.engine, 'server', None):
            self.engine.server.broadcast({"action": "start_hand"})

        self.deck.refill_random(52)

        pids = sorted(list(self.players.keys()))
        self.dealer_idx = (self.dealer_idx + 1) % len(pids)

        sb_idx = (self.dealer_idx + 1) % len(pids)
        bb_idx = (self.dealer_idx + 2) % len(pids)
        sb_id = pids[sb_idx]
        bb_id = pids[bb_idx]

        self.round_bets[sb_id] = min(100, self.money[sb_id])
        self.money[sb_id] -= self.round_bets[sb_id]

        self.round_bets[bb_id] = min(200, self.money[bb_id])
        self.money[bb_id] -= self.round_bets[bb_id]

        self.current_bet = self.round_bets[bb_id]
        self.acted_players.clear()

        self.current_turn_idx = bb_idx
        self.game_phase = "dealing"

        self._sync_state()

        for _ in range(2):
            for pid in self.active_players:
                c = self.deck.erase(-1)
                self._deal_to_player(c, pid)

    def _safe_take_card(self, pid, card):
        if pid in self.players:
            hand = self.players[pid].get_deck().cards
            if not any(c.value == card.value and c.suit == card.suit for c in hand):
                self.players[pid].take_card(card)

    def _deal_to_player(self, card, pid):
        if pid not in self.players: return
        if getattr(self.engine, 'server', None):
            self.engine.server.broadcast({"action": "deal_player", "target": pid, "val": card.value, "suit": card.suit})

        px, py = self._get_player_pos(pid)
        p_len = len(self.players[pid].get_deck())

        offset_x = random.randint(int(sc(-5)), int(sc(5)))
        offset_y = random.randint(int(sc(-5)), int(sc(5)))
        angle = random.randint(-8, 8)
        self.card_visuals[card] = {"offset": (offset_x, offset_y), "angle": angle}

        start_x = int(px - (self.card_w + sc(40)) // 2)
        end_x = int(start_x + p_len * sc(40)) + offset_x
        end_y = py + offset_y

        shirt_raw = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])
        shirt = pygame.transform.smoothscale(shirt_raw, (self.card_w, self.card_h))

        img = shirt if pid != self.engine.my_id else self._get_cached_texture(card.get_texture_path(), (self.card_w, self.card_h))

        self.animator.add(img, self.deck_pos, (end_x, end_y), lambda c=card, p=pid: [Assets.sounds['card'].play(), self._safe_take_card(p, c)], 15, end_angle=angle)

    def _deal_community(self, count):
        for _ in range(count):
            c = self.deck.erase(-1)
            if getattr(self.engine, 'server', None):
                self.engine.server.broadcast({"action": "deal_community", "val": c.value, "suit": c.suit})
            self._deal_community_anim(c)

    def _deal_community_anim(self, c):
        idx = len(self.community_cards)
        offset_x = random.randint(int(sc(-5)), int(sc(5)))
        offset_y = random.randint(int(sc(-5)), int(sc(5)))
        angle = random.randint(-5, 5)
        self.card_visuals[c] = {"offset": (offset_x, offset_y), "angle": angle}

        total_w = 5 * sc(145)
        start_x = self.cx - total_w // 2

        end_x = int(start_x + idx * sc(145)) + offset_x
        end_y = self.cy - sc(80) + offset_y

        def _append_community(card):
            Assets.sounds['card'].play()
            if not any(c_in.value == card.value and c_in.suit == card.suit for c_in in self.community_cards):
                self.community_cards.append(card)

        self.animator.add(self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h)),
                          self.deck_pos, (end_x, end_y),
                          lambda card=c: _append_community(card), 15, end_angle=angle)

    def _sync_state(self):
        if getattr(self.engine, 'server', None):
            data = {
                "action": "sync",
                "pot": self.pot,
                "current_bet": self.current_bet,
                "round_bets": {k: v for k, v in self.round_bets.items()},
                "money": {k: v for k, v in self.money.items()},
                "active_players": list(self.active_players),
                "current_turn_idx": self.current_turn_idx,
                "game_phase": self.game_phase,
                "dealer_idx": self.dealer_idx,
                "community_cards": [{"val": c.value, "suit": c.suit} for c in self.community_cards],
                "hands": {pid: [{"val": c.value, "suit": c.suit} for c in p.get_deck().cards] for pid, p in self.players.items()}
            }
            self.engine.server.broadcast(data)

    def _place_bet(self, pid, amount):
        real_amount = min(amount, self.money[pid])
        if real_amount < 0: return

        self.money[pid] -= real_amount
        self.round_bets[pid] = self.round_bets.get(pid, 0) + real_amount

        if self.round_bets[pid] > self.current_bet:
            self.current_bet = self.round_bets[pid]
            self.acted_players.clear()

        self.acted_players.add(pid)

        if pid == self.engine.my_id:
            self.engine.current_progress["money"] = self.money[pid]
            save_progress(self.engine.current_progress)

        Assets.sounds['chip'].play()
        theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"

        chip_val = 100
        for d in [10000, 2500, 1000, 500, 250, 100]:
            if real_amount >= d:
                chip_val = d
                break

        c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{chip_val}.png"), (self.cw, self.ch))
        px, py = self._get_player_pos(pid)

        if pid == self.engine.my_id:
            start_x, start_y = int(px - sc(220)), int(py + sc(80))
        else:
            start_x, start_y = int(px - self.w_c // 2), int(py - sc(70))

        target_x = int(px - self.w_c // 2 + random.randint(int(sc(-20)), int(sc(20))))
        target_y = int(self.cy - sc(20) + random.randint(int(sc(-20)), int(sc(20))))

        self.animator.add(c_img, (start_x, start_y), (target_x, target_y), self.rebuild_placed_chips, 15)

    def _check_round_over(self):
        if len(self.active_players) <= 1:
            return True

        for pid in self.active_players:
            if pid not in self.acted_players and self.money[pid] > 0:
                return False
            if self.round_bets.get(pid, 0) < self.current_bet and self.money[pid] > 0:
                return False
        return True

    def _next_turn(self):
        if self._check_round_over():
            self._next_phase()
            return

        pids = sorted(list(self.players.keys()))
        original_idx = self.current_turn_idx

        while True:
            self.current_turn_idx = (self.current_turn_idx + 1) % len(pids)
            curr_id = pids[self.current_turn_idx]

            if curr_id in self.active_players and self.money[curr_id] > 0:
                if curr_id not in self.acted_players or self.round_bets.get(curr_id, 0) < self.current_bet:
                    break

            if self.current_turn_idx == original_idx:
                self._next_phase()
                return

        self.bot_timer = 0
        self._sync_state()

    def _next_phase(self):
        for pid, bet in self.round_bets.items():
            self.pot += bet
        self.round_bets = {pid: 0 for pid in self.players}
        self.current_bet = 0
        self.acted_players.clear()
        self.rebuild_placed_chips()

        if len(self.active_players) <= 1:
            self._showdown()
            return

        if self.game_phase == "preflop":
            self.game_phase = "flop"
            self._deal_community(3)
        elif self.game_phase == "flop":
            self.game_phase = "turn"
            self._deal_community(1)
        elif self.game_phase == "turn":
            self.game_phase = "river"
            self._deal_community(1)
        elif self.game_phase == "river":
            self._showdown()
            return

        self.current_turn_idx = self.dealer_idx
        self._sync_state()

    def _showdown(self):
        self.game_phase = "showdown"
        for pid, bet in self.round_bets.items():
            self.pot += bet
        self.round_bets = {pid: 0 for pid in self.players}

        if len(self.active_players) == 1:
            winner = list(self.active_players)[0]
            self.money[winner] += self.pot
            self.last_winners = [winner]
        else:
            best_score = (-1, [])
            winners = []

            for pid in self.active_players:
                hand = self.players[pid].get_deck().cards + self.community_cards
                score = evaluate_hand(hand)

                if score[0] > best_score[0]:
                    best_score = score
                    winners = [pid]
                elif score[0] == best_score[0]:
                    for i in range(len(score[1])):
                        if score[1][i] > best_score[1][i]:
                            best_score = score
                            winners = [pid]
                            break
                        elif score[1][i] < best_score[1][i]:
                            break
                    else:
                        winners.append(pid)

            split = self.pot // len(winners)
            for w in winners:
                self.money[w] += split
            self.last_winners = winners

        if self.engine.my_id in self.money:
            self.engine.current_progress["money"] = self.money[self.engine.my_id]
            save_progress(self.engine.current_progress)

        if getattr(self.engine, 'server', None):
            self.engine.server.broadcast({
                "action": "showdown_results",
                "winners": self.last_winners,
                "money": {k: v for k, v in self.money.items()}
            })

    def update(self):
        self.animator.update()

        if self.mode == "multiplayer_host" and getattr(self.engine, 'server', None):
            self._handle_server()
            if self.game_phase == "waiting" and len(self.players) == getattr(self.engine, 'target_players', 2):
                self.start_hand()
            elif self.game_phase == "showdown" and len(self.players) > 0 and len(self.ready_to_play) == len(self.players):
                self.start_hand()
        elif self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
            self._handle_client()

        if self.mode != "multiplayer_client":
            if self.game_phase == "dealing" and not self.animator.queue:
                self.game_phase = "preflop"
                self._next_turn()

            elif self.game_phase in ["flop", "turn", "river"] and not self.animator.queue:
                if self.current_turn_idx == self.dealer_idx and len(self.acted_players) == 0:
                    self._next_turn()

        if self.game_phase in ["preflop", "flop", "turn", "river"] and not self.animator.queue:
            if self.mode == "singleplayer" and not self._is_my_turn():
                if self.bot_timer == 0:
                    self.bot_timer = pygame.time.get_ticks() + 1000
                elif pygame.time.get_ticks() >= self.bot_timer:
                    self.bot_timer = 0
                    self._handle_bot_turn()
            else:
                self.bot_timer = 0

    def _is_my_turn(self):
        pids = sorted(list(self.players.keys()))
        if not pids: return False
        return pids[self.current_turn_idx] == self.engine.my_id

    def _handle_bot_turn(self):
        pids = sorted(list(self.players.keys()))
        bot_id = pids[self.current_turn_idx]

        if bot_id not in self.active_players or self.money[bot_id] == 0:
            self._next_turn()
            return

        to_call = self.current_bet - self.round_bets.get(bot_id, 0)

        val = sum(c.value for c in self.players[bot_id].get_deck())
        if to_call > self.money[bot_id] // 2 and val < 15 and random.random() < 0.6:
            self.active_players.remove(bot_id)
            self._next_turn()
            return

        chip_options = [100, 250, 500, 1000, 2500]
        affordable_chips = [c for c in chip_options if c <= self.money[bot_id] - to_call]

        bet_amount = to_call

        if affordable_chips and random.random() < 0.4:
            bet_amount += random.choice(affordable_chips)

        self._place_bet(bot_id, bet_amount)
        self._next_turn()

    def _handle_server(self):
        while not self.engine.server.message_queue.empty():
            msg = self.engine.server.message_queue.get()
            data = msg["data"]
            action = data.get("action")
            cid = data.get("client_id")

            if action == "internal_player_joined":
                self.init_player(cid)
                profiles = {p: {"title": self.player_titles.get(p, "Новичок"), "nickname": self.player_nicknames.get(p, f"Player {p+1}")} for p in self.players}
                self.engine.server.broadcast({"action": "profiles_sync", "profiles": profiles})
                self._sync_state()
                continue
            elif action == "internal_player_left":
                pids_before = sorted(list(self.players.keys()))
                was_turn = (pids_before and self.current_turn_idx < len(pids_before) and pids_before[self.current_turn_idx] == cid)

                self.players.pop(cid, None)
                self.money.pop(cid, None)
                if cid in self.active_players:
                    self.active_players.remove(cid)
                self.acted_players.discard(cid)
                self.ready_to_play.discard(cid)
                self.player_titles.pop(cid, None)
                self.player_nicknames.pop(cid, None)

                pids_after = sorted(list(self.players.keys()))
                if pids_after:
                    self.dealer_idx = self.dealer_idx % len(pids_after)

                if self.game_phase in ["preflop", "flop", "turn", "river"]:
                    if was_turn:
                        self.current_turn_idx -= 1
                        if self.current_turn_idx < 0:
                            self.current_turn_idx = max(0, len(pids_after) - 1)
                        if pids_after:
                            self._next_turn()
                    else:
                        if pids_before and self.current_turn_idx < len(pids_before):
                            curr_id = pids_before[self.current_turn_idx]
                            if curr_id in pids_after:
                                self.current_turn_idx = pids_after.index(curr_id)
                        if pids_after and self._check_round_over():
                            self._next_phase()
                self.rebuild_placed_chips()
                self._sync_state()
                continue

            pids = sorted(list(self.players.keys()))

            if action == "set_profile":
                self.player_titles[cid] = data.get("title", "Новичок")
                self.player_nicknames[cid] = data.get("nickname", "Player")
                if "money" in data:
                    self.money[cid] = data["money"]
                profiles = {p: {"title": self.player_titles.get(p, "Новичок"), "nickname": self.player_nicknames.get(p, f"Player {p+1}")} for p in self.players}
                self.engine.server.broadcast({"action": "profiles_sync", "profiles": profiles})
                self._sync_state()
            elif action == "emoji":
                idx = data.get("idx")
                self._show_emoji(cid, idx)
                self.engine.server.broadcast({"action": "emoji", "id": cid, "idx": idx})
            elif action == "fold" and pids and self.current_turn_idx < len(pids) and pids[self.current_turn_idx] == cid and self.game_phase in ["preflop", "flop", "turn", "river"]:
                if cid in self.active_players:
                    self.active_players.remove(cid)
                self._next_turn()
            elif action == "call" and pids and self.current_turn_idx < len(pids) and pids[self.current_turn_idx] == cid and self.game_phase in ["preflop", "flop", "turn", "river"]:
                to_call = self.current_bet - self.round_bets.get(cid, 0)
                self._place_bet(cid, to_call)
                self._next_turn()
            elif action == "raise" and pids and self.current_turn_idx < len(pids) and pids[self.current_turn_idx] == cid and self.game_phase in ["preflop", "flop", "turn", "river"]:
                amt = data.get("amount", 0)
                to_call = self.current_bet - self.round_bets.get(cid, 0)
                if amt > 0 and (amt >= to_call + self.min_raise or amt == self.money.get(cid, 0)):
                    self._place_bet(cid, amt)
                    self._next_turn()
            elif action == "restart" and self.game_phase == "showdown":
                self.ready_to_play.add(cid)
                self.engine.server.broadcast({"action": "ready", "id": cid})

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
                if msg_obj["id"] in self.active_players:
                    self.active_players.remove(msg_obj["id"])
                self.player_titles.pop(msg_obj["id"], None)
                self.player_nicknames.pop(msg_obj["id"], None)
                self.rebuild_placed_chips()
            elif action == "deal_player":
                target = msg_obj["target"]
                c = Card(msg_obj["val"], msg_obj["suit"])
                self._deal_to_player(c, target)
            elif action == "deal_community":
                c = Card(msg_obj["val"], msg_obj["suit"])
                self._deal_community_anim(c)
            elif action == "sync":
                self.pot = msg_obj["pot"]
                self.current_bet = msg_obj["current_bet"]
                self.round_bets = {int(k): v for k, v in msg_obj["round_bets"].items()}
                self.money = {int(k): v for k, v in msg_obj["money"].items()}
                self.active_players = set(msg_obj["active_players"])
                self.current_turn_idx = msg_obj["current_turn_idx"]
                self.game_phase = msg_obj["game_phase"]
                self.dealer_idx = msg_obj["dealer_idx"]

                if "community_cards" in msg_obj:
                    self.community_cards = [Card(c["val"], c["suit"]) for c in msg_obj["community_cards"]]
                if "hands" in msg_obj:
                    for pid_str, cards in msg_obj["hands"].items():
                        pid = int(pid_str)
                        if pid in self.players:
                            self.players[pid].clear_deck()
                            for c in cards:
                                self.players[pid].take_card(Card(c["val"], c["suit"]))

                self.rebuild_placed_chips()
            elif action == "showdown_results":
                self.last_winners = msg_obj["winners"]
                self.money = {int(k): v for k, v in msg_obj["money"].items()}
                self.game_phase = "showdown"
                if self.engine.my_id in self.money:
                    self.engine.current_progress["money"] = self.money[self.engine.my_id]
                    save_progress(self.engine.current_progress)
            elif action == "emoji":
                self._show_emoji(msg_obj["id"], msg_obj["idx"])
            elif action == "ready":
                self.ready_to_play.add(msg_obj["id"])
            elif action == "start_hand":
                self.reset_game_state()

    def handle_events(self, events):
        mx, my = self.engine.mx, self.engine.my
        px_my, py_my = self._get_player_pos(self.engine.my_id)
        info_y_my = py_my + self.card_h + sc(10)

        emoji_btn_rect = pygame.Rect(int(px_my - sc(150) - self.emoji_btn_size - sc(15)), int(info_y_my + sc(20)), self.emoji_btn_size, self.emoji_btn_size)
        reset_rect = pygame.Rect(int(self.mountain_pos[0] + sc(90)), int(self.mountain_pos[1] - sc(160)), int(sc(300)), int(sc(40)))

        panel_w, panel_h = int(sc(350)), int(sc(180))
        btn_y = int(self.engine.HEIGHT - sc(120))
        panel_x = int(self.engine.WIDTH - sc(400) - panel_w // 2)
        panel_y = int(btn_y - panel_h - sc(20))
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and (event.button == 3 or (event.button == 1 and reset_rect.collidepoint(mx, my))):
                if self.staged_raise > 0:
                    Assets.sounds['chip'].play()
                    self.staged_raise = 0
                    self.rebuild_placed_chips()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.emoji_panel_open:
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

                can_exit = self.game_phase in ["waiting", "showdown"]

                if can_exit and self.exit_btn.collidepoint(mx, my):
                    Assets.sounds['back'].play()
                    if getattr(self.engine, 'server', None):
                        self.engine.server.stop()
                        self.engine.server = None
                    if getattr(self.engine, 'client', None):
                        self.engine.client.disconnect()
                        self.engine.client = None
                    if self.engine.my_id in self.money:
                        self.engine.current_progress["money"] = self.money.get(self.engine.my_id, 0)
                        save_progress(self.engine.current_progress)
                    self.engine.switch_scene("menu")
                    return

                if self.game_phase == "showdown":
                    if self.restart_btn.collidepoint(mx, my) and self.engine.my_id not in self.ready_to_play:
                        Assets.sounds['enter'].play()
                        if self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
                            self.engine.client.send_data({"action": "restart"})
                        elif self.mode == "multiplayer_host":
                            self.ready_to_play.add(self.engine.my_id)
                            if getattr(self.engine, 'server', None): self.engine.server.broadcast({"action": "ready", "id": self.engine.my_id})
                        elif self.mode == "singleplayer":
                            self.start_hand()
                    return

                if self._is_my_turn() and not self.animator.queue and self.game_phase in ["preflop", "flop", "turn", "river"]:
                    to_call = self.current_bet - self.round_bets.get(self.engine.my_id, 0)
                    can_raise = self.staged_raise >= self.min_raise

                    if self.fold_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play()
                        self.staged_raise = 0
                        self.rebuild_placed_chips()
                        if self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
                            self.engine.client.send_data({"action": "fold"})
                        else:
                            if self.engine.my_id in self.active_players:
                                self.active_players.remove(self.engine.my_id)
                            self._next_turn()

                    elif self.call_btn.collidepoint(mx, my):
                        Assets.sounds['enter'].play()
                        self.staged_raise = 0
                        self.rebuild_placed_chips()
                        if self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
                            self.engine.client.send_data({"action": "call"})
                        else:
                            self._place_bet(self.engine.my_id, to_call)
                            self._next_turn()

                    elif self.raise_btn.collidepoint(mx, my) and can_raise:
                        Assets.sounds['enter'].play()
                        total_bet = to_call + self.staged_raise
                        self.staged_raise = 0
                        self.rebuild_placed_chips()
                        if self.mode == "multiplayer_client" and getattr(self.engine, 'client', None):
                            self.engine.client.send_data({"action": "raise", "amount": total_bet})
                        else:
                            self._place_bet(self.engine.my_id, total_bet)
                            self._next_turn()

                    bet_val = 0
                    if self.set_bet_10000.rect.collidepoint(mx, my): bet_val = 10000
                    elif self.set_bet_2500.rect.collidepoint(mx, my): bet_val = 2500
                    elif self.set_bet_1000.rect.collidepoint(mx, my): bet_val = 1000
                    elif self.set_bet_500.rect.collidepoint(mx, my): bet_val = 500
                    elif self.set_bet_250.rect.collidepoint(mx, my): bet_val = 250
                    elif self.set_bet_100.rect.collidepoint(mx, my): bet_val = 100

                    if bet_val > 0 and self.money.get(self.engine.my_id, 0) >= to_call + self.staged_raise + bet_val:
                        if self.staged_raise + bet_val <= 100000:
                            Assets.sounds['chip'].play()
                            self.staged_raise += bet_val
                            theme = "cyberpunk" if self.engine.current_theme == "cyberpunk" else "default"
                            c_img = self._get_cached_texture(os.path.join("textures", "chips", theme, f"{bet_val}.png"), (self.cw, self.ch))
                            px, py = self._get_player_pos(self.engine.my_id)
                            anim_start = (int(self.mountain_pos[0] + sc(100)), int(self.mountain_pos[1] + sc(80)))
                            temp_val = self.round_bets.get(self.engine.my_id, 0) + self.staged_raise
                            count = sum(temp_val // d for d in [10000, 2500, 1000, 500, 250, 100])
                            anim_end = (int(px - sc(220)), int(py + sc(80) - max(0, count - 1) * sc(8)))

                            self.animator.add(c_img, anim_start, anim_end, self.rebuild_placed_chips, 20)

    def _get_player_pos(self, pid):
        if pid == self.engine.my_id:
            return (self.cx, int(self.engine.HEIGHT - sc(330)))

        other_ids = [p for p in self.players if p != self.engine.my_id]
        if not other_ids: return (self.cx, int(sc(150)))

        idx = other_ids.index(pid)
        spacing = self.engine.WIDTH // (len(other_ids) + 1)
        return (spacing * (idx + 1), int(sc(150)))

    def rebuild_placed_chips(self):
        self.placed_chips.clear()
        for pid, p in self.players.items():
            val = self.round_bets.get(pid, 0)

            if pid == self.engine.my_id:
                val += self.staged_raise

            if val <= 0:
                continue

            px, py = self._get_player_pos(pid)

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

                if pid == self.engine.my_id:
                    chip_x = int(px - sc(220))
                    chip_y = int(py + sc(80) - i * sc(8))
                else:
                    chip_x = int(px - self.w_c // 2)
                    chip_y = int(py + self.card_h + sc(-70) - i * sc(8))

                self.placed_chips.append((img, (chip_x, chip_y)))

    def draw(self, window):
        mx, my = self.engine.mx, self.engine.my
        window.blit(self.engine.current_bg, (0, 0))

        current_time = pygame.time.get_ticks()
        expired = [pid for pid, data in self.active_emojis.items() if current_time > data["timer"]]
        for pid in expired:
            del self.active_emojis[pid]

        shirt_raw = Assets.images.get(f"shirt_{self.engine.current_theme}", Assets.images['shirt_red'])
        shirt = pygame.transform.smoothscale(shirt_raw, (self.card_w, self.card_h))

        for i in range(5): window.blit(shirt, (self.deck_pos[0] - i * 2, self.deck_pos[1] - i * 2))

        if self.community_cards:
            total_w = 5 * sc(145)
            start_x = self.cx - total_w // 2
            for i, c in enumerate(self.community_cards):
                vis = self.card_visuals.get(c, {"offset": (0,0), "angle": 0})
                img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h))
                x = int(start_x + i * sc(145)) + vis["offset"][0]
                y = self.cy - sc(80) + vis["offset"][1]

                if vis["angle"] != 0:
                    img = pygame.transform.rotozoom(img, vis["angle"], 1.0)
                    rect = img.get_rect(center=(x + self.card_w//2, y + self.card_h//2))
                    window.blit(img, rect.topleft)
                else:
                    window.blit(img, (x, y))

        pot_rect = pygame.Rect(0, 0, int(sc(300)), int(sc(60)))
        pot_rect.center = (self.cx, self.cy - sc(130))
        draw_alpha_rect(window, (0, 0, 0, 160), pot_rect, (218, 165, 32), int(sc(2)), int(sc(15)))
        draw_text_centered(window, f"{t('Pot:')} {self.pot}$", Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), pot_rect)

        pids = sorted(list(self.players.keys()))
        for pid in pids:
            p = self.players[pid]
            px, py = self._get_player_pos(pid)

            p_len = len(p.get_deck())
            if p_len > 0:
                start_x = int(px - (self.card_w + (p_len - 1) * sc(40)) // 2)
                for i, c in enumerate(p.get_deck()):
                    vis = self.card_visuals.get(c, {"offset": (0,0), "angle": 0})
                    x = int(start_x + i * sc(40)) + vis["offset"][0]
                    y = py + vis["offset"][1]

                    show_face = (pid == self.engine.my_id) or (self.game_phase == "showdown" and pid in self.active_players)
                    c_img = self._get_cached_texture(c.get_texture_path(), (self.card_w, self.card_h)) if show_face else shirt

                    if vis["angle"] != 0:
                        c_img = pygame.transform.rotozoom(c_img, vis["angle"], 1.0)
                        rect = c_img.get_rect(center=(x + self.card_w//2, y + self.card_h//2))
                        window.blit(c_img, rect.topleft)
                    else:
                        window.blit(c_img, (x, y))

            if pid not in self.active_players:
                box_color = (100, 100, 100)
            elif pids and self.current_turn_idx < len(pids) and pids[self.current_turn_idx] == pid and self.game_phase not in ["waiting", "dealing", "showdown"]:
                box_color = (255, 215, 0)
            else:
                box_color = (218, 165, 32)

            info_y = py + self.card_h + sc(10) if pid == self.engine.my_id else py - sc(140)

            draw_alpha_rect(window, (0, 0, 0, 160), (int(px - sc(150)), int(info_y), int(sc(300)), int(sc(120))), box_color, int(sc(2)), int(sc(10)))

            name = self.engine.nickname_text if pid == self.engine.my_id else self.player_nicknames.get(pid, f"Player {pid}" if self.mode != "singleplayer" else f"Bot {pid}")
            p_title = self.player_titles.get(pid, "Шулер")

            draw_text_centered(window, f"[{t(p_title)}]", Assets.fonts['text30'], self.get_title_color(p_title), (0,0,0), (int(px - sc(150)), int(info_y + sc(10)), int(sc(300)), int(sc(30))), int(sc(2)))
            draw_text_centered(window, f"{name}: {self.money.get(pid, 0)}$", Assets.fonts['text30'], (255,255,255), (0,0,0), (int(px - sc(150)), int(info_y + sc(50)), int(sc(300)), int(sc(30))))
            draw_text_centered(window, f"{t('Bet:')} {self.round_bets.get(pid, 0)}", Assets.fonts['text30'], (255,255,255), (0,0,0), (int(px - sc(150)), int(info_y + sc(90)), int(sc(300)), int(sc(30))))

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
            ping_y = int(info_y + sc(35))

            for b in range(4):
                bw = int(sc(4))
                bh = int(sc(6 + b * 4))
                bx = ping_x + b * int(sc(6))
                by = ping_y - bh
                c = p_col if b < p_bars else (100, 100, 100)
                pygame.draw.rect(window, c, (bx, by, bw, bh))

            if pids and pid == pids[self.dealer_idx]:
                pygame.draw.circle(window, (255,255,255), (int(px - sc(170)), int(info_y + sc(45))), int(sc(15)))
                draw_text_centered(window, "D", Assets.fonts['text20'], (0,0,0), (0,0,0), (int(px - sc(180)), int(info_y + sc(35)), int(sc(20)), int(sc(20))))

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
                        emoji_x = int(px - sc(260))
                        emoji_y = int(info_y - sc(60))
                    else:
                        emoji_x = int(px + sc(200))
                        emoji_y = int(info_y + sc(60))

                    img_rect = current_img.get_rect(center=(emoji_x, emoji_y))
                    window.blit(current_img, img_rect.topleft)

            if pid == self.engine.my_id:
                emoji_btn_rect = pygame.Rect(int(px - sc(150) - self.emoji_btn_size - sc(15)), int(info_y + sc(20)), self.emoji_btn_size, self.emoji_btn_size)
                draw_alpha_rect(window, (0, 0, 0, 160), emoji_btn_rect, (218, 165, 32), int(sc(2)), int(sc(10)))
                window.blit(Assets.images['logo_emoji'], emoji_btn_rect.topleft)

                if self.emoji_panel_open:
                    panel_w, panel_h = int(sc(350)), int(sc(180))
                    btn_y = int(self.engine.HEIGHT - sc(120))
                    panel_x = int(self.engine.WIDTH - sc(400) - panel_w // 2)
                    panel_y = int(btn_y - panel_h - sc(20))
                    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

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

        for chip_img, chip_pos in self.placed_chips:
            window.blit(chip_img, chip_pos)

        self.animator.draw(window)

        window.blit(Assets.images['all_chips'], self.mountain_pos)

        if self.game_phase == "waiting":
            draw_alpha_rect(window, (0, 0, 0, 160), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))), (218, 165, 32), int(sc(2)), int(sc(15)))
            draw_text_centered(window, t("Waiting for players..."), Assets.fonts['text50'], (255, 255, 255), (0, 0, 0), (int(self.cx - sc(250)), int(self.cy - sc(30)), int(sc(500)), int(sc(60))))

        if self._is_my_turn() and self.game_phase not in ["showdown", "waiting"]:
            to_call = self.current_bet - self.round_bets.get(self.engine.my_id, 0)

            h_f = self.fold_btn.collidepoint(mx, my)
            draw_alpha_rect(window, (0, 0, 0, 160), self.fold_btn, (255, 100, 100) if h_f else (200, 50, 50), int(sc(3)) if h_f else int(sc(2)), int(sc(15)))
            draw_text_centered(window, t("Fold"), Assets.fonts['f50'], (255, 255, 255), (0, 0, 0), self.fold_btn)

            h_c = self.call_btn.collidepoint(mx, my)
            lbl = f"{t('Call')} {to_call}" if to_call > 0 else t("Check")
            draw_alpha_rect(window, (0, 0, 0, 160), self.call_btn, (255, 215, 0) if h_c else (218, 165, 32), int(sc(3)) if h_c else int(sc(2)), int(sc(15)))
            draw_text_centered(window, lbl, Assets.fonts['f40'], (255, 255, 255), (0, 0, 0), self.call_btn)

            h_r = self.raise_btn.collidepoint(mx, my)
            can_raise = self.staged_raise >= self.min_raise
            r_col = (255, 215, 0) if h_r and can_raise else ((218, 165, 32) if can_raise else (100, 100, 100))
            draw_alpha_rect(window, (0, 0, 0, 160), self.raise_btn, r_col, int(sc(3)) if h_r and can_raise else int(sc(2)), int(sc(15)))
            draw_text_centered(window, f"{t('Raise')} {self.staged_raise}" if self.staged_raise else t("Raise"), Assets.fonts['f40'], (255, 255, 255), (0, 0, 0), self.raise_btn)

            my_m = self.money.get(self.engine.my_id, 0)
            if my_m >= to_call + self.staged_raise + 100: self.set_bet_100.draw()
            if my_m >= to_call + self.staged_raise + 250: self.set_bet_250.draw()
            if my_m >= to_call + self.staged_raise + 500: self.set_bet_500.draw()
            if my_m >= to_call + self.staged_raise + 1000: self.set_bet_1000.draw()
            if my_m >= to_call + self.staged_raise + 2500: self.set_bet_2500.draw()
            if my_m >= to_call + self.staged_raise + 10000: self.set_bet_10000.draw()

            if self.staged_raise > 0:
                reset_rect = pygame.Rect(int(self.mountain_pos[0] + sc(90)), int(self.mountain_pos[1] - sc(160)), int(sc(300)), int(sc(40)))
                h_res = reset_rect.collidepoint(mx, my)
                b_color = (255, 100, 100) if h_res else (200, 50, 50)
                draw_alpha_rect(window, (0, 0, 0, 160), reset_rect, b_color, int(sc(3)) if h_res else int(sc(2)), int(sc(10)))
                draw_text_centered(window, t("Reset Bet"), Assets.fonts['text30'], (255, 255, 255), (0, 0, 0), reset_rect)

        if self.game_phase == "showdown":
            if self.engine.my_id in self.last_winners:
                text = t("You win!")
            else:
                winner_id = self.last_winners[0]
                winner_name = self.player_nicknames.get(winner_id, f"Player {winner_id}" if self.mode != "singleplayer" else f"Bot {winner_id}")
                text = t(f"{winner_name} wins!") if len(self.last_winners) == 1 else t("Split pot!")

            win_rect = pygame.Rect(0, 0, int(sc(900)), int(sc(120)))
            win_rect.center = (self.cx, self.cy)
            draw_alpha_rect(window, (0, 0, 0, 180), win_rect, (218, 165, 32), int(sc(3)), int(sc(15)))
            draw_text_centered(window, text, Assets.fonts['f80'], (255, 215, 0), (0, 0, 0), win_rect)

            if self.mode == "singleplayer" or self.engine.my_id not in self.ready_to_play:
                h_rs = self.restart_btn.collidepoint(mx, my)
                draw_alpha_rect(window, (0, 0, 0, 160), self.restart_btn, (255, 215, 0) if h_rs else (218, 165, 32), int(sc(3)) if h_rs else int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Next Hand"), Assets.fonts['f60'] if h_rs else Assets.fonts['f50'], "gradient" if h_rs else (255, 255, 255), (0, 0, 0), self.restart_btn)
            else:
                draw_alpha_rect(window, (0, 0, 0, 160), self.restart_btn, (218, 165, 32), int(sc(2)), int(sc(15)))
                draw_text_centered(window, t("Waiting for players..."), Assets.fonts['text40'], (255, 255, 255), (0, 0, 0), self.restart_btn)

        can_exit = self.game_phase in ["waiting", "showdown"]
        if can_exit:
            h_e = self.exit_btn.collidepoint(mx, my)
            draw_alpha_rect(window, (0, 0, 0, 160), self.exit_btn, (255, 215, 0) if h_e else (218, 165, 32), int(sc(3)) if h_e else int(sc(2)), int(sc(15)))
            draw_text_centered(window, t("Exit"), Assets.fonts['f50'], "gradient" if h_e else (255, 255, 255), (0, 0, 0), self.exit_btn)