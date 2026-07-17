import random
import os

SUITS = ["clubs", "diamonds", "hearts", "spades"]

class Card:
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
        self.texture_path = ""
        self.set_value(value, suit)

    def set_value(self, value, suit):
        if value < 1 or value > 13:
            raise ValueError("wrong value")
        if suit not in SUITS:
            raise ValueError("wrong suit")

        self.value = value
        self.suit = suit

        if value == 1:
            filename = "A.png"
        elif value == 11:
            filename = "J.png"
        elif value == 12:
            filename = "Q.png"
        elif value == 13:
            filename = "K.png"
        else:
            filename = f"{value}.png"

        self.texture_path = os.path.join("textures", "cards", "cards_wood", self.suit, filename)

    def get_value(self):
        return self.value

    def get_texture_path(self):
        return self.texture_path

class Deck:
    def __init__(self):
        self.cards = []

    def add_card_by_value(self, value, suit):
        self.cards.append(Card(value, suit))

    def add_card(self, card):
        self.cards.append(card)

    def fill_random(self, size):
        for _ in range(size):
            self.add_card_by_value(random.randint(1, 13), random.choice(SUITS))

    def refill_random(self, size):
        self.clear_deck()
        self.fill_random(size)

    def clear_deck(self):
        self.cards.clear()

    def fill_in_order(self, size=52):
        count = 0
        while count < size:
            for suit in SUITS:
                for val in range(1, 14):
                    if count >= size:
                        break
                    self.add_card_by_value(val, suit)
                    count += 1
                if count >= size:
                    break

    def erase(self, index):
        return self.cards.pop(index)

    def __len__(self):
        return len(self.cards)

    def __getitem__(self, i):
        return self.cards[i]

class Chip:
    def __init__(self, value):
        self.value = 0
        self.texture_path = ""
        self.set_value(value)

    def set_value(self, value):
        valid_values = {
            0: "None",
            100: "100.png",
            250: "250.png",
            500: "500.png",
            1000: "1000.png",
            2500: "2500.png",
            10000: "10000.png"
        }

        if value in valid_values:
            self.value = value
            if value == 0:
                self.texture_path = "None"
            else:
                self.texture_path = os.path.join("textures", "chips", valid_values[value])
            return True
        return False

    def get_value(self):
        return self.value

    def get_texture_path(self):
        return self.texture_path

class Player:
    def __init__(self, is_dealer):
        self.deck_in_hand = Deck()
        self.bet = Chip(0)
        self.is_dealer = is_dealer

    def set_bet(self, value):
        self.bet = Chip(value)

    def get_bet(self):
        return self.bet

    def take_card_from_deck(self, other_deck):
        if len(other_deck) == 0:
            raise Exception("empty deck")
        card = other_deck.erase(-1)
        self.deck_in_hand.add_card(card)

    def take_rand_card_from_deck(self, other_deck):
        if len(other_deck) == 0:
            raise Exception("empty deck")
        idx = random.randint(0, len(other_deck) - 1)
        card = other_deck.erase(idx)
        self.deck_in_hand.add_card(card)
        return card

    def take_card(self, card):
        self.deck_in_hand.add_card(card)

    def check_value_in_hand(self):
        total = 0
        aces = 0
        for card in self.deck_in_hand.cards:
            val = card.get_value()
            if val == 1:
                aces += 1
                total += 11
            elif val > 10:
                total += 10
            else:
                total += val

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def clear_deck(self):
        self.deck_in_hand.clear_deck()

    def get_deck(self):
        return self.deck_in_hand
