"""
מנטר עסקאות טלגרם - ממשק גרפי מודרני
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import asyncio
import json
import os
import webbrowser
import re
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient, events

import config

PRODUCTS_FILE  = os.path.join(os.path.dirname(__file__), "products.json")
SESSION_FILE   = os.path.join(os.path.dirname(__file__), "session")
DEALS_FILE     = os.path.join(os.path.dirname(__file__), "deals.json")
CHANNELS_FILE  = os.path.join(os.path.dirname(__file__), "channels.json")

# ─── צבעים ────────────────────────────────────────────────
BG          = "#0f0f13"       # רקע ראשי
BG2         = "#1a1a24"       # רקע כרטיסים
BG3         = "#22222f"       # רקע שורות / inputs
ACCENT      = "#6c63ff"       # סגול ראשי
ACCENT2     = "#00d4aa"       # ירוק-טורקיז
DANGER      = "#ff5c5c"       # אדום
TEXT        = "#e8e8f0"       # טקסט ראשי
TEXT2       = "#8888aa"       # טקסט משני
BORDER      = "#2e2e42"       # מסגרות
ROW_ODD     = "#1e1e2a"
ROW_EVEN    = "#181824"
SEL_BG      = "#3d3a6e"


def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"label": str(ch), "value": ch} for ch in config.CHANNELS_TO_MONITOR]

def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return config.PRODUCTS[:]

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def load_deals():
    if os.path.exists(DEALS_FILE):
        with open(DEALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_deals(deals):
    with open(DEALS_FILE, "w", encoding="utf-8") as f:
        json.dump(deals[-500:], f, ensure_ascii=False, indent=2)

def extract_url(text):
    urls = re.findall(r'https?://[^\s\)\]\>]+', text)
    return urls[0] if urls else ""

def check_message(text, products):
    text_lower = text.lower()
    found = []
    for product in products:
        if any(kw.lower() in text_lower for kw in product["keywords"]):
            if not any(ex.lower() in text_lower for ex in product.get("exclude_keywords", [])):
                found.append(product)
    return found


# ─── עיצוב גלובלי ─────────────────────────────────────────
def apply_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",
        background=BG, foreground=TEXT,
        font=("Segoe UI", 10), borderwidth=0, relief="flat")

    style.configure("TFrame",    background=BG)
    style.configure("Card.TFrame", background=BG2, relief="flat")

    style.configure("TLabel",    background=BG,  foreground=TEXT)
    style.configure("Dim.TLabel", background=BG2, foreground=TEXT2, font=("Segoe UI", 8))
    style.configure("Head.TLabel", background=BG, foreground=TEXT,  font=("Segoe UI", 13, "bold"))
    style.configure("Sub.TLabel",  background=BG2, foreground=TEXT, font=("Segoe UI", 10))

    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab",
        background=BG2, foreground=TEXT2,
        padding=[18, 8], font=("Segoe UI", 10), borderwidth=0)
    style.map("TNotebook.Tab",
        background=[("selected", BG3)],
        foreground=[("selected", TEXT)],
        expand=[("selected", [0, 0, 0, 2])])

    # כפתור ראשי
    style.configure("Accent.TButton",
        background=ACCENT, foreground="#ffffff",
        font=("Segoe UI", 10, "bold"), padding=[16, 8], borderwidth=0, relief="flat")
    style.map("Accent.TButton",
        background=[("active", "#5a52dd"), ("disabled", "#3a3a55")])

    # כפתור עצור
    style.configure("Stop.TButton",
        background=DANGER, foreground="#ffffff",
        font=("Segoe UI", 10, "bold"), padding=[16, 8], borderwidth=0, relief="flat")
    style.map("Stop.TButton",
        background=[("active", "#cc4444"), ("disabled", "#3a3a55")])

    # כפתור רגיל
    style.configure("TButton",
        background=BG3, foreground=TEXT,
        font=("Segoe UI", 9), padding=[12, 6], borderwidth=0, relief="flat")
    style.map("TButton",
        background=[("active", "#2e2e44"), ("disabled", "#1a1a24")])

    style.configure("TEntry",
        fieldbackground=BG3, foreground=TEXT,
        insertcolor=TEXT, borderwidth=1, relief="flat",
        padding=[8, 6])
    style.map("TEntry", fieldbackground=[("focus", "#2a2a3a")])

    style.configure("Treeview",
        background=ROW_EVEN, foreground=TEXT,
        fieldbackground=ROW_EVEN, rowheight=28,
        font=("Segoe UI", 9), borderwidth=0)
    style.configure("Treeview.Heading",
        background=BG3, foreground=TEXT2,
        font=("Segoe UI", 9, "bold"), borderwidth=0, relief="flat", padding=[6, 6])
    style.map("Treeview",
        background=[("selected", SEL_BG)],
        foreground=[("selected", TEXT)])

    style.configure("TScrollbar",
        background=BG3, troughcolor=BG2,
        borderwidth=0, arrowsize=12, relief="flat")

    root.configure(bg=BG)


def make_card(parent, **kwargs):
    f = tk.Frame(parent, bg=BG2, **kwargs)
    return f

def make_label(parent, text, size=10, bold=False, color=None, bg=None):
    font = ("Segoe UI", size, "bold" if bold else "normal")
    return tk.Label(parent,
        text=text, font=font,
        fg=color or TEXT, bg=bg or BG,
        anchor="e")

def make_entry(parent, width=30, show=None):
    e = tk.Entry(parent, width=width,
        bg=BG3, fg=TEXT, insertbackground=TEXT,
        relief="flat", font=("Segoe UI", 10),
        highlightthickness=1, highlightcolor=ACCENT,
        highlightbackground=BORDER)
    if show:
        e.config(show=show)
    return e

def make_btn(parent, text, command, color=ACCENT, fg="#fff", width=None):
    btn = tk.Button(parent, text=text, command=command,
        bg=color, fg=fg, activebackground=color,
        activeforeground=fg, relief="flat",
        font=("Segoe UI", 10, "bold"),
        padx=16, pady=7, cursor="hand2",
        bd=0)
    if width:
        btn.config(width=width)
    # hover effect
    btn.bind("<Enter>", lambda e: btn.config(bg=_darken(color)))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn

def make_small_btn(parent, text, command, color=BG3):
    btn = tk.Button(parent, text=text, command=command,
        bg=color, fg=TEXT2, activebackground=BORDER,
        activeforeground=TEXT, relief="flat",
        font=("Segoe UI", 9), padx=10, pady=4,
        cursor="hand2", bd=0)
    btn.bind("<Enter>", lambda e: btn.config(bg=BORDER))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn

def _darken(hex_color):
    """כהה קצת צבע hex."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    r, g, b = max(0,r-20), max(0,g-20), max(0,b-20)
    return f"#{r:02x}{g:02x}{b:02x}"

def section_header(parent, text, bg=BG):
    f = tk.Frame(parent, bg=bg)
    tk.Label(f, text=text, font=("Segoe UI", 12, "bold"),
             fg=TEXT, bg=bg).pack(side=tk.LEFT)
    tk.Frame(f, bg=BORDER, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12,0), pady=6)
    return f

def dark_listbox(parent, height=8, **kw):
    sb = tk.Scrollbar(parent, bg=BG3, troughcolor=BG2,
                      relief="flat", bd=0, width=8)
    lb = tk.Listbox(parent,
        bg=BG3, fg=TEXT, selectbackground=SEL_BG,
        selectforeground=TEXT, activestyle="none",
        font=("Segoe UI", 10), relief="flat",
        highlightthickness=0, borderwidth=0,
        height=height, yscrollcommand=sb.set, **kw)
    sb.config(command=lb.yview)
    return lb, sb


# ─────────────────────────────────────────────
# חלון התחברות
# ─────────────────────────────────────────────
class LoginDialog(tk.Toplevel):
    def __init__(self, parent, client, loop):
        super().__init__(parent)
        self.title("התחברות לטלגרם")
        self.geometry("380x240")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=BG)

        self.client = client
        self.loop   = loop
        self.result = None
        self._phone = None
        self._hash  = None

        self._build_phone_ui()

    def _build_phone_ui(self):
        self._clear()
        tk.Label(self, text="התחברות לטלגרם", font=("Segoe UI", 13, "bold"),
                 fg=TEXT, bg=BG).pack(pady=(24, 4))
        tk.Label(self, text="מספר טלפון (כולל קידומת +972)",
                 font=("Segoe UI", 9), fg=TEXT2, bg=BG).pack()

        self.phone_entry = make_entry(self, width=28)
        self.phone_entry.pack(pady=(8, 0))
        self.phone_entry.insert(0, "+972")
        self.phone_entry.focus()

        self.status = tk.Label(self, text="", font=("Segoe UI", 9), fg=DANGER, bg=BG)
        self.status.pack(pady=4)

        self.btn = make_btn(self, "שלח קוד", self._send_code)
        self.btn.pack(pady=4)

    def _send_code(self):
        self._phone = self.phone_entry.get().strip()
        self.status.config(text="שולח קוד...", fg=TEXT2)
        self.btn.config(state=tk.DISABLED)
        future = asyncio.run_coroutine_threadsafe(
            self.client.send_code_request(self._phone), self.loop)
        def on_done(f):
            try:
                self._hash = f.result().phone_code_hash
                self.after(0, self._build_code_ui)
            except Exception as e:
                self.after(0, lambda: self.status.config(text=f"שגיאה: {e}", fg=DANGER))
                self.after(0, lambda: self.btn.config(state=tk.NORMAL))
        future.add_done_callback(on_done)

    def _build_code_ui(self):
        self._clear()
        self.geometry("380x280")
        tk.Label(self, text="הכנס קוד אימות", font=("Segoe UI", 13, "bold"),
                 fg=TEXT, bg=BG).pack(pady=(24, 4))
        tk.Label(self, text="הקוד נשלח לטלגרם שלך",
                 font=("Segoe UI", 9), fg=TEXT2, bg=BG).pack()

        self.code_entry = make_entry(self, width=14)
        self.code_entry.pack(pady=(10, 0))
        self.code_entry.config(font=("Segoe UI", 16), justify="center")
        self.code_entry.focus()

        tk.Label(self, text="סיסמת אימות דו-שלבי (אם קיימת)",
                 font=("Segoe UI", 9), fg=TEXT2, bg=BG).pack(pady=(14, 2))
        self.pass_entry = make_entry(self, width=24, show="•")
        self.pass_entry.pack()

        self.status2 = tk.Label(self, text="", font=("Segoe UI", 9), fg=DANGER, bg=BG)
        self.status2.pack(pady=4)

        make_btn(self, "התחבר", self._login).pack(pady=4)

    def _login(self):
        code     = self.code_entry.get().strip()
        password = self.pass_entry.get().strip()
        self.status2.config(text="מתחבר...", fg=TEXT2)

        async def do_login():
            try:
                await self.client.sign_in(self._phone, code, phone_code_hash=self._hash)
            except Exception as e:
                err = str(e)
                if "Two-steps" in err or "PASSWORD" in err.upper() or "SessionPasswordNeeded" in err:
                    if not password:
                        raise Exception("נדרשת סיסמת אימות דו-שלבי")
                    await self.client.sign_in(password=password)
                else:
                    raise

        future = asyncio.run_coroutine_threadsafe(do_login(), self.loop)
        def on_done(f):
            try:
                f.result()
                self.result = True
                self.after(0, self.destroy)
            except Exception as e:
                self.after(0, lambda: self.status2.config(text=f"שגיאה: {e}", fg=DANGER))
        future.add_done_callback(on_done)

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()


# ─────────────────────────────────────────────
# האפליקציה הראשית
# ─────────────────────────────────────────────
class DealMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("מנטר עסקאות טלגרם")
        self.root.geometry("860x700")
        self.root.resizable(True, True)
        apply_theme(root)

        self.products = load_products()
        self.channels = load_channels()
        self.deals    = load_deals()
        self.running  = False
        self.client   = None
        self.loop     = None
        self.thread   = None

        self._build_ui()
        self.refresh_deals_tab()

    # ─── UI shell ─────────────────────────────

    def _build_ui(self):
        # header bar
        hdr = tk.Frame(self.root, bg="#0a0a10", height=48)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  🛒  מנטר עסקאות טלגרם",
                 font=("Segoe UI", 13, "bold"), fg=TEXT, bg="#0a0a10").pack(side=tk.LEFT, padx=12)
        self.status_var = tk.StringVar(value="⚪  לא פעיל")
        tk.Label(hdr, textvariable=self.status_var,
                 font=("Segoe UI", 9), fg=TEXT2, bg="#0a0a10").pack(side=tk.RIGHT, padx=16)

        # notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        for title, builder in [
            ("  📦  מוצרים  ",    self._build_products_tab),
            ("  📡  ערוצים  ",   self._build_channels_tab),
            ("  ▶  ניטור  ",     self._build_monitor_tab),
            ("  🛒  עסקאות  ",   self._build_deals_tab),
        ]:
            tab = tk.Frame(self.notebook, bg=BG)
            self.notebook.add(tab, text=title)
            builder(tab)

    # ─── helper: padded card ──────────────────

    def _card(self, parent, title=None, pady=(12,6)):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill=tk.X, padx=16, pady=pady)
        card = tk.Frame(outer, bg=BG2, padx=14, pady=12)
        card.pack(fill=tk.X)
        if title:
            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"),
                     fg=ACCENT, bg=BG2).pack(anchor="e", pady=(0,8))
        return card

    # ─── טאב מוצרים ──────────────────────────

    def _build_products_tab(self, parent):
        tk.Frame(parent, bg=BG, height=12).pack()

        card = self._card(parent, title="הוספת מוצר חדש")

        row0 = tk.Frame(card, bg=BG2)
        row0.pack(fill=tk.X, pady=3)
        tk.Label(row0, text="שם המוצר:", font=("Segoe UI",9), fg=TEXT2, bg=BG2, width=16, anchor="e").pack(side=tk.RIGHT)
        self.entry_name = make_entry(row0, width=34)
        self.entry_name.pack(side=tk.RIGHT, padx=(0,8))

        row1 = tk.Frame(card, bg=BG2)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="מילות חיפוש:", font=("Segoe UI",9), fg=TEXT2, bg=BG2, width=16, anchor="e").pack(side=tk.RIGHT)
        self.entry_keywords = make_entry(row1, width=34)
        self.entry_keywords.pack(side=tk.RIGHT, padx=(0,8))

        tk.Label(card, text="לדוגמא: rockport, רוקפורט  (מופרדות בפסיק)",
                 font=("Segoe UI",8), fg=TEXT2, bg=BG2).pack(anchor="e", pady=(2,8))

        make_btn(card, "➕  הוסף מוצר", self.add_product).pack(anchor="e")

        # list
        lf = tk.Frame(parent, bg=BG)
        lf.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4,4))

        section_header(lf, "מוצרים מוגדרים").pack(fill=tk.X, pady=(4,6))

        list_wrap = tk.Frame(lf, bg=BG2, padx=2, pady=2)
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.products_list, sb = dark_listbox(list_wrap, height=10)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self.products_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        make_small_btn(parent, "🗑  מחק מוצר נבחר", self.delete_product, color=BG2).pack(pady=6)
        self.refresh_products_list()

    def add_product(self):
        name   = self.entry_name.get().strip()
        kw_raw = self.entry_keywords.get().strip()
        if not name:
            messagebox.showwarning("שגיאה", "יש להכניס שם מוצר")
            return
        if not kw_raw:
            messagebox.showwarning("שגיאה", "יש להכניס לפחות מילת חיפוש אחת")
            return
        keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
        self.products.append({"name": name, "keywords": keywords, "exclude_keywords": []})
        save_products(self.products)
        self.refresh_products_list()
        self.entry_name.delete(0, tk.END)
        self.entry_keywords.delete(0, tk.END)
        self.log(f"✅ נוסף מוצר: {name}")

    def delete_product(self):
        sel = self.products_list.curselection()
        if not sel:
            messagebox.showwarning("שגיאה", "בחר מוצר למחיקה")
            return
        idx  = sel[0]
        name = self.products[idx]["name"]
        if messagebox.askyesno("אישור", f"למחוק את המוצר '{name}'?"):
            self.products.pop(idx)
            save_products(self.products)
            self.refresh_products_list()
            self.log(f"🗑 נמחק מוצר: {name}")

    def refresh_products_list(self):
        self.products_list.delete(0, tk.END)
        for p in self.products:
            self.products_list.insert(tk.END, f"   {p['name']}   ·   {', '.join(p['keywords'])}")

    # ─── טאב ערוצים ──────────────────────────

    def _build_channels_tab(self, parent):
        tk.Frame(parent, bg=BG, height=12).pack()

        card = self._card(parent, title="הוספת ערוץ חדש")

        row0 = tk.Frame(card, bg=BG2)
        row0.pack(fill=tk.X, pady=3)
        tk.Label(row0, text="שם תצוגה:", font=("Segoe UI",9), fg=TEXT2, bg=BG2, width=18, anchor="e").pack(side=tk.RIGHT)
        self.ch_entry_label = make_entry(row0, width=30)
        self.ch_entry_label.pack(side=tk.RIGHT, padx=(0,8))

        row1 = tk.Frame(card, bg=BG2)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="Username / ID:", font=("Segoe UI",9), fg=TEXT2, bg=BG2, width=18, anchor="e").pack(side=tk.RIGHT)
        self.ch_entry_value = make_entry(row1, width=30)
        self.ch_entry_value.pack(side=tk.RIGHT, padx=(0,8))

        hint = "ציבורי: BuyBuyShai  |  פרטי: -1001260047165  |  לינק t.me/c/ID/msg → קח את ה-ID"
        tk.Label(card, text=hint, font=("Segoe UI",8), fg=TEXT2, bg=BG2).pack(anchor="e", pady=(4,8))

        make_btn(card, "➕  הוסף ערוץ", self.add_channel).pack(anchor="e")

        lf = tk.Frame(parent, bg=BG)
        lf.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4,4))
        section_header(lf, "ערוצים מוגדרים").pack(fill=tk.X, pady=(4,6))

        list_wrap = tk.Frame(lf, bg=BG2, padx=2, pady=2)
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.channels_config_list, sb = dark_listbox(list_wrap, height=10)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self.channels_config_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        make_small_btn(parent, "🗑  מחק ערוץ נבחר", self.delete_channel, color=BG2).pack(pady=6)
        self.refresh_channels_list()

    def add_channel(self):
        label = self.ch_entry_label.get().strip()
        value = self.ch_entry_value.get().strip()
        if not label:
            messagebox.showwarning("שגיאה", "יש להכניס שם תצוגה לערוץ")
            return
        if not value:
            messagebox.showwarning("שגיאה", "יש להכניס username או ID של הערוץ")
            return
        try:
            value = int(value)
        except ValueError:
            value = value.lstrip("@")
        if value in [ch["value"] for ch in self.channels]:
            messagebox.showwarning("שגיאה", "ערוץ זה כבר קיים ברשימה")
            return
        self.channels.append({"label": label, "value": value})
        save_channels(self.channels)
        self.refresh_channels_list()
        self.ch_entry_label.delete(0, tk.END)
        self.ch_entry_value.delete(0, tk.END)
        self.log(f"📢 נוסף ערוץ: {label}")

    def delete_channel(self):
        sel = self.channels_config_list.curselection()
        if not sel:
            messagebox.showwarning("שגיאה", "בחר ערוץ למחיקה")
            return
        idx  = sel[0]
        name = self.channels[idx]["label"]
        if messagebox.askyesno("אישור", f"למחוק את הערוץ '{name}'?"):
            self.channels.pop(idx)
            save_channels(self.channels)
            self.refresh_channels_list()
            self.log(f"🗑 נמחק ערוץ: {name}")

    def refresh_channels_list(self):
        self.channels_config_list.delete(0, tk.END)
        for ch in self.channels:
            self.channels_config_list.insert(tk.END, f"   {ch['label']}   ·   {ch['value']}")

    # ─── טאב ניטור ───────────────────────────

    def _build_monitor_tab(self, parent):
        tk.Frame(parent, bg=BG, height=12).pack()

        # כפתורי שליטה
        ctrl_card = tk.Frame(parent, bg=BG2, padx=20, pady=16)
        ctrl_card.pack(fill=tk.X, padx=16)

        btn_row = tk.Frame(ctrl_card, bg=BG2)
        btn_row.pack()

        self.btn_start = make_btn(btn_row, "▶   התחל ניטור", self.start_monitor, color=ACCENT2, fg="#000")
        self.btn_start.pack(side=tk.LEFT, padx=8)

        self.btn_stop = make_btn(btn_row, "⏹   עצור", self.stop_monitor, color=DANGER)
        self.btn_stop.config(state=tk.DISABLED, bg="#3a2222")
        self.btn_stop.pack(side=tk.LEFT, padx=8)

        # ערוצים מחוברים
        lf = tk.Frame(parent, bg=BG)
        lf.pack(fill=tk.X, padx=16, pady=(14,0))
        section_header(lf, "ערוצים מחוברים").pack(fill=tk.X, pady=(0,6))

        ch_wrap = tk.Frame(lf, bg=BG2, padx=2, pady=2)
        ch_wrap.pack(fill=tk.X)
        self.channels_list, ch_sb = dark_listbox(ch_wrap, height=4)
        ch_sb.pack(side=tk.LEFT, fill=tk.Y)
        self.channels_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # לוג
        log_f = tk.Frame(parent, bg=BG)
        log_f.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14,6))
        section_header(log_f, "יומן פעילות").pack(fill=tk.X, pady=(0,6))

        self.log_box = tk.Text(
            log_f, bg="#0d0d18", fg="#9090c0",
            insertbackground=TEXT, font=("Consolas", 9),
            relief="flat", bd=0, state=tk.DISABLED,
            highlightthickness=1, highlightbackground=BORDER)
        log_sb = tk.Scrollbar(log_f, bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=8)
        log_sb.config(command=self.log_box.yview)
        self.log_box.config(yscrollcommand=log_sb.set)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        make_small_btn(parent, "נקה לוג", self.clear_log, color=BG2).pack(pady=6)

    def log(self, msg):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {msg}\n"
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, line)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete(1.0, tk.END)
        self.log_box.config(state=tk.DISABLED)

    def add_channel_to_list(self, name):
        self.channels_list.insert(tk.END, f"   ✅  {name}")

    # ─── טאב עסקאות ──────────────────────────

    def _build_deals_tab(self, parent):
        # top bar
        top = tk.Frame(parent, bg=BG, padx=16, pady=10)
        top.pack(fill=tk.X)
        tk.Label(top, text="עסקאות שנמצאו", font=("Segoe UI",13,"bold"),
                 fg=TEXT, bg=BG).pack(side=tk.RIGHT)
        self.deals_count_var = tk.StringVar(value="")
        tk.Label(top, textvariable=self.deals_count_var,
                 font=("Segoe UI",10,"bold"), fg=ACCENT, bg=BG).pack(side=tk.RIGHT, padx=10)
        make_small_btn(top, "🗑  נקה הכל", self.clear_deals).pack(side=tk.LEFT)

        # treeview
        tree_f = tk.Frame(parent, bg=BG)
        tree_f.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0,4))

        cols = ("time","product","channel","preview","link")
        self.deals_tree = ttk.Treeview(tree_f, columns=cols, show="headings", selectmode="browse")
        self.deals_tree.heading("time",    text="זמן",            anchor="e")
        self.deals_tree.heading("product", text="מוצר",           anchor="e")
        self.deals_tree.heading("channel", text="ערוץ",           anchor="e")
        self.deals_tree.heading("preview", text="תצוגה מקדימה",   anchor="e")
        self.deals_tree.heading("link",    text="לינק",           anchor="center")
        self.deals_tree.column("time",    width=130, stretch=False, anchor="e")
        self.deals_tree.column("product", width=140, stretch=False, anchor="e")
        self.deals_tree.column("channel", width=130, stretch=False, anchor="e")
        self.deals_tree.column("preview", width=280,               anchor="e")
        self.deals_tree.column("link",    width=70,  stretch=False, anchor="center")

        self.deals_tree.tag_configure("odd",  background=ROW_ODD)
        self.deals_tree.tag_configure("even", background=ROW_EVEN)
        self.deals_tree.tag_configure("new",  background="#1e2a1e")

        vsb = ttk.Scrollbar(tree_f, orient=tk.VERTICAL,   command=self.deals_tree.yview)
        hsb = ttk.Scrollbar(tree_f, orient=tk.HORIZONTAL, command=self.deals_tree.xview)
        self.deals_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.deals_tree.pack(fill=tk.BOTH, expand=True)

        self.deals_tree.bind("<Double-1>",       self._on_deal_click)
        self.deals_tree.bind("<<TreeviewSelect>>", self._on_deal_select)

        # detail panel
        det_f = tk.Frame(parent, bg=BG2, padx=10, pady=8)
        det_f.pack(fill=tk.X, padx=16, pady=(0,4))
        tk.Label(det_f, text="פרטי ההודעה:", font=("Segoe UI",9,"bold"),
                 fg=ACCENT, bg=BG2).pack(anchor="e")
        self.deal_detail = tk.Text(det_f, height=5,
            bg="#0d0d18", fg=TEXT, font=("Segoe UI",9),
            relief="flat", bd=0, state=tk.DISABLED, wrap=tk.WORD,
            highlightthickness=0)
        self.deal_detail.pack(fill=tk.X, pady=(4,0))

        make_btn(parent, "🔗  פתח לינק", self._open_selected_link,
                 color=ACCENT).pack(pady=(4,10))

    def add_deal(self, product_name, channel_name, text, link, is_history=False):
        ts      = datetime.now().strftime("%d/%m %H:%M")
        prefix  = "[היסטוריה] " if is_history else ""
        preview = text.replace("\n", " ").strip()[:90]
        deal = {"time": ts, "product": product_name, "channel": channel_name,
                "text": text[:1000], "link": link, "history": is_history}
        self.deals.append(deal)
        save_deals(self.deals)

        link_label = "🔗 פתח" if link else "—"
        n = len(self.deals_tree.get_children())
        tag = "new" if not is_history else ("odd" if n % 2 else "even")
        self.deals_tree.insert("", 0, values=(
            f"{prefix}{ts}", product_name, channel_name, preview, link_label), tags=(tag,))

        count = len(self.deals_tree.get_children())
        self.deals_count_var.set(f"({count})")

        if not is_history:
            self.notebook.select(3)

    def refresh_deals_tab(self):
        for i, deal in enumerate(reversed(self.deals)):
            link_label = "🔗 פתח" if deal.get("link") else "—"
            prefix = "[היסטוריה] " if deal.get("history") else ""
            preview = deal.get("text","").replace("\n"," ").strip()[:90]
            tag = "odd" if i % 2 else "even"
            self.deals_tree.insert("", tk.END, values=(
                f"{prefix}{deal['time']}", deal["product"],
                deal["channel"], preview, link_label), tags=(tag,))
        count = len(self.deals_tree.get_children())
        if count:
            self.deals_count_var.set(f"({count})")

    def _on_deal_select(self, event):
        sel = self.deals_tree.selection()
        if not sel:
            return
        idx      = self.deals_tree.index(sel[0])
        real_idx = len(self.deals) - 1 - idx
        if 0 <= real_idx < len(self.deals):
            deal = self.deals[real_idx]
            self.deal_detail.config(state=tk.NORMAL)
            self.deal_detail.delete(1.0, tk.END)
            self.deal_detail.insert(tk.END, deal.get("text", ""))
            if deal.get("link"):
                self.deal_detail.insert(tk.END, f"\n\n🔗 {deal['link']}")
            self.deal_detail.config(state=tk.DISABLED)

    def _on_deal_click(self, _):
        self._open_selected_link()

    def _open_selected_link(self):
        sel = self.deals_tree.selection()
        if not sel:
            return
        idx      = self.deals_tree.index(sel[0])
        real_idx = len(self.deals) - 1 - idx
        if 0 <= real_idx < len(self.deals):
            link = self.deals[real_idx].get("link", "")
            if link:
                webbrowser.open(link)
            else:
                messagebox.showinfo("אין לינק", "להודעה זו אין לינק ישיר (ערוץ פרטי)")

    def clear_deals(self):
        if messagebox.askyesno("אישור", "למחוק את כל העסקאות השמורות?"):
            self.deals = []
            save_deals([])
            for item in self.deals_tree.get_children():
                self.deals_tree.delete(item)
            self.deals_count_var.set("")
            self.deal_detail.config(state=tk.NORMAL)
            self.deal_detail.delete(1.0, tk.END)
            self.deal_detail.config(state=tk.DISABLED)

    # ─── ניטור ───────────────────────────────

    def start_monitor(self):
        if not self.products:
            messagebox.showwarning("שגיאה", "אין מוצרים מוגדרים.")
            return
        self.running = True
        self.btn_start.config(state=tk.DISABLED, bg="#1a3a2a")
        self.btn_stop.config(state=tk.NORMAL, bg=DANGER)
        self.channels_list.delete(0, tk.END)
        self.status_var.set("🟡  מתחבר...")
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop_monitor(self):
        self.running = False
        client, loop = self.client, self.loop
        if client and loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(client.disconnect(), loop)
            # _on_stopped יקרא מה-finally של _run_loop
        else:
            self._on_stopped()

    def _on_stopped(self):
        try:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_start.config(bg=ACCENT2)
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_stop.config(bg="#3a2222")
            self.status_var.set("⚪  לא פעיל")
        except Exception:
            pass

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._monitor())
        except Exception as e:
            try:
                self.root.after(0, lambda: self.log(f"❌ שגיאה: {e}"))
            except Exception:
                pass
        finally:
            try:
                self.loop.close()
            except Exception:
                pass
            self.loop   = None
            self.client = None
            try:
                self.root.after(0, self._on_stopped)
                self.root.after(0, lambda: self.log("⏹ הניטור הופסק"))
            except Exception:
                pass

    async def _monitor(self):
        self.root.after(0, lambda: self.log("🔌 מתחבר לטלגרם..."))
        self.client = TelegramClient(SESSION_FILE, config.API_ID, config.API_HASH)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            login_done = asyncio.Event()
            def open_login():
                dlg = LoginDialog(self.root, self.client, self.loop)
                self.root.wait_window(dlg)
                if dlg.result:
                    self.loop.call_soon_threadsafe(login_done.set)
                else:
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(self._abort("התחברות בוטלה"), loop=self.loop))
            self.root.after(0, open_login)
            await login_done.wait()

        self.root.after(0, lambda: self.log("✅ מחובר לטלגרם!"))

        valid_channels = []
        for ch in [c["value"] for c in self.channels]:
            try:
                entity = await self.client.get_entity(ch)
                name   = getattr(entity, "title", str(ch))
                valid_channels.append(entity)
                self.root.after(0, lambda n=name: self.add_channel_to_list(n))
                self.root.after(0, lambda n=name: self.log(f"   📢 ערוץ מחובר: {n}"))
            except Exception as e:
                self.root.after(0, lambda c=ch, err=e: self.log(f"   ❌ {c}: {err}"))

        if not valid_channels:
            self.root.after(0, lambda: self.log("❌ לא נמצאו ערוצים תקינים"))
            return

        channel_ids       = [ch.id for ch in valid_channels]
        products_snapshot = self.products[:]

        self.root.after(0, lambda: self.status_var.set("🟢  פעיל — מנטר"))
        self.root.after(0, lambda: self.log(
            f"👁  מנטר {len(valid_channels)} ערוצים, {len(products_snapshot)} מוצרים"))

        # היסטוריה
        self.root.after(0, lambda: self.log("🔎 סורק 24 שעות אחרונות..."))
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        found_count = 0
        for entity in valid_channels:
            ch_name = getattr(entity, "title", str(entity.id))
            async for msg in self.client.iter_messages(entity, limit=500):
                if msg.date < since:
                    break
                text = msg.text or ""
                if not text:
                    continue
                for product in check_message(text, products_snapshot):
                    found_count += 1
                    link = (f"https://t.me/{entity.username}/{msg.id}"
                            if getattr(entity, "username", None) else extract_url(text))
                    self.root.after(0, lambda pn=product["name"], cn=ch_name, t=text, l=link:
                                    self.add_deal(pn, cn, t, l, is_history=True))
                    self.root.after(0, lambda pn=product["name"], cn=ch_name:
                                    self.log(f"   🛒 [היסטוריה] {pn} ב-{cn}"))

        self.root.after(0, lambda: self.log(f"✅ סריקה הסתיימה — {found_count} עסקאות נמצאו"))

        @self.client.on(events.NewMessage(chats=channel_ids))
        async def handler(event):
            text = event.message.text or ""
            if not text:
                return
            for product in check_message(text, products_snapshot):
                channel_name = getattr(event.chat, "title", "ערוץ לא ידוע")
                link = ""
                try:
                    chat = event.message.chat
                    if getattr(chat, "username", None):
                        link = f"https://t.me/{chat.username}/{event.message.id}"
                except Exception:
                    pass
                if not link:
                    link = extract_url(text)

                self.root.after(0, lambda pn=product["name"], cn=channel_name, t=text, l=link:
                                self.add_deal(pn, cn, t, l, is_history=False))
                self.root.after(0, lambda pn=product["name"], cn=channel_name:
                                self.log(f"🛒 עסקה חדשה! {pn} ב-{cn}"))
                try:
                    alert = (f"🛒 **עסקה חדשה!**\n📦 {product['name']}\n📢 {channel_name}\n\n"
                             f"{text[:400]}{'...' if len(text)>400 else ''}")
                    if link:
                        alert += f"\n\n🔗 {link}"
                    await self.client.send_message("me", alert, parse_mode="markdown")
                except Exception:
                    pass

        await self.client.run_until_disconnected()

    async def _abort(self, msg):
        self.root.after(0, lambda: self.log(f"❌ {msg}"))
        self.root.after(0, self.stop_monitor)


if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    root = tk.Tk()
    app  = DealMonitorApp(root)
    root.mainloop()
