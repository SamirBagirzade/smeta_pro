"""Template management window implementation."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLineEdit, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QSettings
import ast
import math
import re

from dialogs import TemplateItemDialog, ProductSelectionDialog, _parse_calc_text


def _extract_expr_names(expr):
    if not expr:
        return set()
    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        return set()
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _is_valid_variable_name(name):
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name or ""))


class TemplateManagementWindow(QDialog):
    """Template Management Window - Create and manage generic templates with product mapping"""

    def __init__(self, parent=None, db=None, boq_window=None):
        super().__init__(parent)
        self.db = db
        self.boq_window = boq_window  # Reference to SmetaWindow for loading items
        self.current_template_id = None
        self.template_items = []
        
        # Column width preferences
        self.settings = QSettings("SmetaPro", "TemplateManagementWindow")
        self.template_column_widths = {}
        self.template_column_min_widths = {}
        self.items_column_widths = {}
        self.items_column_min_widths = {}
        # Load saved widths
        for i in range(2):  # Template list: 2 columns
            width = self.settings.value(f"template_column_width_{i}", type=int)
            if width:
                self.template_column_widths[i] = width
        for i in range(6):  # Items table: 6 columns
            width = self.settings.value(f"items_column_width_{i}", type=int)
            if width:
                self.items_column_widths[i] = width
        
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
        # Set interactive resizing
        for i in range(self.template_list.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Set default column widths and minimums
        default_widths = [150, 80]  # Name, Count
        for i, width in enumerate(default_widths):
            self.template_column_min_widths[i] = width
            header.setMinimumSectionSize(width)
            if i in self.template_column_widths:
                header.resizeSection(i, self.template_column_widths[i])
            else:
                header.resizeSection(i, width)
        
        # Connect resize signal
        header.sectionResized.connect(self.on_template_column_resized)

        left_panel.addWidget(self.template_list)

        # Template list buttons
        template_btn_layout = QHBoxLayout()

        self.new_template_btn = QPushButton("➕ Yeni")
        self.new_template_btn.clicked.connect(self.create_new_template)
        self.new_template_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold;")

        self.delete_template_btn = QPushButton("🗑️ Sil")
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.delete_template_btn.setStyleSheet("background-color: #f44336; color: white; padding: 6px 12px; border: none; border-radius: 4px;")

        self.copy_template_btn = QPushButton("📄 Kopyala")
        self.copy_template_btn.clicked.connect(self.copy_template)
        self.copy_template_btn.setStyleSheet("background-color: #607D8B; color: white; padding: 6px 12px; border: none; border-radius: 4px;")

        self.rename_template_btn = QPushButton("✏️ Adını Dəyiş")
        self.rename_template_btn.clicked.connect(self.rename_template)
        self.rename_template_btn.setStyleSheet("background-color: #5D4037; color: white; padding: 6px 12px; border: none; border-radius: 4px;")

        template_btn_layout.addWidget(self.new_template_btn)
        template_btn_layout.addWidget(self.copy_template_btn)
        template_btn_layout.addWidget(self.rename_template_btn)
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
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["Generik Ad", "Dəyişən", "Miqdar", "Ölçü Vahidi", "Defolt Qiymət", "Tip"]
        )
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        items_header = self.items_table.horizontalHeader()
        # Set interactive resizing
        for i in range(self.items_table.columnCount()):
            items_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Set default column widths and minimums
        default_widths = [150, 100, 80, 80, 100, 80]  # Generic Name, Variable, Amount, Unit, Price, Type
        for i, width in enumerate(default_widths):
            self.items_column_min_widths[i] = width
            items_header.setMinimumSectionSize(width)
            if i in self.items_column_widths:
                items_header.resizeSection(i, self.items_column_widths[i])
            else:
                items_header.resizeSection(i, width)
        
        # Connect resize signal
        items_header.sectionResized.connect(self.on_items_column_resized)

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

        self.move_up_btn = QPushButton("⬆️ Yuxarı")
        self.move_up_btn.clicked.connect(self.move_item_up)
        self.move_up_btn.setStyleSheet("background-color: #607D8B; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        self.move_down_btn = QPushButton("⬇️ Aşağı")
        self.move_down_btn.clicked.connect(self.move_item_down)
        self.move_down_btn.setStyleSheet("background-color: #607D8B; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        self.delete_item_btn = QPushButton("🗑️ Sil")
        self.delete_item_btn.clicked.connect(self.delete_item)
        self.delete_item_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        item_btn_layout.addWidget(self.add_generic_btn)
        item_btn_layout.addWidget(self.add_from_db_btn)
        item_btn_layout.addWidget(self.edit_item_btn)
        item_btn_layout.addWidget(self.move_up_btn)
        item_btn_layout.addWidget(self.move_down_btn)
        item_btn_layout.addWidget(self.delete_item_btn)
        item_btn_layout.addStretch()

        right_panel.addLayout(item_btn_layout)

        # Save and Load to Smeta buttons
        action_btn_layout = QHBoxLayout()

        self.save_template_btn = QPushButton("💾 Şablonu Saxla")
        self.save_template_btn.clicked.connect(self.save_template)
        self.save_template_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; font-size: 14px;")

        self.load_to_boq_btn = QPushButton("📂 Smeta-a Yüklə")
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
            self.items_table.setItem(row, 1, QTableWidgetItem(item.get('var_name', '') or ''))
            amount_expr = item.get('amount_expr')
            if amount_expr is None:
                amount_expr = item.get('amount', 1)
            self.items_table.setItem(row, 2, QTableWidgetItem(str(amount_expr)))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.get('unit', '')))

            price_expr = item.get('price_expr', '')
            default_price = item.get('default_price', item.get('unit_price', 0))
            currency = item.get('currency', 'AZN') or 'AZN'
            default_price_azn = item.get('default_price_azn')
            if price_expr:
                price_text = price_expr
            elif item.get('product_id'):
                price_text = "DB qiyməti"
            else:
                if default_price_azn is None:
                    default_price_azn = default_price if currency == 'AZN' else 0
                if currency == "AZN":
                    price_text = f"{default_price:.2f} AZN"
                else:
                    price_text = f"AZN {default_price_azn:.2f} ({default_price:.2f} {currency})"
            self.items_table.setItem(row, 4, QTableWidgetItem(price_text))

            # Type: Generic or DB-linked
            item_type = "DB" if item.get('product_id') else "Generik"
            self.items_table.setItem(row, 5, QTableWidgetItem(item_type))

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
        dialog = ProductSelectionDialog(self, self.db, "", "")
        if dialog.exec():
            product = dialog.get_selected_product()
            if not product:
                return
            unit_price = float(product['price']) if product.get('price') else 0
            currency = product.get('currency', 'AZN') or 'AZN'
            unit_price_azn = product.get('price_azn')
            if unit_price_azn is None:
                unit_price_azn = self.boq_window.currency_manager.convert_to_azn(unit_price, currency) if self.boq_window else unit_price
            item_data = {
                'generic_name': product.get('mehsulun_adi', ''),
                'name': product.get('mehsulun_adi', ''),
                'var_name': '',
                'amount_expr': '1',
                'price_expr': '',
                'category': product.get('category', ''),
                'unit': product.get('olcu_vahidi', '') or 'ədəd',
                'default_price': unit_price,
                'currency': currency,
                'default_price_azn': unit_price_azn,
                'product_id': str(product.get('_id')) if product.get('_id') else None,
                'is_generic': False
            }
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

    def move_item_up(self):
        """Move selected item up in the list"""
        selected_row = self.items_table.currentRow()
        if selected_row <= 0:
            return
        self.template_items[selected_row - 1], self.template_items[selected_row] = (
            self.template_items[selected_row],
            self.template_items[selected_row - 1],
        )
        self.refresh_items_table()
        self.items_table.selectRow(selected_row - 1)

    def move_item_down(self):
        """Move selected item down in the list"""
        selected_row = self.items_table.currentRow()
        if selected_row < 0 or selected_row >= len(self.template_items) - 1:
            return
        self.template_items[selected_row + 1], self.template_items[selected_row] = (
            self.template_items[selected_row],
            self.template_items[selected_row + 1],
        )
        self.refresh_items_table()
        self.items_table.selectRow(selected_row + 1)

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
            used_vars = {}
            for item in self.template_items:
                var_name = (item.get('var_name') or '').strip()
                if not var_name:
                    continue
                if var_name.lower() == "string":
                    QMessageBox.warning(self, "Xəbərdarlıq", "Dəyişən adı 'string' ola bilməz!")
                    return
                if not _is_valid_variable_name(var_name):
                    QMessageBox.warning(self, "Xəbərdarlıq", f"Yanlış dəyişən adı: {var_name}")
                    return
                key = var_name.lower()
                if key in used_vars:
                    QMessageBox.warning(self, "Xəbərdarlıq", f"Təkrarlanan dəyişən adı: {var_name}")
                    return
                used_vars[key] = True

            # Convert items format for saving
            items_to_save = []
            for item in self.template_items:
                items_to_save.append({
                    'generic_name': item.get('generic_name', ''),
                    'name': item.get('name', item.get('generic_name', '')),
                    'var_name': item.get('var_name', ''),
                    'amount_expr': item.get('amount_expr', '1'),
                    'price_expr': item.get('price_expr', ''),
                    'amount_round': bool(item.get('amount_round')),
                    'price_round': bool(item.get('price_round')),
                    'unit': item.get('unit', ''),
                    'default_price': item.get('default_price', 0),
                    'currency': item.get('currency', 'AZN') or 'AZN',
                    'default_price_azn': item.get('default_price_azn'),
                    'product_id': item.get('product_id'),
                    'category': item.get('category', ''),
                    'is_generic': not bool(item.get('product_id'))
                })

            self.db.save_template(template_name, items_to_save)
            self.refresh_template_list()
            QMessageBox.information(self, "Uğurlu", f"Şablon '{template_name}' olaraq saxlanıldı!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Şablon saxlanılarkən xəta: {str(e)}")

    def copy_template(self):
        """Copy selected template to a new one"""
        selected_row = self.template_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Kopyalamaq üçün şablon seçin!")
            return

        template_id = self.template_list.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        template_name = self.template_list.item(selected_row, 0).text()

        try:
            template = self.db.load_template(template_id)
            if not template:
                QMessageBox.warning(self, "Xəbərdarlıq", "Şablon tapılmadı!")
                return

            new_name = self._generate_copy_name(template_name)
            items = template.get('items', [])
            self.db.save_template(new_name, items)
            self.refresh_template_list()
            self._select_template_by_name(new_name)
            QMessageBox.information(self, "Uğurlu", f"Şablon '{new_name}' olaraq kopyalandı!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Şablon kopyalanarkən xəta: {str(e)}")

    def rename_template(self):
        """Rename selected template"""
        selected_row = self.template_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Ad dəyişmək üçün şablon seçin!")
            return

        template_id = self.template_list.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        template_name = self.template_list.item(selected_row, 0).text()

        new_name, ok = QInputDialog.getText(
            self,
            "Şablon Adını Dəyiş",
            "Yeni şablon adı:",
            text=template_name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "Xəbərdarlıq", "Şablon adı boş ola bilməz!")
            return

        try:
            template = self.db.load_template(template_id)
            if not template:
                QMessageBox.warning(self, "Xəbərdarlıq", "Şablon tapılmadı!")
                return

            items = template.get('items', [])
            self.db.save_template(new_name, items)
            self.db.delete_template(template_id)
            self.refresh_template_list()
            self._select_template_by_name(new_name)
            QMessageBox.information(self, "Uğurlu", f"Şablon '{new_name}' olaraq dəyişdirildi!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Şablonun adı dəyişdirilə bilmədi: {str(e)}")

    def _generate_copy_name(self, base_name):
        try:
            templates = self.db.get_all_templates()
        except Exception:
            templates = []
        existing = {t.get('name', '') for t in templates}
        suffix = " (kopya)"
        candidate = f"{base_name}{suffix}"
        counter = 2
        while candidate in existing:
            candidate = f"{base_name}{suffix} {counter}"
            counter += 1
        return candidate

    def _select_template_by_name(self, name):
        for row in range(self.template_list.rowCount()):
            item = self.template_list.item(row, 0)
            if item and item.text() == name:
                self.template_list.selectRow(row)
                self.on_template_selected()
                return

    def load_to_boq(self):
        """Load template items to Smeta with product selection for generic items"""
        if not self.template_items:
            QMessageBox.warning(self, "Xəbərdarlıq", "Şablonda heç bir qeyd yoxdur!")
            return

        if not self.boq_window:
            QMessageBox.warning(self, "Xəbərdarlıq", "Smeta pəncərəsi tapılmadı!")
            return

        # Ask about loading mode
        reply = QMessageBox.question(
            self, "Yükləmə Rejimi",
            "Mövcud Smeta qeydlərini əvəz etmək istəyirsiniz?\n\n'Bəli' - Əvəz et\n'Xeyr' - Mövcud qeydlərə əlavə et",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        replace_mode = (reply == QMessageBox.StandardButton.Yes)

        if replace_mode:
            self.boq_window.boq_items = []
            self.boq_window.next_id = 1

        variables = {"string": int(self.boq_window.string_count or 0)}
        resolved = {}
        pending = list(enumerate(self.template_items))
        errors = []
        progress = True
        while pending and progress:
            progress = False
            next_pending = []
            for idx, item in pending:
                amount_expr = item.get('amount_expr')
                if amount_expr is None:
                    amount_expr = item.get('amount', 1)
                amount_expr = str(amount_expr).strip() if amount_expr is not None else "1"
                names = _extract_expr_names(amount_expr)
                if names - set(variables.keys()):
                    next_pending.append((idx, item))
                    continue
                amount_value = _parse_calc_text(amount_expr, variables)
                if amount_value is None:
                    label = item.get('generic_name', item.get('name', ''))
                    errors.append(f"{label}: miqdar ifadəsi səhvdir")
                    amount_value = 1
                amount_value = max(0.01, float(amount_value))
                if item.get('amount_round'):
                    amount_value = float(math.ceil(amount_value))
                var_name = (item.get('var_name') or '').strip()
                if var_name and var_name.lower() != "string":
                    variables[var_name] = amount_value
                resolved[idx] = {'amount': amount_value}
                progress = True
            pending = next_pending

        for idx, item in pending:
            amount_expr = item.get('amount_expr')
            if amount_expr is None:
                amount_expr = item.get('amount', 1)
            amount_expr = str(amount_expr).strip() if amount_expr is not None else "1"
            missing = _extract_expr_names(amount_expr) - set(variables.keys())
            label = item.get('generic_name', item.get('name', ''))
            if missing:
                errors.append(f"{label}: tapılmayan dəyişənlər: {', '.join(sorted(missing))}")
            resolved[idx] = {'amount': 1.0}

        for idx, item in enumerate(self.template_items):
            price_expr = (item.get('price_expr') or '').strip()
            price_value = None
            if price_expr:
                names = _extract_expr_names(price_expr)
                missing = names - set(variables.keys())
                if missing:
                    label = item.get('generic_name', item.get('name', ''))
                    errors.append(
                        f"{label}: qiymət ifadəsində dəyişən tapılmadı: {', '.join(sorted(missing))}"
                    )
                else:
                    price_value = _parse_calc_text(price_expr, variables)
                    if price_value is None:
                        label = item.get('generic_name', item.get('name', ''))
                        errors.append(f"{label}: qiymət ifadəsi səhvdir")
                    elif item.get('price_round'):
                        price_value = float(math.ceil(price_value))
            resolved[idx]['price'] = price_value

        # Process each template item
        items_added = 0
        skip_remaining_generic = False
        for idx, template_item in enumerate(self.template_items):
            amount_value = resolved.get(idx, {}).get('amount', 1.0)
            price_override = resolved.get(idx, {}).get('price')
            if template_item.get('is_generic') or not template_item.get('product_id'):
                # Generic item - show product selection dialog
                selected_product = None
                if not skip_remaining_generic:
                    selected_product, skip_remaining_generic = self.select_product_for_generic(template_item)
                if selected_product:
                    new_item = self.create_boq_item_from_selection(
                        template_item,
                        selected_product,
                        amount_value=amount_value,
                        price_override=price_override,
                    )
                    self.boq_window.boq_items.append(new_item)
                    self.boq_window.next_id += 1
                    items_added += 1
                else:
                    currency = template_item.get('currency', 'AZN') or 'AZN'
                    unit_price = price_override if price_override is not None else template_item.get('default_price', 0)
                    unit_price_azn = template_item.get('default_price_azn')
                    if unit_price_azn is None:
                        unit_price_azn = self.boq_window.currency_manager.convert_to_azn(unit_price, currency)
                    total = amount_value * float(unit_price_azn)
                    new_item = {
                        'id': self.boq_window.next_id,
                        'name': template_item.get('generic_name', '') or template_item.get('name', ''),
                        'quantity': amount_value,
                        'unit': template_item.get('unit', 'ədəd'),
                        'unit_price': unit_price,
                        'currency': currency,
                        'unit_price_azn': unit_price_azn,
                        'total': total,
                        'margin_percent': 0,
                        'category': template_item.get('category', ''),
                        'source': '',
                        'note': self._build_template_note(template_item=template_item),
                        'is_custom': True,
                        'product_id': None,
                        'quantity_round': bool(template_item.get('amount_round')),
                        'price_round': bool(template_item.get('price_round'))
                    }
                    self.boq_window.boq_items.append(new_item)
                    self.boq_window.next_id += 1
                    items_added += 1
            else:
                # DB-linked item - get current data from DB
                product = self.db.read_product(template_item.get('product_id'))
                if product:
                    currency = product.get('currency', 'AZN') or 'AZN'
                    if price_override is not None:
                        unit_price = float(price_override)
                    else:
                        unit_price = float(product['price']) if product.get('price') else 0
                    unit_price_azn = product.get('price_azn')
                    if unit_price_azn is None:
                        unit_price_azn = self.boq_window.currency_manager.convert_to_azn(unit_price, currency)
                    total = amount_value * float(unit_price_azn)
                    new_item = {
                        'id': self.boq_window.next_id,
                        'name': product['mehsulun_adi'],
                        'quantity': amount_value,
                        'unit': product.get('olcu_vahidi', '') or 'ədəd',
                        'unit_price': unit_price,
                        'currency': currency,
                        'unit_price_azn': unit_price_azn,
                        'total': total,
                        'margin_percent': 0,
                        'category': product.get('category', ''),
                        'source': product.get('mehsul_menbeyi', ''),
                        'note': self._build_template_note(template_item=template_item, product=product),
                        'is_custom': False,
                        'product_id': template_item.get('product_id'),
                        'quantity_round': bool(template_item.get('amount_round')),
                        'price_round': bool(template_item.get('price_round'))
                    }
                    self.boq_window.boq_items.append(new_item)
                    self.boq_window.next_id += 1
                    items_added += 1

        self.boq_window.refresh_table()
        if errors:
            QMessageBox.warning(self, "Xəbərdarlıq", "Bəzi ifadələr qiymətləndirilə bilmədi:\n" + "\n".join(errors[:8]))
        QMessageBox.information(self, "Uğurlu", f"{items_added} qeyd Smeta-a əlavə edildi!")
        self.accept()

    def select_product_for_generic(self, template_item):
        """Show dialog to select a product for a generic template item"""
        label = template_item.get('generic_name') or template_item.get('name', '') or "Generik qeyd"
        dialog = ProductSelectionDialog(
            self,
            self.db,
            label,
            template_item.get('category', '')
        )
        if dialog.exec():
            return dialog.get_selected_product(), False
        return None, bool(getattr(dialog, "skip_all", False))

    def _build_template_note(self, template_item=None, product=None):
        note = ""
        if product:
            note = (product.get('qeyd') or '').strip()
        if not note and template_item:
            note = (template_item.get('note') or '').strip()
        if not note and template_item:
            note = (template_item.get('generic_name') or template_item.get('name') or '').strip()
        if not note and product:
            note = (product.get('mehsulun_adi') or '').strip()
        if not note:
            note = "Qeyd yoxdur"
        return f"Şablondan: {note}"

    def create_boq_item_from_selection(self, template_item, product, amount_value=1.0, price_override=None):
        """Create a Smeta item from template item and selected product"""
        currency = product.get('currency', template_item.get('currency', 'AZN')) or 'AZN'
        if price_override is not None:
            unit_price = float(price_override)
        else:
            unit_price = float(product['price']) if product.get('price') else template_item.get('default_price', 0)
        unit_price_azn = product.get('price_azn', template_item.get('default_price_azn'))
        if unit_price_azn is None:
            unit_price_azn = self.boq_window.currency_manager.convert_to_azn(unit_price, currency)
        return {
            'id': self.boq_window.next_id,
            'name': product['mehsulun_adi'],
            'quantity': amount_value,
            'unit': product.get('olcu_vahidi', '') or template_item.get('unit', 'ədəd'),
            'unit_price': unit_price,
            'currency': currency,
            'unit_price_azn': unit_price_azn,
            'total': float(unit_price_azn) * amount_value,
            'margin_percent': 0,
            'category': product.get('category', ''),
            'source': product.get('mehsul_menbeyi', ''),
            'note': self._build_template_note(template_item=template_item, product=product),
            'is_custom': False,
            'product_id': str(product['_id']),
            'quantity_round': bool(template_item.get('amount_round')),
            'price_round': bool(template_item.get('price_round'))
        }

    def on_template_column_resized(self, logicalIndex, oldSize, newSize):
        """Handle template list column resize"""
        min_width = self.template_column_min_widths.get(logicalIndex, 50)
        if newSize < min_width:
            header = self.template_list.horizontalHeader()
            header.resizeSection(logicalIndex, min_width)
            newSize = min_width
        self.template_column_widths[logicalIndex] = newSize
        self.settings.setValue(f"template_column_width_{logicalIndex}", newSize)

    def on_items_column_resized(self, logicalIndex, oldSize, newSize):
        """Handle items table column resize"""
        min_width = self.items_column_min_widths.get(logicalIndex, 50)
        if newSize < min_width:
            header = self.items_table.horizontalHeader()
            header.resizeSection(logicalIndex, min_width)
            newSize = min_width
        self.items_column_widths[logicalIndex] = newSize
        self.settings.setValue(f"items_column_width_{logicalIndex}", newSize)
