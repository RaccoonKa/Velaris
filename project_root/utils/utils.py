import pygame
import math
import os
import sys



def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')

    return os.path.join(base_path, relative_path)

class Config:
    WIDTH = 1920
    HEIGHT = 1080
    SCALE = 1.0

    @classmethod
    def init(cls):
        info = pygame.display.Info()
        cls.WIDTH, cls.HEIGHT = info.current_w, info.current_h
        scale_x = cls.WIDTH / 1920
        scale_y = cls.HEIGHT / 1080
        cls.SCALE = min(scale_x, scale_y)

def sc(val):
    return int(val * Config.SCALE)

def load_img(path, target_size=None):
    try:
        full_path = resource_path(path)
        img = pygame.image.load(full_path).convert_alpha()
        if target_size:
            return pygame.transform.smoothscale(img, target_size)
        return pygame.transform.smoothscale(
            img, (sc(img.get_width()), sc(img.get_height()))
        )
    except Exception:
        return pygame.Surface((sc(10), sc(10)), pygame.SRCALPHA)

def draw_alpha_rect(surface, color, rect, border_color=(0,0,0), border_width=2, border_radius=0):
    shape_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(shape_surf, color, shape_surf.get_rect(), border_radius=border_radius)
    surface.blit(shape_surf, (rect[0], rect[1]))

    if border_width > 0:
        if border_color == "gradient":
            border_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (255, 255, 255), border_surf.get_rect(), border_width, border_radius=border_radius)
            grad_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
            c1, c2 = (255, 215, 0), (184, 134, 11)
            for y in range(rect[3]):
                ratio = y / max(1, rect[3] - 1)
                c = [c1[i] + (c2[i] - c1[i]) * ratio for i in range(3)]
                pygame.draw.line(grad_surf, c, (0, y), (rect[2], y))
            grad_surf.blit(border_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(grad_surf, (rect[0], rect[1]))
        else:
            border_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, border_color, border_surf.get_rect(), border_width, border_radius=border_radius)
            surface.blit(border_surf, (rect[0], rect[1]))

def draw_gradient_circle(surface, center, radius):
    diam = radius * 2
    circle_surf = pygame.Surface((diam, diam), pygame.SRCALPHA)
    pygame.draw.circle(circle_surf, (255, 255, 255), (radius, radius), radius)

    grad_surf = pygame.Surface((diam, diam), pygame.SRCALPHA)
    c1, c2 = (255, 215, 0), (184, 134, 11)
    for y in range(diam):
        ratio = y / max(1, diam - 1)
        c = [c1[i] + (c2[i] - c1[i]) * ratio for i in range(3)]
        pygame.draw.line(grad_surf, c, (0, y), (diam, y))

    grad_surf.blit(circle_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(grad_surf, (center[0] - radius, center[1] - radius))

def draw_text(surface, text, font, text_color, outline_color, pos, outline_width=0):
    txt_surf = font.render(text, True, (255,255,255) if text_color == "gradient" else text_color)
    outline_width = int(outline_width)
    if outline_width > 0:
        out_surf = font.render(text, True, outline_color)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx*dx + dy*dy <= outline_width*outline_width:
                    surface.blit(out_surf, (pos[0] + dx, pos[1] + dy))

    if text_color == "gradient":
        w, h = txt_surf.get_size()
        if h > 0 and w > 0:
            grad_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            c1, c2 = (255, 215, 0), (184, 134, 11)
            for y in range(h):
                ratio = y / max(1, h - 1)
                c = [c1[i] + (c2[i] - c1[i]) * ratio for i in range(3)]
                pygame.draw.line(grad_surf, c, (0, y), (w, y))
            grad_surf.blit(txt_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(grad_surf, pos)
        else:
            surface.blit(txt_surf, pos)
    else:
        surface.blit(txt_surf, pos)

def draw_text_centered(surface, text, font, text_color, outline_color, rect, outline_width=0, time_ms=0):
    txt_surf = font.render(text, True, (255,255,255) if text_color in ["gradient", "animated_gradient"] else text_color)
    txt_rect = txt_surf.get_rect(center=(rect[0] + rect[2]//2, rect[1] + rect[3]//2))
    outline_width = int(outline_width)
    if outline_width > 0:
        out_surf = font.render(text, True, outline_color)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx*dx + dy*dy <= outline_width*outline_width:
                    surface.blit(out_surf, (txt_rect.x + dx, txt_rect.y + dy))

    if text_color in ["gradient", "animated_gradient"]:
        w, h = txt_surf.get_size()
        if h > 0 and w > 0:
            grad_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            c1, c2 = (255, 215, 0), (184, 134, 11)

            if text_color == "animated_gradient":
                offset = (time_ms / 1000.0) * 2.0
                for y in range(h):
                    ratio = (math.sin(y / max(1, h - 1) * math.pi + offset) + 1) / 2
                    c = [c1[i] + (c2[i] - c1[i]) * ratio for i in range(3)]
                    pygame.draw.line(grad_surf, c, (0, y), (w, y))
            else:
                for y in range(h):
                    ratio = y / max(1, h - 1)
                    c = [c1[i] + (c2[i] - c1[i]) * ratio for i in range(3)]
                    pygame.draw.line(grad_surf, c, (0, y), (w, y))

            grad_surf.blit(txt_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(grad_surf, txt_rect.topleft)
        else:
            surface.blit(txt_surf, txt_rect.topleft)
    else:
        surface.blit(txt_surf, txt_rect.topleft)

def draw_gold_gradient_text(surface, text, font, pos):
    draw_text(surface, text, font, "gradient", (0,0,0), pos, 0)
