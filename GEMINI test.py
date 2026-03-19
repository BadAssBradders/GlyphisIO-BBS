import pygame
import time

# --- Initialize Pygame ---
pygame.init()

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLACK = (0, 0, 0)
CYAN = (0, 255, 255)
DARK_BLUE = (0, 0, 139)
WHITE = (255, 255, 255)

# --- Font Loading ---
# We'll try to load the custom font, but fall back to the default if it's not found.
try:
    # Ensure "Pixellari.ttf" is in the same directory as this script!
    FONT_PIXEL_LARGE = pygame.font.Font("Pixellari.ttf", 24)
    FONT_PIXEL_MEDIUM = pygame.font.Font("Pixellari.ttf", 18)
    FONT_PIXEL_SMALL = pygame.font.Font("Pixellari.ttf", 14)
    print("Loaded Pixellari.ttf font.")
except FileNotFoundError:
    print("Warning: 'Pixellari.ttf' not found.")
    print("Falling back to default pygame font.")
    FONT_PIXEL_LARGE = pygame.font.Font(None, 30)
    FONT_PIXEL_MEDIUM = pygame.font.Font(None, 24)
    FONT_PIXEL_SMALL = pygame.font.Font(None, 20)

# --- Game Setup ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("GlyphisIO Mail Client")
clock = pygame.time.Clock()

# --- Email Data Structures ---
# We will store emails as dictionaries
inbox = [
    {
        "id": 1,
        "from": "GlyphisIO",
        "subject": "Welcome",
        "body": "Your terminal is now active.\nAll transmissions are monitored.\n-GlyphisIO",
        "read": False,
        "timestamp": time.time() - 3600
    }
]
sent = []

# --- Game State Variables ---
current_view = "inbox"  # "inbox", "sent", "compose"
running = True

# --- Compose Screen State ---
compose_to = "GlyphisIO"
compose_subject = ""
compose_body = ""
active_field = "subject"  # "subject" or "body"

# --- Button Rects (for click detection) ---
# We define these once to use for both drawing and clicking
BUTTONS = {
    "new": pygame.Rect(10, 10, 100, 40),
    "inbox": pygame.Rect(120, 10, 100, 40),
    "sent": pygame.Rect(230, 10, 100, 40),
    "refresh": pygame.Rect(690, 10, 100, 40),
}
COMPOSE_FIELDS = {
    "subject": pygame.Rect(100, 120, 680, 40),
    "body": pygame.Rect(100, 170, 680, 350),
    "send": pygame.Rect(680, 540, 100, 40),
}

# --- AI Reply Stub Function ---
def get_ai_reply(subject, body):
    """
    *** ARTIFICIAL INTELLIGENCE STUB ***
    
    This function is a placeholder for your AI logic.
    You mentioned using spaCy and NLTK. This is where you would
    integrate them.
    
    A real implementation would involve:
    1.  Installing spaCy and NLTK:
        `pip install spacy nltk`
    2.  Downloading models:
        `python -m spacy download en_core_web_sm`
        `python -m nltk.downloader punkt`
    3.  Importing the libraries (at the top of this file):
        `import spacy`
        `import nltk`
        `nlp = spacy.load("en_core_web_sm")`
    4.  Processing the 'body' text:
        `doc = nlp(body)`
    5.  Using spaCy for Named Entity Recognition (NER) to find
        keywords:
        `keywords = [ent.text for ent in doc.ents]`
    6.  Using NLTK or spaCy for sentiment analysis or tokenization.
    7.  Crafting a response based on these findings.

    For now, we just return a simple, keyword-based canned response
    in the style of GlyphisIO.
    """
    print(f"[AI STUB] Processing subject: '{subject}', body: '{body}'")
    
    # Simple keyword-based logic for the stub
    lower_body = body.lower()
    
    if "hello" in lower_body or "hi" in lower_body:
        reply_subject = "Re: " + subject
        reply_body = "01001000 01100101 01101100 01101100 01101111 00101110\n\n(Hello.)\n\n-GlyphisIO"
    elif "help" in lower_body or "question" in lower_body:
        reply_subject = "Re: " + subject
        reply_body = "I cannot 'help' you.\nI can only 'observe' and 'process'.\nState your query.\n\n-GlyphisIO"
    elif "glyphis" in lower_body:
        reply_subject = "Query Acknowledged"
        reply_body = "I am the system.\nAll data flows through me.\nYour query is noted.\n\n-GlyphisIO"
    else:
        reply_subject = "Data Received"
        reply_body = "Your transmission has been logged.\nCorrelation is 4.7%.\nResponse irrelevant.\n\n-GlyphisIO"
    
    # Simulate a small delay for the "AI" to "think"
    pygame.time.delay(1500)

    # Return a new email dictionary
    return {
        "id": len(inbox) + len(sent) + 1,
        "from": "GlyphisIO",
        "subject": reply_subject,
        "body": reply_body,
        "read": False,
        "timestamp": time.time()
    }

# --- Drawing Functions ---

def draw_text(text, font, color, surface, x, y, max_width=None):
    """Helper function to draw text, wrapping if needed."""
    if max_width:
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            if "\n" in word:
                parts = word.split("\n")
                for i, part in enumerate(parts):
                    if i > 0:
                        lines.append(current_line)
                        current_line = part
                    else:
                        test_line = (current_line + " " + part).strip()
                        if font.size(test_line)[0] <= max_width:
                            current_line = test_line
                        else:
                            lines.append(current_line)
                            current_line = part
                continue

            test_line = (current_line + " " + word).strip()
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, color)
            surface.blit(text_surface, (x, y + i * font.get_linesize()))
    else:
        # Handle newlines for non-wrapped text
        lines = text.split('\n')
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, color)
            surface.blit(text_surface, (x, y + i * font.get_linesize()))

def draw_ui():
    """Draws the main navigation buttons and layout lines."""
    # Top bar
    pygame.draw.rect(screen, DARK_BLUE, (0, 0, SCREEN_WIDTH, 60), 2)
    
    # Draw buttons
    for name, rect in BUTTONS.items():
        # Highlight if it's the current view
        if name == current_view:
            pygame.draw.rect(screen, CYAN, rect, 2)
        else:
            pygame.draw.rect(screen, DARK_BLUE, rect, 2)
        
        draw_text(name.capitalize(), FONT_PIXEL_MEDIUM, CYAN, screen, rect.x + 15, rect.y + 10)

def draw_inbox_view():
    """Draws the list of emails in the inbox."""
    draw_text("Inbox", FONT_PIXEL_LARGE, CYAN, screen, 10, 70)
    
    # Draw list header
    pygame.draw.line(screen, DARK_BLUE, (10, 100), (790, 100), 2)
    draw_text("From", FONT_PIXEL_MEDIUM, CYAN, screen, 20, 110)
    draw_text("Subject", FONT_PIXEL_MEDIUM, CYAN, screen, 200, 110)
    pygame.draw.line(screen, DARK_BLUE, (10, 130), (790, 130), 2)
    
    # Draw email items
    y_offset = 140
    # Sort emails by timestamp, newest first
    sorted_inbox = sorted(inbox, key=lambda e: e['timestamp'], reverse=True)
    
    for email in sorted_inbox:
        color = WHITE if email['read'] else CYAN
        draw_text(email['from'], FONT_PIXEL_SMALL, color, screen, 20, y_offset)
        
        subject_text = email['subject']
        if len(subject_text) > 60:
            subject_text = subject_text[:57] + "..."
        draw_text(subject_text, FONT_PIXEL_SMALL, color, screen, 200, y_offset)
        
        y_offset += 25
        if y_offset > SCREEN_HEIGHT - 20:
            break

def draw_sent_view():
    """Draws the list of emails in the sent folder."""
    draw_text("Sent", FONT_PIXEL_LARGE, CYAN, screen, 10, 70)
    
    # Draw list header
    pygame.draw.line(screen, DARK_BLUE, (10, 100), (790, 100), 2)
    draw_text("To", FONT_PIXEL_MEDIUM, CYAN, screen, 20, 110)
    draw_text("Subject", FONT_PIXEL_MEDIUM, CYAN, screen, 200, 110)
    pygame.draw.line(screen, DARK_BLUE, (10, 130), (790, 130), 2)
    
    # Draw email items
    y_offset = 140
    sorted_sent = sorted(sent, key=lambda e: e['timestamp'], reverse=True)

    for email in sorted_sent:
        draw_text(email['to'], FONT_PIXEL_SMALL, WHITE, screen, 20, y_offset)
        
        subject_text = email['subject']
        if len(subject_text) > 60:
            subject_text = subject_text[:57] + "..."
        draw_text(subject_text, FONT_PIXEL_SMALL, WHITE, screen, 200, y_offset)
        
        y_offset += 25
        if y_offset > SCREEN_HEIGHT - 20:
            break

def draw_compose_view():
    """Draws the new email composition screen."""
    draw_text("New Message", FONT_PIXEL_LARGE, CYAN, screen, 10, 70)
    
    # Draw fields
    draw_text("To:", FONT_PIXEL_MEDIUM, CYAN, screen, 20, 130)
    draw_text(compose_to, FONT_PIXEL_MEDIUM, WHITE, screen, 105, 130)
    
    draw_text("Subject:", FONT_PIXEL_MEDIUM, CYAN, screen, 20, 180)
    
    draw_text("Body:", FONT_PIXEL_MEDIUM, CYAN, screen, 20, 230)

    # Draw field boxes
    subject_rect = COMPOSE_FIELDS["subject"]
    body_rect = COMPOSE_FIELDS["body"]
    send_rect = COMPOSE_FIELDS["send"]

    # Subject Box
    pygame.draw.rect(screen, DARK_BLUE, subject_rect.inflate(4, 4), 2)
    draw_text(compose_subject, FONT_PIXEL_MEDIUM, WHITE, screen, subject_rect.x + 5, subject_rect.y + 10)
    
    # Body Box
    pygame.draw.rect(screen, DARK_BLUE, body_rect.inflate(4, 4), 2)
    # Render multi-line body text
    draw_text(compose_body, FONT_PIXEL_MEDIUM, WHITE, screen, body_rect.x + 5, body_rect.y + 10, body_rect.width - 10)
    
    # Send Button
    pygame.draw.rect(screen, DARK_BLUE, send_rect, 2)
    draw_text("Send", FONT_PIXEL_MEDIUM, CYAN, screen, send_rect.x + 25, send_rect.y + 10)
    
    # Blinking cursor
    if time.time() % 1 > 0.5:
        if active_field == "subject":
            cursor_x = subject_rect.x + 5 + FONT_PIXEL_MEDIUM.size(compose_subject)[0]
            cursor_y = subject_rect.y + 8
            pygame.draw.line(screen, CYAN, (cursor_x, cursor_y), (cursor_x, cursor_y + 20), 2)
        
        elif active_field == "body":
            # This is complex. We need to find the end of the last line.
            lines = compose_body.split('\n')
            last_line = lines[-1] if lines else ""
            
            # Simple cursor: just place at end of text
            # A perfect cursor requires re-calculating the text wrapping,
            # which is very complex. We'll use a simpler approach.
            cursor_y = body_rect.y + 10 + (len(lines) - 1) * FONT_PIXEL_MEDIUM.get_linesize()
            cursor_x = body_rect.x + 5 + FONT_PIXEL_MEDIUM.size(last_line)[0]

            # Constrain cursor to box
            if cursor_x > body_rect.right - 10:
                cursor_x = body_rect.x + 5
                cursor_y += FONT_PIXEL_MEDIUM.get_linesize()

            if cursor_y < body_rect.bottom - 20:
                pygame.draw.line(screen, CYAN, (cursor_x, cursor_y), (cursor_x, cursor_y + 20), 2)


# --- Main Game Loop ---
while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # --- Mouse Click Handling ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                pos = event.pos
                
                # Check top nav buttons
                for name, rect in BUTTONS.items():
                    if rect.collidepoint(pos):
                        if name == "new":
                            current_view = "compose"
                            # Reset compose fields
                            compose_subject = ""
                            compose_body = ""
                            active_field = "subject"
                        elif name == "inbox":
                            current_view = "inbox"
                        elif name == "sent":
                            current_view = "sent"
                        elif name == "refresh":
                            print("Refresh clicked (no action)")
                
                # Check compose screen interactions
                if current_view == "compose":
                    if COMPOSE_FIELDS["subject"].collidepoint(pos):
                        active_field = "subject"
                    elif COMPOSE_FIELDS["body"].collidepoint(pos):
                        active_field = "body"
                    elif COMPOSE_FIELDS["send"].collidepoint(pos):
                        print("Send button clicked!")
                        
                        # 1. Create the 'sent' email object
                        sent_email = {
                            "id": len(inbox) + len(sent) + 1,
                            "to": compose_to,
                            "from": "Player",
                            "subject": compose_subject,
                            "body": compose_body,
                            "read": True,
                            "timestamp": time.time()
                        }
                        sent.append(sent_email)
                        
                        # 2. Call the AI to get a reply
                        print("Contacting GlyphisIO...")
                        # This part will block while the "AI" thinks
                        ai_reply_email = get_ai_reply(compose_subject, compose_body)
                        
                        # 3. Add the new reply to the inbox
                        inbox.append(ai_reply_email)
                        print("Reply received from GlyphisIO.")
                        
                        # 4. Switch view to inbox to see the new mail
                        current_view = "inbox"

        # --- Keyboard Input Handling (for compose view) ---
        if event.type == pygame.KEYDOWN and current_view == "compose":
            if active_field == "subject":
                if event.key == pygame.K_BACKSPACE:
                    compose_subject = compose_subject[:-1]
                elif event.key == pygame.K_TAB:
                    active_field = "body"
                elif event.key != pygame.K_RETURN:  # No newlines in subject
                    compose_subject += event.unicode
            
            elif active_field == "body":
                if event.key == pygame.K_BACKSPACE:
                    compose_body = compose_body[:-1]
                elif event.key == pygame.K_RETURN:
                    compose_body += "\n"
                elif event.key == pygame.K_TAB:
                    pass # Don't tab out of the body field
                else:
                    compose_body += event.unicode

    # --- Drawing Logic ---
    screen.fill(BLACK)  # Clear screen
    
    draw_ui()  # Draw nav
    
    # Draw current view
    if current_view == "inbox":
        draw_inbox_view()
    elif current_view == "sent":
        draw_sent_view()
    elif current_view == "compose":
        draw_compose_view()

    # --- Update Display ---
    pygame.display.flip()
    
    # --- Frame Rate ---
    clock.tick(30)  # Cap at 30 FPS

# --- Quit Pygame ---
pygame.quit()