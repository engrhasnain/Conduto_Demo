"""Minimal flowing-text PDF writer on top of the reportlab canvas.

Tracks the text of each page so documents can be indexed for search, and reports the
page a block landed on so facts can cite "p.N" as their source."""
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

NAVY = HexColor("#1F3A5F")
GREY = HexColor("#666666")
LIGHT = HexColor("#E8EEF5")

WATERMARK = {"es": "DEMO – DATOS SINTÉTICOS", "pt": "DEMO – DADOS SINTÉTICOS", "en": "DEMO – SYNTHETIC DATA"}
PAGE = {"es": "Página", "pt": "Página", "en": "Page"}


class PdfDoc:
    margin = 56

    def __init__(self, path, lang: str, doc_label: str):
        self.c = canvas.Canvas(str(path), pagesize=A4)
        self.c.setTitle(doc_label)
        self.w, self.h = A4
        self.lang = lang
        self.doc_label = doc_label
        self.pages: list[list[str]] = []
        self._start_page()

    @property
    def page(self) -> int:
        return len(self.pages)

    def _start_page(self):
        self.pages.append([])
        c = self.c
        c.saveState()
        c.setFillColor(HexColor("#EEEEEE"))
        c.setFont("Helvetica-Bold", 44)
        c.translate(self.w / 2, self.h / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, WATERMARK[self.lang])
        c.restoreState()
        c.setFillColor(NAVY)
        c.rect(0, self.h - 42, self.w, 42, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(self.margin, self.h - 27, "CONDUTO")
        c.setFont("Helvetica", 9)
        c.drawRightString(self.w - self.margin, self.h - 26, self.doc_label)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 8)
        c.drawString(self.margin, 30, WATERMARK[self.lang])
        c.drawRightString(self.w - self.margin, 30, f"{PAGE[self.lang]} {self.page}")
        c.setFillColor(HexColor("#000000"))
        self.y = self.h - 75

    def new_page(self):
        self.c.showPage()
        self._start_page()

    def _ensure(self, height: float):
        if self.y - height < 60:
            self.new_page()

    def _wrap(self, text: str, font: str, size: float, width: float) -> list[str]:
        lines, cur = [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if stringWidth(trial, font, size) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines or [""]

    def title(self, text: str, size: int = 15) -> int:
        self._ensure(30)
        self.c.setFont("Helvetica-Bold", size)
        self.c.setFillColor(NAVY)
        for line in self._wrap(text, "Helvetica-Bold", size, self.w - 2 * self.margin):
            self.c.drawString(self.margin, self.y, line)
            self.y -= size + 5
        self.c.setFillColor(HexColor("#000000"))
        self.pages[-1].append(text)
        self.y -= 6
        return self.page

    def heading(self, text: str) -> int:
        self._ensure(28)
        self.y -= 4
        self.c.setFont("Helvetica-Bold", 11)
        self.c.setFillColor(NAVY)
        self.c.drawString(self.margin, self.y, text)
        self.c.setFillColor(HexColor("#000000"))
        self.y -= 16
        self.pages[-1].append(text)
        return self.page

    def para(self, text: str, size: float = 10, indent: float = 0, bold: bool = False) -> int:
        font = "Helvetica-Bold" if bold else "Helvetica"
        lines = self._wrap(text, font, size, self.w - 2 * self.margin - indent)
        self._ensure(len(lines) * (size + 3) + 4)
        page = self.page
        self.c.setFont(font, size)
        for line in lines:
            self.c.drawString(self.margin + indent, self.y, line)
            self.y -= size + 3
        self.y -= 4
        self.pages[-1].append(text)
        return page

    def bullet(self, text: str, size: float = 10) -> int:
        lines = self._wrap(text, "Helvetica", size, self.w - 2 * self.margin - 14)
        self._ensure(len(lines) * (size + 3) + 4)
        page = self.page
        self.c.setFont("Helvetica", size)
        self.c.drawString(self.margin + 2, self.y, "•")
        for line in lines:
            self.c.drawString(self.margin + 14, self.y, line)
            self.y -= size + 3
        self.y -= 3
        self.pages[-1].append(f"• {text}")
        return page

    def kv(self, rows: list[tuple[str, str]], key_width: float = 170) -> int:
        page = self.page
        for k, v in rows:
            lines = self._wrap(str(v), "Helvetica", 10, self.w - 2 * self.margin - key_width)
            h = len(lines) * 13 + 6
            self._ensure(h)
            self.c.setFillColor(LIGHT)
            self.c.rect(self.margin, self.y - h + 11, key_width - 6, h - 2, stroke=0, fill=1)
            self.c.setFillColor(HexColor("#000000"))
            self.c.setFont("Helvetica-Bold", 9.5)
            self.c.drawString(self.margin + 5, self.y, k)
            self.c.setFont("Helvetica", 10)
            yy = self.y
            for line in lines:
                self.c.drawString(self.margin + key_width, yy, line)
                yy -= 13
            self.y -= h
            self.pages[-1].append(f"{k} {v}")
        self.y -= 6
        return page

    def signatures(self, left: str, right: str):
        self._ensure(80)
        self.y -= 40
        x1, x2 = self.margin, self.w / 2 + 20
        self.c.line(x1, self.y, x1 + 200, self.y)
        self.c.line(x2, self.y, x2 + 200, self.y)
        self.c.setFont("Helvetica", 9)
        self.c.drawString(x1, self.y - 12, left)
        self.c.drawString(x2, self.y - 12, right)
        self.y -= 30

    def save(self) -> list[str]:
        self.c.save()
        return ["\n".join(p) for p in self.pages]
