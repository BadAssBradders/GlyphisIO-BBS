import pygame
import sys

# Color data from the image
COLOR_PALETTE = {
    0: "#E5E5E5", 1: "#00FFFF", 2: "#FF00FF", 3: "#0044BB", 4: "#3333CC",
    5: "#BFFFBF", 6: "#112255", 7: "#FFCC11", 8: "#DDCB99", 9: "#F5F5DC",
    10: "#000000", 11: "#116655", 12: "#EE8822", 13: "#33BB11", 14: "#333333",
    15: "#444444", 16: "#FF0000", 17: "#990000", 18: "#BB2222", 19: "#FF5566",
    20: "#FF8866", 21: "#FFFF22", 22: "#FFBB11", 23: "#00FF00", 24: "#445544",
    25: "#22EEFF", 26: "#55CCBB", 27: "#FF99BB", 28: "#77BBEE"
}

# Configuration
WIDTH, HEIGHT = 450, 850
MARGIN = 10
SWATCH_HEIGHT = 22
FONT_SIZE = 18

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CGA+ OS MODE BRADSONIC BASIX")
font = pygame.font.SysFont("monospace", FONT_SIZE, bold=True)
title_font = pygame.font.SysFont("monospace", 20, bold=True)

def draw_swatches():
    screen.fill((200, 200, 200)) # Light grey background
    
    # Draw Title
    title_surf = title_font.render("CGA+ OS MODE BRADSONIC BASIX", True, (0, 0, 0))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 20))
    
    start_y = 60
    for i in range(29):
        hex_color = COLOR_PALETTE[i]
        y_pos = start_y + (i * (SWATCH_HEIGHT + 5))
        
        # Draw Index Number
        num_text = font.render(f"{i:2}", True, (0, 0, 0))
        screen.blit(num_text, (20, y_pos))
        
        # Draw Color Box (with black border)
        pygame.draw.rect(screen, (0, 0, 0), (60, y_pos, 200, SWATCH_HEIGHT))
        pygame.draw.rect(screen, hex_color, (62, y_pos + 2, 196, SWATCH_HEIGHT - 4))
        
        # Draw Hex Label
        hex_text = font.render(hex_color, True, (50, 50, 50))
        screen.blit(hex_text, (275, y_pos))

# Main Loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    draw_swatches()
    pygame.display.flip()

pygame.quit()
sys.exit()