# qt_ansi.py
from typing import Optional, Union, List
import re, html, sys
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextOption, QFont

def configure_textedit(te: QTextEdit, font_family: Optional[str] = None, wrap: bool = False) -> None:
    te.setReadOnly(True)
    te.setAcceptRichText(True)
    te.setWordWrapMode(QTextOption.WrapAnywhere if wrap else QTextOption.NoWrap)
    fam = font_family or ("Menlo" if sys.platform == "darwin" else "DejaVu Sans Mono")
    mono = QFont(fam); mono.setStyleHint(QFont.Monospace)
    te.setFont(mono)

class AnsiLogSink:
    """
    Stream ANSI+UTF-8 chunks into a QTextEdit as HTML.
    cr_mode:
      - 'newline'   : treat every '\\r' as a newline (default; best for logs)
      - 'overwrite' : keep a live last line; '\\r' rewinds and updates in place
    """
    def __init__(self, te: QTextEdit, cr_mode: str = "newline"):
        self._te = te
        self._buf = ""      # pending partial line (newline mode)
        self._live = ""     # last line (overwrite mode)
        self._cr_mode = cr_mode

    def feed(self, data):
        s = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data

        if self._cr_mode == "newline":
            # Strong normalization: turn CRLF and CR into LF
            s = s.replace("\r\n", "\n").replace("\r", "\n")
            self._buf += s
            if "\n" in self._buf:
                lines = self._buf.split("\n")
                for line in lines[:-1]:
                    self._append_html_line(_ansi_to_html(line))
                self._buf = lines[-1]  # trailing partial line
        else:
            # Overwrite mode: CR rewinds within the current (unflushed) line
            i = 0
            while i < len(s):
                ch = s[i]
                if ch == "\r":
                    self._live = ""           # reset current line
                elif ch == "\n":
                    self._append_html_line(_ansi_to_html(self._live))
                    self._live = ""
                else:
                    self._live += ch
                i += 1

    def flush(self):
        if self._cr_mode == "newline":
            if self._buf:
                self._append_html_line(_ansi_to_html(self._buf))
                self._buf = ""
        else:
            if self._live:
                self._append_html_line(_ansi_to_html(self._live))
                self._live = ""

    def _append_html_line(self, html_line: str):
        cur = self._te.textCursor()
        cur.movePosition(cur.End)
        # Insert the styled content…
        cur.insertHtml(html_line)
        # …then force a *real* line break:
        cur.insertBlock()
        self._te.setTextCursor(cur)
        sb = self._te.verticalScrollBar()
        sb.setValue(sb.maximum())


# ---------- ANSI → HTML converter (unchanged) ----------
_ANSI_FG = {
    30:"#000000", 31:"#cc0000", 32:"#00a600", 33:"#999900",
    34:"#0000cc", 35:"#cc00cc", 36:"#00aaaa", 37:"#cccccc",
    90:"#555555", 91:"#ff5555", 92:"#55ff55", 93:"#ffff55",
    94:"#5555ff", 95:"#ff55ff", 96:"#55ffff", 97:"#ffffff",
}
_ANSI_BG = {
    40:"#000000", 41:"#660000", 42:"#004000", 43:"#404000",
    44:"#000066", 45:"#400040", 46:"#004040", 47:"#666666",
    100:"#555555", 101:"#802222", 102:"#228022", 103:"#808022",
    104:"#222280", 105:"#802280", 106:"#228080", 107:"#aaaaaa",
}
_SGR_RE = re.compile(r'\x1b\[([0-9;]*)m')

def _style_css(st: dict) -> str:
    parts: List[str] = []
    if st.get("bold"): parts.append("font-weight:700")
    if st.get("underline"): parts.append("text-decoration:underline")
    if "fg" in st: parts.append(f"color:{st['fg']}")
    if "bg" in st: parts.append(f"background-color:{st['bg']}")
    parts.append("white-space:pre-wrap")
    return ";".join(parts)

def _xterm256_to_hex(idx: int, is_bg: bool) -> str:
    if idx < 0: idx = 0
    if idx > 255: idx = 255
    if idx < 16:
        table = _ANSI_BG if is_bg else _ANSI_FG
        keys = list(table.keys())
        return table.get(keys[idx % len(keys)], "#000000")
    if 16 <= idx <= 231:
        i = idx - 16
        r = (i // 36) % 6; g = (i // 6) % 6; b = i % 6
        to = lambda v: 55 + v * 40 if v > 0 else 0
        return f"#{to(r):02x}{to(g):02x}{to(b):02x}"
    v = 8 + (idx - 232) * 10
    return f"#{v:02x}{v:02x}{v:02x}"

def _ansi_to_html(text: str) -> str:
    out: List[str] = []
    style = {}; pos = 0
    def push(seg: str):
        if seg:
            out.append(f'<span style="{_style_css(style)}">{html.escape(seg)}</span>')
    for m in _SGR_RE.finditer(text):
        seg = text[pos:m.start()]; push(seg)
        codes = [c for c in m.group(1).split(";") if c != ""] or ["0"]
        i = 0
        while i < len(codes):
            try: n = int(codes[i])
            except ValueError: i += 1; continue
            if n == 0: style = {}
            elif n == 1: style["bold"] = True
            elif n == 4: style["underline"] = True
            elif n == 22: style.pop("bold", None)
            elif n == 24: style.pop("underline", None)
            elif 30 <= n <= 37 or 90 <= n <= 97:
                style["fg"] = _ANSI_FG.get(n, style.get("fg"))
            elif 40 <= n <= 47 or 100 <= n <= 107:
                style["bg"] = _ANSI_BG.get(n, style.get("bg"))
            elif n == 39: style.pop("fg", None)
            elif n == 49: style.pop("bg", None)
            elif n in (38, 48):
                is_bg = (n == 48)
                if i + 1 < len(codes):
                    mode = codes[i+1]
                    if mode == "5" and i + 2 < len(codes):
                        try:
                            idx = int(codes[i+2])
                            (style.__setitem__("bg" if is_bg else "fg", _xterm256_to_hex(idx, is_bg)))
                            i += 2
                        except ValueError: pass
                    elif mode == "2" and i + 4 < len(codes):
                        try:
                            r = int(codes[i+2]); g = int(codes[i+3]); b = int(codes[i+4])
                            col = f"#{max(0,min(r,255)):02x}{max(0,min(g,255)):02x}{max(0,min(b,255)):02x}"
                            (style.__setitem__("bg" if is_bg else "fg", col))
                            i += 4
                        except ValueError: pass
            i += 1
        pos = m.end()
    push(text[pos:])
    return "".join(out)
