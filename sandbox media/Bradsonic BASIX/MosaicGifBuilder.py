import os
import tkinter as tk
from tkinter import filedialog, messagebox

import pygame
from PIL import Image


class MosaicGifApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mosaic GIF Builder")
        self.root.geometry("560x360")
        self.root.resizable(False, False)

        self.image_paths = []
        self.current_index = 0
        self.original_image = None
        self.preview_frames = []

        # 14 frames, from chunky mosaic to clearer mosaic.
        self.num_frames = 14
        self.start_block = 30
        self.end_block = 5

        # Speed stored as milliseconds per frame.
        self.frame_duration_ms = tk.IntVar(value=120)

        self.build_ui()

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="Mosaic GIF Builder",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=(12, 6))

        desc = tk.Label(
            self.root,
            text=(
                "Load multiple images, preview one at a time in Pygame,\n"
                "then batch export separate non-looping GIFs for all of them."
            ),
            justify="center"
        )
        desc.pack(pady=(0, 10))

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=6)

        self.load_btn = tk.Button(
            button_frame,
            text="Load Images",
            width=16,
            command=self.load_images
        )
        self.load_btn.grid(row=0, column=0, padx=6)

        self.prev_btn = tk.Button(
            button_frame,
            text="Previous Image",
            width=16,
            state="disabled",
            command=self.show_previous_image
        )
        self.prev_btn.grid(row=0, column=1, padx=6)

        self.next_btn = tk.Button(
            button_frame,
            text="Next Image",
            width=16,
            state="disabled",
            command=self.show_next_image
        )
        self.next_btn.grid(row=0, column=2, padx=6)

        preview_export_frame = tk.Frame(self.root)
        preview_export_frame.pack(pady=6)

        self.preview_btn = tk.Button(
            preview_export_frame,
            text="Preview Current",
            width=16,
            state="disabled",
            command=self.launch_preview
        )
        self.preview_btn.grid(row=0, column=0, padx=6)

        self.export_btn = tk.Button(
            preview_export_frame,
            text="Batch Export GIFs",
            width=16,
            state="disabled",
            command=self.export_all_gifs
        )
        self.export_btn.grid(row=0, column=1, padx=6)

        slider_frame = tk.Frame(self.root)
        slider_frame.pack(pady=(14, 6), fill="x", padx=20)

        self.speed_label = tk.Label(
            slider_frame,
            text=f"Frame Duration: {self.frame_duration_ms.get()} ms"
        )
        self.speed_label.pack(anchor="w")

        self.speed_slider = tk.Scale(
            slider_frame,
            from_=40,
            to=500,
            orient="horizontal",
            resolution=5,
            showvalue=False,
            variable=self.frame_duration_ms,
            command=self.on_speed_change,
            length=500
        )
        self.speed_slider.pack(fill="x")

        note = tk.Label(
            self.root,
            text=(
                "Each source image gets its own GIF. Lower ms = faster animation.\n"
                "Preview stops on the final frame. Exported GIFs are saved as separate files."
            ),
            justify="center",
            fg="#444444"
        )
        note.pack(pady=(8, 0))

        self.current_image_label = tk.Label(
            self.root,
            text="No image loaded.",
            fg="#003366"
        )
        self.current_image_label.pack(pady=(10, 4))

        self.status_label = tk.Label(
            self.root,
            text="Ready.",
            fg="#003366"
        )
        self.status_label.pack(pady=(0, 0))

    def on_speed_change(self, _=None):
        self.speed_label.config(
            text=f"Frame Duration: {self.frame_duration_ms.get()} ms"
        )

    def load_images(self):
        paths = filedialog.askopenfilenames(
            title="Choose one or more images",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("All Files", "*.*")
            ]
        )
        if not paths:
            return

        self.image_paths = list(paths)
        self.current_index = 0
        self.load_current_image()

        self.preview_btn.config(state="normal")
        self.export_btn.config(state="normal")
        self.prev_btn.config(state="normal")
        self.next_btn.config(state="normal")

        self.status_label.config(
            text=f"Loaded {len(self.image_paths)} image(s). {self.num_frames} frames will be generated per GIF."
        )

    def load_current_image(self):
        if not self.image_paths:
            return

        path = self.image_paths[self.current_index]

        try:
            image = Image.open(path).convert("RGB")
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not open image.\n\n{exc}")
            return

        self.original_image = image
        self.preview_frames = self.generate_frames(image)

        self.current_image_label.config(
            text=(
                f"Current: {self.current_index + 1}/{len(self.image_paths)}"
                f"  |  {os.path.basename(path)}"
            )
        )

    def show_previous_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self.load_current_image()

    def show_next_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self.load_current_image()

    def generate_frames(self, image):
        frames = []
        block_sizes = self.get_block_sizes()

        for block in block_sizes:
            frames.append(self.apply_mosaic(image, block))

        return frames

    def get_block_sizes(self):
        if self.num_frames == 1:
            return [self.end_block]

        sizes = []
        step = (self.start_block - self.end_block) / (self.num_frames - 1)
        for i in range(self.num_frames):
            value = self.start_block - (step * i)
            sizes.append(max(1, int(round(value))))

        sizes[0] = self.start_block
        sizes[-1] = self.end_block
        return sizes

    @staticmethod
    def apply_mosaic(image, block_size):
        width, height = image.size
        small_w = max(1, width // block_size)
        small_h = max(1, height // block_size)

        reduced = image.resize((small_w, small_h), Image.Resampling.BILINEAR)
        mosaic = reduced.resize((width, height), Image.Resampling.NEAREST)
        return mosaic

    def launch_preview(self):
        if not self.preview_frames:
            messagebox.showwarning("No Frames", "Load image files first.")
            return

        self.root.withdraw()
        try:
            self.run_pygame_preview()
        finally:
            self.root.deiconify()
            self.root.lift()

    def run_pygame_preview(self):
        pygame.init()

        pil_frame = self.preview_frames[0]
        img_w, img_h = pil_frame.size

        max_w = 1000
        max_h = 700
        scale = min(max_w / img_w, max_h / img_h, 1.0)
        display_w = int(img_w * scale)
        display_h = int(img_h * scale)

        window_w = display_w
        window_h = display_h + 70

        screen = pygame.display.set_mode((window_w, window_h))
        pygame.display.set_caption("Pygame Preview - Mosaic GIF")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("arial", 20)
        small_font = pygame.font.SysFont("arial", 16)

        pygame_frames = []
        for frame in self.preview_frames:
            preview_frame = frame
            if scale != 1.0:
                preview_frame = frame.resize((display_w, display_h), Image.Resampling.NEAREST)

            mode = preview_frame.mode
            data = preview_frame.tobytes()
            surface = pygame.image.fromstring(data, preview_frame.size, mode)
            pygame_frames.append(surface)

        running = True
        paused = False
        frame_idx = 0
        last_advance = pygame.time.get_ticks()
        animation_finished = False

        while running:
            now = pygame.time.get_ticks()
            duration = self.frame_duration_ms.get()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_RIGHT:
                        if frame_idx < len(pygame_frames) - 1:
                            frame_idx += 1
                        last_advance = now
                    elif event.key == pygame.K_LEFT:
                        if frame_idx > 0:
                            frame_idx -= 1
                        animation_finished = False
                        last_advance = now

            if not paused and not animation_finished and now - last_advance >= duration:
                if frame_idx < len(pygame_frames) - 1:
                    frame_idx += 1
                else:
                    animation_finished = True
                last_advance = now

            screen.fill((18, 18, 22))
            screen.blit(pygame_frames[frame_idx], (0, 0))

            state_text = "Stopped on final frame" if animation_finished else "Playing"
            info = font.render(
                f"Frame {frame_idx + 1}/{len(pygame_frames)} | {duration} ms | {state_text}",
                True,
                (235, 235, 235)
            )
            help_text = small_font.render(
                "SPACE pause/resume | LEFT/RIGHT step | ESC close preview",
                True,
                (180, 180, 180)
            )
            screen.blit(info, (10, display_h + 10))
            screen.blit(help_text, (10, display_h + 38))

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

    def build_output_path(self, output_folder, image_path):
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        return os.path.join(output_folder, f"{base_name}_mosaic_reveal.gif")

    def export_single_gif(self, image_path, output_folder):
        image = Image.open(image_path).convert("RGB")
        frames = self.generate_frames(image)
        palettized_frames = [frame.convert("P", palette=Image.Palette.ADAPTIVE) for frame in frames]

        save_path = self.build_output_path(output_folder, image_path)
        palettized_frames[0].save(
            save_path,
            save_all=True,
            append_images=palettized_frames[1:],
            duration=self.frame_duration_ms.get(),
            loop=1,
            optimize=False,
            disposal=2
        )
        return save_path

    def export_all_gifs(self):
        if not self.image_paths:
            messagebox.showwarning("No Images", "Load image files first.")
            return

        output_folder = filedialog.askdirectory(title="Choose output folder for GIFs")
        if not output_folder:
            return

        success_count = 0
        failed = []

        for image_path in self.image_paths:
            try:
                self.export_single_gif(image_path, output_folder)
                success_count += 1
            except Exception as exc:
                failed.append(f"{os.path.basename(image_path)}: {exc}")

        if failed:
            messagebox.showwarning(
                "Batch Export Finished",
                f"Exported {success_count} GIF(s).\n\nFailed:\n" + "\n".join(failed[:10])
            )
        else:
            messagebox.showinfo(
                "Batch Export Finished",
                f"Exported {success_count} GIF(s) to:\n{output_folder}"
            )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MosaicGifApp()
    app.run()
