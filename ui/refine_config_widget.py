from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QComboBox, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

class RefineConfigWidget(QWidget):
    """A floating window to configure prompt/text refinement before sending down."""
    
    # Emits (input_text, output_type, context)
    generate_requested = pyqtSignal(str, str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(600, 550)
        
        self.original_text = ""
        self._setup_ui()
        
    def _setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Background container
        container = QWidget()
        container.setObjectName("container")
        container.setStyleSheet("""
            QWidget#container {
                background-color: rgba(18, 18, 18, 250);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 14px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Inter', Arial, sans-serif;
                font-weight: 500;
                font-size: 13px;
                letter-spacing: 0.5px;
            }
            QLabel.title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 5px;
            }
            QTextEdit, QLineEdit, QComboBox {
                background-color: rgba(30, 30, 30, 255);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 8px;
                padding: 10px;
                font-family: 'Inter', Arial, sans-serif;
                font-size: 13px;
            }
            QTextEdit:focus, QLineEdit:focus, QComboBox:focus {
                border: 1px solid rgba(16, 185, 129, 100); /* Emerald hint */
            }
            QComboBox::drop-down {
                border-left: 1px solid rgba(255, 255, 255, 10);
            }
            QComboBox QAbstractItemView {
                background-color: rgba(30, 30, 30, 255);
                color: #E2E8F0;
                selection-background-color: rgba(255, 255, 255, 20);
                outline: none;
            }
            QPushButton {
                font-family: 'Inter', Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 18px;
            }
            QPushButton#btn_cancel {
                background-color: rgba(255, 255, 255, 10);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 15);
            }
            QPushButton#btn_cancel:hover {
                background-color: rgba(255, 255, 255, 20);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton#btn_generate {
                background-color: #10B981; /* Emerald 500 */
                color: #FFFFFF;
                border: none;
            }
            QPushButton#btn_generate:hover {
                background-color: #059669; /* Emerald 600 */
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Configurar Formato de Salida")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Output Type Selector
        type_layout = QVBoxLayout()
        type_layout.setSpacing(5)
        type_label = QLabel("Tipo de salida:")
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Prompt (estándar)",
            "Correo electrónico",
            "Informe",
            "Novela",
            "Guion de vídeo",
            "Otra (especificar...)"
        ])
        
        self.custom_type_input = QLineEdit()
        self.custom_type_input.setPlaceholderText("Ej: Artículo de blog, Tuit, Poema...")
        self.custom_type_input.setVisible(False)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addWidget(self.custom_type_input)
        layout.addLayout(type_layout)
        
        # Purpose/Context
        ctx_layout = QVBoxLayout()
        ctx_layout.setSpacing(5)
        ctx_label = QLabel("Contexto / Indicaciones (¿Para qué lo necesitas?):")
        self.ctx_input = QLineEdit()
        self.ctx_input.setPlaceholderText("Ej: Es un correo formal para el jefe sobre el proyecto UX...")
        ctx_layout.addWidget(ctx_label)
        ctx_layout.addWidget(self.ctx_input)
        layout.addLayout(ctx_layout)
        
        # Info Base
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        info_label = QLabel("Contenido base (Input crudo / Lluvia de ideas):")
        self.info_edit = QTextEdit()
        self.info_edit.setPlaceholderText("Pega o escribe aquí las escenas desordenadas, puntos del informe...")
        info_layout.addWidget(info_label)
        info_layout.addWidget(self.info_edit)
        layout.addLayout(info_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.hide)
        
        btn_generate = QPushButton("✨ Generar")
        btn_generate.setObjectName("btn_generate")
        btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generate.clicked.connect(self._on_generate)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_generate)
        
        layout.addLayout(btn_layout)
        main_layout.addWidget(container)
        
    def show_for_text(self, original_text: str):
        self.original_text = original_text
        self.info_edit.setPlainText(original_text)
        self.ctx_input.clear()
        self.custom_type_input.clear()
        self.type_combo.setCurrentIndex(0) # Default to Prompt
        self.custom_type_input.setVisible(False)
        
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2
            )
            
        self.show()
        
    def _on_type_changed(self, text: str):
        if text == "Otra (especificar...)":
            self.custom_type_input.setVisible(True)
            self.custom_type_input.setFocus()
        else:
            self.custom_type_input.setVisible(False)

    def _on_generate(self):
        txt = self.info_edit.toPlainText().strip()
        typ = self.type_combo.currentText()
        if typ == "Otra (especificar...)":
            typ = self.custom_type_input.text().strip()
            if not typ:
                typ = "Texto general"
                
        ctx = self.ctx_input.text().strip()
        if txt:
            self.generate_requested.emit(txt, typ, ctx)
            self.hide()
