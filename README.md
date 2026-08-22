# 🎨 Velaris — Resource & Texture Branch

Welcome to the asset branch of the **Velaris** game project! All graphical and audio materials for the project are uploaded here.

---

## 📌 Main Technical Rules

1. **Graphics format:** strictly `.png` with transparency support (Alpha channel).
2. **File naming:**
   * Only lowercase English letters, numbers, and underscores `_`.
   * **No spaces or Cyrillic characters** in filenames (e.g., use `bg_gold.png`, not `фон золото.png`).
3. **Resolution and proportions:** preserve the original dimensions of the files you are replacing to avoid breaking scaling in Pygame.

---

## 📁 Folder Structure

| Folder | What to upload here | Suggested requirements |
| :--- | :--- | :--- |
| `authors/` | Developer avatars and artwork | Square PNGs, transparent background |
| `backgrounds/` | Backgrounds for the main menu and tables | 1920x1080 (or 16:9), `.png` / `.jpg` |
| `cards/` | Card faces and backs | Cards in fixed proportions by suit/rank |
| `chips/` | Betting chips (`100`, `250`, `500`, `1000`, `2500`, `10000`) | Transparent background, `.png` format |
| `companions/` | Character sprites (Leia and Muza) | High resolution, transparent background |
| `cursors/` | In‑game mouse cursors | `.png` |
| `emotions/` | Emoji and reaction icons for chat | Transparent background |
| `different/` | Logos, button icons, UI elements | `.png` with transparency |
| `sound/` | Sound on/off icons | `.png` with transparency |
