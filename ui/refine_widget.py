from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from config import PILL_MARGIN_BOTTOM, PILL_HEIGHT

class RefineWidget(QWidget):
    """A minimal floating button that appears after transcription to offer prompt refinement."""
    
    refine_requested = pyqtSignal(str) # Emits the original text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedSize(140, 34)
        
        self._bg_color = QColor(15, 15, 15, 230)
        self._current_text = ""
        
        # Setup UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        self.btn = QPushButton("✨ Refinar Prompt")
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 10);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 15);
                font-family: 'Inter', Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: #10B981; /* Emerald 500 */
                border: 1px solid #059669; /* Emerald 600 */
            }
        """)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._on_btn_clicked)
        
        layout.addWidget(self.btn)
        
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.setInterval(8000) # Hide after 8 seconds
        self.auto_hide_timer.timeout.connect(self.hide)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 17, 17)
        painter.fillPath(path, self._bg_color)
        
        # Border
        painter.setPen(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 17, 17)
        painter.end()
        
    def show_for_text(self, text: str):
        self._current_text = text
        self.btn.setText("✨ Refinar Prompt")
        self.btn.setEnabled(True)
        
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.center().x() - (self.width() // 2)
            # Position above the main pill: 
            # Pillow is at geo.bottom() - PILL_MARGIN_BOTTOM - PILL_HEIGHT
            # Place this slightly higher so they don't overlap
            y = geo.bottom() - PILL_MARGIN_BOTTOM - PILL_HEIGHT - 44
            self.move(x, y)
            
        self.show()
        self.auto_hide_timer.start()

    def _on_btn_clicked(self):
        self.btn.setText("⏳ Refinando...")
        self.btn.setEnabled(False)
        self.auto_hide_timer.stop() # keep visible while refining
        # Emit signal to main thread handler
        self.refine_requested.emit(self._current_text)
