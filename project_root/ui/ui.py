import pygame

from utils.utils import resource_path

class Button:
    def __init__(self, x, y, width, height, window):
        self.rect = pygame.Rect(x, y, width, height)
        self.window = window
        self.button_color = (255, 255, 255)
        self.border_color = (0, 0, 0)
        self.border_size = 0
        self.image = None
        self.border_set = False

    def set_button_color(self, color):
        self.button_color = color

    def set_button_texture(self, image_path):
        try:
            full_path = resource_path(image_path)
            self.image = pygame.image.load(full_path).convert_alpha()
            self.image = pygame.transform.scale(
                self.image, (self.rect.width, self.rect.height)
            )
        except (AttributeError, FileNotFoundError):
            pass

    def set_border(self, size, color):
        self.border_size = size
        self.border_color = color
        self.border_set = True

    def check_mouse_click(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self):
        if self.border_set:
            pygame.draw.rect(self.window, self.border_color, self.rect)
            inner_rect = self.rect.inflate(-self.border_size * 2, -self.border_size * 2)

            if self.image:
                self.window.blit(self.image, inner_rect.topleft)
            else:
                pygame.draw.rect(self.window, self.button_color, inner_rect)
        else:
            if self.image:
                self.window.blit(self.image, self.rect.topleft)
            else:
                pygame.draw.rect(self.window, self.button_color, self.rect)
