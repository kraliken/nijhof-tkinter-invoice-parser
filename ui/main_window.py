"""
ui/main_window.py — Tkinter alapú főablak

Ez a modul tartalmazza az egész GUI-t. Egy `App` osztályba van szervezve,
amelyet a main.py példányosít és futtat.

Elrendezés (fentről lefelé, scrollozható canvas-on belül):
  1. Header         — cím és alcím
  2. Súgó           — 5 lépéses folyamat, állapotfüggő kiemeléssel
  3. Számlatípus    — kártya-alapú Radiobutton (Multi Alarm / Volvo)
  4. PDF kiválasztás — Tallózás gomb + fájlnév kijelzés
  5. Feldolgozás    — ▶ gomb, progressbar, hiba/siker blokk
  6. Eredmény       — csak sikeres feldolgozás után látható;
                      gombok a PDF, Excel és makró megnyitásához

Állapotgép:
  Az App.state (AppState enum) változik minden lépésnél.
  A set_state() metódus triggereli a GUI frissítéseket.

Háttérszál (threading):
  A PDF feldolgozás háttérszálban fut (_processing_worker), hogy a GUI
  ne fagyjon le. A szálból a GUI frissítés `root.after(0, callback)`-en
  keresztül történik (Tkinter nem thread-safe, csak a fő szálból frissíthető).
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import threading

from ui.state import AppState
from ui.theme import SECTION_PAD, CARD_IDLE, CARD_SELECTED, ERROR_BG, ERROR_FG, SUCCESS_BG, SUCCESS_FG
from core.registry import PARSERS, VALUE_TO_TYPE
from services.file_service import validate_pdf
from services import processing_service
from utils.logger import get_logger


WINDOW_TITLE = "BPiON — Invoice Parser v2.0"
WINDOW_WIDTH = 1020
WINDOW_HEIGHT = 750


class App:
    """Tkinter alapú főablak — az alkalmazás egyetlen ablaka.

    Példányosítás: App()
    Futtatás: app.run()  (blokkoló Tkinter mainloop)
    """

    def __init__(self):
        self.log = get_logger()
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.resizable(True, True)
        self.root.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # --- Alkalmazás állapot ---
        self.state = AppState.IDLE
        self.selected_type: Optional[str] = None   # pl. "multialarm" vagy "volvo"
        self.selected_file: Optional[Path] = None  # a felhasználó által tallózott PDF
        self.parsed_data: Optional[list] = None    # a parser kimenete (jelenleg csak tárolva)
        self.result_path: Optional[Path] = None    # az elkészült Excel fájl útvonala

        self._center_window()  # Az ablak középre igazítása (withdraw → geometry → deiconify)
        self._build_layout()   # Összes widget felépítése
        self.root.update_idletasks()
        self.root.deiconify()  # Ablak megjelenítése (center_window elrejtette)

    def _on_type_selected(self, *_):
        """Számlatípus kártya kiválasztásakor hívódik (IntVar trace callback).

        Ha a felhasználó típust vált (pl. Multialarm-ról Volvora), akkor a korábban
        kiválasztott PDF-et és eredményt törli — különböző típusú PDF-ek nem kompatibilisek.
        """
        value = self._type_var.get()
        new_type = VALUE_TO_TYPE.get(value)

        if new_type != self.selected_type and self.selected_type is not None:
            # Típusváltás: régi fájl és eredmény törlése
            self._clear_file()
            self._reset_result()

        self.selected_type = new_type
        self._highlight_type(self.selected_type)
        self._browse_btn.configure(state="normal")  # Tallózás gomb engedélyezése
        self.set_state(AppState.TYPE_SELECTED)

    def _validate(self) -> Optional[str]:
        """Delegálja a validációt a file_service-nek. Visszaad egy hibaüzenetet vagy None-t."""
        return validate_pdf(self.selected_type, self.selected_file)

    def _start_processing(self):
        """A ▶ Feldolgozás gomb eseménykezelője.

        1. Validál — ha hiba van, azonnal megmutatja és leáll.
        2. PROCESSING állapotba lép, progressbart indít.
        3. Háttérszálban indítja el a tényleges feldolgozást.
        """
        error = self._validate()
        if error:
            self._on_processing_done(error=error)
            return
        self._error_box.pack_forget()
        self.log.info(
            f"Processing started: type={self.selected_type}, file={self.selected_file}"
        )
        self.set_state(AppState.PROCESSING)
        self._process_btn.configure(text="⏳ Számlafeldolgozása...")
        self._progress_bar.configure(mode="indeterminate")
        self._progress_bar.pack(side="left", padx=(10, 0))
        self._progress_bar.start(10)  # 10ms = animáció frissítési ütem
        # daemon=True: ha a főablakot becsukják, a szál is leáll
        threading.Thread(target=self._processing_worker, daemon=True).start()

    def _processing_worker(self):
        """Háttérszálban fut — elvégzi a PDF feldolgozást és Excel exportot.

        FONTOS: Tkinter nem thread-safe — a GUI-t csak a fő szálból szabad frissíteni.
        Ezért a befejezés jelzése `root.after(0, callback)`-en keresztül történik,
        amely a Tkinter event loop-ban fut le a fő szálban.
        """
        try:
            self.result_path = processing_service.run(self.selected_type, self.selected_file)
            self.log.info(f"Excel exported: {self.result_path}")
            # GUI frissítés visszaütemezése a fő szálba
            self.root.after(0, lambda: self._on_processing_done(error=None))
        except Exception as e:
            msg = f"Hiba a feldolgozás során: {e}"
            self.log.error(f"Processing failed: {e}", exc_info=True)
            self.root.after(0, lambda: self._on_processing_done(error=msg))

    def _on_processing_done(self, error: Optional[str]):
        """A feldolgozás befejezésekor hívódik — a fő szálban fut (root.after-on keresztül).

        Leállítja a progressbart, visszaállítja a gombot, és megjeleníti
        a hiba vagy sikeres eredmény blokkot.
        """
        self._progress_bar.stop()
        self._progress_bar.pack_forget()
        self._progress_bar.configure(mode="determinate", value=0)
        self._process_btn.configure(text="▶ Számla feldolgozása")
        if error:
            self._error_msg_label.configure(text=error)
            self._success_box.pack_forget()
            self._error_box.pack(fill="x", pady=(4, 0))
            self.set_state(AppState.ERROR)
        else:
            self._error_box.pack_forget()
            self._success_box.pack(fill="x", pady=(4, 0))
            self._result_name_label.configure(
                text=f"📄 {self.result_path.name}", foreground="black"
            )
            self._result_path_label.configure(text=f"Mentve: {self.result_path}")
            self.set_state(AppState.SUCCESS)

    def _browse_file(self):
        """A Tallózás... gomb eseménykezelője — fájlválasztó dialógust nyit.

        Ha a felhasználó Cancel-lel zárja, nem csinál semmit.
        Sikeres választás után frissíti a fájlnév kijelzőt és
        előhozza a × törlés gombot.
        """
        path = filedialog.askopenfilename(
            title="PDF fájl kiválasztása",
            filetypes=[("PDF fájlok", "*.pdf")],
        )
        if not path:
            return  # Felhasználó Cancel-t nyomott
        self.selected_file = Path(path)
        self.log.debug(f"File selected: {self.selected_file}")
        self._file_name_label.configure(
            text=f"📄 {self.selected_file.name}", foreground="black"
        )
        self._file_path_label.configure(text=f"Teljes elérési út: {self.selected_file}")
        self._clear_btn.pack(side="left", padx=(4, 0))  # × gomb megjelenítése
        if self.selected_type:
            self._reset_result()  # Ha volt korábbi eredmény, töröljük
            self.set_state(AppState.FILE_SELECTED)

    def _reset_result(self):
        """Törli a korábbi feldolgozás eredményét (adat + útvonal + GUI blokkok)."""
        self.parsed_data = None
        self.result_path = None
        self._success_box.pack_forget()
        self._error_box.pack_forget()

    def _clear_file(self):
        """A × gomb eseménykezelője — törli a kiválasztott fájlt.

        Az állapot visszaesik TYPE_SELECTED-re (ha volt típus) vagy IDLE-re.
        """
        self.selected_file = None
        self._file_name_label.configure(
            text="📄 Nincs fájl kiválasztva...", foreground="gray"
        )
        self._file_path_label.configure(text="")
        self._clear_btn.pack_forget()  # × gomb elrejtése
        self._reset_result()
        new_state = AppState.TYPE_SELECTED if self.selected_type else AppState.IDLE
        self.set_state(new_state)

    def _highlight_type(self, selected: str):
        """Frissíti a kártya-widget-ek vizuális megjelenését a kiválasztott típus alapján.

        Az összes kártyán végigmegy, és a kiválasztottat CARD_SELECTED,
        a többit CARD_IDLE stílussal rajzolja újra.
        """
        for type_key, (card, rb, lbl) in self._type_cards.items():
            c = CARD_SELECTED if type_key == selected else CARD_IDLE
            card.configure(bg=c["bg"], highlightbackground=c["border"])
            rb.configure(bg=c["bg"], fg=c["fg"], activebackground=c["bg"])
            lbl.configure(bg=c["bg"], fg=c["sub"])

    def set_state(self, new_state: AppState):
        """Állapotváltás — frissíti az összes állapotfüggő GUI elemet.

        Ez az egyetlen hely, ahol az állapot változik. Mindig ezt kell hívni
        közvetlen `self.state = ...` helyett, hogy a GUI szinkronban maradjon.
        """
        self.log.info(f"State changed: {self.state.name} → {new_state.name}")
        self.state = new_state
        self._update_process_btn()    # Feldolgozás gomb engedélyezettség
        self._update_result_frame()   # Eredmény szekció láthatósága
        self._update_help_steps()     # Súgó lépések kiemelése

    def _update_help_steps(self):
        """Frissíti a súgó lépések vizuális állapotát az aktuális AppState alapján.

        Minden lépés háromféle stílusban jelenhet meg:
          - Kész (✔, áthúzott, szürke): már elvégzett lépések
          - Aktív (félkövér, fekete): az aktuálisan szükséges lépés
          - Jövőbeli (szürke): még nem elérhető lépések

        STATE_MAP: állapot → (done_count, active_idx)
          done_count: hány lépés van áthúzva (befejezett)
          active_idx: melyik index van félkövéren kiemelve
        """
        if not hasattr(self, "_help_step_labels"):
            return  # A widget-ek még nem épültek fel — biztonságos korai kilépés

        # Állapot → (kész lépések száma, aktív lépés indexe)
        STATE_MAP = {
            AppState.IDLE: (0, 0),
            AppState.TYPE_SELECTED: (1, 1),
            AppState.FILE_SELECTED: (2, 2),
            AppState.PROCESSING: (3, 3),
            AppState.SUCCESS: (4, 4),
            AppState.ERROR: (2, 2),  # Hiba esetén visszalép a 3. lépéshez
        }
        done_count, active_idx = STATE_MAP.get(self.state, (0, 0))

        NUMS = ["①", "②", "③", "④", "⑤"]
        for i, (num_lbl, txt_lbl) in enumerate(
            zip(self._help_num_labels, self._help_step_labels)
        ):
            if i < done_count:
                # Befejezett lépés: pipa + áthúzott szürke szöveg
                num_lbl.configure(text="✔", foreground="green")
                txt_lbl.configure(foreground="gray", font=("", 9, "overstrike"))
            elif i == active_idx:
                # Aktív lépés: félkövér fekete szöveg
                num_lbl.configure(text=NUMS[i], foreground="black")
                txt_lbl.configure(foreground="black", font=("", 9, "bold"))
            else:
                # Jövőbeli lépés: szürke, inaktív
                num_lbl.configure(text=NUMS[i], foreground="gray")
                txt_lbl.configure(foreground="gray", font=("", 9))

    def _update_result_frame(self):
        """Az Eredmény szekciót csak SUCCESS állapotban jeleníti meg."""
        if not hasattr(self, "result_frame"):
            return  # A widget még nem épült fel
        if self.state == AppState.SUCCESS:
            self.result_frame.pack(fill="x", pady=(0, 8))
        else:
            self.result_frame.pack_forget()

    def _reset_for_new(self):
        """Az "Új feldolgozás" menüpont — visszaállítja az alkalmazást IDLE állapotba."""
        self._type_var.set(0)  # Radiobutton kijelölés törlése
        self.selected_type = None
        self._highlight_type("")  # Kártyák IDLE stílusba
        self._browse_btn.configure(state="disabled")
        self._clear_file()
        self._reset_result()
        self.set_state(AppState.IDLE)

    def _open_pdf(self):
        """A kiválasztott PDF számla megnyitása az alapértelmezett PDF olvasóval."""
        if not self.selected_file or not self.selected_file.exists():
            messagebox.showerror("Hiba", "A számla fájl nem található.")
            return
        os.startfile(str(self.selected_file))  # Windows-specifikus, megnyitja a fájlt

    def _open_excel(self):
        """Az elkészült Excel fájl megnyitása az alapértelmezett program(Excel)mal."""
        if not self.result_path or not self.result_path.exists():
            messagebox.showerror("Hiba", "A fájl nem található.")
            return
        os.startfile(str(self.result_path))

    def _open_macro(self):
        """Az aktuális számlatípushoz tartozó Excel makró betöltő fájl megnyitása.

        A makró neve a registry-ből jön (pl. "MultiAlarm_betöltő").
        A fájlt a macros/ mappában keresi glob-bal, így a kiterjesztéstől
        (pl. .xlsm) függetlenül megtalálja.
        """
        macro_dir = Path(__file__).parent.parent / "macros"
        base_name = PARSERS[self.selected_type]["macro"] if self.selected_type else ""
        # Glob-bal keresünk, hogy ne kelljen a pontos kiterjesztést tudni
        matches = list(macro_dir.glob(f"{base_name}*")) if macro_dir.exists() else []
        if not matches:
            messagebox.showerror(
                "Hiba",
                f"A '{base_name}' fájl nem található a macros mappában.\n({macro_dir})",
            )
            return
        os.startfile(str(matches[0]))

    def _update_process_btn(self):
        """Frissíti a ▶ Feldolgozás gomb állapotát az aktuális AppState alapján.

        - FILE_SELECTED / SUCCESS / ERROR: engedélyezett (újra lehet próbálni)
        - PROCESSING: letiltva (ne lehessen duplán indítani)
        - IDLE / TYPE_SELECTED: letiltva + súgó hint megjelenítve
        """
        if not hasattr(self, "_process_btn"):
            return  # Widget még nem épült fel
        if self.state in (AppState.FILE_SELECTED, AppState.SUCCESS, AppState.ERROR):
            self._process_btn.configure(state="normal")
            self._process_hint.configure(text="")
        elif self.state == AppState.PROCESSING:
            self._process_btn.configure(state="disabled")
            self._process_hint.configure(text="")
        else:
            # IDLE vagy TYPE_SELECTED: még hiányzik a fájl
            self._process_btn.configure(state="disabled")
            self._process_hint.configure(
                text="Válassz számlatípust és PDF fájlt a folytatáshoz"
            )

    def _center_window(self):
        """Az ablakot vízszintesen középre igazítja, felülre tolja (y=15px).

        A withdraw/deiconify technika elkerüli, hogy az ablak villanjon
        a pozicionálás előtt a képernyő közepétől eltérő helyen.
        """
        self.root.withdraw()  # Elrejtjük a pozicionálás idejére
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()  # noqa: F841 (jelenleg nem használt)
        x = (screen_w - WINDOW_WIDTH) // 2
        # y = (screen_h - WINDOW_HEIGHT) // 2  # Középre is lehetne, de felül jobban látható
        y = 15
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _build_header(self, parent):
        """Fejléc szekció: ikon + cím + alcím."""
        PAD = SECTION_PAD
        self.header_frame = ttk.Frame(parent, padding=10)
        self.header_frame.pack(fill="x", pady=(0, PAD))

        ttk.Label(self.header_frame, text="📄", font=("", 24)).pack(
            side="left", padx=(0, 10)
        )

        header_text = ttk.Frame(self.header_frame)
        header_text.pack(side="left", fill="x", expand=True)
        ttk.Label(
            header_text, text="Nijhof számlafeldolgozó", font=("", 13, "bold")
        ).pack(anchor="w")
        ttk.Label(
            header_text, text="PDF számla importálása és Excel fájl generálása"
        ).pack(anchor="w")

    def _build_help_section(self, parent):
        """Súgó szekció: 5 lépéses folyamat leírása.

        A lépés-label-ek referencióit eltárolja (_help_num_labels, _help_step_labels),
        hogy az _update_help_steps() dinamikusan frissíthesse őket állapotváltáskor.
        """
        PAD = SECTION_PAD
        self.help_frame = ttk.LabelFrame(parent, text="Feldolgozás lépései", padding=10)
        self.help_frame.pack(fill="x", pady=(0, PAD))

        STEPS = [
            ("①", "Válaszd ki a számlatípust (Multi Alarm vagy Volvo)"),
            ("②", "Tallózd ki a feldolgozandó PDF számlát"),
            ("③", 'Kattints a "Számlafeldolgozása" gombra'),
            ("④", "Az Excel fájl elkészült"),
            ("⑤", "Nyisd meg a generált Excel fájlt"),
        ]
        self._help_step_labels = []  # Szöveges label-ek (stílus frissítéshez)
        self._help_num_labels = []   # Szám/pipa label-ek (✔ vagy ①②③④⑤)
        for num, text in STEPS:
            row = ttk.Frame(self.help_frame)
            row.pack(fill="x", pady=2)
            num_lbl = ttk.Label(row, text=num, width=3)
            num_lbl.pack(side="left")
            lbl = ttk.Label(row, text=text)
            lbl.pack(side="left")
            self._help_num_labels.append(num_lbl)
            self._help_step_labels.append(lbl)

    def _build_type_section(self, parent):
        """Számlatípus szekció: kártya-alapú Radiobutton választó.

        Két kártya jelenik meg egymás mellett (grid layout, 1-1 weight → egyforma szélesség).
        Mindkét kártya teljes területe kattintható (nem csak a Radiobutton köre),
        amit a <Button-1> binding biztosít a kártyán és a label-en is.

        _type_cards: {type_key: (card_frame, radiobutton, subtitle_label)}
        _type_var: IntVar — értéke 0 (nincs kiválasztva), 1 (multialarm), 2 (volvo)
        """
        PAD = SECTION_PAD
        self.type_frame = ttk.LabelFrame(parent, text="Számlatípus kiválasztása", padding=10)
        self.type_frame.pack(fill="x", pady=(0, PAD))

        # IntVar: 0 = nincs kiválasztva, >0 = a kártya card_value értéke
        self._type_var = tk.IntVar(value=0)
        # trace_add("write", ...): bármikor változik az IntVar, meghívódik a callback
        self._type_var.trace_add("write", self._on_type_selected)

        # Kártyák sor: 2 egyforma szélességű oszlop
        cards_row = ttk.Frame(self.type_frame)
        cards_row.pack(fill="x", pady=(4, 0))
        cards_row.columnconfigure(0, weight=1)
        cards_row.columnconfigure(1, weight=1)

        self._type_cards = {}
        for type_key, cfg in PARSERS.items():
            col = cfg["card_value"] - 1  # card_value 1-től indul, col 0-tól
            # tk.Frame mert ttk.Frame nem támogatja a bg/highlightbackground stílust
            card = tk.Frame(
                cards_row, highlightthickness=2,
                highlightbackground=CARD_IDLE["border"],
                bg=CARD_IDLE["bg"], padx=8, pady=8,
            )
            card.grid(row=0, column=col, sticky="nsew", padx=(0, 4) if col == 0 else (4, 0))
            rb = tk.Radiobutton(
                card, text=cfg["label"], variable=self._type_var, value=cfg["card_value"],
                bg=CARD_IDLE["bg"], fg=CARD_IDLE["fg"],
                activebackground=CARD_IDLE["bg"], font=("", 9, "bold"),
                anchor="w", cursor="hand2",
            )
            rb.pack(anchor="w")
            lbl = tk.Label(card, text=cfg["subtitle"], bg=CARD_IDLE["bg"], fg=CARD_IDLE["sub"], anchor="w")
            lbl.pack(anchor="w")
            # Kártya és alcím kattinthatóvá tétele: klikk = IntVar frissítés
            for widget in (card, lbl):
                widget.bind("<Button-1>", lambda _e, v=cfg["card_value"]: self._type_var.set(v))
                widget.configure(cursor="hand2")  # Kéz kurzor hover-re
            self._type_cards[type_key] = (card, rb, lbl)

    def _build_file_section(self, parent):
        """PDF kiválasztás szekció: Tallózás gomb + × törlés + fájlnév kijelzés.

        A × gomb (_clear_btn) kezdetben nem csomag-olt (pack_forget) —
        csak fájlválasztás után jelenik meg (_browse_file hívja pack-ot).
        """
        PAD = SECTION_PAD
        self.file_frame = ttk.LabelFrame(parent, text="PDF fájl kiválasztása", padding=10)
        self.file_frame.pack(fill="x", pady=(0, PAD))

        file_row = ttk.Frame(self.file_frame)
        file_row.pack(fill="x")

        # Tallózás gomb: alapból letiltva, TYPE_SELECTED után engedélyeződik
        self._browse_btn = ttk.Button(
            file_row, text="Tallózás...", command=self._browse_file, state="disabled", padding=(10, 4),
        )
        self._browse_btn.pack(side="left")

        # × gomb: fájl törlésére — kezdetben rejtve (nincs pack-olva)
        self._clear_btn = ttk.Button(file_row, text="×", width=2, command=self._clear_file, padding=(4, 4))

        # Fájlnév és teljes útvonal kijelzők
        self._file_name_label = ttk.Label(
            self.file_frame, text="📄 Nincs fájl kiválasztva...", foreground="gray"
        )
        self._file_name_label.pack(anchor="w", pady=(6, 0))

        self._file_path_label = ttk.Label(self.file_frame, text="", foreground="gray")
        self._file_path_label.pack(anchor="w", pady=(2, 0))

    def _build_processing_section(self, parent):
        """Feldolgozás szekció: ▶ gomb, progressbar, hiba és siker visszajelző dobozok.

        A progressbar és a visszajelző dobozok alapból rejtve vannak (nincs pack-olva).
        Megjelenítésük pack()/pack_forget() hívásokkal történik állapotváltáskor.
        """
        PAD = SECTION_PAD
        self.processing_frame = ttk.LabelFrame(parent, text="Feldolgozás", padding=10)
        self.processing_frame.pack(fill="x", pady=(0, PAD))

        proc_row = ttk.Frame(self.processing_frame)
        proc_row.pack(fill="x")

        # ▶ gomb: alapból letiltva, FILE_SELECTED után engedélyeződik
        self._process_btn = ttk.Button(
            proc_row, text="▶ Számlafeldolgozása",
            state="disabled", width=28, command=self._start_processing, padding=(10, 4),
        )
        self._process_btn.pack(side="left")

        # Progressbar: indeterminate (pulzáló) módban fut feldolgozás közben
        # Alapból rejtve — csak PROCESSING állapotban pack-olódik
        self._progress_bar = ttk.Progressbar(proc_row, mode="determinate", length=160, value=0)

        # Hint szöveg: IDLE/TYPE_SELECTED állapotban látható útmutatás
        self._process_hint = ttk.Label(
            proc_row, text="Válasszon számlatípust és PDF fájlt a folytatáshoz", foreground="gray",
        )
        self._process_hint.pack(side="left", padx=(10, 0))

        # --- Hiba visszajelző doboz (ERROR állapotban látható) ---
        self._error_box = tk.Frame(self.processing_frame, bg=ERROR_BG, padx=8, pady=6)
        tk.Label(
            self._error_box, text="⊗ Feldolgozási hiba",
            bg=ERROR_BG, fg=ERROR_FG, font=("", 9, "bold"),
        ).pack(anchor="w")
        # A dinamikus hibaüzenet (wraplength=540: szöveg tördelése széles soroknál)
        self._error_msg_label = tk.Label(
            self._error_box, text="", bg=ERROR_BG, fg=ERROR_FG, wraplength=540, justify="left",
        )
        self._error_msg_label.pack(anchor="w")

        # --- Siker visszajelző doboz (SUCCESS állapotban látható) ---
        self._success_box = tk.Frame(self.processing_frame, bg=SUCCESS_BG, padx=8, pady=6)
        tk.Label(
            self._success_box, text="✔ Feldolgozás sikeresen befejezve",
            bg=SUCCESS_BG, fg=SUCCESS_FG, font=("", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self._success_box, text="Az Excel fájl elmentve a results mappába.",
            bg=SUCCESS_BG, fg=SUCCESS_FG,
        ).pack(anchor="w")

    def _build_result_section(self, parent):
        """Eredmény szekció: elkészült Excel neve + 3 gyors-megnyitó gomb.

        Ez a szekció alapból NEM pack-olt — csak SUCCESS állapotban jelenik meg
        (_update_result_frame() kezeli a láthatóságát).

        Gombok (jobbról balra):
          - Kinyert adatok megnyitása → az elkészült .xlsx
          - Betöltő megnyitása → a macros/ mappában lévő Excel makró fájl
          - Számla megnyitása → az eredeti PDF
        """
        self.result_frame = ttk.LabelFrame(parent, text="Eredmény", padding=10)
        # Alapból rejtve — _update_result_frame() pack-olja SUCCESS esetén

        result_row = ttk.Frame(self.result_frame)
        result_row.pack(fill="x")

        # Az elkészült Excel fájl neve (bal oldal, kitölti a maradék helyet)
        self._result_name_label = ttk.Label(
            result_row, text="📄 Még nincs eredményfájl...", foreground="gray"
        )
        self._result_name_label.pack(side="left", fill="x", expand=True)

        # Gombok jobb oldalon (fordított sorrendben pack-olva, hogy balról jobbra jelenjenek meg)
        self._open_pdf_btn = ttk.Button(
            result_row, text="Számla megnyitása", command=self._open_pdf, padding=(10, 4),
        )
        self._open_pdf_btn.pack(side="right", padx=(8, 0))

        self._open_macro_btn = ttk.Button(
            result_row, text="Betöltő megnyitása", command=self._open_macro, padding=(10, 4),
        )
        self._open_macro_btn.pack(side="right", padx=(8, 0))

        self._open_excel_btn = ttk.Button(
            result_row, text="Kinyert adatok megnyitása", command=self._open_excel, padding=(10, 4),
        )
        self._open_excel_btn.pack(side="right", padx=(8, 0))

        # Teljes útvonal kijelzője (a fájlnév alatt)
        self._result_path_label = ttk.Label(self.result_frame, text="", foreground="gray")
        self._result_path_label.pack(anchor="w", pady=(4, 0))

    def _build_layout(self):
        """A teljes ablak elrendezésének felépítése.

        Struktúra:
          root
          ├── menubar (Új feldolgozás | --- | Kilépés)
          ├── scrollbar (jobb)
          └── canvas (bal, kitölti a maradékot)
                └── content frame (scrollozható tartalom)
                      ├── header
                      ├── help
                      ├── type
                      ├── file
                      ├── processing
                      └── result

        A Canvas + Scrollbar kombináció teszi lehetővé a scrollozást:
          - _on_content_resize: frissíti a scrollrégiót, ha a tartalom változik
            (pl. egy szekció megjelenik/eltűnik)
          - _on_canvas_resize: a content frame szélességét az ablak szélességéhez
            igazítja, hogy a tartalom ne maradjon szűk fix szélességen
        """
        PAD = SECTION_PAD
        # Menüsáv
        menubar = tk.Menu(self.root)
        menubar.add_command(label="Új feldolgozás", command=self._reset_for_new)
        menubar.add_separator()
        menubar.add_command(label="Kilépés", command=self.root.quit)
        self.root.config(menu=menubar)

        # Scrollozható terület: Canvas + függőleges Scrollbar
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # A tényleges tartalom egy Frame a Canvas-on belül
        content = ttk.Frame(canvas, padding=(PAD, PAD))
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_content_resize(event):
            # Tartalom magassága változott (szekció megjelent/eltűnt) → scroll frissítés
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_resize(event):
            # Ablak szélessége változott → content frame igazítása
            canvas.itemconfig(content_window, width=event.width)

        content.bind("<Configure>", _on_content_resize)
        canvas.bind("<Configure>", _on_canvas_resize)

        # Szekciók felépítése (sorrendben jelennek meg az ablakban)
        self._build_header(content)
        self._build_help_section(content)
        self._build_type_section(content)
        self._build_file_section(content)
        self._build_processing_section(content)
        self._build_result_section(content)

    def run(self):
        """Elindítja a Tkinter event loop-ot — blokkol, amíg az ablakot be nem zárják."""
        self.root.mainloop()
