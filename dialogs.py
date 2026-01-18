"""Dialog components for the PyQt CRUD application."""

import json
import os
from datetime import datetime, timezone
import ast

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QPushButton, QMessageBox,
    QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QDoubleSpinBox, QFileDialog,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent
from PyQt6.QtGui import QFont, QColor, QPixmap

from db import DatabaseManager
from currency_settings import CurrencySettingsManager


def _safe_eval_expr(expr):
    """Safely evaluate simple arithmetic expressions."""
    node = ast.parse(expr, mode="eval")
    allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant)
    allowed_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.UAdd, ast.USub)

    def _validate(n):
        if not isinstance(n, allowed_nodes):
            raise ValueError("Invalid expression")
        if isinstance(n, ast.BinOp) and not isinstance(n.op, allowed_ops):
            raise ValueError("Invalid operator")
        if isinstance(n, ast.UnaryOp) and not isinstance(n.op, allowed_ops):
            raise ValueError("Invalid operator")
        for child in ast.iter_child_nodes(n):
            _validate(child)

    _validate(node)
    value = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}})
    if not isinstance(value, (int, float)):
        raise ValueError("Invalid result")
    return float(value)


def _apply_calc_to_spinbox(spinbox, text=None):
    if text is None:
        text = spinbox.lineEdit().text().strip()
    if not text.startswith("="):
        if not text:
            return
        try:
            value = float(text.replace(",", "."))
        except Exception:
            return
        spinbox.setValue(value)
        return
    expr = text[1:].strip()
    if not expr:
        return
    try:
        value = _safe_eval_expr(expr)
    except Exception:
        return
    spinbox.setValue(value)


class _CalcFilter(QObject):
    def __init__(self, spinbox):
        super().__init__(spinbox)
        self.spinbox = spinbox

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            text = obj.text().strip()
            if text.startswith("="):
                _apply_calc_to_spinbox(self.spinbox, text)
                return True
        if event.type() == QEvent.Type.FocusOut:
            text = obj.text().strip()
            if text.startswith("="):
                _apply_calc_to_spinbox(self.spinbox, text)
        return super().eventFilter(obj, event)


def _enable_calc_input(spinbox):
    line_edit = spinbox.lineEdit()
    line_edit.setValidator(None)
    calc_filter = _CalcFilter(spinbox)
    line_edit.installEventFilter(calc_filter)
    spinbox._calc_filter = calc_filter


class DatabaseConfigDialog(QDialog):
    """Dialog for configuring database connection"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = os.path.join(os.path.dirname(__file__), 'db_config.json')
        self.init_ui()
        self.load_saved_config()

    def init_ui(self):
        self.setWindowTitle("MongoDB Əlaqə Parametrləri")
        self.setMinimumWidth(450)

        layout = QFormLayout()

        # Host
        self.host_input = QLineEdit("")
        layout.addRow("Host:", self.host_input)

        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(27017)
        layout.addRow("Port:", self.port_input)

        # Database
        self.database_input = QLineEdit("admin")
        layout.addRow("Database:", self.database_input)

        # User (optional)
        self.user_input = QLineEdit("admin")
        layout.addRow("İstifadəçi:", self.user_input)

        # Password (optional)
        self.password_input = QLineEdit("")
        self.password_input.setPlaceholderText("Şifrə (istəyə bağlı)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Şifrə:", self.password_input)

        # Save credentials checkbox
        self.save_credentials_checkbox = QPushButton("💾 Məlumatları Yadda Saxla")
        self.save_credentials_checkbox.setCheckable(True)
        self.save_credentials_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        layout.addRow(self.save_credentials_checkbox)

        # Buttons
        button_layout = QHBoxLayout()

        self.test_btn = QPushButton("🔌 Əlaqəni Yoxla")
        self.test_btn.clicked.connect(self.test_connection)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)

        self.connect_btn = QPushButton("✅ Qoşul")
        self.connect_btn.clicked.connect(self.accept)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.cancel_btn = QPushButton("❌ Ləğv Et")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addRow(button_layout)

        self.setLayout(layout)

    def test_connection(self):
        """Test the database connection with current parameters"""
        try:
            db = DatabaseManager(
                host=self.host_input.text().strip(),
                port=self.port_input.value(),
                database=self.database_input.text().strip(),
                username=self.user_input.text().strip(),
                password=self.password_input.text()
            )
            success, message = db.test_connection()
            if success:
                QMessageBox.information(
                    self,
                    "Uğurlu",
                    f"Verilənlər bazasına əlaqə uğurlu!\n\n{message}"
                )
            else:
                QMessageBox.warning(self, "Xəta", f"Əlaqə uğursuz:\n{message}")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Əlaqə xətası:\n{str(e)}")

    def load_saved_config(self):
        """Load saved configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # Load values into inputs
                self.host_input.setText(config.get('host', ''))
                self.port_input.setValue(config.get('port', 27017))
                self.database_input.setText(config.get('database', 'admin'))
                self.user_input.setText(config.get('username', 'admin'))
                self.password_input.setText(config.get('password', ''))

                # Check the save button if config exists
                self.save_credentials_checkbox.setChecked(True)
        except Exception as e:
            print(f"Could not load saved config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'host': self.host_input.text().strip(),
                'port': self.port_input.value(),
                'database': self.database_input.text().strip(),
                'username': self.user_input.text().strip(),
                'password': self.password_input.text()
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Could not save config: {e}")

    def delete_saved_config(self):
        """Delete saved configuration file"""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
        except Exception as e:
            print(f"Could not delete config: {e}")

    def get_config(self):
        """Return the database configuration"""
        # Save or delete config based on checkbox state
        if self.save_credentials_checkbox.isChecked():
            self.save_config()
        else:
            self.delete_saved_config()

        return {
            'host': self.host_input.text().strip(),
            'port': self.port_input.value(),
            'database': self.database_input.text().strip(),
            'username': self.user_input.text().strip(),
            'password': self.password_input.text()
        }


class ImageViewerDialog(QDialog):
    """Dialog for viewing product images"""

    def __init__(self, parent=None, image_data=None, product_name=""):
        super().__init__(parent)
        self.image_data = image_data
        self.product_name = product_name
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Şəkil: {self.product_name}")
        self.setMinimumSize(600, 600)

        layout = QVBoxLayout()

        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f0f0f0; border: 2px solid #ccc;")

        if self.image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(self.image_data)

            # Scale image to fit window while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                800, 800,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText("Şəkil yoxdur")
            self.image_label.setStyleSheet("color: #999; font-size: 16px;")

        # Scroll area for large images
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Close button
        close_btn = QPushButton("❌ Bağla")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class PriceHistoryDialog(QDialog):
    """Dialog to show price change history for a product"""

    def __init__(self, parent=None, product_name="", price_history=None, current_price=0):
        super().__init__(parent)
        self.product_name = product_name
        self.price_history = price_history or []
        self.current_price = current_price
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"📈 Qiymət Tarixi - {self.product_name}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Title
        title = QLabel(f"Qiymət Tarixi: {self.product_name}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2196F3; padding: 10px;")
        layout.addWidget(title)

        # Current price label
        current_label = QLabel(f"Cari Qiymət: {self.current_price:.2f} AZN")
        current_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50; padding: 5px;")
        layout.addWidget(current_label)

        # Table for history
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tarix", "Köhnə Qiymət (AZN)", "Yeni Qiymət (AZN)", "Dəyişiklik"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # Populate table (newest first)
        sorted_history = sorted(self.price_history, key=lambda x: x.get('changed_at', datetime.min), reverse=True)

        for entry in sorted_history:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Date
            changed_at = entry.get('changed_at')
            if changed_at:
                if hasattr(changed_at, 'astimezone'):
                    if changed_at.tzinfo is None:
                        changed_at = changed_at.replace(tzinfo=timezone.utc)
                    local_time = changed_at.astimezone()
                    date_str = local_time.strftime("%d.%m.%Y %H:%M")
                else:
                    date_str = str(changed_at)
            else:
                date_str = "N/A"
            self.table.setItem(row, 0, QTableWidgetItem(date_str))

            # Old price
            old_price = entry.get('old_price', 0)
            self.table.setItem(row, 1, QTableWidgetItem(f"{old_price:.2f}"))

            # New price
            new_price = entry.get('new_price', 0)
            self.table.setItem(row, 2, QTableWidgetItem(f"{new_price:.2f}"))

            # Change (difference)
            diff = new_price - old_price
            diff_text = f"+{diff:.2f}" if diff >= 0 else f"{diff:.2f}"
            diff_item = QTableWidgetItem(diff_text)
            if diff > 0:
                diff_item.setForeground(QColor("#f44336"))  # Red for increase
            elif diff < 0:
                diff_item.setForeground(QColor("#4CAF50"))  # Green for decrease
            self.table.setItem(row, 3, diff_item)

        layout.addWidget(self.table)

        # Info label if no history
        if not self.price_history:
            no_history_label = QLabel("Bu məhsul üçün qiymət tarixi yoxdur.")
            no_history_label.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            no_history_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_history_label)

        # Close button
        close_btn = QPushButton("❌ Bağla")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class ProductDialog(QDialog):
    """Dialog for adding/editing products"""

    def __init__(self, parent=None, product=None, mode="add"):
        super().__init__(parent)
        self.product = product
        self.mode = mode
        self.parent_window = parent
        self.currency_manager = CurrencySettingsManager(
            self.parent_window.db if self.parent_window and hasattr(self.parent_window, 'db') else None
        )
        self._original_price = None
        self._original_currency = None
        self._stored_price_azn = None
        self._current_price_azn = 0.0
        self.image_data = None  # Store uploaded image data
        self.image_filename = None
        self.remove_image = False  # Flag to indicate image removal

        # Timer for clearing status messages in dialog
        if self.mode == "add":
            self.status_clear_timer = QTimer()
            self.status_clear_timer.setSingleShot(True)
            self.status_clear_timer.timeout.connect(self._clear_dialog_status)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Yeni Məhsul Əlavə Et" if self.mode == "add" else "Məhsulu Redaktə Et")
        self.setMinimumWidth(500)

        layout = QFormLayout()

        # Product Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Məhsulun adını daxil edin")
        layout.addRow("Məhsulun Adı *:", self.name_input)

        # Category
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Məsələn: İnşaat, Elektrik, Santexnika")
        layout.addRow("Kateqoriya:", self.category_input)

        # Price
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix("")
        layout.addRow("Qiymət:", self.price_input)
        _enable_calc_input(self.price_input)

        # Currency
        self.currency_input = QComboBox()
        self.currency_input.addItems(["AZN", "USD", "EUR", "TRY"])
        layout.addRow("Valyuta:", self.currency_input)

        # Converted price (AZN)
        self.price_azn_label = QLabel("0.00 AZN")
        self.price_azn_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addRow("Qiymət (AZN):", self.price_azn_label)

        # Source/Origin
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Məhsulun mənbəyi")
        layout.addRow("Məhsul Mənbəyi:", self.source_input)

        # Unit of measurement
        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText("kg, litr, ədəd və s.")
        layout.addRow("Ölçü Vahidi:", self.unit_input)

        # Note
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Əlavə qeydlər")
        self.note_input.setMaximumHeight(80)
        layout.addRow("Qeyd:", self.note_input)

        # Image upload section
        image_layout = QHBoxLayout()
        self.upload_image_btn = QPushButton("📷 Şəkil Yüklə")
        self.upload_image_btn.clicked.connect(self.upload_image)
        self.upload_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        image_layout.addWidget(self.upload_image_btn)

        self.image_status_label = QLabel("Şəkil yoxdur")
        self.image_status_label.setStyleSheet("color: #666; font-style: italic;")
        image_layout.addWidget(self.image_status_label)

        self.remove_image_btn = QPushButton("🗑️ Şəkli Sil")
        self.remove_image_btn.clicked.connect(self.remove_image_action)
        self.remove_image_btn.setVisible(False)
        self.remove_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        image_layout.addWidget(self.remove_image_btn)

        image_layout.addStretch()
        layout.addRow("Şəkil:", image_layout)

        # Fill fields if editing
        if self.product:
            self.name_input.setText(self.product['mehsulun_adi'])
            self.category_input.setText(self.product.get('category', '') or '')
            self.price_input.setValue(float(self.product['price']) if self.product.get('price') else 0)
            currency = self.product.get('currency', 'AZN') or 'AZN'
            self._original_price = float(self.product.get('price') or 0)
            self._original_currency = currency
            self._stored_price_azn = self.product.get('price_azn')
            idx = self.currency_input.findText(currency)
            if idx >= 0:
                self.currency_input.setCurrentIndex(idx)
            self.source_input.setText(self.product.get('mehsul_menbeyi', '') or '')
            self.unit_input.setText(self.product.get('olcu_vahidi', '') or '')
            self.note_input.setText(self.product.get('qeyd', '') or '')

            # Check if product has an image
            if self.product.get('image_id'):
                self.image_status_label.setText("✓ Şəkil mövcuddur")
                self.image_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.remove_image_btn.setVisible(True)

        self.price_input.valueChanged.connect(self.update_converted_price)
        self.currency_input.currentTextChanged.connect(self.update_converted_price)
        self.update_converted_price()

        # Status label (for add mode)
        if self.mode == "add":
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addRow(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()

        if self.mode == "add":
            self.save_btn = QPushButton("💾 Əlavə Et və Davam Et")
            self.save_btn.clicked.connect(self.save_and_continue)
        else:
            self.save_btn = QPushButton("💾 Yadda Saxla")
            self.save_btn.clicked.connect(self.accept)

        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.cancel_btn = QPushButton("❌ Bağla" if self.mode == "add" else "❌ Ləğv Et")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addRow(button_layout)

        self.setLayout(layout)

    def upload_image(self):
        """Handle image upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Şəkil Seçin",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    self.image_data = f.read()
                    self.image_filename = os.path.basename(file_path)

                self.image_status_label.setText(f"✓ {self.image_filename}")
                self.image_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.remove_image_btn.setVisible(True)
                self.remove_image = False
            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Şəkil yüklənə bilmədi: {e}")

    def remove_image_action(self):
        """Mark image for removal"""
        self.image_data = None
        self.image_filename = None
        self.remove_image = True
        self.image_status_label.setText("Şəkil yoxdur")
        self.image_status_label.setStyleSheet("color: #666; font-style: italic;")
        self.remove_image_btn.setVisible(False)

    def get_data(self):
        """Returns the form data"""
        currency = self.currency_input.currentText()
        price = self.price_input.value() if self.price_input.value() > 0 else None
        price_azn = self._current_price_azn if price is not None else None
        data = {
            'mehsulun_adi': self.name_input.text().strip(),
            'category': self.category_input.text().strip() or None,
            'price': price,
            'price_azn': price_azn if price is not None else None,
            'currency': currency,
            'mehsul_menbeyi': self.source_input.text().strip() or None,
            'qeyd': self.note_input.toPlainText().strip() or None,
            'olcu_vahidi': self.unit_input.text().strip() or None
        }

        # Add image information
        data['image_data'] = self.image_data
        data['image_filename'] = self.image_filename
        data['remove_image'] = self.remove_image

        return data

    def update_converted_price(self):
        currency = self.currency_input.currentText()
        price = self.price_input.value()
        if self._stored_price_azn is not None and self._original_price == price and self._original_currency == currency:
            price_azn = float(self._stored_price_azn)
        else:
            price_azn = self.currency_manager.convert_to_azn(price, currency)
        self._current_price_azn = price_azn
        self.price_azn_label.setText(f"{price_azn:.2f} AZN")

    def save_and_continue(self):
        """Save product and clear form for adding another (add mode only)"""
        if not self.name_input.text().strip():
            self.status_label.setText("⚠️ Məhsulun adı mütləqdir!")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 5px;")
            return

        data = self.get_data()
        try:
            # Call parent window's database to create product
            if self.parent_window and self.parent_window.db:
                # Handle image upload
                image_id = None
                if data['image_data']:
                    image_id = self.parent_window.db.save_image(data['image_data'], data['image_filename'])

                self.parent_window.db.create_product(
                    data['mehsulun_adi'],
                    data['price'],
                    data['mehsul_menbeyi'],
                    data['qeyd'],
                    data['olcu_vahidi'],
                    data['category'],
                    image_id=image_id,
                    currency=data.get('currency', 'AZN'),
                    price_azn=data.get('price_azn')
                )

                # Show success status in dialog
                self.status_label.setText(f"✅ '{data['mehsulun_adi']}' uğurla əlavə edildi!")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")

                # Auto-clear dialog status after 2 seconds
                self.status_clear_timer.stop()
                self.status_clear_timer.start(2000)

                # Update parent window's table
                self.parent_window.load_products(preserve_status=True)

                # Show status in main window
                self.parent_window.show_status(
                    f"✅ '{data['mehsulun_adi']}' məhsulu əlavə edildi",
                    color="#4CAF50"
                )

                # Clear form for next entry
                self.clear_form()

                # Set focus back to name field
                self.name_input.setFocus()

        except Exception as e:
            self.status_label.setText(f"❌ Xəta: {str(e)}")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 5px;")
            # Auto-clear error after 4 seconds
            self.status_clear_timer.stop()
            self.status_clear_timer.start(4000)

    def clear_form(self):
        """Clear all input fields"""
        self.name_input.clear()
        self.category_input.clear()
        self.price_input.setValue(0)
        self.source_input.clear()
        self.unit_input.clear()
        self.note_input.clear()

        # Clear image data
        self.image_data = None
        self.image_filename = None
        self.remove_image = False
        self.image_status_label.setText("Şəkil yoxdur")
        self.image_status_label.setStyleSheet("color: #666; font-style: italic;")
        self.remove_image_btn.setVisible(False)

    def _clear_dialog_status(self):
        """Clear the status label in the dialog"""
        if hasattr(self, 'status_label'):
            self.status_label.setText("")

    def accept(self):
        """Validate before accepting (edit mode)"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Xəbərdarlıq", "Məhsulun adı mütləqdir!")
            return
        super().accept()


class SmetaItemDialog(QDialog):
    """Dialog for adding items to Smeta (from DB or custom)"""

    def __init__(self, parent=None, db=None, item=None, mode="add_from_db"):
        super().__init__(parent)
        self.db = db
        self.item = item
        self.mode = mode  # "add_from_db", "custom", "edit"
        self.currency_manager = CurrencySettingsManager(self.db)
        self._original_price = None
        self._original_currency = None
        self._stored_unit_price_azn = None
        self._current_unit_price_azn = 0.0
        self.init_ui()

    def init_ui(self):
        if self.mode == "add_from_db":
            self.setWindowTitle("Məhsul Əlavə Et (Verilənlər Bazasından)")
        elif self.mode == "custom":
            self.setWindowTitle("Xüsusi Qeyd Əlavə Et")
        else:
            self.setWindowTitle("Qeydi Redaktə Et")

        self.setMinimumWidth(500)
        layout = QFormLayout()

        # Product selection (only for add_from_db mode)
        if self.mode == "add_from_db":
            self.product_combo = QLineEdit()
            self.product_combo.setPlaceholderText("Məhsul ID-ni daxil edin")
            layout.addRow("Məhsul ID:", self.product_combo)

        # Name (editable for custom, read-only for DB items)
        self.name_input = QLineEdit()
        if self.mode == "add_from_db":
            self.name_input.setReadOnly(True)
            self.name_input.setPlaceholderText("ID daxil etdikdən sonra avtomatik doldurulacaq")
        else:
            self.name_input.setPlaceholderText("Məhsul/İş adını daxil edin")
        layout.addRow("Adı:", self.name_input)

        # Quantity
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.01, 999999.99)
        self.quantity_input.setDecimals(2)
        self.quantity_input.setValue(1)
        layout.addRow("Miqdar:", self.quantity_input)

        # Unit
        self.unit_input = QLineEdit()
        if self.mode == "add_from_db":
            self.unit_input.setReadOnly(True)
        else:
            self.unit_input.setPlaceholderText("kg, m², ədəd və s.")
        layout.addRow("Ölçü Vahidi:", self.unit_input)

        # Unit Price
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix("")
        if self.mode == "add_from_db":
            self.price_input.setReadOnly(True)
        layout.addRow("Vahid Qiymət:", self.price_input)
        if self.mode != "add_from_db":
            _enable_calc_input(self.price_input)

        # Currency
        self.currency_input = QComboBox()
        self.currency_input.addItems(["AZN", "USD", "EUR", "TRY"])
        if self.mode == "add_from_db":
            self.currency_input.setEnabled(False)
        layout.addRow("Valyuta:", self.currency_input)

        # Unit price converted to AZN
        self.price_azn_label = QLabel("0.00 AZN")
        self.price_azn_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addRow("Vahid Qiymət (AZN):", self.price_azn_label)

        # Total (calculated, read-only)
        self.total_label = QLabel("0.00 AZN")
        self.total_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout.addRow("Cəmi:", self.total_label)

        # Margin percent
        self.margin_input = QDoubleSpinBox()
        self.margin_input.setRange(0, 100)
        self.margin_input.setDecimals(1)
        self.margin_input.setValue(0)
        self.margin_input.setSuffix(" %")
        layout.addRow("Marja %:", self.margin_input)

        # Final price with margin (calculated, read-only)
        self.final_total_label = QLabel("0.00 AZN")
        self.final_total_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addRow("Yekun (Marja ilə):", self.final_total_label)

        # Connect quantity change to update total
        self.quantity_input.valueChanged.connect(self.update_total)
        self.price_input.valueChanged.connect(self.update_total)
        self.margin_input.valueChanged.connect(self.update_total)
        self.currency_input.currentTextChanged.connect(self.update_total)

        # Load product info button (for add_from_db mode)
        if self.mode == "add_from_db":
            self.load_btn = QPushButton("📥 Məhsul Məlumatını Yüklə")
            self.load_btn.clicked.connect(self.load_product_info)
            self.load_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0b7dda;
                }
            """)
            layout.addRow(self.load_btn)

        # Fill fields if editing
        if self.item:
            self.name_input.setText(self.item.get('name', ''))
            self.quantity_input.setValue(float(self.item.get('quantity', 1)))
            self.unit_input.setText(self.item.get('unit', ''))
            self.price_input.setValue(float(self.item.get('unit_price', 0)))
            currency = self.item.get('currency', 'AZN') or 'AZN'
            self._original_price = float(self.item.get('unit_price') or 0)
            self._original_currency = currency
            self._stored_unit_price_azn = self.item.get('unit_price_azn')
            idx = self.currency_input.findText(currency)
            if idx >= 0:
                self.currency_input.setCurrentIndex(idx)
            self.margin_input.setValue(float(self.item.get('margin_percent', 0)))
            self.update_total()

        # Buttons
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 Əlavə Et" if self.mode != "edit" else "💾 Yadda Saxla")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.cancel_btn = QPushButton("❌ Ləğv Et")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addRow(button_layout)

        self.setLayout(layout)

    def load_product_info(self):
        """Load product information from database"""
        try:
            product_id = self.product_combo.text().strip()
            product = self.db.read_product(product_id)

            if product:
                self.name_input.setText(product['mehsulun_adi'])
                self.unit_input.setText(product.get('olcu_vahidi', '') or 'ədəd')
                self.price_input.setValue(float(product['price']) if product.get('price') else 0)
                currency = product.get('currency', 'AZN') or 'AZN'
                idx = self.currency_input.findText(currency)
                if idx >= 0:
                    self.currency_input.setCurrentIndex(idx)
                self.update_total()
                QMessageBox.information(self, "Uğurlu", "Məhsul məlumatı yükləndi!")
            else:
                QMessageBox.warning(self, "Xəta", "Bu ID-yə sahib məhsul tapılmadı!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Xəta baş verdi: {str(e)}")

    def update_total(self):
        """Update total price and final total with margin"""
        quantity = self.quantity_input.value()
        unit_price = self.price_input.value()
        currency = self.currency_input.currentText()
        if self._stored_unit_price_azn is not None and self._original_price == unit_price and self._original_currency == currency:
            unit_price_azn = float(self._stored_unit_price_azn)
        else:
            unit_price_azn = self.currency_manager.convert_to_azn(unit_price, currency)
        self._current_unit_price_azn = unit_price_azn
        total = quantity * unit_price_azn
        margin_percent = self.margin_input.value()
        final_total = total * (1 + margin_percent / 100)
        self.price_azn_label.setText(f"{unit_price_azn:.2f} AZN")
        self.total_label.setText(f"{total:.2f} AZN")
        self.final_total_label.setText(f"{final_total:.2f} AZN")

    def get_data(self):
        """Get form data"""
        product_id = None
        if self.mode == "add_from_db" and hasattr(self, 'product_combo') and self.product_combo.text().strip():
            product_id = self.product_combo.text().strip()
        elif self.item:
            product_id = self.item.get('product_id')

        currency = self.currency_input.currentText()
        unit_price_azn = self._current_unit_price_azn
        data = {
            'product_id': product_id,
            'name': self.name_input.text().strip(),
            'quantity': self.quantity_input.value(),
            'unit': self.unit_input.text().strip(),
            'unit_price': self.price_input.value(),
            'unit_price_azn': unit_price_azn,
            'total': self.quantity_input.value() * unit_price_azn,
            'currency': currency,
            'margin_percent': self.margin_input.value(),
            'is_custom': self.item.get('is_custom') if self.item else self.mode == "custom"
        }

        if self.item:
            data['category'] = self.item.get('category', '')
            data['source'] = self.item.get('source', '')
            data['note'] = self.item.get('note', '')

        return data

    def accept(self):
        """Validate before accepting"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Xəbərdarlıq", "Ad mütləqdir!")
            return
        if self.quantity_input.value() <= 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Miqdar 0-dan böyük olmalıdır!")
            return
        super().accept()


class TemplateItemDialog(QDialog):
    """Dialog for adding/editing template items"""

    def __init__(self, parent=None, mode="generic", db=None, item=None):
        super().__init__(parent)
        self.mode = mode
        self.db = db
        self.item = item
        self.selected_product = None
        self.currency_manager = CurrencySettingsManager(self.db)
        self.init_ui()

    def init_ui(self):
        if self.mode == "generic":
            self.setWindowTitle("Generik Qeyd Əlavə Et")
        else:
            self.setWindowTitle("DB-dən Qeyd Əlavə Et")

        self.setMinimumWidth(400)
        layout = QFormLayout()

        # Generic name
        self.generic_name_input = QLineEdit()
        self.generic_name_input.setPlaceholderText("Məs: AC açar, Kabel 2.5mm², Lampa")
        layout.addRow("Generik Ad:", self.generic_name_input)

        # Category (for filtering when loading)
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Kateqoriya (filtrasiya üçün)")
        layout.addRow("Kateqoriya:", self.category_input)

        # Unit
        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText("ədəd, m, kg və s.")
        layout.addRow("Ölçü Vahidi:", self.unit_input)

        # Default price
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix("")
        layout.addRow("Defolt Qiymət:", self.price_input)
        _enable_calc_input(self.price_input)

        # Currency
        self.currency_input = QComboBox()
        self.currency_input.addItems(["AZN", "USD", "EUR", "TRY"])
        layout.addRow("Valyuta:", self.currency_input)

        # Converted price
        self.price_azn_label = QLabel("0.00 AZN")
        self.price_azn_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addRow("Qiymət (AZN):", self.price_azn_label)

        # Product selection (for DB mode)
        if self.mode == "from_db":
            self.product_id_input = QLineEdit()
            self.product_id_input.setPlaceholderText("Məhsul ID-ni daxil edin")
            layout.addRow("Məhsul ID:", self.product_id_input)

            self.load_product_btn = QPushButton("📥 Məhsul Yüklə")
            self.load_product_btn.clicked.connect(self.load_product_info)
            self.load_product_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; border: none; border-radius: 4px;")
            layout.addRow(self.load_product_btn)

        # Fill if editing
        if self.item:
            self.generic_name_input.setText(self.item.get('generic_name', self.item.get('name', '')))
            self.category_input.setText(self.item.get('category', ''))
            self.unit_input.setText(self.item.get('unit', ''))
            self.price_input.setValue(self.item.get('default_price', 0))
            currency = self.item.get('currency', 'AZN') or 'AZN'
            idx = self.currency_input.findText(currency)
            if idx >= 0:
                self.currency_input.setCurrentIndex(idx)
            if self.mode == "from_db" and self.item.get('product_id'):
                self.product_id_input.setText(self.item.get('product_id'))

        self.price_input.valueChanged.connect(self.update_converted_price)
        self.currency_input.currentTextChanged.connect(self.update_converted_price)
        self.update_converted_price()

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Saxla")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;")

        cancel_btn = QPushButton("❌ Ləğv Et")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        self.setLayout(layout)

    def load_product_info(self):
        """Load product info from database"""
        if not self.db:
            return

        product_id = self.product_id_input.text().strip()
        if not product_id:
            QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul ID-ni daxil edin!")
            return

        try:
            product = self.db.read_product(product_id)
            if product:
                self.selected_product = product
                self.generic_name_input.setText(product['mehsulun_adi'])
                self.category_input.setText(product.get('category', ''))
                self.unit_input.setText(product.get('olcu_vahidi', '') or 'ədəd')
                self.price_input.setValue(float(product['price']) if product.get('price') else 0)
                currency = product.get('currency', 'AZN') or 'AZN'
                idx = self.currency_input.findText(currency)
                if idx >= 0:
                    self.currency_input.setCurrentIndex(idx)
                QMessageBox.information(self, "Uğurlu", "Məhsul məlumatı yükləndi!")
            else:
                QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul tapılmadı!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Xəta: {str(e)}")

    def get_data(self):
        """Get item data"""
        data = {
            'generic_name': self.generic_name_input.text().strip(),
            'name': self.generic_name_input.text().strip(),
            'category': self.category_input.text().strip(),
            'unit': self.unit_input.text().strip(),
            'default_price': self.price_input.value(),
            'currency': self.currency_input.currentText(),
            'default_price_azn': self.currency_manager.convert_to_azn(
                self.price_input.value(),
                self.currency_input.currentText()
            ),
            'is_generic': self.mode == "generic"
        }

        if self.mode == "from_db" and hasattr(self, 'product_id_input'):
            data['product_id'] = self.product_id_input.text().strip() or None

        return data

    def accept(self):
        if not self.generic_name_input.text().strip():
            QMessageBox.warning(self, "Xəbərdarlıq", "Generik ad boş ola bilməz!")
            return
        super().accept()

    def update_converted_price(self):
        currency = self.currency_input.currentText()
        price = self.price_input.value()
        price_azn = self.currency_manager.convert_to_azn(price, currency)
        self.price_azn_label.setText(f"{price_azn:.2f} AZN")


class ProductSelectionDialog(QDialog):
    """Dialog for selecting a product when loading a generic template item"""

    def __init__(self, parent=None, db=None, generic_name="", category=""):
        super().__init__(parent)
        self.db = db
        self.generic_name = generic_name
        self.category = category
        self.selected_product = None
        self.currency_manager = CurrencySettingsManager(self.db)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Məhsul Seç: {self.generic_name}")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(f"'{self.generic_name}' üçün məhsul seçin:")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Axtar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Məhsul adı ilə axtar...")
        self.search_input.setText(self.generic_name)  # Pre-fill with generic name
        self.search_input.textChanged.connect(self.search_products)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Products table
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(4)
        self.products_table.setHorizontalHeaderLabels(["ID", "Məhsul Adı", "Kateqoriya", "Qiymət"])
        self.products_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.products_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.products_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.products_table.doubleClicked.connect(self.accept)

        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.products_table)

        # Buttons
        button_layout = QHBoxLayout()

        select_btn = QPushButton("✅ Seç")
        select_btn.clicked.connect(self.accept)
        select_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;")

        skip_btn = QPushButton("⏭️ Keç")
        skip_btn.clicked.connect(self.reject)
        skip_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
        skip_btn.setToolTip("Bu qeydi Smeta-a əlavə etmə")

        button_layout.addStretch()
        button_layout.addWidget(select_btn)
        button_layout.addWidget(skip_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initial search
        self.search_products()

    def search_products(self):
        """Search products by name"""
        self.products_table.setRowCount(0)
        search_text = self.search_input.text().strip()

        try:
            # Use the db's search method if available
            if hasattr(self.db, 'search_products'):
                products = self.db.search_products(search_text if search_text else None)
            else:
                products = self.db.read_all_products()
                if search_text:
                    search_lower = search_text.lower()
                    products = [p for p in products if search_lower in p.get('mehsulun_adi', '').lower()]

            for product in products[:100]:  # Limit to 100 results
                row = self.products_table.rowCount()
                self.products_table.insertRow(row)

                id_item = QTableWidgetItem(str(product['_id']))
                id_item.setData(Qt.ItemDataRole.UserRole, product)
                self.products_table.setItem(row, 0, id_item)

                self.products_table.setItem(row, 1, QTableWidgetItem(product.get('mehsulun_adi', '')))
                self.products_table.setItem(row, 2, QTableWidgetItem(product.get('category', '')))

                currency = product.get('currency', 'AZN') or 'AZN'
                price = float(product['price']) if product.get('price') else 0
                price_azn = product.get('price_azn')
                if price_azn is None:
                    price_azn = self.currency_manager.convert_to_azn(price, currency)
                if currency == "AZN":
                    price_text = f"{price:.2f} AZN"
                else:
                    price_text = f"AZN {price_azn:.2f} ({price:.2f} {currency})"
                self.products_table.setItem(row, 3, QTableWidgetItem(price_text))

        except Exception as e:
            print(f"Search error: {e}")

    def get_selected_product(self):
        """Get the selected product"""
        return self.selected_product

    def accept(self):
        selected_row = self.products_table.currentRow()
        if selected_row >= 0:
            self.selected_product = self.products_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            super().accept()
        else:
            QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul seçin!")
