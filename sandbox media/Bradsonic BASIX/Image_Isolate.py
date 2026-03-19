import os
import sys
import pygame
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageGrab

# ----------------------------
# Configuration
# ----------------------------
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
TOP_BAR_HEIGHT = 60
BG_COLOUR = (30, 30, 35)
TOP_BAR_COLOUR = (45, 45, 55)
BUTTON_COLOUR = (70, 70, 90)
BUTTON_HOVER_COLOUR = (95, 95, 120)
BUTTON_TEXT_COLOUR = (240, 240, 240)
SELECTION_COLOUR = (0, 255, 255)
SELECTION_FILL = (0, 255, 255, 50)
IMAGE_BG = (15, 15, 15)

# ----------------------------
# Tkinter root (hidden)
# ----------------------------
root = tk.Tk()
root.withdraw()

# ----------------------------
# Pygame setup
# ----------------------------
pygame.init()
pygame.display.set_caption("Image Selection Crop Tool")
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20)
small_font = pygame.font.SysFont("arial", 16)

# ----------------------------
# Button class
# ----------------------------
class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback

    def draw(self, surface, mouse_pos):
        colour = BUTTON_HOVER_COLOUR if self.rect.collidepoint(mouse_pos) else BUTTON_COLOUR
        pygame.draw.rect(surface, colour, self.rect, border_radius=8)
        label = font.render(self.text, True, BUTTON_TEXT_COLOUR)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

# ----------------------------
# App state
# ----------------------------
image_path = None
pil_image = None
pygame_image = None
display_image = None

# Image display placement and scaling
image_draw_rect = pygame.Rect(0, 0, 0, 0)
image_scale = 1.0

# Selection in DISPLAY coordinates relative to image area
selection_rect = None

# Interaction states
creating_selection = False
dragging_selection = False
selection_start = None
drag_offset = (0, 0)

status_message = "Click 'Open Image' or press Ctrl+V to paste an image."

# ----------------------------
# Utility functions
# ----------------------------
def set_status(message):
    global status_message
    status_message = message


def load_pil_image(pil, source_name="clipboard image"):
    global image_path, pil_image, pygame_image, display_image, image_draw_rect, image_scale, selection_rect

    try:
        pil = pil.convert("RGBA")
        pil_image = pil
        image_path = source_name

        mode = pil.mode
        size = pil.size
        data = pil.tobytes()
        pygame_image = pygame.image.fromstring(data, size, mode)

        fit_image_to_window()
        selection_rect = None
        set_status(f"Loaded: {source_name}")

    except Exception as e:
        messagebox.showerror("Error", f"Could not load image:\n{e}")
        set_status("Failed to load image.")


def load_image():
    path = filedialog.askopenfilename(
        title="Open Image",
        filetypes=[
            ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp"),
            ("All files", "*.*")
        ]
    )

    if not path:
        return

    try:
        pil = Image.open(path)
        load_pil_image(pil, os.path.basename(path))
    except Exception as e:
        messagebox.showerror("Error", f"Could not load image:\n{e}")
        set_status("Failed to load image.")


def paste_clipboard_image():
    try:
        grabbed = ImageGrab.grabclipboard()

        if grabbed is None:
            messagebox.showinfo("Clipboard", "No image found in the clipboard.")
            set_status("Clipboard does not contain an image.")
            return

        # Sometimes clipboard contains a list of file paths instead of a direct image
        if isinstance(grabbed, list):
            image_files = [p for p in grabbed if os.path.isfile(p) and p.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"))]
            if image_files:
                pil = Image.open(image_files[0])
                load_pil_image(pil, os.path.basename(image_files[0]))
                return
            else:
                messagebox.showinfo("Clipboard", "Clipboard contains files, but no supported image file was found.")
                set_status("Clipboard had files, but no supported image.")
                return

        if isinstance(grabbed, Image.Image):
            load_pil_image(grabbed, "clipboard_image")
            return

        messagebox.showinfo("Clipboard", "Clipboard content is not a supported image.")
        set_status("Clipboard content is not a supported image.")

    except Exception as e:
        messagebox.showerror("Error", f"Could not paste clipboard image:\n{e}")
        set_status("Failed to paste clipboard image.")


def fit_image_to_window():
    global display_image, image_draw_rect, image_scale

    if pygame_image is None:
        return

    available_w = WINDOW_WIDTH - 40
    available_h = WINDOW_HEIGHT - TOP_BAR_HEIGHT - 40

    img_w, img_h = pygame_image.get_size()
    scale_x = available_w / img_w
    scale_y = available_h / img_h
    image_scale = min(scale_x, scale_y, 1.0)

    new_w = int(img_w * image_scale)
    new_h = int(img_h * image_scale)

    display_image = pygame.transform.smoothscale(pygame_image, (new_w, new_h))

    x = (WINDOW_WIDTH - new_w) // 2
    y = TOP_BAR_HEIGHT + ((WINDOW_HEIGHT - TOP_BAR_HEIGHT - new_h) // 2)
    image_draw_rect = pygame.Rect(x, y, new_w, new_h)


def clamp_rect_to_image(rect):
    if rect is None:
        return None

    r = rect.copy()

    if r.left < image_draw_rect.left:
        r.left = image_draw_rect.left
    if r.top < image_draw_rect.top:
        r.top = image_draw_rect.top
    if r.right > image_draw_rect.right:
        r.right = image_draw_rect.right
    if r.bottom > image_draw_rect.bottom:
        r.bottom = image_draw_rect.bottom

    if r.width < 1:
        r.width = 1
    if r.height < 1:
        r.height = 1

    return r


def normalised_rect(start_pos, end_pos):
    x1, y1 = start_pos
    x2, y2 = end_pos
    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return pygame.Rect(left, top, width, height)


def save_selection():
    global selection_rect

    if pil_image is None:
        messagebox.showinfo("No image", "Please open or paste an image first.")
        return

    if selection_rect is None or selection_rect.width < 2 or selection_rect.height < 2:
        messagebox.showinfo("No selection", "Please create a selection first.")
        return

    try:
        rel_x = selection_rect.x - image_draw_rect.x
        rel_y = selection_rect.y - image_draw_rect.y
        rel_w = selection_rect.width
        rel_h = selection_rect.height

        orig_x = int(rel_x / image_scale)
        orig_y = int(rel_y / image_scale)
        orig_w = int(rel_w / image_scale)
        orig_h = int(rel_h / image_scale)

        img_w, img_h = pil_image.size
        orig_x = max(0, min(orig_x, img_w - 1))
        orig_y = max(0, min(orig_y, img_h - 1))
        orig_w = max(1, min(orig_w, img_w - orig_x))
        orig_h = max(1, min(orig_h, img_h - orig_y))

        cropped = pil_image.crop((orig_x, orig_y, orig_x + orig_w, orig_y + orig_h))

        save_path = filedialog.asksaveasfilename(
            title="Save Selection As PNG",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile="selection.png"
        )

        if not save_path:
            return

        cropped.save(save_path, "PNG")
        set_status(f"Saved selection to: {save_path}")
        messagebox.showinfo("Saved", f"Selection saved successfully:\n{save_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Could not save selection:\n{e}")
        set_status("Failed to save selection.")


def clear_selection():
    global selection_rect
    selection_rect = None
    set_status("Selection cleared.")

# ----------------------------
# Buttons
# ----------------------------
buttons = [
    Button(20, 12, 140, 36, "Open Image", load_image),
    Button(180, 12, 150, 36, "Paste Image", paste_clipboard_image),
    Button(350, 12, 160, 36, "Save Selection", save_selection),
    Button(530, 12, 140, 36, "Clear Selection", clear_selection),
]

# ----------------------------
# Main loop
# ----------------------------
running = True

while running:
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        for button in buttons:
            button.handle_event(event)

        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            if event.key == pygame.K_ESCAPE:
                running = False

            # Ctrl+V paste support
            elif event.key == pygame.K_v and (mods & pygame.KMOD_CTRL):
                paste_clipboard_image()

        if pil_image is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if image_draw_rect.collidepoint(event.pos):
                    if selection_rect and selection_rect.collidepoint(event.pos):
                        dragging_selection = True
                        drag_offset = (event.pos[0] - selection_rect.x, event.pos[1] - selection_rect.y)
                    else:
                        creating_selection = True
                        selection_start = event.pos
                        selection_rect = pygame.Rect(event.pos[0], event.pos[1], 0, 0)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                creating_selection = False
                dragging_selection = False

                if selection_rect is not None:
                    selection_rect = clamp_rect_to_image(selection_rect)

                    if selection_rect.width < 2 or selection_rect.height < 2:
                        selection_rect = None

            elif event.type == pygame.MOUSEMOTION:
                if creating_selection and selection_start:
                    new_rect = normalised_rect(selection_start, event.pos)
                    selection_rect = new_rect.clip(image_draw_rect)

                elif dragging_selection and selection_rect is not None:
                    new_x = event.pos[0] - drag_offset[0]
                    new_y = event.pos[1] - drag_offset[1]
                    moved = pygame.Rect(new_x, new_y, selection_rect.width, selection_rect.height)
                    selection_rect = clamp_rect_to_image(moved)

    # ----------------------------
    # Drawing
    # ----------------------------
    screen.fill(BG_COLOUR)

    pygame.draw.rect(screen, TOP_BAR_COLOUR, (0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT))
    for button in buttons:
        button.draw(screen, mouse_pos)

    if display_image is not None:
        pygame.draw.rect(screen, IMAGE_BG, image_draw_rect.inflate(10, 10))
        screen.blit(display_image, image_draw_rect.topleft)

    if selection_rect is not None:
        overlay = pygame.Surface((selection_rect.width, selection_rect.height), pygame.SRCALPHA)
        overlay.fill(SELECTION_FILL)
        screen.blit(overlay, selection_rect.topleft)
        pygame.draw.rect(screen, SELECTION_COLOUR, selection_rect, 2)

        size_text = small_font.render(
            f"{selection_rect.width} x {selection_rect.height}px (display)",
            True,
            (255, 255, 255)
        )
        text_pos = (selection_rect.x, max(TOP_BAR_HEIGHT + 5, selection_rect.y - 22))
        screen.blit(size_text, text_pos)

    status_surface = small_font.render(status_message, True, (220, 220, 220))
    screen.blit(status_surface, (20, WINDOW_HEIGHT - 28))

    help_text = "Open an image, or press Ctrl+V to paste one. Drag to create a selection, drag inside it to move it, then save as PNG."
    help_surface = small_font.render(help_text, True, (180, 180, 180))
    screen.blit(help_surface, (20, TOP_BAR_HEIGHT + 5))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()