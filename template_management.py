"""Template management window implementation."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt

from dialogs import TemplateItemDialog, ProductSelectionDialog


class TemplateManagementWindow(QDialog):
    """Template Management Window - Create and manage generic templates with product mapping"""

    def __init__(self, parent=None, db=None, boq_window=None):
        super().__init__(parent)
        self.db = db
        self.boq_window = boq_window  # Reference to BoQWindow for loading items
        self.current_template_id = None
        self.template_items = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("📋 Şablon İdarəetməsi")
        self.setMinimumSize(900, 600)

        main_layout = QHBoxLayout()

        # Left panel - Template list
        left_panel = QVBoxLayout()

        templates_label = QLabel("Şablonlar")
        templates_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        left_panel.addWidget(templates_label)

        self.template_list = QTableWidget()
        self.template_list.setColumnCount(2)
        self.template_list.setHorizontalHeaderLabels(["Şablon Adı", "Qeyd Sayı"])
        self.template_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.template_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.template_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.template_list.clicked.connect(self.on_template_selected)
        self.template_list.setMaximumWidth(300)

        header = self.template_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        left_panel.addWidget(self.template_list)

        # Template list buttons
        template_btn_layout = QHBoxLayout()

        self.new_template_btn = QPushButton("➕ Yeni")
        self.new_template_btn.clicked.connect(self.create_new_template)
        self.new_template_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold;")

        self.delete_template_btn = QPushButton("🗑️ Sil")
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.delete_template_btn.setStyleSheet("background-color: #f44336; color: white; padding: 6px 12px; border: none; border-radius: 4px;")

        template_btn_layout.addWidget(self.new_template_btn)
        template_btn_layout.addWidget(self.delete_template_btn)
        left_panel.addLayout(template_btn_layout)

        main_layout.addLayout(left_panel)

        # Right panel - Template items
        right_panel = QVBoxLayout()

        # Template name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Şablon Adı:")
        name_label.setStyleSheet("font-weight: bold;")
        self.template_name_input = QLineEdit()
        self.template_name_input.setPlaceholderText("Şablon adını daxil edin")
        self.template_name_input.setStyleSheet("padding: 8px; font-size: 14px;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.template_name_input)
        right_panel.addLayout(name_layout)

        # Items table
        items_label = QLabel("Şablon Qeydləri")
        items_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        right_panel.addWidget(items_label)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Generik Ad", "Ölçü Vahidi", "Defolt Qiymət", "Tip"])
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        items_header = self.items_table.horizontalHeader()
        items_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        items_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        items_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        items_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        right_panel.addWidget(self.items_table)

        # Item buttons
        item_btn_layout = QHBoxLayout()

        self.add_generic_btn = QPushButton("➕ Generik Qeyd")
        self.add_generic_btn.clicked.connect(self.add_generic_item)
        self.add_generic_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;")
        self.add_generic_btn.setToolTip("Sərbəst generik qeyd əlavə et (məs: 'AC açar')")

        self.add_from_db_btn = QPushButton("📦 DB-dən Qeyd")
        self.add_from_db_btn.clicked.connect(self.add_item_from_db)
        self.add_from_db_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;")
        self.add_from_db_btn.setToolTip("Verilənlər bazasından məhsul seç")

        self.edit_item_btn = QPushButton("✏️ Redaktə")
        self.edit_item_btn.clicked.connect(self.edit_item)
        self.edit_item_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        self.delete_item_btn = QPushButton("🗑️ Sil")
        self.delete_item_btn.clicked.connect(self.delete_item)
        self.delete_item_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        item_btn_layout.addWidget(self.add_generic_btn)
        item_btn_layout.addWidget(self.add_from_db_btn)
        item_btn_layout.addWidget(self.edit_item_btn)
        item_btn_layout.addWidget(self.delete_item_btn)
        item_btn_layout.addStretch()

        right_panel.addLayout(item_btn_layout)

        # Save and Load to BoQ buttons
        action_btn_layout = QHBoxLayout()

        self.save_template_btn = QPushButton("💾 Şablonu Saxla")
        self.save_template_btn.clicked.connect(self.save_template)
        self.save_template_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; font-size: 14px;")

        self.load_to_boq_btn = QPushButton("📂 BoQ-a Yüklə")
        self.load_to_boq_btn.clicked.connect(self.load_to_boq)
        self.load_to_boq_btn.setStyleSheet("background-color: #673AB7; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; font-size: 14px;")

        action_btn_layout.addStretch()
        action_btn_layout.addWidget(self.save_template_btn)
        action_btn_layout.addWidget(self.load_to_boq_btn)

        right_panel.addLayout(action_btn_layout)

        main_layout.addLayout(right_panel)

        self.setLayout(main_layout)

        # Load existing templates
        self.refresh_template_list()

    def refresh_template_list(self):
        """Refresh the template list from database"""
        self.template_list.setRowCount(0)

        try:
            templates = self.db.get_all_templates()
            for template in templates:
                row = self.template_list.rowCount()
                self.template_list.insertRow(row)

                name_item = QTableWidgetItem(template['name'])
                name_item.setData(Qt.ItemDataRole.UserRole, template['id'])
                self.template_list.setItem(row, 0, name_item)

                item_count = len(template.get('items', []))
                self.template_list.setItem(row, 1, QTableWidgetItem(str(item_count)))
        except Exception as e:
            print(f"Error loading templates: {e}")

    def on_template_selected(self):
        """Load selected template into editor"""
        selected_row = self.template_list.currentRow()
        if selected_row < 0:
            return

        template_id = self.template_list.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        template_name = self.template_list.item(selected_row, 0).text()

        try:
            template = self.db.load_template(template_id)
            if template:
                self.current_template_id = template_id
                self.template_name_input.setText(template_name)
                self.template_items = template.get('items', [])
                self.refresh_items_table()
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Şablon yüklənərkən xəta: {str(e)}")

    def refresh_items_table(self):
        """Refresh the items table"""
        self.items_table.setRowCount(0)

        for item in self.template_items:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)

            self.items_table.setItem(row, 0, QTableWidgetItem(item.get('generic_name', item.get('name', ''))))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.get('unit', '')))
            default_price = item.get('default_price', item.get('unit_price', 0))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"{default_price:.2f}"))

            # Type: Generic or DB-linked
            item_type = "DB" if item.get('product_id') else "Generik"
            self.items_table.setItem(row, 3, QTableWidgetItem(item_type))

    def create_new_template(self):
        """Create a new empty template"""
        self.current_template_id = None
        self.template_name_input.setText("")
        self.template_name_input.setPlaceholderText("Yeni şablon adı")
        self.template_items = []
        self.refresh_items_table()

    def delete_template(self):
        """Delete selected template"""
        selected_row = self.template_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Silmək üçün şablon seçin!")
            return

        template_name = self.template_list.item(selected_row, 0).text()
        template_id = self.template_list.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self, "Təsdiq",
            f"'{template_name}' şablonunu silmək istədiyinizdən əminsiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_template(template_id)
                self.refresh_template_list()
                if self.current_template_id == template_id:
                    self.create_new_template()
                QMessageBox.information(self, "Uğurlu", "Şablon silindi!")
            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Şablon silinərkən xəta: {str(e)}")

    def add_generic_item(self):
        """Add a generic template item"""
        dialog = TemplateItemDialog(self, mode="generic")
        if dialog.exec():
            item_data = dialog.get_data()
            self.template_items.append(item_data)
            self.refresh_items_table()

    def add_item_from_db(self):
        """Add item from database as template item"""
        dialog = TemplateItemDialog(self, mode="from_db", db=self.db)
        if dialog.exec():
            item_data = dialog.get_data()
            self.template_items.append(item_data)
            self.refresh_items_table()

    def edit_item(self):
        """Edit selected item"""
        selected_row = self.items_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Redaktə etmək üçün qeyd seçin!")
            return

        item = self.template_items[selected_row]
        mode = "from_db" if item.get('product_id') else "generic"
        dialog = TemplateItemDialog(self, mode=mode, db=self.db, item=item)
        if dialog.exec():
            item_data = dialog.get_data()
            self.template_items[selected_row] = item_data
            self.refresh_items_table()

    def delete_item(self):
        """Delete selected item"""
        selected_row = self.items_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Silmək üçün qeyd seçin!")
            return

        del self.template_items[selected_row]
        self.refresh_items_table()

    def save_template(self):
        """Save current template"""
        template_name = self.template_name_input.text().strip()
        if not template_name:
            QMessageBox.warning(self, "Xəbərdarlıq", "Şablon adı boş ola bilməz!")
            return

        if not self.template_items:
            QMessageBox.warning(self, "Xəbərdarlıq", "Şablona ən azı bir qeyd əlavə edin!")
            return

        try:
            # Convert items format for saving
            items_to_save = []
            for item in self.template_items:
                items_to_save.append({
                    'generic_name': item.get('generic_name', ''),
                    'name': item.get('name', item.get('generic_name', '')),
                    'unit': item.get('unit', ''),
                    'default_price': item.get('default_price', 0),
                    'product_id': item.get('product_id'),
                    'category': item.get('category', ''),
                    'is_generic': not bool(item.get('product_id'))
                })

            self.db.save_template(template_name, items_to_save)
            self.refresh_template_list()
            QMessageBox.information(self, "Uğurlu", f"Şablon '{template_name}' olaraq saxlanıldı!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Şablon saxlanılarkən xəta: {str(e)}")

    def load_to_boq(self):
        """Load template items to BoQ with product selection for generic items"""
        if not self.template_items:
            QMessageBox.warning(self, "Xəbərdarlıq", "Şablonda heç bir qeyd yoxdur!")
            return

        if not self.boq_window:
            QMessageBox.warning(self, "Xəbərdarlıq", "BoQ pəncərəsi tapılmadı!")
            return

        # Ask about loading mode
        reply = QMessageBox.question(
            self, "Yükləmə Rejimi",
            "Mövcud BoQ qeydlərini əvəz etmək istəyirsiniz?\n\n'Bəli' - Əvəz et\n'Xeyr' - Mövcud qeydlərə əlavə et",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        replace_mode = (reply == QMessageBox.StandardButton.Yes)

        if replace_mode:
            self.boq_window.boq_items = []
            self.boq_window.next_id = 1

        # Process each template item
        items_added = 0
        for template_item in self.template_items:
            if template_item.get('is_generic') or not template_item.get('product_id'):
                # Generic item - show product selection dialog
                selected_product = self.select_product_for_generic(template_item)
                if selected_product:
                    new_item = self.create_boq_item_from_selection(template_item, selected_product)
                    self.boq_window.boq_items.append(new_item)
                    self.boq_window.next_id += 1
                    items_added += 1
            else:
                # DB-linked item - get current data from DB
                product = self.db.read_product(template_item.get('product_id'))
                if product:
                    new_item = {
                        'id': self.boq_window.next_id,
                        'name': product['mehsulun_adi'],
                        'quantity': 1,
                        'unit': product.get('olcu_vahidi', '') or 'ədəd',
                        'unit_price': float(product['price']) if product.get('price') else 0,
                        'total': float(product['price']) if product.get('price') else 0,
                        'margin_percent': 0,
                        'category': product.get('category', ''),
                        'source': product.get('mehsul_menbeyi', ''),
                        'note': '',
                        'is_custom': False,
                        'product_id': template_item.get('product_id')
                    }
                    self.boq_window.boq_items.append(new_item)
                    self.boq_window.next_id += 1
                    items_added += 1

        self.boq_window.refresh_table()
        QMessageBox.information(self, "Uğurlu", f"{items_added} qeyd BoQ-a əlavə edildi!")
        self.accept()

    def select_product_for_generic(self, template_item):
        """Show dialog to select a product for a generic template item"""
        dialog = ProductSelectionDialog(
            self,
            self.db,
            template_item.get('generic_name', ''),
            template_item.get('category', '')
        )
        if dialog.exec():
            return dialog.get_selected_product()
        return None

    def create_boq_item_from_selection(self, template_item, product):
        """Create a BoQ item from template item and selected product"""
        return {
            'id': self.boq_window.next_id,
            'name': product['mehsulun_adi'],
            'quantity': 1,
            'unit': product.get('olcu_vahidi', '') or template_item.get('unit', 'ədəd'),
            'unit_price': float(product['price']) if product.get('price') else template_item.get('default_price', 0),
            'total': float(product['price']) if product.get('price') else template_item.get('default_price', 0),
            'margin_percent': 0,
            'category': product.get('category', ''),
            'source': product.get('mehsul_menbeyi', ''),
            'note': f"Şablondan: {template_item.get('generic_name', '')}",
            'is_custom': False,
            'product_id': str(product['_id'])
        }
