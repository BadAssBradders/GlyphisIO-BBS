import os
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
from PIL import Image
import pygame

# The exact BRADSONIC BASIX Palette
PALETTE_HEX = [
    "#E5E5E5", "#00FFFF", "#FF00FF", "#0044BB", "#3333CC",
    "#BFFFBF", "#112255", "#FFCC11", "#DDCB99", "#F5F5DC",
    "#000000", "#116655", "#EE8822", "#33BB11", "#333333",
    "#444444", "#FF0000", "#990000", "#BB2222", "#FF5566",
    "#FF8866", "#FFFF22", "#FFBB11", "#00FF00", "#445544",
    "#22EEFF", "#55CCBB", "#FF99BB", "#77BBEE"
]


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


RGB_PALETTE = np.array([hex_to_rgb(h) for h in PALETTE_HEX], dtype=np.float32)


def convert_image_to_palette(image_path):
    """
    Load an image, convert every pixel to the nearest palette colour,
    and return both the PIL image and the save path.
    """
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img, dtype=np.float32)

    h, w, _ = img_array.shape
    pixels = img_array.reshape(-1, 3)

    # Euclidean distance to palette colours
    distances = np.linalg.norm(pixels[:, np.newaxis] - RGB_PALETTE, axis=2)
    nearest_indices = np.argmin(distances, axis=1)

    new_pixels = RGB_PALETTE[nearest_indices].astype(np.uint8)
    new_img_array = new_pixels.reshape((h, w, 3))
    output_img = Image.fromarray(new_img_array)

    base, ext = os.path.splitext(image_path)
    save_path = f"{base}_BRADSONIC{ext}"
    output_img.save(save_path)

    return output_img, save_path


def pil_to_pygame(pil_img):
    """
    Convert a PIL image into a pygame Surface.
    """
    mode = pil_img.mode
    size = pil_img.size
    data = pil_img.tobytes()

    return pygame.image.fromstring(data, size, mode)


def scale_surface_to_width(surface, max_width):
    """
    Scale a pygame surface to fit a maximum width while keeping aspect ratio.
    """
    w, h = surface.get_size()
    if w <= max_width:
        return surface

    scale = max_width / w
    new_w = int(w * scale)
    new_h = int(h * scale)
    return pygame.transform.smoothscale(surface, (new_w, new_h))


def choose_files():
    """
    Use tkinter only for the file picker.
    """
    root = tk.Tk()
    root.withdraw()
    root.update()

    file_paths = filedialog.askopenfilenames(
        title="Select Images",
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.webp")]
    )

    root.destroy()
    return list(file_paths)


def main():
    file_paths = choose_files()

    if not file_paths:
        print("No files selected.")
        return

    converted_items = []

    # Convert first
    for path in file_paths:
        try:
            converted_pil, save_path = convert_image_to_palette(path)
            converted_items.append({
                "original_path": path,
                "save_path": save_path,
                "pil_image": converted_pil
            })
            print(f"Processed: {os.path.basename(path)}")
        except Exception as e:
            print(f"Failed to process {path}: {e}")

    if not converted_items:
        messagebox.showerror("Error", "No images were successfully processed.")
        return

    # Start pygame viewer
    pygame.init()
    pygame.display.set_caption("BRADSONIC Converted Image Viewer")

    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 700
    BG = (10, 10, 10)
    PANEL = (25, 25, 25)
    TEXT = (0, 255, 255)
    SUBTEXT = (200, 200, 200)
    BORDER = (255, 0, 255)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("couriernew", 20)
    small_font = pygame.font.SysFont("couriernew", 16)

    # Pre-build surfaces
    max_image_width = SCREEN_WIDTH - 80
    spacing = 30
    header_height = 55

    render_items = []
    y_cursor = 20

    for item in converted_items:
        surface = pil_to_pygame(item["pil_image"])
        surface = scale_surface_to_width(surface, max_image_width)

        filename = os.path.basename(item["save_path"])
        label_surface = font.render(filename, True, TEXT)

        w, h = surface.get_size()

        render_items.append({
            "label": label_surface,
            "subtext": small_font.render(
                f"{w}x{h}", True, SUBTEXT
            ),
            "image": surface,
            "y": y_cursor,
            "block_height": label_surface.get_height() + 8 + h + spacing
        })

        y_cursor += label_surface.get_height() + 8 + h + spacing

    total_content_height = y_cursor
    scroll_y = 0
    scroll_speed = 40

    running = True
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * scroll_speed

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    scroll_y += scroll_speed
                elif event.key == pygame.K_UP:
                    scroll_y -= scroll_speed
                elif event.key == pygame.K_PAGEDOWN:
                    scroll_y += 300
                elif event.key == pygame.K_PAGEUP:
                    scroll_y -= 300
                elif event.key == pygame.K_HOME:
                    scroll_y = 0
                elif event.key == pygame.K_END:
                    scroll_y = total_content_height

        max_scroll = max(0, total_content_height - (SCREEN_HEIGHT - header_height))
        scroll_y = max(0, min(scroll_y, max_scroll))

        screen.fill(BG)

        # Header
        pygame.draw.rect(screen, PANEL, (0, 0, SCREEN_WIDTH, header_height))
        pygame.draw.line(screen, BORDER, (0, header_height), (SCREEN_WIDTH, header_height), 2)

        title = font.render("BRADSONIC Converted Images", True, TEXT)
        help_text = small_font.render(
            "Mouse wheel / Up Down / Page Up Page Down / Home End",
            True,
            SUBTEXT
        )

        screen.blit(title, (20, 10))
        screen.blit(help_text, (20, 30))

        # Content area
        for item in render_items:
            draw_y = item["y"] - scroll_y + header_height

            # Cull off-screen items for speed
            if draw_y + item["block_height"] < header_height or draw_y > SCREEN_HEIGHT:
                continue

            label = item["label"]
            subtext = item["subtext"]
            image = item["image"]

            img_x = 40
            label_x = 40
            label_y = draw_y
            img_y = label_y + label.get_height() + 8

            # Panel behind each entry
            panel_rect = pygame.Rect(
                20,
                label_y - 8,
                SCREEN_WIDTH - 40,
                label.get_height() + 16 + image.get_height() + 10
            )
            pygame.draw.rect(screen, PANEL, panel_rect)
            pygame.draw.rect(screen, BORDER, panel_rect, 2)

            screen.blit(label, (label_x, label_y))
            screen.blit(subtext, (SCREEN_WIDTH - 140, label_y + 2))
            screen.blit(image, (img_x, img_y))

        pygame.display.flip()

    pygame.quit()

    # Friendly little popup after closing
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Done",
        f"Processed and saved {len(converted_items)} image(s).\n"
        f"Close this box to finish."
    )
    root.destroy()


if __name__ == "__main__":
    main()