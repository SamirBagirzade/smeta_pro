"""Settings dialog for currency rates."""

from datetime import timezone

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QLabel, QDoubleSpinBox,
    QHBoxLayout, QPushButton, QMessageBox, QVBoxLayout
)

from currency_settings import CurrencySettingsManager


class CurrencySettingsDialog(QDialog):
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.manager = CurrencySettingsManager(db)
        self.setWindowTitle("Valyuta Ayarları")
        self.setMinimumWidth(450)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.api_url_input = QLineEdit()
        form.addRow("API URL:", self.api_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key:", self.api_key_input)

        self.last_fetch_label = QLabel("N/A")
        form.addRow("Son Yenilənmə:", self.last_fetch_label)

        self.usd_rate = QDoubleSpinBox()
        self.usd_rate.setRange(0, 1000000)
        self.usd_rate.setDecimals(6)
        form.addRow("USD -> AZN:", self.usd_rate)

        self.eur_rate = QDoubleSpinBox()
        self.eur_rate.setRange(0, 1000000)
        self.eur_rate.setDecimals(6)
        form.addRow("EUR -> AZN:", self.eur_rate)

        self.try_rate = QDoubleSpinBox()
        self.try_rate.setRange(0, 1000000)
        self.try_rate.setDecimals(6)
        form.addRow("TRY -> AZN:", self.try_rate)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()

        update_btn = QPushButton("Yenilə (5 gün)")
        update_btn.clicked.connect(self.update_if_due)

        force_btn = QPushButton("Məcburi Yenilə")
        force_btn.clicked.connect(self.force_update)

        save_btn = QPushButton("Yadda Saxla")
        save_btn.clicked.connect(self.save_settings)

        cancel_btn = QPushButton("Ləğv Et")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(force_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_settings(self):
        data = self.manager.load()
        self.api_url_input.setText(data.get("api_url", ""))
        self.api_key_input.setText(data.get("api_key", ""))
        rates = data.get("rates", {})
        self.usd_rate.setValue(float(rates.get("USD", 0)))
        self.eur_rate.setValue(float(rates.get("EUR", 0)))
        self.try_rate.setValue(float(rates.get("TRY", 0)))

        last_fetch = self.manager.last_fetch_time()
        if last_fetch:
            local_time = last_fetch.astimezone()
            self.last_fetch_label.setText(local_time.strftime("%d.%m.%Y %H:%M"))
        else:
            self.last_fetch_label.setText("N/A")

    def update_if_due(self):
        try:
            if not self.manager.is_update_due(min_days=5):
                QMessageBox.information(self, "Məlumat", "Yeniləmə hələ vaxtı çatmayıb.")
                return
            self.manager.update_from_api(force=False, min_days=5)
            self.load_settings()
            QMessageBox.information(self, "Uğurlu", "Valyuta məzənnələri yeniləndi.")
        except Exception as e:
            QMessageBox.warning(self, "Xəta", f"Yeniləmə alınmadı:\n{str(e)}")

    def force_update(self):
        try:
            self.manager.update_from_api(force=True, min_days=5)
            self.load_settings()
            QMessageBox.information(self, "Uğurlu", "Valyuta məzənnələri yeniləndi.")
        except Exception as e:
            QMessageBox.warning(self, "Xəta", f"Yeniləmə alınmadı:\n{str(e)}")

    def save_settings(self):
        data = self.manager.load()
        data["api_url"] = self.api_url_input.text().strip()
        data["api_key"] = self.api_key_input.text().strip()
        data["rates"] = {
            "AZN": 1.0,
            "USD": self.usd_rate.value(),
            "EUR": self.eur_rate.value(),
            "TRY": self.try_rate.value(),
        }
        # Leave last_fetch unchanged for manual edits
        self.manager.save(data)
        self.accept()
