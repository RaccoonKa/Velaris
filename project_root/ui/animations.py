import pygame
import math

def ease_out_cubic(t):
    return 1 - math.pow(1 - t, 3)

class Animator:
    def __init__(self):
        self.queue = []

    def add(self, img, start_pos, end_pos, on_finish=None, frames=25, start_angle=0, end_angle=0):
        self.queue.append({
            "img": img,
            "start": start_pos,
            "end": end_pos,
            "current": list(start_pos),
            "start_angle": start_angle,
            "end_angle": end_angle,
            "current_angle": start_angle,
            "frame": 0,
            "total_frames": frames,
            "on_finish": on_finish
        })

    def update(self):
        if not self.queue:
            return False

        anim = self.queue[0]
        anim["frame"] += 1
        t = anim["frame"] / anim["total_frames"]

        eased_t = ease_out_cubic(t)

        anim["current"][0] = anim["start"][0] + (anim["end"][0] - anim["start"][0]) * eased_t
        anim["current"][1] = anim["start"][1] + (anim["end"][1] - anim["start"][1]) * eased_t

        anim["current_angle"] = anim["start_angle"] + (anim["end_angle"] - anim["start_angle"]) * eased_t

        if anim["frame"] >= anim["total_frames"]:
            finished_anim = self.queue.pop(0)
            if finished_anim["on_finish"]:
                finished_anim["on_finish"]()
        return True

    def draw(self, surface):
        if self.queue:
            anim = self.queue[0]
            img = anim["img"]

            if anim.get("current_angle", 0) != 0:
                cx = anim["current"][0] + img.get_width() / 2
                cy = anim["current"][1] + img.get_height() / 2

                rotated_img = pygame.transform.rotozoom(img, anim["current_angle"], 1.0)

                rotated_rect = rotated_img.get_rect(center=(cx, cy))
                surface.blit(rotated_img, rotated_rect.topleft)
            else:
                surface.blit(img, anim["current"])

    def clear(self):
        self.queue.clear()

def play_splash_screen(window, clock, vsync, logo_img):
    splash_start_time = pygame.time.get_ticks()
    splash_duration_in = 1000
    splash_duration_hold = 2000
    splash_duration_out = 1500
    splash_total = splash_duration_in + splash_duration_hold + splash_duration_out

    cx, cy = window.get_rect().center
    logo_rect = logo_img.get_rect(center=(cx, cy))

    while True:
        current_time = pygame.time.get_ticks() - splash_start_time

        if current_time < splash_duration_in:
            alpha = int(255 * (current_time / splash_duration_in))
        elif current_time < splash_duration_in + splash_duration_hold:
            alpha = 255
        elif current_time < splash_total:
            alpha = int(255 * (1 - (current_time - splash_duration_in - splash_duration_hold) / splash_duration_out))
        else:
            return True

        window.fill((0, 0, 0))
        logo_img.set_alpha(max(0, min(255, alpha)))
        window.blit(logo_img, logo_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return True

        pygame.display.flip()

        if vsync:
            clock.tick(float(60))
        else:
            clock.tick(float(120))
