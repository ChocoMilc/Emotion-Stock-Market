import sys
import os
import sqlite3
import random
from datetime import datetime
from collections import deque

from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QRect
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl

player = None

def play_popup_sound():
    global player
    if player is None:
        player = QMediaPlayer()
        media = QMediaContent(QUrl.fromLocalFile(os.path.abspath("data/sqek.mp3")))
        player.setMedia(media)
        player.setVolume(100)
    player.play()

# ── DB SETUP ───────────────────────────────────────────────────────────────────
DB_DIR  = "data"
DB_FILE = os.path.join(DB_DIR, "emotions.db")
os.makedirs(DB_DIR, exist_ok=True)
conn = sqlite3.connect(DB_FILE)
conn.execute('''
    CREATE TABLE IF NOT EXISTS emotions (
        timestamp TEXT,
        happy REAL, sad REAL, mad REAL,
        silly REAL, devious REAL, sanity REAL,
        energy REAL, hunger REAL
    )
''')
conn.commit()

# ── OVERLAY WITH STOCK LINES ───────────────────────────────────────────────────
class EmotionOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.title_height = 20  # Height for title box

        self.emotion_data = {e: deque(maxlen=25) for e in [
            'happy','sad','mad','silly','devious','sanity','energy','hunger'
        ]}
        self.timestamps = deque(maxlen=25)

        self.colors = {
            'happy': QColor(255, 215, 0),
            'sad': QColor(30, 144, 255),
            'mad': QColor(255, 69, 0),
            'silly': QColor(255, 105, 180),
            'devious': QColor(148, 0, 211),
            'sanity': QColor(128, 128, 128),
            'energy': QColor(255, 206, 92),
            'hunger': QColor(82, 32, 13)
        }

        self.load_emotions_from_db()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        side = 200
        screen_padding = 70
        self.setGeometry(
            screen_padding - 47,
            screen.height() - (side + self.title_height) - screen_padding,
            side,
            side + self.title_height
        )
        self.show()

    def load_emotions_from_db(self):
        cursor = conn.execute(
            '''
            SELECT happy, sad, mad, silly, devious, sanity, energy, hunger
            FROM emotions
            ORDER BY timestamp DESC
            LIMIT 25
            '''
        )
        rows = cursor.fetchall()
        rows = rows[::-1]

        for row in rows:
            for i, emo in enumerate(self.emotion_data.keys()):
                self.emotion_data[emo].append(row[i])

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Draw background with transparency
        p.fillRect(self.rect(), QColor(255, 255, 255, 200))

        # Draw title box
        title_rect = QRect(0, 0, self.width(), self.title_height)
        p.setPen(QColor(0, 0, 0))
        p.drawText(title_rect, Qt.AlignCenter, "The Stock Market")

        # Move painter down for the chart area
        p.translate(0, self.title_height)
        effective_height = self.height() - self.title_height

        # Grid setup
        padding = 0
        pen = QPen(QColor(220, 220, 220), 1)
        p.setPen(pen)

        # Draw grid lines
        for y in range(padding, effective_height - padding + 1, 20):
            p.drawLine(padding, y, self.width() - padding, y)

        # Draw emotion lines
        for emo, vals in self.emotion_data.items():
            if len(vals) < 2: continue

            available_width = self.width() - 2 * padding
            available_height = effective_height - 2 * padding
            step = available_width / (len(vals) - 1)

            path = QPainterPath()
            for i, v in enumerate(vals):
                x = padding + i * step
                y = padding + ((100 - v) / 100 * available_height)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            p.setPen(QPen(self.colors[emo], 2))
            p.drawPath(path)

    def update_emotions(self, new_vals):
        for emo, v in new_vals.items():
            self.emotion_data[emo].append(v)
        self.update()

# ── DIALOG + LOGIC ─────────────────────────────────────────────────────────────
EMOS = ['happy','sad','mad','silly','devious','sanity','energy','hunger']
last = {e:50.0 for e in EMOS}

def ask_and_log():
    play_popup_sound()
    global last
    current = {}
    for emo in EMOS:
        val, ok = QInputDialog.getDouble(
            overlay,
            f"{emo.capitalize()} (0–100%)",
            f"How much {emo}?",
            value=last[emo],
            min=0, max=100, decimals=1
        )
        if not ok:
            print("Dialog canceled! Skipping update.")
            pass
        current[emo] = val
    if ok:
        ts = datetime.now().isoformat()
        conn.execute(
            '''
            INSERT INTO emotions VALUES (?,?,?,?,?,?,?,?,?)
            ''',
            (ts,
            current['happy'], current['sad'], current['mad'],
            current['silly'], current['devious'], current['sanity'],
            current['energy'], current['hunger'])
        )
        conn.commit()

        changes = {
            e: ((current[e] - last[e]) / last[e] * 100)
            if last[e] != 0 else 0
            for e in EMOS
        }
        print("\n📊 Emotional Market Update 📊")
        for emo, ch in changes.items():
            arrow = "↑" if ch > 0 else "↓"
            print(f"{arrow} {emo.capitalize()}: {abs(ch):.1f}%")
        if any(c < -20 for c in changes.values()):
            print("⚠️ EMOTIONAL CRASH IMMINENT ⚠️")

        overlay.update_emotions(current)
        last = current

    QTimer.singleShot(10 * 60 * 1000, ask_and_log)

# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, lambda *args: QCoreApplication.quit())

    app = QApplication(sys.argv)
    overlay = EmotionOverlay()

    QTimer.singleShot(1000, ask_and_log)
    sys.exit(app.exec_())
