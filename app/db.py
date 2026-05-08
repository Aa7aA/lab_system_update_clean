import sqlite3
from pathlib import Path
import os
import shutil
import sys
from datetime import datetime

from .constants import ANTIBIOTICS


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

def get_starter_db_path() -> Path:
    # Running as packaged app (PyInstaller one-folder)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidate = exe_dir / "_internal" / "app" / "data" / "starter_lab.db"
        if candidate.exists():
            return candidate

    # Running from source
    return PROJECT_DIR / "app" / "data" / "starter_lab.db"


STARTER_DB_PATH = get_starter_db_path()

APP_DATA_DIR = Path(os.getenv("APPDATA", str(PROJECT_DIR))) / "AlshafaqLab"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DATA_DIR / "lab.db"
LEGACY_DB_PATH = PROJECT_DIR / "lab.db"




def ensure_db_file_location() -> None:
    if DB_PATH.exists():
        return

    # Use bundled starter DB
    if STARTER_DB_PATH.exists():
        shutil.copy2(STARTER_DB_PATH, DB_PATH)
        return

    # Fallback: create empty DB
    DB_PATH.touch()


def backup_database() -> None:
    """
    Rotating backup system (keeps only 3 backups)
    """
    ensure_db_file_location()

    if not DB_PATH.exists():
        return

    backup_dir = APP_DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    latest = backup_dir / "LabBackup_latest.db"
    prev1 = backup_dir / "LabBackup_previous_1.db"
    prev2 = backup_dir / "LabBackup_previous_2.db"

    # Rotate files
    if prev1.exists():
        if prev2.exists():
            prev2.unlink()
        prev1.rename(prev2)

    if latest.exists():
        latest.rename(prev1)

    # Create new latest backup
    shutil.copy2(DB_PATH, latest)


def _configure_conn(conn: sqlite3.Connection) -> sqlite3.Connection:
    # Make rows dict-like: row["patient_name"]
    conn.row_factory = sqlite3.Row

    # Enforce FK constraints
    conn.execute("PRAGMA foreign_keys = ON;")

    # Performance pragmas (safe for desktop apps)
    # WAL improves concurrency and avoids frequent full-file locks.
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")

    return conn


def get_conn() -> sqlite3.Connection:
    ensure_db_file_location()
    conn = sqlite3.connect(DB_PATH)
    return _configure_conn(conn)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    # NOTE: table is from our code, not user input
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_tests_layout_columns(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "tests")
    if "col" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN col INTEGER")
    if "pos" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN pos INTEGER")


def ensure_titers_two_column(conn: sqlite3.Connection) -> None:
    # Force Titers category layout
    conn.execute(
        """
        UPDATE categories
        SET layout_type='titers_two_col'
        WHERE module_code='Tests' AND name='Titers'
        """
    )

    # Ensure all Titers tests have a col (default 1)
    conn.execute(
        """
        UPDATE tests
        SET col = COALESCE(col, 1)
        WHERE module_code='Tests' AND category_name='Titers'
        """
    )

    # OPTIONAL: If you want all Titers dropdowns to have Positive/Negative at minimum
    # (Only inserts if not already present)
    rows = conn.execute(
        """
        SELECT id FROM tests
        WHERE module_code='Tests' AND category_name='Titers'
        """
    ).fetchall()

    for (tid,) in rows:
        conn.execute(
            "INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order) VALUES (?, ?, ?)",
            (tid, "Negative", 10),
        )
        conn.execute(
            "INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order) VALUES (?, ?, ?)",
            (tid, "Positive", 20),
        )


def ensure_category_layout_columns(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "categories")
    if "layout_type" not in cols:
        conn.execute("ALTER TABLE categories ADD COLUMN layout_type TEXT")
    if "layout_meta" not in cols:
        conn.execute("ALTER TABLE categories ADD COLUMN layout_meta TEXT")


def ensure_tests_display_label(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "tests")
    if "display_label" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN display_label TEXT")


def ensure_hematology_two_column(conn: sqlite3.Connection) -> None:
    # 1) Ensure category uses two_col
    conn.execute(
        """
        UPDATE categories
        SET layout_type = 'two_col'
        WHERE module_code='Tests' AND name='Hematology test'
        """
    )

    # 2) Ensure all existing Hematology tests default to column 1
    conn.execute(
        """
        UPDATE tests
        SET col = COALESCE(col, 1)
        WHERE module_code='Tests' AND category_name='Hematology test'
        """
    )

    # 3) Add the right-column tests (idempotent)
    right_tests = [
        ("BloodGroup", "dropdown", "", 100, 2),
        ("E.S.R", "text", "", 110, 2),
        ("D- Dimer", "text", "", 120, 2),
        ("Control Time", "text", "", 130, 2),
    ]

    for test_name, input_type, unit_default, sort_order, col in right_tests:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(module_code, category_name, test_name, input_type, unit_default, sort_order, col)
            VALUES ('Tests', 'Hematology test', ?, ?, ?, ?, ?)
            """,
            (test_name, input_type, unit_default, sort_order, col),
        )

    # 4) Add BloodGroup dropdown options
    row = conn.execute(
        """
        SELECT id FROM tests
        WHERE module_code='Tests' AND category_name='Hematology test' AND test_name='BloodGroup'
        """
    ).fetchone()

    if row:
        bloodgroup_id = int(row["id"])
        options = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        for i, opt in enumerate(options, start=1):
            conn.execute(
                """
                INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order)
                VALUES (?, ?, ?)
                """,
                (bloodgroup_id, opt, i * 10),
            )


# ---------------------------
# SFA: FORCE ORIGINAL LAYOUT
# ---------------------------
def ensure_sfa_original_layout(conn: sqlite3.Connection) -> None:
    """
    Force SFA module to exactly match the original program.
    Fully rebuilds SFA categories + tests + dropdown options.
    (Does NOT delete report_results history.)
    """
    module_code = "SFA"

    physical_cat = "physical Examination"
    micro_cat = "Microscopical Examination"
    motility_cat = "Motility"

    physical_tests = [
        "Appearance",
        "Volume",
        "Liquifaction",
        "Reaction",
        "Sperm count per ml",
    ]

    micro_tests = [
        "Normal",
        "Abnormal",
        "Pus Cells",
        "R.B.C",
        "Others",
    ]

    motility_tests = [
        "Grade A (Rapid progressive)",
        "Grade B (Rapid progressive)",
        "Grade C (Rapid progressive)",
        "Grade D (Immotile)",
    ]

    # ----------------------------
    # 1) FULL CLEAN SFA STRUCTURE
    # ----------------------------
    test_ids = conn.execute(
        "SELECT id FROM tests WHERE module_code=?",
        (module_code,),
    ).fetchall()

    ids = [int(r[0]) for r in test_ids]
    if ids:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(f"DELETE FROM test_options WHERE test_id IN ({placeholders})", ids)

    conn.execute("DELETE FROM tests WHERE module_code=?", (module_code,))
    conn.execute("DELETE FROM categories WHERE module_code=?", (module_code,))

    # ----------------------------
    # 2) RECREATE CATEGORIES
    # ----------------------------
    categories = [
        (physical_cat, 1),
        (micro_cat, 2),
        (motility_cat, 3),
    ]
    for name, order in categories:
        conn.execute(
            """
            INSERT INTO categories(module_code, name, sort_order, layout_type, layout_meta)
            VALUES (?, ?, ?, '', '')
            """,
            (module_code, name, order),
        )

    # ----------------------------
    # 3) INSERT TESTS
    # ----------------------------
    dropdown_tests = {
        "Appearance",
        "Reaction",
        "Pus Cells",
        "R.B.C",
        "Others",
    }

    def insert_tests(category: str, test_list: list[str]) -> None:
        for i, name in enumerate(test_list, start=1):
            input_type = "dropdown" if name in dropdown_tests else "text"
            conn.execute(
                """
                INSERT INTO tests(
                    module_code, category_name, test_name,
                    input_type, unit_default,
                    sort_order, col, pos
                )
                VALUES (?, ?, ?, ?, '', ?, 1, ?)
                """,
                (module_code, category, name, input_type, i * 10, i),
            )

    insert_tests(physical_cat, physical_tests)
    insert_tests(micro_cat, micro_tests)
    insert_tests(motility_cat, motility_tests)

    # ----------------------------
    # 4) INSERT DROPDOWN OPTIONS
    # ----------------------------
    def get_test_id(category: str, name: str) -> int | None:
        r = conn.execute(
            """
            SELECT id FROM tests
            WHERE module_code=? AND category_name=? AND test_name=?
            """,
            (module_code, category, name),
        ).fetchone()
        return int(r["id"]) if r else None

    def add_options(test_id: int, options: list[str]) -> None:
        for idx, opt in enumerate(options, start=1):
            conn.execute(
                """
                INSERT INTO test_options(test_id, option_value, sort_order)
                VALUES (?, ?, ?)
                """,
                (test_id, opt, idx * 10),
            )

    appearance_opts = [
        "Opalescent Gray",
        "Milky",
        "cloudy",
        "Turbid",
        "Bloody",
    ]

    reaction_opts = [
        "acidic",
        "alkaline",
        "pH=5",
        "pH=6",
        "pH=6.5",
        "pH=7",
        "pH=8",
        "pH=9",
    ]

    hpfs = [
        "Nil",
        "(0--1)H.P.F",
        "(1--2)H.P.F",
        "(2--3)H.P.F",
        "(3--4)H.P.F",
        "(4--5)H.P.F",
        "(5--6)H.P.F",
        "(6--7)H.P.F",
        "(7--8)H.P.F",
        "(+)H.P.F",
        "(++)H.P.F",
        "(+++)H.P.F",
        "(++++)H.P.F",
    ]

    tid = get_test_id(physical_cat, "Appearance")
    if tid:
        add_options(tid, appearance_opts)

    tid = get_test_id(physical_cat, "Reaction")
    if tid:
        add_options(tid, reaction_opts)

    for name in ["Pus Cells", "R.B.C", "Others"]:
        tid = get_test_id(micro_cat, name)
        if tid:
            add_options(tid, hpfs)



def ensure_sputum_plus_module(conn: sqlite3.Connection) -> None:
    # Use the exact module code you currently have in your UI title/tab: "Sputum+"
    MODULE = "Sputum+"
    CAT = "Sputum+"

    # 1) Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 50)
        """,
        (MODULE, MODULE),
    )

    # 2) Ensure category exists (single tab)
    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type)
        VALUES (?, ?, 1, 'sputum_plus_override')
        """,
        (MODULE, CAT),
    )

    # 3) DELETE old tests of Sputum+ (so your module becomes identical)
    # This is the key difference: you currently have Color/Consistency/etc.
    conn.execute(
        "DELETE FROM tests WHERE module_code=? AND category_name=?",
        (MODULE, CAT),
    )

    # 4) Insert the exact rows in the correct order
    def add_test(test_name: str, sort_order: int) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(module_code, category_name, test_name, input_type, unit_default, sort_order)
            VALUES (?, ?, ?, 'dropdown', '', ?)
            """,
            (MODULE, CAT, test_name, sort_order),
        )

    # AFB section
    add_test("Specimen", 10)
    add_test("AFB Header", 20)
    add_test("AFB Result 1", 30)
    add_test("AFB Result 2", 40)
    add_test("AFB Result 3", 50)
    add_test("AFB Result 4", 60)
    add_test("AFB Result 5", 70)
    add_test("AFB Result 6", 80)

    # Gram stain section
    add_test("Gram Header", 90)
    add_test("Polymorph nuclear cell", 100)
    add_test("Diplococci", 110)
    add_test("Mouth flora", 120)
    add_test("Gram Extra 1", 130)
    add_test("Gram Extra 2", 140)

    # Helper to insert dropdown options for a test
    def set_options(test_name: str, options: list[str]) -> None:
        row = conn.execute(
            """
            SELECT id FROM tests
            WHERE module_code=? AND category_name=? AND test_name=?
            """,
            (MODULE, CAT, test_name),
        ).fetchone()
        if not row:
            return
        tid = int(row["id"])

        # wipe old options for that test (safe because we rebuilt tests)
        conn.execute("DELETE FROM test_options WHERE test_id=?", (tid,))

        for i, opt in enumerate(options, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order) VALUES (?, ?, ?)",
                (tid, opt, i * 10),
            )

    # Specimen dropdown options
    set_options("Specimen", [
        "Sputum for A.F.B:",
        "Skin scraping for KoH",
    ])

    # Header dropdown options
    set_options("AFB Header", [
        "Z - N stain shows:",
        "Direct smaen for KoH showes:",
    ])

    # Main AFB result options
    set_options("AFB Result 1", [
        "No Acid fast bacilli seen (Negaive -ve)",
        "Acid fast bacilli seen (Positive +ve)",
        "fungal elements seen (positive)",
        "fungial elements seen (positive)",
    ])

    # Gram header options
    set_options("Gram Header", [
        "Sputum for Gramstain shows:",
    ])

    # Polymorph options
    set_options("Polymorph nuclear cell", [
        "few number for polymorph nuclear cell",
        "large number for polymorph nuclear cell",
        "moderate number for polymorph nuclear cell",
    ])

    # Diplococci options
    set_options("Diplococci", [
        "few number for G+ve diplococci.",
        "large number for G+ve diplococci.",
        "moderate number for G+ve diplococci.",
        "few number for G-ve diplococci.",
        "large number for G-ve diplococci.",
        "moderate number for G-ve diplococci.",
    ])

    # Mouth flora options
    set_options("Mouth flora", [
        "normal mouth flora seen",
    ])


def ensure_gue_module(conn: sqlite3.Connection) -> None:
    MODULE = "GUE"
    CAT = "GUE"

    # Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 45)
        """,
        (MODULE, MODULE),
    )

    # Ensure category exists
    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type)
        VALUES (?, ?, 1, 'gue_override')
        """,
        (MODULE, CAT),
    )

    # Rebuild GUE tests
    conn.execute("DELETE FROM tests WHERE module_code=? AND category_name=?", (MODULE, CAT))

    def add_dd(test_name: str, sort_order: int) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(module_code, category_name, test_name, input_type, unit_default, sort_order)
            VALUES (?, ?, ?, 'dropdown', '', ?)
            """,
            (MODULE, CAT, test_name, sort_order),
        )

    # Physical
    add_dd("color", 10)
    add_dd("appearance", 20)
    add_dd("reaction", 30)
    add_dd("sp_gravity", 40)
    add_dd("albumin", 50)
    add_dd("sugar", 60)
    add_dd("bile_pigment", 70)
    add_dd("urobilinogen", 80)
    add_dd("ketone_bodies", 90)
    add_dd("protein", 100)

    # Microscopic
    add_dd("pus_cell", 110)
    add_dd("rbc", 120)
    add_dd("epith_cell", 130)
    add_dd("casts", 140)
    add_dd("crystals_1", 150)
    add_dd("crystals_2", 160)
    add_dd("bacteria", 170)
    add_dd("other_1", 180)
    add_dd("other_2", 190)




def ensure_gse_module(conn: sqlite3.Connection) -> None:
    MODULE = "GSE"
    CAT = "GSE"

    # Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 60)
        """,
        (MODULE, MODULE),
    )

    # Ensure category exists (single tab)
    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type)
        VALUES (?, ?, 1, 'gse_override')
        """,
        (MODULE, CAT),
    )

    # Wipe old tests so it becomes identical to original
    conn.execute("DELETE FROM tests WHERE module_code=? AND category_name=?", (MODULE, CAT))

    def add_dd(test_name: str, sort_order: int) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(module_code, category_name, test_name, input_type, unit_default, sort_order)
            VALUES (?, ?, ?, 'dropdown', '', ?)
            """,
            (MODULE, CAT, test_name, sort_order),
        )

    # --- Left panel: Physically Examination ---
    add_dd("Color", 10)
    add_dd("Consistency", 20)
    add_dd("pH", 30)

    # --- Right panel: Microscopical Examination ---
    add_dd("R.b.cs", 40)
    add_dd("Pus cell", 50)
    add_dd("Cyst", 60)
    add_dd("Trophozoite", 70)
    add_dd("Ova", 80)
    add_dd("Monilia", 90)
    add_dd("Fatty droplt", 100)
    add_dd("Undigested food", 110)
    add_dd("Other", 120)

    # Helper to replace options
    def set_options(test_name: str, options: list[str]) -> None:
        row = conn.execute(
            """
            SELECT id FROM tests
            WHERE module_code=? AND category_name=? AND test_name=?
            """,
            (MODULE, CAT, test_name),
        ).fetchone()
        if not row:
            return
        tid = int(row["id"])
        conn.execute("DELETE FROM test_options WHERE test_id=?", (tid,))
        for i, opt in enumerate(options, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order) VALUES (?, ?, ?)",
                (tid, opt, i * 10),
            )

    # -------------------
    # Options (from your screenshots)
    # -------------------

    set_options("Color", ["Brown", "Yellowish", "redish", "Black", "Green"])

    set_options("Consistency", ["solid", "semi solid", "Liquide", "semi Liquide", "Mucus"])

    set_options("pH", ["acidic", "alkaline", "pH=5", "pH=6", "pH=6.5", "pH=7", "pH=8", "pH=9"])

    # RBC / Pus cell use the same numeric scale list (Nil + ranges + plus signs)
    scale = [
        "Nil",
        "(0--1)H.P.F",
        "(1--3)H.P.F",
        "(3--5)H.P.F",
        "(5--7)H.P.F",
        "(7--9)H.P.F",
        "(+)H.P.F",
        "(++)H.P.F",
        "(+++)H.P.F",
        "(++++)H.P.F",
    ]
    set_options("R.b.cs", scale)
    set_options("Pus cell", scale)

    set_options("Cyst", ["Nil", "E.Histolytica seen", "E.Histolytica (+)", "E. Coli seen"])

    set_options("Trophozoite", ["Nil", "E.Histolytica seen", "E.Histolytica (+)", "E. Coli seen"])

    set_options("Ova", ["Nil", "seen"])

    set_options("Monilia", ["Nil", "few", "(+)", "(++)", "(+++)"])

    set_options("Fatty droplt", ["Nil", "seen"])

    set_options("Undigested food", ["Nil", "seen"])

    set_options("Other", ["Nil", "Bacteria: seen", "Bacteria: Few", "Bacteria: Heavy"])



def ensure_stone_module(conn: sqlite3.Connection) -> None:
    MODULE = "Stone"
    CAT = "Stone"

    # 1) Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 70)
        """,
        (MODULE, MODULE),
    )

    # 2) Ensure category exists (single tab)
    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type)
        VALUES (?, ?, 1, 'stone_override')
        """,
        (MODULE, CAT),
    )

    # 3) Remove old Stone tests so it becomes identical
    conn.execute("DELETE FROM tests WHERE module_code=? AND category_name=?", (MODULE, CAT))

    def add_dd(test_name: str, sort_order: int) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(module_code, category_name, test_name, input_type, unit_default, sort_order)
            VALUES (?, ?, ?, 'dropdown', '', ?)
            """,
            (MODULE, CAT, test_name, sort_order),
        )

    # ---- Top row ----
    add_dd("Final Diagnosis", 5)

    # ---- Left panel fields ----
    add_dd("Color", 10)
    add_dd("Texture", 20)
    add_dd("Calcium Oxalate", 30)
    add_dd("Carbonate", 40)
    add_dd("Phosphate", 50)
    add_dd("Magnisum", 60)   # keep original spelling
    add_dd("Uric acid", 70)
    add_dd("Cystin", 80)

    def set_options(test_name: str, options: list[str]) -> None:
        row = conn.execute(
            """
            SELECT id FROM tests
            WHERE module_code=? AND category_name=? AND test_name=?
            """,
            (MODULE, CAT, test_name),
        ).fetchone()
        if not row:
            return
        tid = int(row["id"])
        conn.execute("DELETE FROM test_options WHERE test_id=?", (tid,))
        for i, opt in enumerate(options, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order) VALUES (?, ?, ?)",
                (tid, opt, i * 10),
            )

    # Options from screenshots
    set_options("Color", ["black"])         # add more if you want
    set_options("Texture", ["solid"])       # add more if you want

    posneg = ["Negative(-ve)", "Positive(+ve)"]
    set_options("Calcium Oxalate", posneg)
    set_options("Carbonate", posneg)
    set_options("Phosphate", posneg)
    set_options("Magnisum", posneg)
    set_options("Uric acid", posneg)
    set_options("Cystin", posneg)

    # Final Diagnosis options (not shown in your screenshots)
    # Keep it editable anyway, but adding a few common ones helps.
    set_options("Final Diagnosis", [
        "",
        "Calcium Oxalate stone",
        "Uric acid stone",
        "Cystine stone",
        "Mixed stone",
    ])




def ensure_hvs_module(conn: sqlite3.Connection) -> None:
    MODULE = "HVS"
    CAT = "HVS"

    # Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 80)
        """,
        (MODULE, MODULE),
    )

    # Single category tab (UI will be overridden)
    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type)
        VALUES (?, ?, 1, 'hvs_override')
        """,
        (MODULE, CAT),
    )

    # Make it identical: reset tests for this module/category
    conn.execute("DELETE FROM tests WHERE module_code=? AND category_name=?", (MODULE, CAT))

    def add_dd(test_name: str, sort_order: int) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(module_code, category_name, test_name, input_type, unit_default, sort_order)
            VALUES (?, ?, ?, 'dropdown', '', ?)
            """,
            (MODULE, CAT, test_name, sort_order),
        )

    # Right-top box
    add_dd("Sample", 5)
    add_dd("Method", 10)

    # Left panel fields (exact names as shown)
    add_dd("R.B.Cs", 20)
    add_dd("Pus cells", 30)
    add_dd("Epith cells", 40)
    add_dd("Bacteria", 50)
    add_dd("Monilia", 60)
    add_dd("Trichamonas vaginalis", 70)

    def set_options(test_name: str, options: list[str]) -> None:
        row = conn.execute(
            """
            SELECT id FROM tests
            WHERE module_code=? AND category_name=? AND test_name=?
            """,
            (MODULE, CAT, test_name),
        ).fetchone()
        if not row:
            return
        tid = int(row["id"])
        conn.execute("DELETE FROM test_options WHERE test_id=?", (tid,))
        for i, opt in enumerate(options, start=1):
            conn.execute(
                "INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order) VALUES (?, ?, ?)",
                (tid, opt, i * 10),
            )

    # Dropdown options from screenshots
    set_options("Sample", ["High Vaginal Swab"])
    set_options("Method", ["Direct Examination"])

    # All parameter dropdowns show Nil (you can add more later)
    nil_only = ["Nil"]
    for tn in ["R.B.Cs", "Pus cells", "Epith cells", "Bacteria", "Monilia", "Trichamonas vaginalis"]:
        set_options(tn, nil_only)




#new

def ensure_normal_ranges_table(conn: sqlite3.Connection) -> None:
    table_exists = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'normal_ranges'
        """
    ).fetchone() is not None

    if not table_exists:
        conn.execute(
            """
            CREATE TABLE normal_ranges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_code TEXT NOT NULL,
                category_name TEXT NOT NULL,
                test_name TEXT NOT NULL,
                range_mode TEXT DEFAULT 'none',
                gender TEXT,
                age_min INTEGER,
                age_max INTEGER,
                label TEXT,
                min_value TEXT,
                max_value TEXT,
                unit TEXT,
                subject TEXT,
                normal_text TEXT,
                sort_order INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(module_code) REFERENCES modules(code) ON DELETE CASCADE
            )
            """
        )
    else:
        info_rows = conn.execute("PRAGMA table_info(normal_ranges)").fetchall()
        cols = {str(r[1]) for r in info_rows}
        pk_cols = [str(r[1]) for r in info_rows if int(r[5] or 0) > 0]

        needs_rebuild = (
            "id" not in cols
            or pk_cols != ["id"]
        )

        if needs_rebuild:
            conn.execute(
                """
                CREATE TABLE normal_ranges_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_code TEXT NOT NULL,
                    category_name TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    range_mode TEXT DEFAULT 'none',
                    gender TEXT,
                    age_min INTEGER,
                    age_max INTEGER,
                    label TEXT,
                    min_value TEXT,
                    max_value TEXT,
                    unit TEXT,
                    subject TEXT,
                    normal_text TEXT,
                    sort_order INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(module_code) REFERENCES modules(code) ON DELETE CASCADE
                )
                """
            )

            select_parts = [
                "module_code",
                "category_name",
                "test_name",
                "'none' AS range_mode",
                "NULL AS gender",
                "NULL AS age_min",
                "NULL AS age_max",
                "NULL AS label",
                "min_value",
                "max_value",
                "unit",
                "NULL AS subject",
                "normal_text",
                "0 AS sort_order",
                "updated_at",
            ]

            if "range_mode" in cols:
                select_parts[3] = "COALESCE(range_mode, 'none') AS range_mode"
            if "gender" in cols:
                select_parts[4] = "gender"
            if "age_min" in cols:
                select_parts[5] = "age_min"
            if "age_max" in cols:
                select_parts[6] = "age_max"
            if "label" in cols:
                select_parts[7] = "label"
            if "subject" in cols:
                select_parts[11] = "subject"
            if "sort_order" in cols:
                select_parts[13] = "COALESCE(sort_order, 0) AS sort_order"

            conn.execute(
                f"""
                INSERT INTO normal_ranges_new (
                    module_code,
                    category_name,
                    test_name,
                    range_mode,
                    gender,
                    age_min,
                    age_max,
                    label,
                    min_value,
                    max_value,
                    unit,
                    subject,
                    normal_text,
                    sort_order,
                    updated_at
                )
                SELECT
                    {", ".join(select_parts)}
                FROM normal_ranges
                """
            )

            conn.execute("DROP TABLE normal_ranges")
            conn.execute("ALTER TABLE normal_ranges_new RENAME TO normal_ranges")
        else:
            if "range_mode" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN range_mode TEXT DEFAULT 'none'")
            if "gender" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN gender TEXT")
            if "age_min" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN age_min INTEGER")
            if "age_max" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN age_max INTEGER")
            if "label" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN label TEXT")
            if "subject" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN subject TEXT")
            if "sort_order" not in cols:
                conn.execute("ALTER TABLE normal_ranges ADD COLUMN sort_order INTEGER DEFAULT 0")

    row = conn.execute("SELECT COUNT(*) AS c FROM normal_ranges").fetchone()
    existing_count = int(row["c"]) if row else 0

    if existing_count == 0:
        conn.execute(
            """
            INSERT OR IGNORE INTO normal_ranges (
                module_code,
                category_name,
                test_name,
                range_mode,
                min_value,
                max_value,
                unit,
                normal_text,
                sort_order,
                updated_at
            )
            SELECT
                t.module_code,
                t.category_name,
                tr.test_name,
                'none',
                CASE WHEN tr.min_value IS NULL THEN '' ELSE CAST(tr.min_value AS TEXT) END,
                CASE WHEN tr.max_value IS NULL THEN '' ELSE CAST(tr.max_value AS TEXT) END,
                COALESCE(tr.unit, ''),
                '',
                0,
                datetime('now')
            FROM test_ranges tr
            JOIN tests t
              ON t.test_name = tr.test_name
            """
        )

    conn.execute(
        """
        UPDATE normal_ranges
        SET range_mode = 'none'
        WHERE range_mode IS NULL OR TRIM(range_mode) = ''
        """
    )

    conn.execute(
        """
        UPDATE normal_ranges
        SET sort_order = 0
        WHERE sort_order IS NULL
        """
    )




def ensure_culture_db_structure(conn: sqlite3.Connection) -> None:
    MODULE = "Culture"

    # 1) Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 15)
        """,
        (MODULE, MODULE),
    )

    # 2) Ensure core categories exist
    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type, layout_meta)
        VALUES (?, ?, 1, 'form', '')
        """,
        (MODULE, "Culture"),
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type, layout_meta)
        VALUES (?, ?, 2, 'culture_antibiotics', '')
        """,
        (MODULE, "Antibiotics"),
    )

    # 3) Ensure Sample and Result tests exist
    conn.execute(
        """
        INSERT OR IGNORE INTO tests(
            module_code, category_name, test_name,
            input_type, unit_default, sort_order, col, pos
        )
        VALUES (?, ?, ?, 'dropdown', '', 10, 1, 1)
        """,
        (MODULE, "Culture", "Sample"),
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO tests(
            module_code, category_name, test_name,
            input_type, unit_default, sort_order, col, pos
        )
        VALUES (?, ?, ?, 'dropdown', '', 20, 1, 2)
        """,
        (MODULE, "Culture", "Result"),
    )

    # 4) Ensure antibiotics exist as dropdown tests
    for i, name in enumerate(ANTIBIOTICS, start=1):
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(
                module_code, category_name, test_name,
                input_type, unit_default, sort_order, col, pos
            )
            VALUES (?, ?, ?, 'dropdown', '', ?, 1, ?)
            """,
            (MODULE, "Antibiotics", name, i * 10, i),
        )

    # 5) Helper to get test_id
    def get_test_id(category_name: str, test_name: str) -> int | None:
        row = conn.execute(
            """
            SELECT id
            FROM tests
            WHERE module_code = ? AND category_name = ? AND test_name = ?
            """,
            (MODULE, category_name, test_name),
        ).fetchone()
        return int(row["id"]) if row else None

    # 6) Helper to ensure options exist
    def add_options(category_name: str, test_name: str, options: list[str]) -> None:
        test_id = get_test_id(category_name, test_name)
        if test_id is None:
            return

        for idx, opt in enumerate(options, start=1):
            conn.execute(
                """
                INSERT OR IGNORE INTO test_options(test_id, option_value, sort_order)
                VALUES (?, ?, ?)
                """,
                (test_id, opt, idx * 10),
            )

    # 7) Sample options
    add_options("Culture", "Sample", [
        "",
        "Urine for C/S",
        "Pus for C/S",
        "Stool for C/S",
        "Wound swab for C/S",
        "H.vaginal swab for C/S",
        "Eye swab for C/S",
        "Ear swab for C/S",
        "Nasial for C/S",
    ])

    # 8) Result options
    add_options("Culture", "Result", [
        "",
        "No pathogenic bacterial growth could be isolated",
        "Culture: Yield growth of Morillia sp",
        "Culture: Yield growth of E. Coli",
        "Culture: Yield growth of Entero coccus spp",
        "Culture: Yield growth of Klebsiella sp",
        "Culture: Yield growth of Strept pyogen",
        "Culture: Yield growth of Staph aureus",
        "Culture: Yield growth of Pseudo monas spp",
        "Culture: Yield growth of Proteus spp",
        "Culture: Yield growth of Strept Faecalis",
        "Culture: Heavy growth of Staph.Saprophyticus .",
        "Culture: Yield growth of Staphylococcus spp",
        "Culture: Yield growth of Streptococcus spp.",
    ])

    # 9) Antibiotic options
    for ab in ANTIBIOTICS:
        add_options("Antibiotics", ab, ["", "S", "I", "R"])


def ensure_tests_module_structure(conn: sqlite3.Connection) -> None:
    MODULE = "Tests"

    # Ensure module exists
    conn.execute(
        """
        INSERT OR IGNORE INTO modules(code, display_name, sort_order)
        VALUES (?, ?, 10)
        """,
        (MODULE, MODULE),
    )

    # Ensure base categories exist
    categories = [
        ("Hematology test", 1, "two_col"),
        ("Titers", 2, "titers_two_col"),
    ]

    for name, sort_order, layout_type in categories:
        conn.execute(
            """
            INSERT OR IGNORE INTO categories(module_code, name, sort_order, layout_type, layout_meta)
            VALUES (?, ?, ?, ?, '')
            """,
            (MODULE, name, sort_order, layout_type),
        )

    # Ensure some base Hematology tests exist
    hematology_tests = [
        ("Hb", "text", "", 10, 1),
        ("W.B.C", "text", "", 20, 1),
        ("P.C.V", "text", "", 30, 1),
        ("Platelets", "text", "", 40, 1),
    ]

    for test_name, input_type, unit_default, sort_order, col in hematology_tests:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(
                module_code, category_name, test_name,
                input_type, unit_default, sort_order, col, pos
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (MODULE, "Hematology test", test_name, input_type, unit_default, sort_order, col, sort_order // 10),
        )

    # Ensure some base Titers tests exist
    titers_tests = [
        ("Widal", "dropdown", "", 10, 1),
        ("Brucella", "dropdown", "", 20, 1),
    ]

    for test_name, input_type, unit_default, sort_order, col in titers_tests:
        conn.execute(
            """
            INSERT OR IGNORE INTO tests(
                module_code, category_name, test_name,
                input_type, unit_default, sort_order, col, pos
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (MODULE, "Titers", test_name, input_type, unit_default, sort_order, col, sort_order // 10),
        )


def ensure_lab_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lab_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
        """
    )

    defaults = {
        "footer_text": "دوميز - شارع جامع الرشيد - مجمع الشفق الطبي - مجاور صيدلية ليا",
        "lab_phone": "07725017776",
        "whatsapp_number": "07725017776",
        "previous_results_enabled": "0",
    }

    for key, value in defaults.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO lab_settings(setting_key, setting_value)
            VALUES (?, ?)
            """,
            (key, value),
        )


def get_lab_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute(
        """
        SELECT setting_value
        FROM lab_settings
        WHERE setting_key = ?
        """,
        (key,),
    ).fetchone()
    if not row:
        return default
    return str(row[0] or default)


def set_lab_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO lab_settings(setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value
        """,
        (key, value),
    )



def ensure_core_modules(conn: sqlite3.Connection) -> None:
    core_modules = [
        ("Tests", "Tests", 10),
        ("Culture", "Culture", 15),
        ("CBC", "CBC", 20),
        ("SFA", "SFA", 30),
        ("Sputum+", "Sputum+", 40),
        ("GUE", "GUE", 45),
        ("GSE", "GSE", 50),
        ("Torch", "Torch", 55),
        ("Stone", "Stone", 60),
        ("HVS", "HVS", 70),
    ]

    for code, display_name, sort_order in core_modules:
        conn.execute(
            """
            INSERT OR IGNORE INTO modules(code, display_name, sort_order)
            VALUES (?, ?, ?)
            """,
            (code, display_name, sort_order),
        )

def has_existing_test_data(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) FROM tests").fetchone()
    return bool(row and int(row[0]) > 0)


def init_db() -> None:
    
    
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                code TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_code TEXT NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,

                -- layout support
                layout_type TEXT,
                layout_meta TEXT,

                UNIQUE(module_code, name),
                FOREIGN KEY(module_code) REFERENCES modules(code) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_code TEXT NOT NULL,
                category_name TEXT NOT NULL,
                test_name TEXT NOT NULL,

                -- UI config
                display_label TEXT,
                input_type TEXT NOT NULL DEFAULT 'text',   -- text | dropdown | textarea
                unit_default TEXT,

                sort_order INTEGER NOT NULL DEFAULT 0,

                -- layout support
                col INTEGER,
                pos INTEGER,

                UNIQUE(module_code, category_name, test_name),
                FOREIGN KEY(module_code) REFERENCES modules(code) ON DELETE CASCADE

                -- Recommended integrity (future migration):
                -- FOREIGN KEY(module_code, category_name)
                --   REFERENCES categories(module_code, name) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS test_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                option_value TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                UNIQUE(test_id, option_value),
                FOREIGN KEY(test_id) REFERENCES tests(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS test_ranges (
                test_name TEXT PRIMARY KEY,
                min_value REAL,
                max_value REAL,
                unit TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                patient_name TEXT NOT NULL,
                doctor_name TEXT,
                gender TEXT,
                age INTEGER,
                patient_code TEXT,
                copies INTEGER NOT NULL DEFAULT 1,
                report_date TEXT NOT NULL,
                external_lab INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS report_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                module TEXT NOT NULL,
                category TEXT NOT NULL,
                test_name TEXT NOT NULL,
                result TEXT,
                unit TEXT,
                min_value TEXT,
                max_value TEXT,
                flag TEXT,
                FOREIGN KEY(report_id) REFERENCES reports(report_id) ON DELETE CASCADE,
                UNIQUE(report_id, module, category, test_name)
            );

            -- Indexes (performance)
            CREATE INDEX IF NOT EXISTS idx_reports_patient_date
                ON reports(patient_name, report_date);

            CREATE INDEX IF NOT EXISTS idx_reports_updated
                ON reports(updated_at);

            CREATE INDEX IF NOT EXISTS idx_report_results_report_module
                ON report_results(report_id, module);

            CREATE INDEX IF NOT EXISTS idx_tests_module_category_sort
                ON tests(module_code, category_name, sort_order);

            CREATE INDEX IF NOT EXISTS idx_test_options_test_sort
                ON test_options(test_id, sort_order);
        """)

        # Safety upgrades for old DBs
        ensure_tests_layout_columns(conn)
        ensure_category_layout_columns(conn)
        ensure_tests_display_label(conn)
        ensure_normal_ranges_table(conn)

        # Check whether this is a brand-new empty database
        module_count_row = conn.execute("SELECT COUNT(*) AS n FROM modules").fetchone()
        module_count = int(module_count_row["n"] if module_count_row and module_count_row["n"] is not None else 0)

        # Always keep schema/support tables ready
        ensure_lab_settings_table(conn)
        ensure_core_modules(conn)


        has_test_data = has_existing_test_data(conn)

        if module_count == 0 and not has_test_data:
            # Only seed a minimal structure when the database is truly empty
            ensure_tests_module_structure(conn)
            ensure_culture_db_structure(conn)
            ensure_gue_module(conn)
            ensure_hematology_two_column(conn)
            ensure_titers_two_column(conn)
            ensure_gse_module(conn)
            ensure_stone_module(conn)
            ensure_hvs_module(conn)
            ensure_sfa_original_layout(conn)
            ensure_sputum_plus_module(conn)
        else:
            # Existing starter DB or migrated DB: do not overwrite rich structures
            ensure_culture_db_structure(conn)

        conn.commit()




def find_previous_test_results_for_report(
    conn,
    *,
    patient_name: str,
    current_report_id: str,
    months: int = 3,
) -> dict[tuple[str, str], dict]:
    """
    For Tests module only:
    Find latest previous result for same patient + same category + same test
    within the last N months.
    """
    patient_name = (patient_name or "").strip()
    current_report_id = (current_report_id or "").strip()

    if not patient_name:
        return {}

    rows = conn.execute(
        """
        SELECT
            rr.category,
            rr.test_name,
            COALESCE(rr.result, '') AS result,
            COALESCE(rr.unit, '') AS unit,
            COALESCE(rr.flag, '') AS flag,
            r.report_date
        FROM report_results rr
        JOIN reports r ON r.report_id = rr.report_id
        WHERE
            rr.module = 'Tests'
            AND TRIM(COALESCE(rr.result, '')) <> ''
            AND LOWER(TRIM(r.patient_name)) = LOWER(TRIM(?))
            AND rr.report_id <> ?
            AND date(r.report_date) >= date('now', ?)
        ORDER BY date(r.report_date) DESC, r.updated_at DESC
        """,
        (patient_name, current_report_id, f"-{int(months)} months"),
    ).fetchall()

    out: dict[tuple[str, str], dict] = {}

    for row in rows:
        key = (str(row["category"] or ""), str(row["test_name"] or ""))
        if key in out:
            continue

        out[key] = {
            "category": str(row["category"] or ""),
            "test_name": str(row["test_name"] or ""),
            "result": str(row["result"] or ""),
            "unit": str(row["unit"] or ""),
            "flag": str(row["flag"] or ""),
            "previous_date": str(row["report_date"] or ""),
        }

    return out


def find_latest_previous_report(
    conn,
    *,
    patient_name: str,
    module_code: str,
    current_report_id: str = "",
    months: int = 3,
) -> dict | None:
    """
    Find latest previous report for same patient + same module within N months.
    Used by Prev button.
    """
    patient_name = (patient_name or "").strip()
    module_code = (module_code or "").strip()
    current_report_id = (current_report_id or "").strip()

    if not patient_name or not module_code:
        return None

    row = conn.execute(
        """
        SELECT
            r.report_id,
            r.patient_name,
            r.doctor_name,
            r.gender,
            r.age,
            r.patient_code,
            r.report_date
        FROM reports r
        WHERE
            LOWER(TRIM(r.patient_name)) = LOWER(TRIM(?))
            AND r.report_id <> ?
            AND date(r.report_date) >= date('now', ?)
            AND EXISTS (
                SELECT 1
                FROM report_results rr
                WHERE rr.report_id = r.report_id
                  AND rr.module = ?
                  AND TRIM(COALESCE(rr.result, '')) <> ''
            )
        ORDER BY date(r.report_date) DESC, r.updated_at DESC
        LIMIT 1
        """,
        (patient_name, current_report_id, f"-{int(months)} months", module_code),
    ).fetchone()

    return dict(row) if row else None


def fetch_report_rows_for_pdf(conn, *, report_id: str, module_code: str) -> list[dict]:
    """
    Fetch saved rows for a previous report so it can be printed again.
    """
    rows = conn.execute(
        """
        SELECT
            rr.category AS category,
            rr.test_name AS test_name,
            COALESCE(rr.result, '') AS result,
            COALESCE(rr.unit, '') AS unit,
            COALESCE(rr.flag, '') AS flag
        FROM report_results rr
        LEFT JOIN categories c
            ON c.module_code = rr.module
           AND c.name = rr.category
        LEFT JOIN tests t
            ON t.module_code = rr.module
           AND t.category_name = rr.category
           AND t.test_name = rr.test_name
        WHERE rr.report_id = ?
          AND rr.module = ?
          AND TRIM(COALESCE(rr.result, '')) <> ''
        ORDER BY
            COALESCE(c.sort_order, 999999),
            rr.category,
            COALESCE(t.sort_order, 999999),
            COALESCE(t.pos, 999999),
            rr.test_name
        """,
        (report_id, module_code),
    ).fetchall()

    return [dict(r) for r in rows]



def is_previous_results_enabled(conn) -> bool:
    value = get_lab_setting(conn, "previous_results_enabled", "0")
    return str(value or "0").strip() == "1"