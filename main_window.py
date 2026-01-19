"""Main window implementation."""

import csv
import sys
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView,
    QMenu, QCheckBox, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QAbstractTableModel, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QColor, QShortcut, QKeySequence

from db import DatabaseManager
from dialogs import (
    CsvImportOptionsDialog, DatabaseConfigDialog, ImageViewerDialog,
    PriceHistoryDialog, ProductDialog, SmetaItemDialog
)
from boq_window import SmetaWindow
from project_window import ProjectWindow
from settings_dialog import CurrencySettingsDialog
from currency_settings import CurrencySettingsManager


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.db = None
        self.boq_window = None  # Single Smeta window instance
        self.project_window = None  # Single Project window instance
        self.currency_manager = CurrencySettingsManager()
        self.table_model = ProductTableModel(self.currency_manager)
        self.proxy_model = ProductFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setSortRole(Qt.ItemDataRole.UserRole)

        # Create a timer for search debouncing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        # Create a timer for clearing status messages
        self.status_timer = QTimer()
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._clear_status)

        self.init_ui()
        self.show_db_config()

    def init_ui(self):
        self.setWindowTitle("🛒 Məhsul İdarəetmə Sistemi - MongoDB CRUD")
        self.setGeometry(100, 100, 1200, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title = QLabel("Məhsul İdarəetmə Sistemi (MongoDB)")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2196F3; padding: 10px;")
        main_layout.addWidget(title)

        # Connection status
        self.connection_label = QLabel("🔴 Verilənlər bazasına qoşulmayıb")
        self.connection_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 5px;")
        self.connection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.connection_label)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Axtar:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Məhsul adı, kateqoriya, qeyd və ya mənbə üzrə axtar...")
        self.search_input.textChanged.connect(self.search_products)

        self.clear_search_btn = QPushButton("❌ Təmizlə")
        self.clear_search_btn.clicked.connect(self.clear_search)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.clear_search_btn)
        main_layout.addLayout(search_layout)

        self.import_btn = QPushButton("⬆️ CSV İdxal")
        self.import_btn.clicked.connect(self.import_products_csv)
        self.import_btn.setEnabled(False)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #455A64;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #37474F;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.export_btn = QPushButton("⬇️ CSV İxrac")
        self.export_btn.clicked.connect(self.export_products_csv)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #546E7A;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        # CSV actions (top)
        csv_layout = QHBoxLayout()
        csv_layout.addStretch()
        csv_layout.addWidget(self.import_btn)
        csv_layout.addWidget(self.export_btn)
        main_layout.addLayout(csv_layout)

        # ID column toggle
        self.show_id_checkbox = QCheckBox("ID sütununu göstər")
        self.show_id_checkbox.setChecked(False)
        self.show_id_checkbox.stateChanged.connect(self.toggle_id_column)
        main_layout.addWidget(self.show_id_checkbox)

        # Table
        self.table = QTableView()
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.setModel(self.proxy_model)

        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Məhsulun Adı
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Kateqoriya
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Qiymət
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Qiymət Dəyişdi (Gün)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Məhsul Mənbəyi
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Ölçü Vahidi
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Qeyd
        self.table.setColumnHidden(0, True)

        # Connect double-click to quick add to Smeta
        self.table.doubleClicked.connect(self.quick_add_to_boq)
        self.table.clicked.connect(lambda *_: self.table.setFocus())
        self.table.installEventFilter(self)
        # Enter handling is implemented via eventFilter on the table.

        # Enable context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        main_layout.addWidget(self.table)

        # Info label
        self.info_label = QLabel("Verilənlər bazasına qoşulun...")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("➕ Yeni Məhsul")
        self.add_btn.clicked.connect(self.add_product)
        self.add_btn.setEnabled(False)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.edit_btn = QPushButton("✏️ Redaktə Et")
        self.edit_btn.clicked.connect(self.edit_product)
        self.edit_btn.setEnabled(False)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.delete_btn = QPushButton("🗑️ Sil")
        self.delete_btn.clicked.connect(self.delete_product)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.refresh_btn = QPushButton("🔄 Yenilə")
        self.refresh_btn.clicked.connect(self.load_products)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.reconnect_btn = QPushButton("🔌 Yenidən Qoşul")
        self.reconnect_btn.clicked.connect(self.show_db_config)
        self.reconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)

        self.add_to_boq_btn = QPushButton("➕ Smeta-ya Əlavə Et")
        self.add_to_boq_btn.clicked.connect(self.add_selected_to_boq)
        self.add_to_boq_btn.setEnabled(False)
        self.add_to_boq_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5E35B1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.boq_btn = QPushButton("📋 Smeta Aç")
        self.boq_btn.clicked.connect(self.open_boq_window)
        self.boq_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BCD4;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ACC1;
            }
        """)

        self.project_btn = QPushButton("📁 Layihələr")
        self.project_btn.clicked.connect(self.open_project_window)
        self.project_btn.setStyleSheet("""
            QPushButton {
                background-color: #795548;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6D4C41;
            }
        """)

        self.settings_btn = QPushButton("⚙️ Ayarlar")
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.add_to_boq_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.reconnect_btn)
        button_layout.addWidget(self.boq_btn)
        button_layout.addWidget(self.project_btn)
        button_layout.addWidget(self.settings_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)

        # Window styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTableView {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 13px;
            }
        """)

        # Setup keyboard shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for MainWindow"""
        # Ctrl+N: Add new product
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.add_product)

        # Ctrl+E: Edit selected product
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.edit_product)

        # Delete: Delete selected product(s)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.delete_product)

        # Ctrl+F: Focus search box
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.focus_search)

        # Ctrl+B: Open Smeta window
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self.open_boq_window)

        # F5: Refresh products
        QShortcut(QKeySequence("F5"), self).activated.connect(self.load_products)

    def focus_search(self):
        """Focus the search input field"""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def eventFilter(self, source, event):
        if source is self.table and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.add_selected_to_boq()
                return True
        return super().eventFilter(source, event)

    def show_db_config(self):
        """Show database configuration dialog"""
        dialog = DatabaseConfigDialog(self)
        if dialog.exec():
            config = dialog.get_config()
            try:
                self.db = DatabaseManager(**config)
                self.currency_manager = CurrencySettingsManager(self.db)
                self.table_model.set_currency_manager(self.currency_manager)
                user_display = f"{config['username']}@" if config['username'] else ""
                self.connection_label.setText(
                    f"🟢 Qoşuldu: {user_display}{config['host']}:{config['port']}/{config['database']}"
                )
                self.connection_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")

                # Enable buttons
                self.add_btn.setEnabled(True)
                self.edit_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
                self.add_to_boq_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self.import_btn.setEnabled(True)
                self.export_btn.setEnabled(True)

                self.load_products()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Verilənlər Bazası Xətası",
                    f"Verilənlər bazasına qoşula bilmədi:\n{str(e)}"
                )

    def load_products(self, preserve_status=False):
        """Load all products into table"""
        if not self.db:
            return

        try:
            products = self.db.read_all_products()
            self.populate_table(products)
            if not preserve_status:
                self._update_info_label(filtered=bool(self.search_input.text().strip()))
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Məhsullar yüklənə bilmədi:\n{str(e)}")

    def toggle_id_column(self):
        """Show or hide the ID column."""
        self.table.setColumnHidden(0, not self.show_id_checkbox.isChecked())

    def populate_table(self, products):
        """Populate table with product data"""
        self.table_model.set_products(products)
        self._refresh_filter_state()

    def add_product(self):
        """Open dialog to add new product"""
        if not self.db:
            return

        # Open dialog - it handles saving and clearing internally
        dialog = ProductDialog(self, mode="add")
        dialog.exec()
        # No need to handle the result - dialog manages everything

    def edit_product(self):
        """Edit selected product"""
        if not self.db:
            return

        product = self._current_product()

        if not product:
            QMessageBox.warning(self, "Xəbərdarlıq", "Zəhmət olmasa redaktə etmək üçün məhsul seçin!")
            return

        product_id = product['id']

        try:
            product = self.db.read_product(product_id)

            if not product:
                QMessageBox.critical(self, "Xəta", "Məhsul tapılmadı!")
                return

            dialog = ProductDialog(self, product=product, mode="edit")
            if dialog.exec():
                data = dialog.get_data()

                # Handle image upload
                image_id = None
                if data['image_data']:
                    # New image uploaded
                    image_id = self.db.save_image(data['image_data'], data['image_filename'])
                elif data['remove_image']:
                    # Image removed
                    image_id = ''  # Empty string signals removal

                success = self.db.update_product(
                    product_id,
                    data['mehsulun_adi'],
                    data['price'],
                    data['mehsul_menbeyi'],
                    data['qeyd'],
                    data['olcu_vahidi'],
                    data['category'],
                    image_id=image_id if image_id is not None else None,
                    currency=data.get('currency', 'AZN'),
                    price_azn=data.get('price_azn'),
                    price_round=data.get('price_round', False)
                )
                if success:
                    QMessageBox.information(self, "Uğurlu", "Məhsul uğurla yeniləndi!")
                    self.load_products()
                else:
                    QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul yenilənə bilmədi!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Məhsul yenilənə bilmədi:\n{str(e)}")

    def delete_product(self):
        """Delete selected product(s)"""
        if not self.db:
            return

        # Get all selected rows
        selected_products = self._selected_products()

        if not selected_products:
            QMessageBox.warning(self, "Xəbərdarlıq", "Zəhmət olmasa silmək üçün məhsul seçin!")
            return

        # Collect product IDs and names
        products_to_delete = []
        for product in selected_products:
            products_to_delete.append((product['id'], product['mehsulun_adi']))

        # Confirm deletion
        if len(products_to_delete) == 1:
            message = f"'{products_to_delete[0][1]}' məhsulunu silmək istədiyinizdən əminsiniz?"
        else:
            message = f"{len(products_to_delete)} məhsulu silmək istədiyinizdən əminsiniz?"

        reply = QMessageBox.question(
            self,
            "Təsdiq",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_count = 0
                failed_count = 0

                for product_id, product_name in products_to_delete:
                    success = self.db.delete_product(product_id)
                    if success:
                        deleted_count += 1
                    else:
                        failed_count += 1

                if deleted_count > 0:
                    QMessageBox.information(
                        self,
                        "Uğurlu",
                        f"{deleted_count} məhsul uğurla silindi!" +
                        (f"\n{failed_count} məhsul silinə bilmədi." if failed_count > 0 else "")
                    )
                    self.load_products()
                else:
                    QMessageBox.warning(self, "Xəbərdarlıq", "Heç bir məhsul silinə bilmədi!")
            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Məhsul silinə bilmədi:\n{str(e)}")

    def view_product_image(self):
        """View product image from context menu"""
        if not self.db:
            return

        product = self._current_product()
        if not product:
            return

        try:
            # Get product ID from the selected row
            product_id = product['id']
            product_name = product['mehsulun_adi']

            # Retrieve product data
            product = self.db.read_product(product_id)

            if not product:
                QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul tapılmadı!")
                return

            # Check if product has an image
            if product.get('image_id'):
                try:
                    # Retrieve image from GridFS
                    image_data = self.db.get_image(product['image_id'])

                    # Show image viewer dialog
                    viewer = ImageViewerDialog(self, image_data, product_name)
                    viewer.exec()
                except Exception as e:
                    QMessageBox.warning(self, "Xəbərdarlıq", f"Şəkil yüklənə bilmədi: {e}")
            else:
                QMessageBox.information(self, "Məlumat", f"'{product_name}' üçün şəkil yoxdur.\n\nŞəkil əlavə etmək üçün məhsulu redaktə edin.")

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Şəkil göstərilə bilmədi:\n{str(e)}")

    def show_price_history(self):
        """Show price history dialog for selected product"""
        if not self.db:
            return

        product = self._current_product()
        if not product:
            return

        try:
            product_id = product['id']
            product_name = product['mehsulun_adi']

            product = self.db.read_product(product_id)
            if not product:
                QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul tapılmadı!")
                return

            price_history = self.db.get_price_history(product_id)
            current_price = product.get('price', 0)

            dialog = PriceHistoryDialog(self, product_name, price_history, current_price)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Qiymət tarixi göstərilə bilmədi:\n{str(e)}")

    def show_context_menu(self, position):
        """Show context menu on right-click"""
        if not self.db:
            return

        # Get selected rows
        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            return

        # Create context menu
        menu = QMenu(self)

        # Single selection actions
        if len(selected_rows) == 1:
            edit_action = menu.addAction("✏️ Redaktə Et")
            edit_action.triggered.connect(self.edit_product)

            copy_action = menu.addAction("📋 Kopyala və Redaktə Et")
            copy_action.triggered.connect(self.copy_product)

            image_action = menu.addAction("🖼️ Şəkli Göstər")
            image_action.triggered.connect(self.view_product_image)

            price_history_action = menu.addAction("📈 Qiymət Tarixi")
            price_history_action.triggered.connect(self.show_price_history)

            menu.addSeparator()

        # Multi-selection compatible actions
        add_to_boq_action = menu.addAction(f"➕ Smeta-a Əlavə Et ({len(selected_rows)} məhsul)")
        add_to_boq_action.triggered.connect(self.add_selected_to_boq)

        menu.addSeparator()

        delete_action = menu.addAction(f"🗑️ Sil ({len(selected_rows)} məhsul)")
        delete_action.triggered.connect(self.delete_product)

        # Show menu at cursor position
        menu.exec(self.table.viewport().mapToGlobal(position))

    def copy_product(self):
        """Copy selected product and open for editing"""
        if not self.db:
            return

        product = self._current_product()
        if not product:
            return

        try:
            # Get product ID and data
            product_id = product['id']
            product = self.db.read_product(product_id)

            if not product:
                QMessageBox.critical(self, "Xəta", "Məhsul tapılmadı!")
                return

            # Create a copy of the product (without _id and image_id)
            product_copy = {
                'mehsulun_adi': product['mehsulun_adi'] + " (kopya)",
                'price': product.get('price'),
                'price_round': product.get('price_round'),
                'mehsul_menbeyi': product.get('mehsul_menbeyi'),
                'qeyd': product.get('qeyd'),
                'olcu_vahidi': product.get('olcu_vahidi'),
                'category': product.get('category')
            }

            # Open dialog in "add" mode with copied data
            dialog = ProductDialog(self, product=product_copy, mode="add")
            dialog.setWindowTitle("Məhsulu Kopyala")

            if dialog.exec():
                data = dialog.get_data()

                # Handle image if copied
                image_id = None
                if data['image_data']:
                    image_id = self.db.save_image(data['image_data'], data['image_filename'])

                # Create new product
                new_product_id = self.db.create_product(
                    data['mehsulun_adi'],
                    data['price'],
                    data['mehsul_menbeyi'],
                    data['qeyd'],
                    data['olcu_vahidi'],
                    data['category'],
                    image_id=image_id,
                    currency=data.get('currency', 'AZN'),
                    price_azn=data.get('price_azn'),
                    price_round=data.get('price_round', False)
                )

                if new_product_id:
                    QMessageBox.information(self, "Uğurlu", "Məhsul kopyalandı və əlavə edildi!")
                    self.load_products()
                else:
                    QMessageBox.warning(self, "Xəbərdarlıq", "Məhsul kopyalana bilmədi!")

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Məhsul kopyalanarkən xəta:\n{str(e)}")

    def quick_add_to_boq(self, index):
        """Quick add product to Smeta on double-click"""
        if not self.db:
            QMessageBox.warning(self, "Xəta", "Verilənlər bazasına qoşulmayıbsınız!")
            return

        # Check if Smeta window exists
        if not self.boq_window:
            QMessageBox.warning(self, "Xəbərdarlıq", "Smeta pəncərəsi açılmayıb! Əvvəlcə 'Smeta Aç' düyməsini basın.")
            return

        try:
            source_index = self.proxy_model.mapToSource(index)
            product = self.table_model.product_at(source_index.row())
            if not product:
                QMessageBox.warning(self, "Xəta", "Məhsul tapılmadı!")
                return
            product_id = product['id']
            product = self.db.read_product(product_id)

            if not product:
                QMessageBox.warning(self, "Xəta", f"Məhsul tapılmadı: {product_id}")
                return

            # Create a pre-filled item for the dialog
            item = {
                'name': product['mehsulun_adi'],
                'quantity': 1,
                'unit': product.get('olcu_vahidi', ''),
                'unit_price': product.get('price', 0),
                'currency': product.get('currency', 'AZN') or 'AZN',
                'unit_price_azn': product.get('price_azn'),
                'category': product.get('category', ''),
                'source': product.get('mehsul_menbeyi', ''),
                'note': product.get('qeyd', '')
            }

            # Show dialog for quantity input
            dialog = SmetaItemDialog(
                self,
                self.db,
                item=item,
                mode="edit",
                string_count=self.boq_window.string_count,
            )
            dialog.setWindowTitle(f"Smeta-a Əlavə Et: {product['mehsulun_adi']}")

            if dialog.exec():
                data = dialog.get_data()
                data['id'] = self.boq_window.next_id
                self.boq_window.next_id += 1
                self.boq_window.boq_items.append(data)
                self.boq_window.refresh_table()
                self.show_status(f"'{product['mehsulun_adi']}' Smeta-a əlavə edildi", "#4CAF50")

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Məhsul əlavə edilərkən xəta:\n{str(e)}")

    def add_selected_to_boq(self):
        """Add selected products to Smeta with sequential quantity dialogs"""
        if not self.db:
            QMessageBox.warning(self, "Xəta", "Verilənlər bazasına qoşulmayıbsınız!")
            return

        # Check if Smeta window exists
        if not self.boq_window:
            QMessageBox.warning(self, "Xəbərdarlıq", "Smeta pəncərəsi açılmayıb! Əvvəlcə 'Smeta yarat' düyməsini basın.")
            return

        # Get all selected rows
        selected_products = self._selected_products()
        if not selected_products:
            return

        # Process each selected product
        added_count = 0
        for product in selected_products:
            product_id = product['id']

            try:
                # Load product from database
                product = self.db.read_product(product_id)
                if not product:
                    QMessageBox.warning(self, "Xəta", f"Məhsul tapılmadı: {product_id}")
                    continue

                # Create a pre-filled item for the dialog
                item = {
                    'name': product['mehsulun_adi'],
                    'quantity': 1,
                    'unit': product.get('olcu_vahidi', ''),
                    'unit_price': product.get('price', 0),
                    'currency': product.get('currency', 'AZN') or 'AZN',
                    'unit_price_azn': product.get('price_azn'),
                    'category': product.get('category', '')
                }

                # Show dialog for quantity input
                dialog = SmetaItemDialog(
                    self,
                    self.db,
                    item=item,
                    mode="edit",
                    string_count=self.boq_window.string_count,
                )
                dialog.setWindowTitle(f"Smeta-a Əlavə Et: {product['mehsulun_adi']}")

                if dialog.exec():
                    # Get the data from dialog
                    data = dialog.get_data()
                    data['id'] = self.boq_window.next_id
                    self.boq_window.next_id += 1

                    # Add to Smeta
                    self.boq_window.boq_items.append(data)
                    added_count += 1
                else:
                    # User cancelled, stop processing remaining items
                    break

            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Məhsul əlavə edilərkən xəta:\n{str(e)}")
                continue

        # Refresh Smeta table and show success message
        if added_count > 0:
            self.boq_window.refresh_table()
            if added_count == 1:
                self.show_status("1 məhsul Smeta-a əlavə edildi", "#4CAF50")
            else:
                self.show_status(f"{added_count} məhsul Smeta-a əlavə edildi", "#4CAF50")

    def search_products(self):
        """Debounced search - waits for user to stop typing"""
        # Stop any existing timer
        self.search_timer.stop()

        # Start a new timer that will trigger search after 300ms of no typing
        self.search_timer.start(300)

    def _perform_search(self):
        """Actually perform the search (called by timer)"""
        if not self.db:
            return

        search_term = self.search_input.text().strip()
        self.proxy_model.set_search_text(search_term)
        self._update_info_label(filtered=True)

    def clear_search(self):
        """Clear search and reload all products"""
        self.search_timer.stop()  # Stop any pending search
        self.search_input.clear()
        self.proxy_model.set_search_text("")
        self._update_info_label(filtered=False)

    def show_status(self, message, color="#4CAF50", duration=3000):
        """Show a temporary status message at the bottom"""
        self.info_label.setText(message)
        self.info_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 5px;")

        # Clear the status after duration (default 3 seconds)
        self.status_timer.stop()
        self.status_timer.start(duration)

    def _clear_status(self):
        """Clear status message and show product count"""
        if self.db:
            try:
                self._update_info_label(filtered=bool(self.search_input.text().strip()))
            except Exception:
                pass

    def open_boq_window(self):
        """Open the Bill of Quantities window (singleton)"""
        if self.boq_window is None or not self.boq_window.isVisible():
            self.boq_window = SmetaWindow(self, self.db)
            self.boq_window.show()
        else:
            # Bring existing window to front
            self.boq_window.raise_()
            self.boq_window.activateWindow()

    def open_project_window(self):
        """Open the Project Management window (singleton)"""
        if not self.db:
            QMessageBox.warning(self, "Xəbərdarlıq", "Əvvəlcə verilənlər bazasına qoşulun!")
            return

        if self.project_window is None or not self.project_window.isVisible():
            self.project_window = ProjectWindow(self, self.db)
            self.project_window.show()
        else:
            # Bring existing window to front
            self.project_window.raise_()
            self.project_window.activateWindow()

    def open_settings(self):
        """Open currency settings dialog"""
        dialog = CurrencySettingsDialog(self, self.db)
        dialog.exec()
        self.table_model.layoutChanged.emit()

    def _current_product(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        source_index = self.proxy_model.mapToSource(index)
        return self.table_model.product_at(source_index.row())

    def _selected_products(self):
        selected_rows = self.table.selectionModel().selectedRows()
        products = []
        for index in selected_rows:
            source_index = self.proxy_model.mapToSource(index)
            product = self.table_model.product_at(source_index.row())
            if product:
                products.append(product)
        return products

    def _refresh_filter_state(self):
        self.proxy_model.set_search_text(self.search_input.text().strip())
        self._update_info_label(filtered=bool(self.search_input.text().strip()))

    def _update_info_label(self, filtered=False):
        if filtered:
            self.info_label.setText(f"Axtarış nəticəsi: {self.proxy_model.rowCount()} məhsul tapıldı")
        else:
            self.info_label.setText(f"Cəmi məhsul sayı: {self.table_model.rowCount()}")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")

    def import_products_csv(self):
        if not self.db:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "CSV İdxal Et",
            "",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return

        options_dialog = CsvImportOptionsDialog(self)
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        mode = options_dialog.mode()

        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    QMessageBox.warning(self, "Xəbərdarlıq", "CSV faylında başlıq tapılmadı.")
                    return

                created = updated = skipped = failed = 0
                for row in reader:
                    if not row:
                        continue
                    product_data = self._parse_csv_row(row)
                    if not product_data:
                        failed += 1
                        continue

                    existing = None
                    if product_data.get("id"):
                        try:
                            existing = self.db.read_product(product_data["id"])
                        except Exception:
                            existing = None
                    if not existing and product_data.get("mehsulun_adi"):
                        existing = self.db.find_product_by_name(product_data["mehsulun_adi"])

                    if existing and mode == "skip":
                        skipped += 1
                        continue

                    if existing and mode == "update":
                        merged = existing.copy()
                        merged.update(product_data)
                        success = self.db.update_product(
                            merged["id"],
                            merged.get("mehsulun_adi", ""),
                            merged.get("price", 0),
                            merged.get("mehsul_menbeyi", ""),
                            merged.get("qeyd", ""),
                            merged.get("olcu_vahidi", ""),
                            merged.get("category", ""),
                            image_id=None,
                            currency=merged.get("currency", "AZN"),
                            price_azn=merged.get("price_azn"),
                            price_round=merged.get("price_round", False)
                        )
                        if success:
                            updated += 1
                        else:
                            failed += 1
                        continue

                    new_id = self.db.create_product(
                        product_data.get("mehsulun_adi", ""),
                        product_data.get("price", 0),
                        product_data.get("mehsul_menbeyi", ""),
                        product_data.get("qeyd", ""),
                        product_data.get("olcu_vahidi", ""),
                        product_data.get("category", ""),
                        image_id=None,
                        currency=product_data.get("currency", "AZN"),
                        price_azn=product_data.get("price_azn"),
                        price_round=product_data.get("price_round", False)
                    )
                    if new_id:
                        created += 1
                    else:
                        failed += 1

            self.load_products()
            QMessageBox.information(
                self,
                "Uğurlu",
                "CSV idxalı tamamlandı.\n"
                f"Yaradıldı: {created}\n"
                f"Yeniləndi: {updated}\n"
                f"Keçildi: {skipped}\n"
                f"Xəta: {failed}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"CSV idxalı alınmadı:\n{str(e)}")

    def export_products_csv(self):
        if not self.db:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "CSV İxrac Et",
            "products.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            products = self.db.read_all_products()
            headers = [
                "id",
                "mehsulun_adi",
                "category",
                "price",
                "currency",
                "price_azn",
                "price_round",
                "mehsul_menbeyi",
                "qeyd",
                "olcu_vahidi",
                "price_last_changed",
            ]
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for product in products:
                    price_last_changed = product.get("price_last_changed")
                    if price_last_changed:
                        if price_last_changed.tzinfo is None:
                            price_last_changed = price_last_changed.replace(tzinfo=timezone.utc)
                        price_last_changed = price_last_changed.isoformat()
                    writer.writerow({
                        "id": product.get("id"),
                        "mehsulun_adi": product.get("mehsulun_adi"),
                        "category": product.get("category", ""),
                        "price": product.get("price", 0),
                        "currency": product.get("currency", "AZN"),
                        "price_azn": product.get("price_azn", ""),
                        "price_round": bool(product.get("price_round", False)),
                        "mehsul_menbeyi": product.get("mehsul_menbeyi", ""),
                        "qeyd": product.get("qeyd", ""),
                        "olcu_vahidi": product.get("olcu_vahidi", ""),
                        "price_last_changed": price_last_changed or "",
                    })

            QMessageBox.information(self, "Uğurlu", f"CSV ixrac edildi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"CSV ixracı alınmadı:\n{str(e)}")

    def _parse_csv_row(self, row):
        def _pick(keys):
            for key in keys:
                if key in row and row[key] != "":
                    return row[key]
            return None

        product_name = _pick(["mehsulun_adi", "name", "product_name"])
        if not product_name:
            return None

        price_value = _pick(["price"])
        try:
            price = float(str(price_value).replace(",", ".")) if price_value is not None else 0.0
        except ValueError:
            price = 0.0

        price_azn_value = _pick(["price_azn"])
        try:
            price_azn = float(str(price_azn_value).replace(",", ".")) if price_azn_value not in (None, "") else None
        except ValueError:
            price_azn = None

        price_round_value = _pick(["price_round"])
        price_round = str(price_round_value).strip().lower() in ("1", "true", "yes") if price_round_value is not None else False

        return {
            "id": _pick(["id", "_id"]),
            "mehsulun_adi": product_name.strip(),
            "category": (_pick(["category"]) or "").strip(),
            "price": price,
            "currency": (_pick(["currency"]) or "AZN").strip() or "AZN",
            "price_azn": price_azn,
            "price_round": price_round,
            "mehsul_menbeyi": (_pick(["mehsul_menbeyi", "source"]) or "").strip(),
            "qeyd": (_pick(["qeyd", "note"]) or "").strip(),
            "olcu_vahidi": (_pick(["olcu_vahidi", "unit"]) or "").strip(),
        }


class ProductTableModel(QAbstractTableModel):
    headers = [
        "ID", "Məhsulun Adı", "Kateqoriya", "Qiymət",
        "Qiymət Dəyişdi (Gün)", "Məhsul Mənbəyi", "Ölçü Vahidi", "Qeyd"
    ]

    def __init__(self, currency_manager, products=None, parent=None):
        super().__init__(parent)
        self.currency_manager = currency_manager
        self._products = list(products or [])

    def set_currency_manager(self, manager):
        self.currency_manager = manager
        self.layoutChanged.emit()

    def set_products(self, products):
        self.beginResetModel()
        self._products = list(products)
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._products)

    def columnCount(self, parent=None):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return section + 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        product = self._products[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.ForegroundRole and column == 4:
            days_since = self._days_since_change(product)
            if days_since is None:
                return None
            if days_since > 365:
                return QColor(211, 47, 47)
            if days_since > 180:
                return QColor(255, 152, 0)
            if days_since > 90:
                return QColor(255, 193, 7)
            return QColor(76, 175, 80)

        if role == Qt.ItemDataRole.UserRole:
            if column == 3:
                return self._price_sort_value(product)
            if column == 4:
                days = self._days_since_change(product)
                return days if days is not None else 10**9
            return self._display_value(product, column)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_value(product, column)

        return None

    def product_at(self, row):
        if row < 0 or row >= len(self._products):
            return None
        return self._products[row]

    def _display_value(self, product, column):
        if column == 0:
            return product.get("id", "")
        if column == 1:
            return product.get("mehsulun_adi", "")
        if column == 2:
            return product.get("category", "") or "N/A"
        if column == 3:
            return self._price_display(product)
        if column == 4:
            days_since = self._days_since_change(product)
            return str(days_since) if days_since is not None else "N/A"
        if column == 5:
            return product.get("mehsul_menbeyi", "") or "N/A"
        if column == 6:
            return product.get("olcu_vahidi", "") or "N/A"
        if column == 7:
            return product.get("qeyd", "") or "N/A"
        return ""

    def _price_display(self, product):
        currency = product.get("currency", "AZN") or "AZN"
        price_value = product.get("price")
        if price_value is None:
            price_value = 0
        price = float(price_value)
        price_azn = product.get("price_azn")
        if price_azn is None:
            price_azn = self.currency_manager.convert_to_azn(price, currency)
        if currency == "AZN":
            return f"{price:.2f} AZN"
        return f"{price_azn:.2f} AZN ({price:.2f} {currency})"

    def _price_sort_value(self, product):
        currency = product.get("currency", "AZN") or "AZN"
        price_value = product.get("price")
        if price_value is None:
            price_value = 0
        price = float(price_value)
        price_azn = product.get("price_azn")
        if price_azn is None:
            price_azn = self.currency_manager.convert_to_azn(price, currency)
        return float(price_azn or 0)

    def _days_since_change(self, product):
        price_last_changed = product.get("price_last_changed")
        if not price_last_changed:
            return None
        if price_last_changed.tzinfo is None:
            price_last_changed = price_last_changed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - price_last_changed).days


class ProductFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_text = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_search_text(self, text):
        self._search_text = (text or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._search_text:
            return True
        model = self.sourceModel()
        product = model.product_at(source_row)
        if not product:
            return False
        haystacks = [
            product.get("id", ""),
            product.get("mehsulun_adi", ""),
            product.get("category", ""),
            product.get("mehsul_menbeyi", ""),
            product.get("qeyd", ""),
            product.get("olcu_vahidi", ""),
        ]
        joined = " ".join(str(value) for value in haystacks if value)
        return self._search_text in joined.lower()
