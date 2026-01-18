"""Project management window implementation."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QDialog,
    QFormLayout, QLineEdit, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ProjectWindow(QMainWindow):
    """Project Management Window"""

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db = db
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("📁 Layihə İdarəetməsi")
        self.setGeometry(200, 200, 900, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Title
        title = QLabel("Layihə İdarəetməsi")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2196F3; padding: 10px;")
        main_layout.addWidget(title)

        # Projects table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Layihə Adı", "Təsvir", "Status", "Smeta Sayı", "Yenilənmə"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.cellDoubleClicked.connect(self.view_project_details)
        main_layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.new_btn = QPushButton("➕ Yeni Layihə")
        self.new_btn.clicked.connect(self.create_project)
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
        """)

        self.edit_btn = QPushButton("✏️ Redaktə Et")
        self.edit_btn.clicked.connect(self.edit_project)
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
            QPushButton:hover { background-color: #0b7dda; }
        """)

        self.delete_btn = QPushButton("🗑️ Sil")
        self.delete_btn.clicked.connect(self.delete_project)
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
            QPushButton:hover { background-color: #da190b; }
        """)

        self.view_boqs_btn = QPushButton("📋 Smeta-ları Gör")
        self.view_boqs_btn.clicked.connect(self.view_project_boqs)
        self.view_boqs_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7B1FA2; }
        """)

        self.add_boq_btn = QPushButton("➕ Smeta Əlavə Et")
        self.add_boq_btn.clicked.connect(self.add_boq_to_project)
        self.add_boq_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e68900; }
        """)

        self.refresh_btn = QPushButton("🔄 Yenilə")
        self.refresh_btn.clicked.connect(self.load_projects)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #546E7A; }
        """)

        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.view_boqs_btn)
        button_layout.addWidget(self.add_boq_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Summary label
        self.summary_label = QLabel("Layihələr yüklənir...")
        self.summary_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        main_layout.addWidget(self.summary_label)

        central_widget.setLayout(main_layout)

        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QTableWidget { background-color: white; border: 1px solid #ddd; border-radius: 5px; }
        """)

        self.load_projects()

    def load_projects(self):
        """Load all projects into the table"""
        if not self.db:
            return

        try:
            projects = self.db.get_all_projects()
            self.table.setRowCount(0)

            for project in projects:
                row = self.table.rowCount()
                self.table.insertRow(row)

                name_item = QTableWidgetItem(project['name'])
                name_item.setData(Qt.ItemDataRole.UserRole, project['id'])
                self.table.setItem(row, 0, name_item)

                self.table.setItem(row, 1, QTableWidgetItem(project.get('description', '')))
                self.table.setItem(row, 2, QTableWidgetItem(project.get('status', 'Aktiv')))
                self.table.setItem(row, 3, QTableWidgetItem(str(len(project.get('boq_ids', [])))))

                updated_at = project.get('updated_at')
                if updated_at and hasattr(updated_at, 'astimezone'):
                    date_str = updated_at.astimezone().strftime("%d.%m.%Y %H:%M")
                else:
                    date_str = "N/A"
                self.table.setItem(row, 4, QTableWidgetItem(date_str))

            self.summary_label.setText(f"Cəmi {len(projects)} layihə tapıldı")

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Layihələr yüklənərkən xəta:\n{str(e)}")

    def create_project(self):
        """Create a new project"""
        if not self.db:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Yeni Layihə")
        dialog.setMinimumWidth(400)

        layout = QFormLayout()

        name_input = QLineEdit()
        name_input.setStyleSheet("padding: 8px;")
        layout.addRow("Layihə Adı:", name_input)

        desc_input = QTextEdit()
        desc_input.setMaximumHeight(100)
        layout.addRow("Təsvir:", desc_input)

        from PyQt6.QtWidgets import QComboBox
        status_combo = QComboBox()
        status_combo.addItems(["Aktiv", "Gözləmədə", "Tamamlandı", "Ləğv edildi"])
        layout.addRow("Status:", status_combo)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Saxla")
        cancel_btn = QPushButton("❌ Ləğv Et")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
        cancel_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Xəbərdarlıq", "Layihə adı boş ola bilməz!")
                return

            try:
                self.db.create_project(name, desc_input.toPlainText(), status_combo.currentText())
                self.load_projects()
                QMessageBox.information(self, "Uğurlu", f"Layihə '{name}' yaradıldı!")
            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Layihə yaradılarkən xəta:\n{str(e)}")

    def edit_project(self):
        """Edit selected project"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Redaktə etmək üçün layihə seçin!")
            return

        project_id = self.table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        project = self.db.get_project(project_id)

        if not project:
            QMessageBox.warning(self, "Xəbərdarlıq", "Layihə tapılmadı!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Layihəni Redaktə Et")
        dialog.setMinimumWidth(400)

        layout = QFormLayout()

        name_input = QLineEdit(project['name'])
        name_input.setStyleSheet("padding: 8px;")
        layout.addRow("Layihə Adı:", name_input)

        desc_input = QTextEdit()
        desc_input.setPlainText(project.get('description', ''))
        desc_input.setMaximumHeight(100)
        layout.addRow("Təsvir:", desc_input)

        from PyQt6.QtWidgets import QComboBox
        status_combo = QComboBox()
        status_combo.addItems(["Aktiv", "Gözləmədə", "Tamamlandı", "Ləğv edildi"])
        current_status = project.get('status', 'Aktiv')
        index = status_combo.findText(current_status)
        if index >= 0:
            status_combo.setCurrentIndex(index)
        layout.addRow("Status:", status_combo)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Saxla")
        cancel_btn = QPushButton("❌ Ləğv Et")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
        cancel_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Xəbərdarlıq", "Layihə adı boş ola bilməz!")
                return

            try:
                self.db.update_project(project_id, name, desc_input.toPlainText(), status_combo.currentText())
                self.load_projects()
                QMessageBox.information(self, "Uğurlu", "Layihə yeniləndi!")
            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Layihə yenilənərkən xəta:\n{str(e)}")

    def delete_project(self):
        """Delete selected project"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Silmək üçün layihə seçin!")
            return

        project_name = self.table.item(selected_row, 0).text()
        project_id = self.table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self, "Təsdiq",
            f"'{project_name}' layihəsini silmək istədiyinizdən əminsiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_project(project_id)
                self.load_projects()
                QMessageBox.information(self, "Uğurlu", "Layihə silindi!")
            except Exception as e:
                QMessageBox.critical(self, "Xəta", f"Layihə silinərkən xəta:\n{str(e)}")

    def view_project_details(self, row, column):
        """View project details on double-click"""
        self.view_project_boqs()

    def view_project_boqs(self):
        """View Smetas in selected project"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Layihə seçin!")
            return

        project_id = self.table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        project_name = self.table.item(selected_row, 0).text()
        project = self.db.get_project(project_id)

        if not project:
            return

        boq_ids = project.get('boq_ids', [])

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Layihə Smeta-ları: {project_name}")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Info label
        layout.addWidget(QLabel(f"Layihədəki Smeta-lar ({len(boq_ids)}):"))

        # Smeta table
        boq_table = QTableWidget()
        boq_table.setColumnCount(3)
        boq_table.setHorizontalHeaderLabels(["Smeta Adı", "Qeyd Sayı", "Ümumi Məbləğ"])
        boq_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        boq_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = boq_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        total_project_amount = 0

        for boq_id in boq_ids:
            try:
                boq = self.db.load_boq_from_cloud(boq_id)
                if boq:
                    row = boq_table.rowCount()
                    boq_table.insertRow(row)

                    name_item = QTableWidgetItem(boq['name'])
                    name_item.setData(Qt.ItemDataRole.UserRole, boq_id)
                    boq_table.setItem(row, 0, name_item)

                    items = boq.get('items', [])
                    boq_table.setItem(row, 1, QTableWidgetItem(str(len(items))))

                    boq_total = sum(
                        item.get('total', 0) * (1 + item.get('margin_percent', 0) / 100)
                        for item in items
                    )
                    total_project_amount += boq_total
                    boq_table.setItem(row, 2, QTableWidgetItem(f"{boq_total:.2f} AZN"))
            except Exception:
                pass

        layout.addWidget(boq_table)

        # Total
        total_label = QLabel(f"Layihənin Ümumi Məbləği: {total_project_amount:.2f} AZN")
        total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50; padding: 10px;")
        layout.addWidget(total_label)

        # Remove button
        button_layout = QHBoxLayout()

        remove_btn = QPushButton("🗑️ Seçilmiş Smeta-u Çıxar")
        remove_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

        def remove_selected():
            sel_row = boq_table.currentRow()
            if sel_row >= 0:
                boq_id_to_remove = boq_table.item(sel_row, 0).data(Qt.ItemDataRole.UserRole)
                try:
                    self.db.remove_boq_from_project(project_id, boq_id_to_remove)
                    boq_table.removeRow(sel_row)
                    self.load_projects()
                    QMessageBox.information(dialog, "Uğurlu", "Smeta layihədən çıxarıldı!")
                except Exception as e:
                    QMessageBox.critical(dialog, "Xəta", str(e))

        remove_btn.clicked.connect(remove_selected)
        button_layout.addWidget(remove_btn)

        close_btn = QPushButton("❌ Bağla")
        close_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def add_boq_to_project(self):
        """Add a cloud Smeta to selected project"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Əvvəlcə layihə seçin!")
            return

        project_id = self.table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        project_name = self.table.item(selected_row, 0).text()
        project = self.db.get_project(project_id)

        if not project:
            return

        try:
            all_boqs = self.db.get_all_cloud_boqs()
            existing_boq_ids = project.get('boq_ids', [])

            # Filter out already added Smetas
            available_boqs = [b for b in all_boqs if b['id'] not in existing_boq_ids]

            if not available_boqs:
                QMessageBox.information(self, "Məlumat", "Əlavə etmək üçün Smeta yoxdur. Bütün Smeta-lar artıq layihədədir.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Smeta Əlavə Et: {project_name}")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(350)

            layout = QVBoxLayout()
            layout.addWidget(QLabel("Əlavə etmək istədiyiniz Smeta-u seçin:"))

            boq_table = QTableWidget()
            boq_table.setColumnCount(3)
            boq_table.setHorizontalHeaderLabels(["Smeta Adı", "Qeyd Sayı", "Yenilənmə"])
            boq_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            boq_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            boq_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

            header = boq_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

            for boq in available_boqs:
                row = boq_table.rowCount()
                boq_table.insertRow(row)

                name_item = QTableWidgetItem(boq['name'])
                name_item.setData(Qt.ItemDataRole.UserRole, boq['id'])
                boq_table.setItem(row, 0, name_item)

                boq_table.setItem(row, 1, QTableWidgetItem(str(len(boq.get('items', [])))))

                updated_at = boq.get('updated_at')
                if updated_at and hasattr(updated_at, 'astimezone'):
                    date_str = updated_at.astimezone().strftime("%d.%m.%Y")
                else:
                    date_str = "N/A"
                boq_table.setItem(row, 2, QTableWidgetItem(date_str))

            layout.addWidget(boq_table)

            button_layout = QHBoxLayout()
            add_btn = QPushButton("➕ Əlavə Et")
            cancel_btn = QPushButton("❌ Ləğv Et")
            add_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px;")
            cancel_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 8px 16px; border: none; border-radius: 4px;")

            selected_boq = [None]

            def on_add():
                sel_row = boq_table.currentRow()
                if sel_row >= 0:
                    selected_boq[0] = boq_table.item(sel_row, 0).data(Qt.ItemDataRole.UserRole)
                    dialog.accept()

            add_btn.clicked.connect(on_add)
            cancel_btn.clicked.connect(dialog.reject)
            boq_table.cellDoubleClicked.connect(lambda: on_add())

            button_layout.addWidget(add_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted and selected_boq[0]:
                self.db.add_boq_to_project(project_id, selected_boq[0])
                self.load_projects()
                QMessageBox.information(self, "Uğurlu", "Smeta layihəyə əlavə edildi!")

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Smeta əlavə edilərkən xəta:\n{str(e)}")
