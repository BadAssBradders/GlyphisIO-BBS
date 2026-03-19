"""
WOLF PRO : BRADSONIC-TELCO TELEBASE — Standalone School Database Viewer

Run directly:  python school_database_standalone.py
Starts at the login screen (admin / password).

Also importable: SchoolDatabaseApp can be instantiated and driven from OS_Mode.
"""
import os
import sys
import math
import time
import json
import random
from typing import Any, Dict, List, Optional, Tuple

import pygame

# ---------------------------------------------------------------------------
# PIL (optional — needed for animated GIF mugshots)
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageSequence
    _pil_available = True
except ImportError:
    _pil_available = False

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SCHOOL_HACK_DIR = _SCRIPT_DIR  # This file lives in School_Hack/
_DATA_DIR = os.path.dirname(os.path.dirname(_SCHOOL_HACK_DIR))  # Up to Data/

def _data_path(*parts: str) -> str:
    """Resolve a path relative to the Data/ folder."""
    return os.path.join(_DATA_DIR, *parts)

def _school_hack_path(*parts: str) -> str:
    """Resolve a path relative to School_Hack/."""
    return os.path.join(_SCHOOL_HACK_DIR, *parts)

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
COLOR_BLACK     = (0, 0, 0)
COLOR_WHITE     = (255, 255, 255)
COLOR_GREEN     = (0, 255, 0)
COLOR_CYAN      = (0, 255, 255)
COLOR_YELLOW    = (255, 255, 0)
COLOR_RED       = (255, 0, 0)
COLOR_NEON_GREEN = (0, 255, 160)
COLOR_BG_TITLE  = (40, 40, 60)

# ---------------------------------------------------------------------------
# Database constants
# ---------------------------------------------------------------------------
SCHOOL_DATABASE_GRADE_VALUES = ["A", "B", "C", "D", "F"]
SCHOOL_DATABASE_ELECTIVES = ["MUSIC", "DRAMA", "CONSUMER STUDIES", "PEACE STUDIES"]
SCHOOL_DATABASE_SUBJECTS = [
    "ENGLISH",
    "U.S.HISTORY",
    "AMERICAN PACIFICA POLITIC",
    "MATHMATICS",
    "SCIENCE",
    "PHYSICAL EDUCATION",
    "COMPUTER SCIENCE",
    "ART",
]
SCHOOL_DATABASE_KEY_ORDER = SCHOOL_DATABASE_SUBJECTS + ["ELECTIVE"]
STATE_VERSION = 3
SCHOOL_DATABASE_HOMEROOMS = ["RM 104", "RM 207", "RM 112", "RM 305", "RM 118", "RM 201", "RM 310", "RM 103"]

# ---------------------------------------------------------------------------
# Saturday Clubs
# ---------------------------------------------------------------------------
SATURDAY_CLUBS_POOL = [
    "Computer Club", "Amateur Radio Club", "Chess Club", "Art Club",
    "Drama Society", "Science Olympiad", "Music Club", "Photography Club",
    "Peace Committee", "Library Volunteers",
]
SATURDAY_CLUBS_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
SATURDAY_CLUBS_ROOMS = ["RM 104", "RM 207", "RM 112", "RM 305", "RM 118", "RM 201", "RM 310", "RM 103"]

SATURDAY_CLUBS_OVERRIDES = {
    "1m_BRADSONIC_mosaic_reveal.gif": ["Computer Club", "Amateur Radio Club"],
    "2m_BRADSONIC_mosaic_reveal.gif": ["Computer Club", "Chess Club"],
    "1f_BRADSONIC_mosaic_reveal.gif": ["Computer Club", "Drama Society"],
}

# ---------------------------------------------------------------------------
# Disciplinary Records
# ---------------------------------------------------------------------------
DISCIPLINARY_GENERIC_POOL = [
    "LATE TO CLASS", "UNIFORM VIOLATION", "TALKING DURING ASSEMBLY",
    "MISSING HOMEWORK X3", "RUNNING IN CORRIDOR", "CHEWING GUM IN CLASS",
    "LATE RETURN FROM LUNCH BREAK", "DISRUPTIVE BEHAVIOR IN ASSEMBLY"
]

DISCIPLINARY_OVERRIDES = {
    "1m_BRADSONIC_mosaic_reveal.gif": [
        "USING THE LIBRARY BRADSONIC COMPUTER TO LISTEN TO PIRATE RADIO",
        "ANTI-PACIFICA GRAFFITI - EAST STAIRWELL (DENIED INVOLVEMENT)",
        "FOUND IN SERVER ROOM AFTER HOURS",
    ],
    "2m_BRADSONIC_mosaic_reveal.gif": [
        "UNAUTHORIZED SOFTWARE ON SCHOOL COMPUTER",
        "ANTI-PACIFICA LITERATURE FOUND IN LOCKER",
        "EXCESSIVE TARDINESS - NOTED FATIGUE",
    ],
    "1f_BRADSONIC_mosaic_reveal.gif": [
        "CAUGHT PLAYING VIDEO GAMES ON LIBRARY COMPUTER DURING ENGLISH CLASS",
        "ANTI-PACIFICA STICKER ON LOCKER (VERBAL WARNING)",
        "COUNSELOR REFERRAL - PERSISTENT FATIGUE",
    ],
}

# ---------------------------------------------------------------------------
# Counselor Notes
# ---------------------------------------------------------------------------
COUNSELOR_OVERRIDES = {
    "1m_BRADSONIC_mosaic_reveal.gif": [
        "Student shows exceptional aptitude in electronics and computing. Frequently tired in morning classes. Warned about excessive time in radio club room.",
        "Concerns raised re: potential access to BANNED CONTENT via personal modem. Student denies. Parents contacted - no action taken.",
        "[FLAGGED] Possible connection to unauthorized BBS activity. Refer to administration if further incidents.",
    ],
    "2m_BRADSONIC_mosaic_reveal.gif": [
        "Academically strong but increasingly withdrawn. Appears fatigued - possible late-night computer use. Recommend sleep hygiene discussion.",
        "Student questioned about anti-Pacifica materials. Claims 'research for history paper.' No further action.",
        "[FLAGGED] Found debugging school network login system. Claims 'testing security.' Impressive but concerning.",
    ],
    "1f_BRADSONIC_mosaic_reveal.gif": [
        "Bright, articulate student. Active in drama but distracted this term. Frequently tired. Close friends with Vandengate and Kanderton.",
        "Raised concerns about Pacifica curriculum in class - noted by faculty as 'politically aware beyond her years.'",
        "[FLAGGED] Suspected of coordinating with other students to access restricted terminal functions. No direct evidence. Monitor.",
    ],
}

COUNSELOR_GENERIC_POOL = [
    "No concerns at this time.",
    "Performing within expected parameters.",
    "Recommend continued attendance monitoring.",
]

SCHOOL_DATABASE_MALE_FIRST_NAMES = [
    "Bertie", "Jason", "Calvin", "Darren", "Elliot", "Franklin", "Gavin", "Harvey",
    "Isaac", "Julian", "Kieran", "Landon", "Marcus", "Nathan", "Owen", "Preston",
    "Quentin", "Ryan", "Spencer", "Trevor", "Vincent", "Wesley", "Zachary",
]
SCHOOL_DATABASE_FEMALE_FIRST_NAMES = [
    "Rosaline", "Abigail", "Beatrice", "Caroline", "Daphne", "Eliza", "Felicity", "Georgia",
    "Heather", "Iris", "Jillian", "Katherine", "Lydia", "Melanie", "Naomi", "Olivia",
    "Penelope", "Ramona", "Sabrina", "Tabitha", "Valerie", "Whitney", "Yvonne",
]
SCHOOL_DATABASE_SURNAMES = [
    "Cloud", "Vandengate", "Kanderton", "Hollis", "Mercer", "Whitlock", "Prescott", "Danvers",
    "Sinclair", "Bennett", "Winslow", "Parker", "Ashford", "Monroe", "Talbot", "Hawthorne",
    "Reeves", "Caldwell", "Fairchild", "Keating", "Marlowe", "Pierce", "Locke", "Bishop",
    "Wren", "Pembroke", "Sloane", "Thatcher", "Vale", "Crosby", "Templeton", "Sterling",
    "Redgrave", "Bellamy", "Dunlop", "Kingsley", "Wexler", "Lennox", "Drayton", "Yorke",
]

# ---------------------------------------------------------------------------
# Save file path (sits next to this script)
# ---------------------------------------------------------------------------
_SAVE_FILE = _school_hack_path("school_database_state.json")


class SchoolDatabaseApp:
    """Self-contained Telebase school database UI.

    Can run standalone (``run()`` method) or be embedded by instantiating and
    calling ``update(dt)`` / ``draw()`` / ``handle_event(event)`` each frame.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, screen: pygame.Surface, scale: float = 1.0,
                 get_state_callback=None, save_state_callback=None):
        self.screen = screen
        self.scale = scale

        # External persistence hooks (default: local JSON file)
        self._get_state_cb = get_state_callback or self._load_state_from_file
        self._save_state_cb = save_state_callback or self._save_state_to_file

        # Font
        self.font: Optional[pygame.font.Font] = None
        self._load_font()

        # State
        self.mode = "login_username"  # start at login
        self.running = True
        self.db_state: Dict[str, Any] = {}
        self.sections = ["ATTENDANCE SCORES", "REPORT CARDS", "DISCIPLINARY RECORDS", "COUNSELOR NOTES", "SATURDAY CLUBS"]
        self.home_index = 0
        self.login_username = ""
        self.login_password = ""
        self.login_error = ""
        self.selected_student = 0
        self.selected_field = 0
        self.editing = False
        self.attendance_editing = False

        # Scroll offset for new sections
        self.scroll_offset = 0

        # Animation
        self.anim_cache: Dict[str, Dict[str, Any]] = {}
        self.anim_key: Optional[str] = None
        self.anim_frame: int = 0
        self.anim_timer: float = 0.0
        self.anim_finished: bool = False

        # Debug dedup
        self._dbg_last_draw = ""
        self._dbg_last_mug = ""

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------
    def _load_font(self) -> None:
        font_path = _data_path("OS", "VT323-Regular.ttf")
        font_size = max(int(21 * self.scale), 16)
        try:
            self.font = pygame.font.Font(font_path, font_size)
        except Exception as e:
            print(f"[SCHOOL_DB] Font load failed ({font_path}): {e}")
            self.font = pygame.font.Font(None, font_size)

    # ------------------------------------------------------------------
    # Persistence (standalone JSON file)
    # ------------------------------------------------------------------
    @staticmethod
    def _load_state_from_file() -> Optional[Dict]:
        if os.path.exists(_SAVE_FILE):
            try:
                with open(_SAVE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[SCHOOL_DB] Failed to load save: {e}")
        return None

    @staticmethod
    def _save_state_to_file(state: Dict) -> None:
        try:
            with open(_SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[SCHOOL_DB] Failed to save: {e}")

    # ------------------------------------------------------------------
    # Student data generation (deterministic from filenames)
    # ------------------------------------------------------------------
    @staticmethod
    def _seed(text: str) -> int:
        return sum((i + 1) * ord(c) for i, c in enumerate(text))

    def _make_id(self, mug: str, idx: int) -> str:
        s = self._seed(mug)
        serial = 1000 + ((s + idx * 37) % 9000)
        div = "A" if "f_bradsonic" in mug.lower() else "B"
        return f"TMH-89-{div}{serial:04d}"

    def _make_name(self, mug: str, gender: str, used_names: set, used_surnames: set) -> str:
        overrides = {
            "1m_BRADSONIC_mosaic_reveal.gif": "Bertie Vandengate",
            "2m_BRADSONIC_mosaic_reveal.gif": "Jason Kanderton",
            "1f_BRADSONIC_mosaic_reveal.gif": "Rosaline Cloud",
        }
        if mug in overrides:
            full = overrides[mug]
            used_names.add(full); used_surnames.add(full.split()[-1])
            return full
        firsts = SCHOOL_DATABASE_FEMALE_FIRST_NAMES if gender == "f" else SCHOOL_DATABASE_MALE_FIRST_NAMES
        s = self._seed(mug)
        fi = s % len(firsts)
        li = (s // max(1, len(firsts))) % len(SCHOOL_DATABASE_SURNAMES)
        for so in range(max(len(firsts), len(SCHOOL_DATABASE_SURNAMES)) * 3):
            last = SCHOOL_DATABASE_SURNAMES[(li + so) % len(SCHOOL_DATABASE_SURNAMES)]
            if last in used_surnames:
                continue
            for fo in range(len(firsts)):
                first = firsts[(fi + fo) % len(firsts)]
                cand = f"{first} {last}"
                if cand not in used_names:
                    used_names.add(cand); used_surnames.add(last)
                    return cand
        cand = f"{firsts[fi]} {SCHOOL_DATABASE_SURNAMES[li]} {len(used_names)+1}"
        used_names.add(cand)
        return cand

    def _build_student(self, mug: str, idx: int, un: set, us: set) -> Dict[str, Any]:
        gender = "f" if "f_bradsonic" in mug.lower() else "m"
        s = self._seed(mug)
        rng = random.Random(s)
        name = self._make_name(mug, gender, un, us)
        elective = SCHOOL_DATABASE_ELECTIVES[s % len(SCHOOL_DATABASE_ELECTIVES)]
        grades = {subj: SCHOOL_DATABASE_GRADE_VALUES[rng.randrange(0, 3)] for subj in SCHOOL_DATABASE_SUBJECTS}

        if mug == "1m_BRADSONIC_mosaic_reveal.gif":
            elective = "MUSIC"
            grades.update({"ENGLISH": "C", "U.S.HISTORY": "C", "AMERICAN PACIFICA POLITIC": "A",
                           "MATHMATICS": "A", "SCIENCE": "A", "PHYSICAL EDUCATION": "A",
                           "COMPUTER SCIENCE": "A", "ART": "A"})
        elif mug == "2m_BRADSONIC_mosaic_reveal.gif":
            elective = "MUSIC"
            grades.update({"ENGLISH": "B", "U.S.HISTORY": "B", "AMERICAN PACIFICA POLITIC": "A",
                           "MATHMATICS": "A", "SCIENCE": "A", "PHYSICAL EDUCATION": "A",
                           "COMPUTER SCIENCE": "A", "ART": "A"})
        elif mug == "1f_BRADSONIC_mosaic_reveal.gif":
            grades = {subj: "A" for subj in SCHOOL_DATABASE_SUBJECTS}
            grades["ENGLISH"] = "C"; grades["U.S.HISTORY"] = "C"

        # Saturday Clubs
        if mug in SATURDAY_CLUBS_OVERRIDES:
            clubs = SATURDAY_CLUBS_OVERRIDES[mug]
        else:
            n_clubs = 1 + (s % 2)
            club_indices = [(s + i * 7) % len(SATURDAY_CLUBS_POOL) for i in range(n_clubs)]
            seen = set()
            clubs = []
            for ci in club_indices:
                c = SATURDAY_CLUBS_POOL[ci]
                if c not in seen:
                    seen.add(c)
                    clubs.append(c)

        # Disciplinary Records
        if mug in DISCIPLINARY_OVERRIDES:
            disciplinary = DISCIPLINARY_OVERRIDES[mug]
        else:
            n_disc = s % 2  # 0 or 1 incidents for generic students
            if n_disc > 0:
                disc_idx = s % len(DISCIPLINARY_GENERIC_POOL)
                disciplinary = [DISCIPLINARY_GENERIC_POOL[disc_idx]]
            else:
                disciplinary = []

        # Counselor Notes
        if mug in COUNSELOR_OVERRIDES:
            counselor_notes = COUNSELOR_OVERRIDES[mug]
        else:
            note_idx = s % len(COUNSELOR_GENERIC_POOL)
            counselor_notes = [COUNSELOR_GENERIC_POOL[note_idx]]

        return {"id": self._make_id(mug, idx), "mug_filename": mug, "name": name,
                "gender": gender, "elective": elective, "grades": grades,
                "attendance": rng.randint(78, 99),
                "clubs": clubs, "disciplinary": disciplinary,
                "counselor_notes": counselor_notes}

    def _build_default_state(self) -> Dict[str, Any]:
        mugs_dir = _school_hack_path("School_Mugs")
        mug_files = sorted(f for f in os.listdir(mugs_dir) if f.lower().endswith(".gif")) if os.path.isdir(mugs_dir) else []
        print(f"[SCHOOL_DB] Mugs dir: {mugs_dir}  found {len(mug_files)} GIFs")
        un: set = set(); us: set = set()
        students = [self._build_student(f, i, un, us) for i, f in enumerate(mug_files)]
        return {"version": STATE_VERSION, "students": students}

    def _normalize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        students = state.get("students", [])
        if not isinstance(students, list):
            return self._build_default_state()
        rebuilt: List[Dict] = []; un: set = set(); us: set = set()
        for idx, raw in enumerate(students):
            if not isinstance(raw, dict):
                continue
            mug = str(raw.get("mug_filename", "")).strip()
            if not mug:
                continue
            base = self._build_student(mug, idx, un, us)
            grades = raw.get("grades")
            if isinstance(grades, dict):
                base["grades"] = {
                    subj: str(grades.get(subj, base["grades"][subj])).upper()
                    if str(grades.get(subj, base["grades"][subj])).upper() in SCHOOL_DATABASE_GRADE_VALUES
                    else base["grades"][subj]
                    for subj in SCHOOL_DATABASE_SUBJECTS
                }
            elective = str(raw.get("elective", base["elective"])).upper()
            if elective in SCHOOL_DATABASE_ELECTIVES:
                base["elective"] = elective
            try:
                base["attendance"] = max(0, min(100, int(raw.get("attendance", base["attendance"]))))
            except (TypeError, ValueError):
                pass
            rebuilt.append(base)
        return {"version": STATE_VERSION, "students": rebuilt}

    def _ensure_loaded(self) -> None:
        if self.db_state.get("students"):
            return
        stored = self._get_state_cb()
        if isinstance(stored, dict) and isinstance(stored.get("students"), list):
            self.db_state = self._normalize_state(stored)
        else:
            self.db_state = self._build_default_state()
        self._save_state_cb(self.db_state)
        if self.db_state.get("students"):
            self.selected_student = min(self.selected_student, len(self.db_state["students"]) - 1)
            self._reset_animation(force=True)

    def _save_db(self) -> None:
        if self.db_state:
            self._save_state_cb(self.db_state)

    def _students(self) -> List[Dict]:
        self._ensure_loaded()
        return self.db_state.get("students", [])

    def _student(self) -> Optional[Dict]:
        students = self._students()
        if not students:
            return None
        self.selected_student %= len(students)
        return students[self.selected_student]

    # ------------------------------------------------------------------
    # GIF animation
    # ------------------------------------------------------------------
    def _load_animation(self, mug_filename: str) -> Dict[str, Any]:
        cached = self.anim_cache.get(mug_filename)
        if cached:
            return cached
        frames: List[pygame.Surface] = []
        durations: List[float] = []
        gif_path = _school_hack_path("School_Mugs", mug_filename)
        print(f"[SCHOOL_DB] Loading GIF: '{mug_filename}'")
        print(f"[SCHOOL_DB]   Resolved path: {gif_path}")
        print(f"[SCHOOL_DB]   PIL available: {_pil_available}")
        print(f"[SCHOOL_DB]   File exists: {os.path.exists(gif_path)}")
        if _pil_available and os.path.exists(gif_path):
            try:
                with Image.open(gif_path) as img:
                    for frame in ImageSequence.Iterator(img):
                        converted = frame.convert("RGBA")
                        surf = pygame.image.fromstring(converted.tobytes(), converted.size, "RGBA").convert_alpha()
                        frames.append(surf)
                        dur = frame.info.get("duration", img.info.get("duration", 90))
                        durations.append(max(0.04, float(dur) / 1000.0))
                print(f"[SCHOOL_DB]   Loaded {len(frames)} frames OK ({frames[0].get_size() if frames else 'N/A'})")
            except Exception as e:
                print(f"[SCHOOL_DB]   ERROR loading GIF: {e}")
                frames = []; durations = []
        else:
            if not _pil_available:
                print("[SCHOOL_DB]   FAIL: PIL/Pillow not installed")
            else:
                print(f"[SCHOOL_DB]   FAIL: File not found at {gif_path}")
        if not frames:
            print(f"[SCHOOL_DB]   Using fallback surface for '{mug_filename}'")
            fb = pygame.Surface((96, 120), pygame.SRCALPHA)
            fb.fill(COLOR_BLACK)
            pygame.draw.rect(fb, COLOR_CYAN, fb.get_rect(), 2)
            frames = [fb]; durations = [0.1]
        self.anim_cache[mug_filename] = {"frames": frames, "durations": durations}
        return self.anim_cache[mug_filename]

    def _reset_animation(self, force: bool = False) -> None:
        student = self._student()
        if not student:
            self.anim_key = None; return
        key = student.get("mug_filename")
        if not force and self.anim_key == key:
            return
        self._load_animation(key)
        self.anim_key = key
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_finished = False

    def _current_frame(self) -> Optional[pygame.Surface]:
        student = self._student()
        if not student:
            return None
        anim = self._load_animation(student.get("mug_filename", ""))
        frames = anim.get("frames", [])
        if not frames:
            return None
        return frames[min(self.anim_frame, len(frames) - 1)]

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _grade_value(grade: str) -> int:
        return {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}.get((grade or "").upper(), 0)

    def _gpa(self, student: Dict) -> float:
        grades = student.get("grades", {})
        vals = [self._grade_value(grades.get(s, "F")) for s in SCHOOL_DATABASE_SUBJECTS]
        return sum(vals) / max(1, len(vals))

    def _student_seed(self, student: Dict[str, Any]) -> int:
        return self._seed(student.get("mug_filename", ""))

    def _homeroom(self, student: Dict[str, Any]) -> str:
        return SCHOOL_DATABASE_HOMEROOMS[self._student_seed(student) % len(SCHOOL_DATABASE_HOMEROOMS)]

    def _record_date(self, student: Dict[str, Any], index: int, month_step: int, day_step: int,
                     start_month: int = 1) -> str:
        seed = self._student_seed(student)
        month = start_month + ((seed + index * month_step) % (13 - start_month))
        day = 1 + ((seed + index * day_step) % 28)
        return f"{month:02d}/{day:02d}/89"

    def _club_slot(self, student: Dict[str, Any], index: int) -> Tuple[str, str]:
        seed = self._student_seed(student)
        day = SATURDAY_CLUBS_DAYS[(seed + index * 3) % len(SATURDAY_CLUBS_DAYS)]
        room = SATURDAY_CLUBS_ROOMS[(seed + index * 5) % len(SATURDAY_CLUBS_ROOMS)]
        return day, room

    def _change_student(self, delta: int) -> None:
        students = self._students()
        if not students:
            return
        self.selected_student = (self.selected_student + delta) % len(students)
        self._reset_animation(force=True)

    def _change_report_value(self, delta: int) -> None:
        student = self._student()
        if not student:
            return
        field = SCHOOL_DATABASE_KEY_ORDER[self.selected_field]
        if field == "ELECTIVE":
            cur = student.get("elective", SCHOOL_DATABASE_ELECTIVES[0])
            if cur not in SCHOOL_DATABASE_ELECTIVES:
                cur = SCHOOL_DATABASE_ELECTIVES[0]
            i = SCHOOL_DATABASE_ELECTIVES.index(cur)
            student["elective"] = SCHOOL_DATABASE_ELECTIVES[(i + delta) % len(SCHOOL_DATABASE_ELECTIVES)]
        else:
            grades = student.setdefault("grades", {})
            cur = grades.get(field, "C")
            if cur not in SCHOOL_DATABASE_GRADE_VALUES:
                cur = "C"
            i = SCHOOL_DATABASE_GRADE_VALUES.index(cur)
            grades[field] = SCHOOL_DATABASE_GRADE_VALUES[(i + delta) % len(SCHOOL_DATABASE_GRADE_VALUES)]
        self._save_db()

    def _change_attendance(self, delta: int) -> None:
        student = self._student()
        if not student:
            return
        student["attendance"] = max(0, min(100, int(student.get("attendance", 85)) + delta))
        self._save_db()

    # ------------------------------------------------------------------
    # Text wrapping
    # ------------------------------------------------------------------
    def _wrap(self, text: str, max_w: int) -> List[str]:
        words = text.split(" ")
        lines: List[str] = []
        cur = ""
        for word in words:
            test = cur + (" " if cur else "") + word
            if self.font.render(test, True, COLOR_GREEN).get_width() <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                if self.font.render(word, True, COLOR_GREEN).get_width() > max_w:
                    for ch in word:
                        tc = cur + ch
                        if self.font.render(tc, True, COLOR_GREEN).get_width() <= max_w:
                            cur = tc
                        else:
                            if cur:
                                lines.append(cur)
                            cur = ch
                else:
                    cur = word
        if cur:
            lines.append(cur)
        return lines if lines else [""]

    # ------------------------------------------------------------------
    # Update (call each frame with dt)
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.mode in ("school_db_attendance", "school_db_report_cards", "school_db_home",
                         "school_db_disciplinary", "school_db_counselor", "school_db_clubs"):
            student = self._student()
            if student:
                anim = self._load_animation(student.get("mug_filename", ""))
                frames = anim.get("frames", [])
                durations = anim.get("durations", [])
                if frames and not self.anim_finished:
                    fi = min(self.anim_frame, len(frames) - 1)
                    dur = durations[fi] if fi < len(durations) else 0.08
                    self.anim_timer += dt
                    while self.anim_timer >= dur and not self.anim_finished:
                        self.anim_timer -= dur
                        if self.anim_frame < len(frames) - 1:
                            self.anim_frame += 1
                            fi = self.anim_frame
                            dur = durations[fi] if fi < len(durations) else 0.08
                        else:
                            self.anim_finished = True
                            self.anim_timer = 0.0

    # ------------------------------------------------------------------
    # Input (call for each pygame.KEYDOWN event)
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the event was consumed."""
        if event.type != pygame.KEYDOWN:
            return False

        # --- Login username ---
        if self.mode == "login_username":
            if event.key == pygame.K_BACKSPACE:
                self.login_username = self.login_username[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self.mode = "login_password"
                self.login_error = ""
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.unicode and event.unicode.isprintable():
                self.login_username += event.unicode
            return True

        # --- Login password ---
        if self.mode == "login_password":
            if event.key == pygame.K_BACKSPACE:
                self.login_password = self.login_password[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.login_username.strip().lower() == "admin" and self.login_password == "password":
                    self.login_error = ""
                    self.mode = "school_db_home"
                    self._ensure_loaded()
                else:
                    self.login_error = "ACCESS DENIED"
                    self.login_password = ""
            elif event.key == pygame.K_ESCAPE:
                self.login_password = ""
                self.login_error = ""
                self.mode = "login_username"
            elif event.unicode and event.unicode.isprintable():
                self.login_password += event.unicode
            return True

        # --- Home ---
        if self.mode == "school_db_home":
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                self.home_index = (self.home_index - 1) % len(self.sections)
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB):
                self.home_index = (self.home_index + 1) % len(self.sections)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.selected_field = 0
                self.editing = False
                self.attendance_editing = False
                self.scroll_offset = 0
                _mode_map = {
                    0: "school_db_attendance",
                    1: "school_db_report_cards",
                    2: "school_db_disciplinary",
                    3: "school_db_counselor",
                    4: "school_db_clubs",
                }
                self.mode = _mode_map.get(self.home_index, "school_db_attendance")
                self._reset_animation(force=True)
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            return True

        # --- Attendance ---
        if self.mode == "school_db_attendance":
            if event.key == pygame.K_ESCAPE:
                self.attendance_editing = False
                self.mode = "school_db_home"
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB) and not self.attendance_editing:
                self._change_student(1 if event.key in (pygame.K_RIGHT, pygame.K_TAB) else -1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.attendance_editing = not self.attendance_editing
            elif self.attendance_editing and event.key in (pygame.K_LEFT, pygame.K_DOWN):
                self._change_attendance(-1)
            elif self.attendance_editing and event.key in (pygame.K_RIGHT, pygame.K_UP):
                self._change_attendance(1)
            return True

        # --- Report cards ---
        if self.mode == "school_db_report_cards":
            if event.key == pygame.K_ESCAPE:
                self.editing = False
                self.mode = "school_db_home"
            elif event.key == pygame.K_UP and not self.editing:
                self.selected_field = max(0, self.selected_field - 1)
            elif event.key == pygame.K_DOWN and not self.editing:
                self.selected_field = min(len(SCHOOL_DATABASE_KEY_ORDER) - 1, self.selected_field + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.editing = not self.editing
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                if self.editing:
                    self._change_report_value(1 if event.key in (pygame.K_RIGHT, pygame.K_TAB) else -1)
                else:
                    self._change_student(1 if event.key in (pygame.K_RIGHT, pygame.K_TAB) else -1)
            return True

        # --- Disciplinary / Counselor / Clubs ---
        if self.mode in ("school_db_disciplinary", "school_db_counselor", "school_db_clubs"):
            if event.key == pygame.K_ESCAPE:
                self.scroll_offset = 0
                self.mode = "school_db_home"
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self._change_student(1 if event.key in (pygame.K_RIGHT, pygame.K_TAB) else -1)
                self.scroll_offset = 0
            elif event.key == pygame.K_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif event.key == pygame.K_DOWN:
                self.scroll_offset += 1
            return True

        return False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self) -> None:
        """Draw the current mode into self.screen."""
        if not self.font:
            return
        sw, sh = self.screen.get_size()
        # Outer frame
        frame = pygame.Rect(0, 0, sw, sh)
        pygame.draw.rect(self.screen, COLOR_BLACK, frame)
        pygame.draw.rect(self.screen, COLOR_NEON_GREEN, frame, 2)

        pad = int(8 * self.scale)
        cx, cy = pad, pad
        cw, ch = sw - pad * 2, sh - pad * 2
        lh = self.font.get_linesize()

        if self.mode in ("login_username", "login_password"):
            self._draw_login(cx, cy, cw, ch, lh)
        elif self.mode == "school_db_home":
            self._draw_home(cx, cy, cw, ch, lh)
        elif self.mode in ("school_db_attendance", "school_db_report_cards"):
            self._draw_record(cx, cy, cw, ch, lh, self.mode == "school_db_attendance")
        elif self.mode == "school_db_disciplinary":
            self._draw_disciplinary(cx, cy, cw, ch, lh)
        elif self.mode == "school_db_counselor":
            self._draw_counselor(cx, cy, cw, ch, lh)
        elif self.mode == "school_db_clubs":
            self._draw_clubs(cx, cy, cw, ch, lh)

    # --- Login screen ---
    def _draw_login(self, cx: int, cy: int, cw: int, ch: int, lh: int) -> None:
        title = self.font.render("WOLF PRO TELEBASE LOGIN", True, COLOR_YELLOW)
        self.screen.blit(title, (cx, cy + int(10 * self.scale)))
        uline = f"USERNAME : {self.login_username}"
        pline = "PASSWORD : " + ("*" * len(self.login_password))
        self.screen.blit(self.font.render(uline, True, COLOR_CYAN), (cx, cy + int(50 * self.scale)))
        self.screen.blit(self.font.render(pline, True, COLOR_CYAN), (cx, cy + int(80 * self.scale)))
        self.screen.blit(self.font.render("Use admin / password", True, COLOR_GREEN), (cx, cy + int(130 * self.scale)))
        if self.login_error:
            self.screen.blit(self.font.render(self.login_error, True, COLOR_RED), (cx, cy + int(160 * self.scale)))
        # Blinking cursor
        active = pline if self.mode == "login_password" else uline
        cursor_surf = self.font.render(active + "_", True, COLOR_GREEN)
        cursor_y = cy + (int(80 * self.scale) if self.mode == "login_password" else int(50 * self.scale))
        self.screen.blit(cursor_surf, (cx, cursor_y))

    # --- Home / directory screen ---
    def _draw_home(self, cx: int, cy: int, cw: int, ch: int, lh: int) -> None:
        frame_rect = pygame.Rect(cx, cy, cw, ch)
        self._draw_header(frame_rect, "WOLF PRO : BRADSONIC-TELCO TELEBASE", "NODE OK")
        panel_top = cy + int(38 * self.scale)
        panel_rect = pygame.Rect(cx + int(10 * self.scale), panel_top, cw - int(20 * self.scale), ch - int(74 * self.scale))
        self._draw_panel(panel_rect, "DIRECTORY MAP", COLOR_YELLOW)
        title = self.font.render("TOKYO METROPOLITAN HIGH SCHOOL / INDEX", True, COLOR_GREEN)
        self.screen.blit(title, (cx + int(24 * self.scale), panel_top + int(18 * self.scale)))
        menu_top = panel_top + int(42 * self.scale)
        menu_gap = int(26 * self.scale)
        for idx, section in enumerate(self.sections):
            y = menu_top + idx * menu_gap
            prefix = ">" if idx == self.home_index else " "
            color = COLOR_YELLOW if idx == self.home_index else COLOR_CYAN
            self.screen.blit(self.font.render(f"{prefix} {section}", True, color), (cx + int(24 * self.scale), y))
        access_y = menu_top + len(self.sections) * menu_gap + int(16 * self.scale)
        self.screen.blit(self.font.render("Access path: connected node handshake / student records mirror", True, COLOR_GREEN),
                         (cx + int(24 * self.scale), access_y))
        footer = "[UP/DOWN] SELECT   [ENTER] OPEN   [ESC] EXIT"
        fs = self.font.render(footer, True, COLOR_GREEN)
        self.screen.blit(fs, (cx + int(10 * self.scale), cy + ch - lh - int(6 * self.scale)))

    # --- Record view (attendance or report card) ---
    def _draw_record(self, cx: int, cy: int, cw: int, ch: int, lh: int, attendance_view: bool) -> None:
        footer_hint = "[LEFT/RIGHT/TAB] STUDENT   [ENTER] EDIT   [ESC] BACK" if attendance_view else \
            "[UP/DOWN] FIELD   [LEFT/RIGHT/TAB] STUDENT   [ENTER] EDIT   [ESC] BACK"
        layout = self._draw_record_shell(cx, cy, cw, ch, lh, footer_hint=footer_hint)
        if not layout:
            return

        body_top, body_bottom, right_x, table_right = layout
        student = self._student()
        if not student:
            return

        name_text = student.get("name", "UNKNOWN").upper()
        self.screen.blit(self.font.render(name_text, True, COLOR_YELLOW), (right_x, body_top))
        self.screen.blit(self.font.render("TOKYO METROPOLITAN HIGH SCHOOL", True, COLOR_GREEN), (right_x, body_top + lh))
        title_text_r = "ATTENDANCE SCORES" if attendance_view else "TERM REPORT 3 . 1989"
        self.screen.blit(self.font.render(title_text_r, True, COLOR_GREEN), (right_x, body_top + lh * 2))
        div_y = body_top + lh * 3 + int(2 * self.scale)
        pygame.draw.line(self.screen, COLOR_NEON_GREEN, (right_x, div_y), (table_right, div_y), 1)
        table_top = div_y + int(4 * self.scale)

        if attendance_view:
            rows = [
                ("ATTENDANCE SCORE", f"{int(student.get('attendance', 0)):03d}%"),
                ("STATUS", "GOOD" if int(student.get("attendance", 0)) >= 90 else ("WATCH" if int(student.get("attendance", 0)) >= 80 else "RISK")),
                ("NODE", "TOK-MET-EDU-04"),
            ]
            avail = body_bottom - table_top
            gap = max(lh, avail // max(1, len(rows)))
            for idx, (label, value) in enumerate(rows):
                ry = table_top + idx * gap
                color = COLOR_YELLOW if idx == 0 else COLOR_CYAN
                if idx == 0 and self.attendance_editing:
                    color = COLOR_GREEN
                    pygame.draw.rect(self.screen, (0, 40, 0), pygame.Rect(right_x, ry, table_right - right_x, lh))
                self.screen.blit(self.font.render(label, True, color), (right_x, ry))
                vs = self.font.render(value, True, color)
                self.screen.blit(vs, (table_right - vs.get_width(), ry))
        else:
            subject_labels = {
                "ENGLISH": "ENGLISH", "U.S.HISTORY": "U.S. HISTORY",
                "AMERICAN PACIFICA POLITIC": "PACIFICA PEACE STUDIES", "MATHMATICS": "MATHEMATICS",
                "SCIENCE": "SCIENCE", "PHYSICAL EDUCATION": "PHYSICAL EDUCATION",
                "COMPUTER SCIENCE": "COMPUTER SCIENCE", "ART": "ART",
            }
            self.screen.blit(self.font.render("SUBJECT", True, COLOR_YELLOW), (right_x, table_top))
            _two_ch = self.font.size("WW")[0]  # width of ~2 characters
            gh = self.font.render("GRADE", True, COLOR_YELLOW)
            self.screen.blit(gh, (table_right - gh.get_width() - _two_ch, table_top))
            rows_top = table_top + lh + int(2 * self.scale)
            rows = [(subject_labels.get(s, s), student.get("grades", {}).get(s, "F")) for s in SCHOOL_DATABASE_SUBJECTS]
            rows.append(("ELECTIVE:" + student.get("elective", "N/A").upper(), ""))
            avail = body_bottom - rows_top
            gap = max(lh, avail // max(1, len(rows)))
            for idx, (label, value) in enumerate(rows):
                ry = rows_top + idx * gap
                is_sel = idx == self.selected_field
                color = COLOR_GREEN if is_sel else COLOR_CYAN
                if is_sel and self.editing:
                    color = COLOR_YELLOW
                if is_sel:
                    pygame.draw.rect(self.screen, (0, 40, 0), pygame.Rect(right_x, ry, table_right - right_x, lh))
                self.screen.blit(self.font.render(label, True, color), (right_x, ry))
                if value:
                    vs = self.font.render(str(value), True, color)
                    self.screen.blit(vs, (table_right - vs.get_width() - _two_ch, ry))
            gpa_y = rows_top + len(rows) * gap
            if gpa_y < body_bottom - lh:
                gs = self.font.render(f"G.P.A.: {self._gpa(student):0.2f}/4.00", True, COLOR_YELLOW)
                self.screen.blit(gs, (table_right - gs.get_width(), gpa_y))

    # --- Record shell (shared layout for all record views) ---
    def _draw_record_shell(self, cx: int, cy: int, cw: int, ch: int, lh: int,
                           footer_hint: str = "[LEFT/RIGHT/TAB] STUDENT   [UP/DOWN] SCROLL   [ESC] BACK"
                           ) -> Optional[Tuple]:
        """Draw frame, footer, left mugshot+info, return layout coords or None."""
        student = self._student()
        if not student:
            self.screen.blit(self.font.render("NO STUDENT RECORDS AVAILABLE", True, COLOR_RED), (cx, cy))
            return None

        sw, sh = self.screen.get_size()
        pad = int(6 * self.scale)

        # Outer frame
        frame_top = cy
        frame_rect = pygame.Rect(cx, frame_top, cw, cy + ch - frame_top)
        pygame.draw.rect(self.screen, COLOR_BLACK, frame_rect)
        pygame.draw.rect(self.screen, COLOR_NEON_GREEN, frame_rect, 2)

        # RECORD ##/##
        rec_surf = self.font.render(f"RECORD {self.selected_student + 1:02d}/{len(self._students()):02d}", True, COLOR_YELLOW)
        self.screen.blit(rec_surf, (frame_rect.right - rec_surf.get_width() - pad, frame_rect.y + int(3 * self.scale)))

        # Footer
        fl1 = "TERMINAL: PC98-21   NODE: TOK-MET-EDU-04   DATABASE: TELEBASE STUDENT SYS v3.4"
        footer_h = lh * 2 + int(6 * self.scale)
        footer_top = frame_rect.bottom - footer_h - int(2 * self.scale)
        pygame.draw.line(self.screen, COLOR_NEON_GREEN, (frame_rect.x + 2, footer_top), (frame_rect.right - 2, footer_top), 1)
        self.screen.blit(self.font.render(fl1, True, COLOR_CYAN), (frame_rect.x + pad, footer_top + int(2 * self.scale)))
        self.screen.blit(self.font.render(footer_hint, True, COLOR_GREEN), (frame_rect.x + pad, footer_top + int(2 * self.scale) + lh))

        # Body area
        body_top = frame_rect.y + int(sh * 0.015)
        body_bottom = footer_top - int(4 * self.scale)

        # Columns
        left_w = int(cw * 0.35)
        right_x = cx + left_w + pad
        table_right = cx + cw - pad

        # Left: mugshot + info
        details = [
            ("ID:", student.get("id", "").upper()),
            ("ATTENDANCE:", f"{int(student.get('attendance', 0)):03d}%"),
            ("HOMEROOM:", self._homeroom(student)),
            ("GPA:", f"{self._gpa(student):0.2f}/4.00"),
        ]
        info_block_h = len(details) * (lh + int(2 * self.scale)) + pad
        mug_area_top = frame_rect.y + int(sh * 0.01)
        mug_area_bottom = body_bottom - info_block_h
        mug_max_h = min(int(200 * self.scale), max(int(40 * self.scale), mug_area_bottom - mug_area_top - pad))
        mug_max_w = left_w - pad * 2

        info_y = mug_area_top + mug_max_h + pad
        for idx, (label, value) in enumerate(details):
            row_y = info_y + idx * (lh + int(2 * self.scale))
            ls = self.font.render(label, True, COLOR_GREEN)
            vs = self.font.render(f" {value}", True, COLOR_CYAN)
            self.screen.blit(ls, (cx + pad, row_y))
            self.screen.blit(vs, (cx + pad + ls.get_width(), row_y))

        # Mugshot
        mug_surface = self._current_frame()
        if mug_surface is not None:
            s = min(mug_max_w / max(1, mug_surface.get_width()), mug_max_h / max(1, mug_surface.get_height())) * 0.85
            scaled = pygame.transform.smoothscale(mug_surface, (max(1, int(mug_surface.get_width() * s)),
                                                                 max(1, int(mug_surface.get_height() * s))))
            mx = cx + pad + (mug_max_w - scaled.get_width()) // 2
            my = mug_area_top + (mug_max_h - scaled.get_height()) // 2
            self.screen.blit(scaled, (mx, my))

        return (body_top, body_bottom, right_x, table_right)

    # --- Disciplinary Records view ---
    def _draw_disciplinary(self, cx: int, cy: int, cw: int, ch: int, lh: int) -> None:
        layout = self._draw_record_shell(cx, cy, cw, ch, lh)
        if not layout:
            return
        body_top, body_bottom, right_x, table_right = layout
        student = self._student()

        name_text = student.get("name", "UNKNOWN").upper()
        self.screen.blit(self.font.render(name_text, True, COLOR_YELLOW), (right_x, body_top))
        self.screen.blit(self.font.render("DISCIPLINARY RECORD", True, COLOR_GREEN), (right_x, body_top + lh))
        div_y = body_top + lh * 2 + int(2 * self.scale)
        pygame.draw.line(self.screen, COLOR_NEON_GREEN, (right_x, div_y), (table_right, div_y), 1)

        entries = student.get("disciplinary", [])
        row_y = div_y + int(4 * self.scale)
        max_w = table_right - right_x

        if not entries:
            self.screen.blit(self.font.render("NO INCIDENTS ON FILE", True, COLOR_GREEN), (right_x, row_y))
            return

        # Build all lines first for scrolling
        all_lines = []
        for i, entry in enumerate(entries):
            date_str = self._record_date(student, i, month_step=3, day_step=7)
            wrapped = self._wrap(f"{date_str}  {entry}", max_w)
            all_lines.extend(wrapped)

        # Apply scroll offset
        visible_lines = max(1, (body_bottom - row_y) // lh)
        max_scroll = max(0, len(all_lines) - visible_lines)
        self.scroll_offset = min(self.scroll_offset, max_scroll)
        display_lines = all_lines[self.scroll_offset:self.scroll_offset + visible_lines]

        for line in display_lines:
            if row_y + lh > body_bottom:
                break
            self.screen.blit(self.font.render(line, True, COLOR_CYAN), (right_x, row_y))
            row_y += lh

    # --- Counselor Notes view ---
    def _draw_counselor(self, cx: int, cy: int, cw: int, ch: int, lh: int) -> None:
        layout = self._draw_record_shell(cx, cy, cw, ch, lh)
        if not layout:
            return
        body_top, body_bottom, right_x, table_right = layout
        student = self._student()

        name_text = student.get("name", "UNKNOWN").upper()
        self.screen.blit(self.font.render(name_text, True, COLOR_YELLOW), (right_x, body_top))
        self.screen.blit(self.font.render("COUNSELOR NOTES - CONFIDENTIAL", True, COLOR_RED), (right_x, body_top + lh))
        div_y = body_top + lh * 2 + int(2 * self.scale)
        pygame.draw.line(self.screen, COLOR_NEON_GREEN, (right_x, div_y), (table_right, div_y), 1)

        notes = student.get("counselor_notes", [])
        row_y = div_y + int(4 * self.scale)
        max_w = table_right - right_x

        if not notes:
            self.screen.blit(self.font.render("NO COUNSELOR NOTES ON FILE", True, COLOR_GREEN), (right_x, row_y))
            return

        # Build all lines for scrolling
        all_lines = []  # list of (text, color)
        for i, note in enumerate(notes):
            date_str = self._record_date(student, i, month_step=5, day_step=11, start_month=2)
            is_flagged = note.startswith("[FLAGGED]")
            color = COLOR_RED if is_flagged else COLOR_CYAN
            all_lines.append((f"--- {date_str} ---", COLOR_GREEN))
            wrapped = self._wrap(note, max_w)
            for wl in wrapped:
                all_lines.append((wl, color))
            all_lines.append(("", COLOR_CYAN))  # blank spacer

        # Apply scroll offset
        visible_lines = max(1, (body_bottom - row_y) // lh)
        max_scroll = max(0, len(all_lines) - visible_lines)
        self.scroll_offset = min(self.scroll_offset, max_scroll)
        display_lines = all_lines[self.scroll_offset:self.scroll_offset + visible_lines]

        for text, color in display_lines:
            if row_y + lh > body_bottom:
                break
            if text:
                self.screen.blit(self.font.render(text, True, color), (right_x, row_y))
            row_y += lh

    # --- Saturday Clubs view ---
    def _draw_clubs(self, cx: int, cy: int, cw: int, ch: int, lh: int) -> None:
        layout = self._draw_record_shell(cx, cy, cw, ch, lh)
        if not layout:
            return
        body_top, body_bottom, right_x, table_right = layout
        student = self._student()

        name_text = student.get("name", "UNKNOWN").upper()
        self.screen.blit(self.font.render(name_text, True, COLOR_YELLOW), (right_x, body_top))
        self.screen.blit(self.font.render("SATURDAY CLUB MEMBERSHIPS", True, COLOR_GREEN), (right_x, body_top + lh))
        div_y = body_top + lh * 2 + int(2 * self.scale)
        pygame.draw.line(self.screen, COLOR_NEON_GREEN, (right_x, div_y), (table_right, div_y), 1)

        clubs = student.get("clubs", [])
        row_y = div_y + int(4 * self.scale)

        if not clubs:
            self.screen.blit(self.font.render("NO CLUB MEMBERSHIPS", True, COLOR_GREEN), (right_x, row_y))
            return

        all_lines = []
        for i, club in enumerate(clubs):
            day, room = self._club_slot(student, i)
            all_lines.append(f"{club.upper():<26s}{day}  {room}")

        visible_lines = max(1, (body_bottom - row_y) // lh)
        max_scroll = max(0, len(all_lines) - visible_lines)
        self.scroll_offset = min(self.scroll_offset, max_scroll)
        display_lines = all_lines[self.scroll_offset:self.scroll_offset + visible_lines]

        for line in display_lines:
            if row_y + lh > body_bottom:
                break
            self.screen.blit(self.font.render(line, True, COLOR_CYAN), (right_x, row_y))
            row_y += lh

    # --- Shared draw helpers ---
    def _draw_header(self, frame_rect: pygame.Rect, title: str, status: str) -> None:
        pygame.draw.rect(self.screen, COLOR_BLACK, frame_rect)
        pygame.draw.rect(self.screen, COLOR_NEON_GREEN, frame_rect, 2)
        hh = int(30 * self.scale)
        hr = pygame.Rect(frame_rect.x, frame_rect.y, frame_rect.width, hh)
        pygame.draw.rect(self.screen, COLOR_BLACK, hr)
        pygame.draw.line(self.screen, COLOR_NEON_GREEN, hr.bottomleft, hr.bottomright, 2)
        ts = self.font.render(title, True, COLOR_YELLOW)
        ss = self.font.render(status, True, COLOR_CYAN)
        self.screen.blit(ts, (hr.x + int(8 * self.scale), hr.y + int(7 * self.scale)))
        self.screen.blit(ss, (hr.right - ss.get_width() - int(8 * self.scale), hr.y + int(7 * self.scale)))

    def _draw_panel(self, rect: pygame.Rect, title: Optional[str] = None, title_color=COLOR_GREEN) -> None:
        pygame.draw.rect(self.screen, COLOR_BLACK, rect)
        pygame.draw.rect(self.screen, COLOR_NEON_GREEN, rect, 2)
        if title:
            label = f" {title} "
            ts = self.font.render(label, True, title_color)
            bg = pygame.Rect(rect.x + int(10 * self.scale), rect.y - int(2 * self.scale),
                             ts.get_width() + int(6 * self.scale), ts.get_height())
            pygame.draw.rect(self.screen, COLOR_BLACK, bg)
            self.screen.blit(ts, (bg.x + int(3 * self.scale), bg.y))

    # ------------------------------------------------------------------
    # Standalone runner
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Main loop for standalone execution."""
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(30) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    w, h = 665, 375
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("WOLF PRO : BRADSONIC-TELCO TELEBASE")
    app = SchoolDatabaseApp(screen, scale=1.0)
    app.run()
    pygame.quit()


if __name__ == "__main__":
    main()
