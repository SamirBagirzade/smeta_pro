"""
PyQt6 CRUD Application for Product Management with MongoDB
Database Structure:
- _id: ObjectId (Primary Key, auto-generated)
- mehsulun_adi: string (Required)
- price: float
- mehsul_menbeyi: string
- qeyd: string
- olcu_vahidi: string
- category: string
- price_last_changed: datetime (timestamp of last price change)
- image_id: ObjectId (Optional, reference to GridFS file)

Images are stored in GridFS for efficient binary storage.
Double-click any product row to view its image.
"""

import sys
import re
import json
import os
from datetime import datetime, timezone
from urllib.parse import quote_plus
from pymongo import MongoClient, ASCENDING, TEXT
from bson.objectid import ObjectId
import gridfs
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QTextEdit,
    QGroupBox, QHeaderView, QSpinBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QByteArray
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QPixmap


class DatabaseManager:
    """Handles all MongoDB database operations"""

    def __init__(self, host="", port=27017, database="admin",
                 username="admin", password=""):
        """
        Initialize database connection parameters

        Args:
            host: Database host
            port: Database port (default: 27017)
            database: Database name
            username: Database username (optional)
            password: Database password (optional)
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.client = None
        self.db = None
        self.collection = None
        self.fs = None  # GridFS for storing images
        self.connect()
        self.setup_indexes()

    def connect(self):
        """Create and maintain database connection"""
        try:
            # Build connection string with URL-encoded credentials
            if self.username and self.password:
                # URL-encode username and password to handle special characters
                encoded_username = quote_plus(self.username)
                encoded_password = quote_plus(self.password)
                connection_string = f"mongodb://{encoded_username}:{encoded_password}@{self.host}:{self.port}/{self.database}"
            else:
                connection_string = f"mongodb://{self.host}:{self.port}/"

            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            self.db = self.client[self.database]
            self.collection = self.db['products']
            self.fs = gridfs.GridFS(self.db)  # Initialize GridFS for image storage

            # Test connection
            self.client.server_info()

        except Exception as e:
            raise Exception(f"Database connection error: {e}")

    def setup_indexes(self):
        """Create indexes for faster searching"""
        try:
            # Create text indexes for search functionality
            self.collection.create_index([
                ("mehsulun_adi", TEXT),
                ("mehsul_menbeyi", TEXT),
                ("qeyd", TEXT),
                ("category", TEXT)
            ])

            # Create regular indexes for common queries
            self.collection.create_index([("mehsulun_adi", ASCENDING)])
            self.collection.create_index([("category", ASCENDING)])

            print("MongoDB indexes created successfully for fast searching.")
        except Exception as e:
            print(f"Note: Could not create indexes: {e}")

    def create_product(self, mehsulun_adi, price, mehsul_menbeyi, qeyd, olcu_vahidi, category, image_id=None):
        """Create a new product"""
        try:
            product = {
                'mehsulun_adi': mehsulun_adi,
                'price': price,
                'mehsul_menbeyi': mehsul_menbeyi,
                'qeyd': qeyd,
                'olcu_vahidi': olcu_vahidi,
                'category': category,
                'price_last_changed': datetime.now(timezone.utc)
            }
            if image_id:
                product['image_id'] = image_id
            result = self.collection.insert_one(product)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Failed to create product: {e}")

    def read_all_products(self):
        """Read all products"""
        try:
            products = list(self.collection.find().sort("_id", ASCENDING))
            # Convert ObjectId to string for display
            for product in products:
                product['id'] = str(product['_id'])
            return products
        except Exception as e:
            raise Exception(f"Failed to read products: {e}")

    def read_product(self, product_id):
        """Read a single product by ID"""
        try:
            # Handle both string and ObjectId
            if isinstance(product_id, str):
                product_id = ObjectId(product_id)

            product = self.collection.find_one({'_id': product_id})
            if product:
                product['id'] = str(product['_id'])
            return product
        except Exception as e:
            raise Exception(f"Failed to read product: {e}")

    def update_product(self, product_id, mehsulun_adi, price, mehsul_menbeyi, qeyd, olcu_vahidi, category, image_id=None):
        """Update an existing product"""
        try:
            # Handle both string and ObjectId
            if isinstance(product_id, str):
                product_id = ObjectId(product_id)

            # Get current product to check if price changed
            current_product = self.collection.find_one({'_id': product_id})

            update_data = {
                '$set': {
                    'mehsulun_adi': mehsulun_adi,
                    'price': price,
                    'mehsul_menbeyi': mehsul_menbeyi,
                    'qeyd': qeyd,
                    'olcu_vahidi': olcu_vahidi,
                    'category': category
                }
            }

            # If price changed, update the timestamp
            if current_product and current_product.get('price') != price:
                update_data['$set']['price_last_changed'] = datetime.now(timezone.utc)

            # Handle image update
            if image_id is not None:
                # Delete old image if exists
                if current_product and current_product.get('image_id'):
                    try:
                        self.fs.delete(current_product['image_id'])
                    except:
                        pass

                if image_id:  # New image uploaded
                    update_data['$set']['image_id'] = image_id
                else:  # Image removed
                    update_data['$unset'] = {'image_id': ''}

            result = self.collection.update_one({'_id': product_id}, update_data)
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            raise Exception(f"Failed to update product: {e}")

    def delete_product(self, product_id):
        """Delete a product"""
        try:
            # Handle both string and ObjectId
            if isinstance(product_id, str):
                product_id = ObjectId(product_id)

            result = self.collection.delete_one({'_id': product_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete product: {e}")

    def search_products(self, search_term):
        """Search products by name, source, note, or category"""
        try:
            # Use text search for better performance
            products = list(self.collection.find(
                {'$text': {'$search': search_term}}
            ).sort("_id", ASCENDING))

            # If no results with text search, try regex (fallback)
            if not products:
                # Escape special regex characters to treat them as literals
                escaped_term = re.escape(search_term)
                regex_pattern = {'$regex': escaped_term, '$options': 'i'}
                products = list(self.collection.find({
                    '$or': [
                        {'mehsulun_adi': regex_pattern},
                        {'mehsul_menbeyi': regex_pattern},
                        {'qeyd': regex_pattern},
                        {'category': regex_pattern}
                    ]
                }).sort("_id", ASCENDING))

            # Convert ObjectId to string
            for product in products:
                product['id'] = str(product['_id'])

            return products
        except Exception as e:
            raise Exception(f"Failed to search products: {e}")

    def test_connection(self):
        """Test database connection"""
        try:
            info = self.client.server_info()
            return True, f"MongoDB version: {info.get('version', 'Unknown')}"
        except Exception as e:
            return False, str(e)

    def save_image(self, image_data, filename):
        """Save image to GridFS and return the file ID"""
        try:
            file_id = self.fs.put(image_data, filename=filename)
            return file_id
        except Exception as e:
            raise Exception(f"Failed to save image: {e}")

    def get_image(self, file_id):
        """Retrieve image from GridFS"""
        try:
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)
            image_file = self.fs.get(file_id)
            return image_file.read()
        except Exception as e:
            raise Exception(f"Failed to retrieve image: {e}")

    def delete_image(self, file_id):
        """Delete image from GridFS"""
        try:
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)
            self.fs.delete(file_id)
        except Exception as e:
            raise Exception(f"Failed to delete image: {e}")


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


class ProductDialog(QDialog):
    """Dialog for adding/editing products"""

    def __init__(self, parent=None, product=None, mode="add"):
        super().__init__(parent)
        self.product = product
        self.mode = mode
        self.parent_window = parent
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
        self.price_input.setSuffix(" AZN")
        layout.addRow("Qiymət:", self.price_input)

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
            self.source_input.setText(self.product.get('mehsul_menbeyi', '') or '')
            self.unit_input.setText(self.product.get('olcu_vahidi', '') or '')
            self.note_input.setText(self.product.get('qeyd', '') or '')

            # Check if product has an image
            if self.product.get('image_id'):
                self.image_status_label.setText("✓ Şəkil mövcuddur")
                self.image_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.remove_image_btn.setVisible(True)

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
        data = {
            'mehsulun_adi': self.name_input.text().strip(),
            'category': self.category_input.text().strip() or None,
            'price': self.price_input.value() if self.price_input.value() > 0 else None,
            'mehsul_menbeyi': self.source_input.text().strip() or None,
            'qeyd': self.note_input.toPlainText().strip() or None,
            'olcu_vahidi': self.unit_input.text().strip() or None
        }

        # Add image information
        data['image_data'] = self.image_data
        data['image_filename'] = self.image_filename
        data['remove_image'] = self.remove_image

        return data

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

                product_id = self.parent_window.db.create_product(
                    data['mehsulun_adi'],
                    data['price'],
                    data['mehsul_menbeyi'],
                    data['qeyd'],
                    data['olcu_vahidi'],
                    data['category'],
                    image_id=image_id
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


class BoQItemDialog(QDialog):
    """Dialog for adding items to BoQ (from DB or custom)"""

    def __init__(self, parent=None, db=None, item=None, mode="add_from_db"):
        super().__init__(parent)
        self.db = db
        self.item = item
        self.mode = mode  # "add_from_db", "custom", "edit"
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
        self.price_input.setSuffix(" AZN")
        if self.mode == "add_from_db":
            self.price_input.setReadOnly(True)
        layout.addRow("Vahid Qiymət:", self.price_input)

        # Total (calculated, read-only)
        self.total_label = QLabel("0.00 AZN")
        self.total_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        layout.addRow("Cəmi:", self.total_label)

        # Connect quantity change to update total
        self.quantity_input.valueChanged.connect(self.update_total)
        self.price_input.valueChanged.connect(self.update_total)

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
                self.update_total()
                QMessageBox.information(self, "Uğurlu", "Məhsul məlumatı yükləndi!")
            else:
                QMessageBox.warning(self, "Xəta", "Bu ID-yə sahib məhsul tapılmadı!")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Xəta baş verdi: {str(e)}")

    def update_total(self):
        """Update total price"""
        quantity = self.quantity_input.value()
        unit_price = self.price_input.value()
        total = quantity * unit_price
        self.total_label.setText(f"{total:.2f} AZN")

    def get_data(self):
        """Get form data"""
        return {
            'product_id': self.product_combo.text().strip() if self.mode == "add_from_db" and hasattr(self, 'product_combo') and self.product_combo.text().strip() else None,
            'name': self.name_input.text().strip(),
            'quantity': self.quantity_input.value(),
            'unit': self.unit_input.text().strip(),
            'unit_price': self.price_input.value(),
            'total': self.quantity_input.value() * self.price_input.value(),
            'is_custom': self.mode == "custom"
        }

    def accept(self):
        """Validate before accepting"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Xəbərdarlıq", "Ad mütləqdir!")
            return
        if self.quantity_input.value() <= 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Miqdar 0-dan böyük olmalıdır!")
            return
        super().accept()


class BoQWindow(QMainWindow):
    """Bill of Quantities Window"""

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.parent_window = parent
        self.db = db
        self.boq_items = []  # List to store BoQ items
        self.next_id = 1
        self.boq_name = "BoQ 1"  # Default name
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("📋 Bill of Quantities (BoQ)")
        self.setGeometry(150, 150, 1000, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Title and Name section
        title_layout = QHBoxLayout()

        title = QLabel("Bill of Quantities")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2196F3; padding: 10px;")

        # BoQ Name input
        name_label = QLabel("BoQ Adı:")
        name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.boq_name_input = QLineEdit(self.boq_name)
        self.boq_name_input.setMaximumWidth(200)
        self.boq_name_input.setStyleSheet("font-size: 14px; padding: 5px;")
        self.boq_name_input.textChanged.connect(self.update_boq_name)

        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(name_label)
        title_layout.addWidget(self.boq_name_input)

        main_layout.addLayout(title_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "№", "Adı", "Kateqoriya", "Miqdar", "Ölçü Vahidi", "Vahid Qiymət (AZN)", "Cəmi (AZN)", "Mənbə", "Qeyd", "Növ"
        ])

        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # №
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Adı
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Kateqoriya
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Miqdar
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Ölçü Vahidi
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Vahid Qiymət
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Cəmi
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Mənbə
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # Qeyd
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Növ

        main_layout.addWidget(self.table)

        # Summary label
        self.summary_label = QLabel("Ümumi Məbləğ: 0.00 AZN")
        self.summary_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50; padding: 10px;")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.summary_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_custom_btn = QPushButton("➕ Xüsusi Qeyd Əlavə Et")
        self.add_custom_btn.clicked.connect(self.add_custom_item)
        self.add_custom_btn.setStyleSheet("""
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
        """)

        self.edit_btn = QPushButton("✏️ Redaktə Et")
        self.edit_btn.clicked.connect(self.edit_item)
        self.edit_btn.setStyleSheet("""
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
        """)

        self.delete_btn = QPushButton("🗑️ Sil")
        self.delete_btn.clicked.connect(self.delete_item)
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
        """)

        self.save_boq_btn = QPushButton("💾 BoQ Yadda Saxla")
        self.save_boq_btn.clicked.connect(self.save_boq)
        self.save_boq_btn.setStyleSheet("""
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

        self.load_boq_btn = QPushButton("📂 BoQ Yüklə")
        self.load_boq_btn.clicked.connect(self.load_boq)
        self.load_boq_btn.setStyleSheet("""
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
        """)

        self.export_excel_btn = QPushButton("📊 Excel-ə İxrac Et")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_excel_btn.setStyleSheet("""
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
        """)

        self.combine_boq_btn = QPushButton("🔗 BoQ-ları Birləşdir")
        self.combine_boq_btn.clicked.connect(self.combine_boqs_to_excel)
        self.combine_boq_btn.setStyleSheet("""
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
        """)

        button_layout.addWidget(self.add_custom_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.save_boq_btn)
        button_layout.addWidget(self.load_boq_btn)
        button_layout.addWidget(self.export_excel_btn)
        button_layout.addWidget(self.combine_boq_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)
        central_widget.setLayout(main_layout)

        # Apply light mode styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        """)

    def add_from_database(self):
        """Add item from database"""
        if not self.db:
            QMessageBox.warning(self, "Xəta", "Verilənlər bazasına qoşulmayıbsınız!")
            return

        dialog = BoQItemDialog(self, self.db, mode="add_from_db")
        if dialog.exec():
            data = dialog.get_data()
            data['id'] = self.next_id
            self.next_id += 1
            self.boq_items.append(data)
            self.refresh_table()

    def add_custom_item(self):
        """Add custom item (not from database)"""
        dialog = BoQItemDialog(self, self.db, mode="custom")
        if dialog.exec():
            data = dialog.get_data()
            data['id'] = self.next_id
            self.next_id += 1
            self.boq_items.append(data)
            self.refresh_table()

    def edit_item(self):
        """Edit selected item"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Redaktə etmək üçün qeyd seçin!")
            return

        item = self.boq_items[selected_row]
        mode = "custom" if item.get('is_custom') else "edit"

        dialog = BoQItemDialog(self, self.db, item=item, mode=mode)
        if dialog.exec():
            data = dialog.get_data()
            data['id'] = item['id']
            self.boq_items[selected_row] = data
            self.refresh_table()

    def delete_item(self):
        """Delete selected item(s)"""
        # Get all selected rows
        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(self, "Xəbərdarlıq", "Silmək üçün qeyd seçin!")
            return

        # Confirm deletion
        if len(selected_rows) == 1:
            message = "Bu qeydi silmək istədiyinizdən əminsiniz?"
        else:
            message = f"{len(selected_rows)} qeydi silmək istədiyinizdən əminsiniz?"

        reply = QMessageBox.question(
            self,
            "Təsdiq",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Get row indices and sort in descending order
            # This allows us to delete from bottom to top without affecting other indices
            rows_to_delete = sorted([index.row() for index in selected_rows], reverse=True)

            # Delete items from the list
            for row in rows_to_delete:
                del self.boq_items[row]

            self.refresh_table()

    def refresh_table(self):
        """Refresh the BoQ table"""
        self.table.setRowCount(0)
        total_sum = 0

        for item in self.boq_items:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Column 0: №
            self.table.setItem(row_position, 0, QTableWidgetItem(str(item['id'])))
            # Column 1: Adı
            self.table.setItem(row_position, 1, QTableWidgetItem(item['name']))
            # Column 2: Kateqoriya
            self.table.setItem(row_position, 2, QTableWidgetItem(item.get('category', '') or 'N/A'))
            # Column 3: Miqdar
            self.table.setItem(row_position, 3, QTableWidgetItem(f"{item['quantity']:.2f}"))
            # Column 4: Ölçü Vahidi
            self.table.setItem(row_position, 4, QTableWidgetItem(item['unit']))
            # Column 5: Vahid Qiymət
            self.table.setItem(row_position, 5, QTableWidgetItem(f"{item['unit_price']:.2f}"))
            # Column 6: Cəmi
            self.table.setItem(row_position, 6, QTableWidgetItem(f"{item['total']:.2f}"))
            # Column 7: Mənbə
            self.table.setItem(row_position, 7, QTableWidgetItem(item.get('source', '') or 'N/A'))
            # Column 8: Qeyd
            self.table.setItem(row_position, 8, QTableWidgetItem(item.get('note', '') or 'N/A'))
            # Column 9: Növ
            item_type = "Xüsusi" if item.get('is_custom') else "DB"
            self.table.setItem(row_position, 9, QTableWidgetItem(item_type))

            total_sum += item['total']

        # Update summary
        self.summary_label.setText(f"Ümumi Məbləğ: {total_sum:.2f} AZN")

    def export_to_excel(self):
        """Export BoQ to Excel file"""
        if not self.boq_items:
            QMessageBox.warning(self, "Xəbərdarlıq", "BoQ boşdur! İxrac etmək üçün məhsul əlavə edin.")
            return

        try:
            # Import openpyxl
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            except ImportError:
                QMessageBox.critical(
                    self,
                    "Xəta",
                    "openpyxl kitabxanası tapılmadı!\n\nYükləmək üçün terminal-da:\npip install openpyxl"
                )
                return

            # Ask user for file location
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "BoQ-u Excel-ə İxrac Et",
                "BoQ.xlsx",
                "Excel Files (*.xlsx)"
            )

            if not file_path:
                return

            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Bill of Quantities"

            # Define styles
            header_fill = PatternFill(start_color="2196F3", end_color="2196F3", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_alignment = Alignment(horizontal="center", vertical="center")

            total_fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
            total_font = Font(bold=True, color="FFFFFF", size=12)

            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # Add title
            ws.merge_cells('A1:J1')
            ws['A1'] = "BILL OF QUANTITIES (BOQ)"
            ws['A1'].font = Font(bold=True, size=16, color="2196F3")
            ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 30

            # Add headers
            headers = ["№", "Adı", "Kateqoriya", "Miqdar", "Ölçü Vahidi", "Vahid Qiymət (AZN)", "Cəmi (AZN)", "Mənbə", "Qeyd", "Növ"]
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col_num)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = border

            # Add data
            total_sum = 0
            for row_num, item in enumerate(self.boq_items, 4):
                # Column 1: №
                ws.cell(row=row_num, column=1, value=item['id']).border = border
                # Column 2: Adı
                ws.cell(row=row_num, column=2, value=item['name']).border = border
                # Column 3: Kateqoriya
                ws.cell(row=row_num, column=3, value=item.get('category', '') or 'N/A').border = border
                # Column 4: Miqdar
                ws.cell(row=row_num, column=4, value=item['quantity']).border = border
                # Column 5: Ölçü Vahidi
                ws.cell(row=row_num, column=5, value=item['unit']).border = border
                # Column 6: Vahid Qiymət
                ws.cell(row=row_num, column=6, value=item['unit_price']).border = border
                # Column 7: Cəmi
                ws.cell(row=row_num, column=7, value=item['total']).border = border
                # Column 8: Mənbə
                ws.cell(row=row_num, column=8, value=item.get('source', '') or 'N/A').border = border
                # Column 9: Qeyd
                ws.cell(row=row_num, column=9, value=item.get('note', '') or 'N/A').border = border
                # Column 10: Növ
                item_type = "Xüsusi" if item.get('is_custom') else "DB"
                ws.cell(row=row_num, column=10, value=item_type).border = border

                # Format numbers
                ws.cell(row=row_num, column=4).number_format = '0.00'
                ws.cell(row=row_num, column=6).number_format = '0.00'
                ws.cell(row=row_num, column=7).number_format = '0.00'

                total_sum += item['total']

            # Add total row
            total_row = len(self.boq_items) + 5
            ws.merge_cells(f'A{total_row}:F{total_row}')
            total_cell = ws[f'A{total_row}']
            total_cell.value = "ÜMUMİ MƏBLƏĞ:"
            total_cell.fill = total_fill
            total_cell.font = total_font
            total_cell.alignment = Alignment(horizontal="right", vertical="center")
            total_cell.border = border

            total_value_cell = ws[f'G{total_row}']
            total_value_cell.value = total_sum
            total_value_cell.fill = total_fill
            total_value_cell.font = total_font
            total_value_cell.alignment = Alignment(horizontal="center", vertical="center")
            total_value_cell.border = border
            total_value_cell.number_format = '0.00'

            # Fill remaining cells in total row
            for col in ['H', 'I', 'J']:
                ws[f'{col}{total_row}'].fill = total_fill
                ws[f'{col}{total_row}'].border = border

            # Adjust column widths
            ws.column_dimensions['A'].width = 8
            ws.column_dimensions['B'].width = 30
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 10
            ws.column_dimensions['E'].width = 12
            ws.column_dimensions['F'].width = 18
            ws.column_dimensions['G'].width = 15
            ws.column_dimensions['H'].width = 20
            ws.column_dimensions['I'].width = 20
            ws.column_dimensions['J'].width = 10

            # Save file
            wb.save(file_path)

            QMessageBox.information(
                self,
                "Uğurlu",
                f"BoQ uğurla Excel-ə ixrac edildi!\n\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"İxrac zamanı xəta:\n{str(e)}")

    def update_boq_name(self):
        """Update BoQ name from input field"""
        self.boq_name = self.boq_name_input.text().strip() or "BoQ 1"

    def save_boq(self):
        """Save BoQ to JSON file"""
        if not self.boq_items:
            QMessageBox.warning(self, "Xəbərdarlıq", "BoQ boşdur! Yadda saxlamaq üçün məhsul əlavə edin.")
            return

        try:
            import json
            from PyQt6.QtWidgets import QFileDialog

            # Ask user for file location
            default_name = f"{self.boq_name}.json" if self.boq_name else "BoQ.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "BoQ-u Yadda Saxla",
                default_name,
                "JSON Files (*.json)"
            )

            if not file_path:
                return

            # Prepare data for saving
            save_data = {
                'boq_name': self.boq_name,
                'next_id': self.next_id,
                'items': self.boq_items
            }

            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(
                self,
                "Uğurlu",
                f"BoQ uğurla yadda saxlanıldı!\n\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"BoQ yadda saxlanarkən xəta:\n{str(e)}")

    def load_boq(self):
        """Load BoQ from JSON file and update prices from database"""
        try:
            import json
            from PyQt6.QtWidgets import QFileDialog

            # Ask user for file to load
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "BoQ Yüklə",
                "",
                "JSON Files (*.json)"
            )

            if not file_path:
                return

            # Confirm if current BoQ will be replaced
            if self.boq_items:
                reply = QMessageBox.question(
                    self,
                    "Təsdiq",
                    "Mövcud BoQ məlumatları əvəz olunacaq. Davam etmək istəyirsiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # Load from file
            with open(file_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            self.boq_name = save_data.get('boq_name', 'BoQ 1')
            self.boq_name_input.setText(self.boq_name)
            self.next_id = save_data.get('next_id', 1)
            loaded_items = save_data.get('items', [])

            # Update prices from database for items that came from DB
            updated_count = 0
            for item in loaded_items:
                if not item.get('is_custom') and item.get('product_id') and self.db:
                    try:
                        # Get current product data from database
                        product = self.db.read_product(item['product_id'])
                        if product:
                            # Update price, category, source, and note from database
                            old_price = item['unit_price']
                            new_price = float(product['price']) if product.get('price') else 0

                            item['unit_price'] = new_price
                            item['total'] = item['quantity'] * new_price
                            item['category'] = product.get('category', '') or ''
                            item['source'] = product.get('mehsul_menbeyi', '') or ''
                            item['note'] = product.get('qeyd', '') or ''

                            if old_price != new_price:
                                updated_count += 1
                    except Exception as e:
                        # If product not found or error, keep the saved data
                        pass

            self.boq_items = loaded_items
            self.refresh_table()

            message = f"BoQ uğurla yükləndi!\n\n{len(loaded_items)} məhsul yükləndi."
            if updated_count > 0:
                message += f"\n{updated_count} məhsulun qiyməti yeniləndi."

            QMessageBox.information(self, "Uğurlu", message)

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"BoQ yüklənərkən xəta:\n{str(e)}")

    def combine_boqs_to_excel(self):
        """Combine multiple BoQs into a single Excel file"""
        try:
            import json
            from PyQt6.QtWidgets import QFileDialog
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            # Ask user to select multiple BoQ files
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "BoQ Fayllarını Seçin",
                "",
                "JSON Files (*.json)"
            )

            if not file_paths or len(file_paths) < 2:
                QMessageBox.warning(self, "Xəbərdarlıq", "Ən azı 2 BoQ faylı seçin!")
                return

            # Load all BoQs
            boqs = []
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        boq_data = json.load(f)
                        boqs.append({
                            'name': boq_data.get('boq_name', os.path.basename(file_path)),
                            'items': boq_data.get('items', [])
                        })
                except Exception as e:
                    QMessageBox.warning(self, "Xəbərdarlıq", f"Fayl oxuna bilmədi: {os.path.basename(file_path)}\n{str(e)}")

            if len(boqs) < 2:
                QMessageBox.warning(self, "Xəbərdarlıq", "Ən azı 2 BoQ uğurla yüklənməlidir!")
                return

            # Create a unified list of all unique items (by name)
            all_items_dict = {}
            for boq in boqs:
                for item in boq['items']:
                    item_key = item['name']
                    if item_key not in all_items_dict:
                        all_items_dict[item_key] = {
                            'name': item['name'],
                            'unit': item.get('unit', 'ədəd'),
                            'unit_price': item.get('unit_price', 0),
                            'category': item.get('category', ''),
                            'source': item.get('source', ''),
                            'note': item.get('note', ''),
                            'quantities': {}
                        }

            # Fill quantities for each BoQ
            for boq_idx, boq in enumerate(boqs):
                boq_name = boq['name']
                for item in boq['items']:
                    item_key = item['name']
                    all_items_dict[item_key]['quantities'][boq_name] = item.get('quantity', 0)

            # Ensure all items have entries for all BoQs (fill with 0 if missing)
            for item_data in all_items_dict.values():
                for boq in boqs:
                    if boq['name'] not in item_data['quantities']:
                        item_data['quantities'][boq['name']] = 0

            # Ask user for output file
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "Birləşdirilmiş BoQ-u Yadda Saxla",
                "Birləşdirilmiş_BoQ.xlsx",
                "Excel Files (*.xlsx)"
            )

            if not output_path:
                return

            # Create Excel workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Combined BoQ"

            # Define styles
            header_fill = PatternFill(start_color="2196F3", end_color="2196F3", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            total_fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
            total_font = Font(bold=True, color="FFFFFF", size=11)

            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # Title
            num_boqs = len(boqs)
            ws.merge_cells(f'A1:{chr(65 + 5 + num_boqs)}1')
            ws['A1'] = "BİRLƏŞDİRİLMİŞ BILL OF QUANTITIES (BOQ)"
            ws['A1'].font = Font(bold=True, size=16, color="2196F3")
            ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 30

            # Headers
            headers = ["№", "Adı", "Kateqoriya", "Ölçü Vahidi", "Vahid Qiymət (AZN)"]
            for boq in boqs:
                headers.append(f"{boq['name']}\n(Miqdar)")
            headers.append("Cəmi\nMiqdar")
            headers.append("Cəmi\nQiymət (AZN)")

            col_num = 1
            for header in headers:
                cell = ws.cell(row=3, column=col_num)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = border
                col_num += 1

            # Data rows
            row_num = 4
            for idx, (item_name, item_data) in enumerate(sorted(all_items_dict.items()), 1):
                ws.cell(row=row_num, column=1, value=idx).border = border
                ws.cell(row=row_num, column=2, value=item_data['name']).border = border
                ws.cell(row=row_num, column=3, value=item_data['category'] or 'N/A').border = border
                ws.cell(row=row_num, column=4, value=item_data['unit']).border = border
                ws.cell(row=row_num, column=5, value=item_data['unit_price']).border = border
                ws.cell(row=row_num, column=5).number_format = '0.00'

                # Quantities for each BoQ
                col = 6
                first_qty_col = chr(65 + 5)  # F
                for boq in boqs:
                    qty = item_data['quantities'][boq['name']]
                    ws.cell(row=row_num, column=col, value=qty).border = border
                    ws.cell(row=row_num, column=col).number_format = '0.00'
                    col += 1

                last_qty_col = chr(65 + col - 2)  # Last BoQ column

                # Total quantity column (SUM formula)
                total_qty_col = chr(65 + col - 1)
                total_qty_cell = ws.cell(row=row_num, column=col)
                total_qty_cell.value = f"=SUM({first_qty_col}{row_num}:{last_qty_col}{row_num})"
                total_qty_cell.border = border
                total_qty_cell.number_format = '0.00'
                total_qty_cell.font = Font(bold=True)
                col += 1

                # Total price column (Total Quantity * Unit Price)
                price_col = 'E'  # Unit price column
                total_price_cell = ws.cell(row=row_num, column=col)
                total_price_cell.value = f"={total_qty_col}{row_num}*{price_col}{row_num}"
                total_price_cell.border = border
                total_price_cell.number_format = '#,##0.00'
                total_price_cell.font = Font(bold=True)

                row_num += 1

            # Add grand total row
            total_row = row_num + 1
            ws.merge_cells(f'A{total_row}:{chr(65 + 5 + num_boqs)}{total_row}')
            total_label_cell = ws[f'A{total_row}']
            total_label_cell.value = "ÜMUMİ MƏBLƏĞ:"
            total_label_cell.fill = total_fill
            total_label_cell.font = total_font
            total_label_cell.alignment = Alignment(horizontal="right", vertical="center")
            total_label_cell.border = border

            # Grand total formula
            total_price_col = chr(65 + 6 + num_boqs)
            grand_total_cell = ws[f'{total_price_col}{total_row}']
            grand_total_cell.value = f"=SUM({total_price_col}4:{total_price_col}{row_num - 1})"
            grand_total_cell.fill = total_fill
            grand_total_cell.font = total_font
            grand_total_cell.alignment = Alignment(horizontal="center", vertical="center")
            grand_total_cell.border = border
            grand_total_cell.number_format = '#,##0.00'

            # Adjust column widths
            ws.column_dimensions['A'].width = 6
            ws.column_dimensions['B'].width = 35
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 12
            ws.column_dimensions['E'].width = 18

            for i in range(num_boqs + 2):  # BoQ columns + Total Qty + Total Price
                col_letter = chr(70 + i)  # Start from F
                ws.column_dimensions[col_letter].width = 14

            # Save file
            wb.save(output_path)

            QMessageBox.information(
                self,
                "Uğurlu",
                f"BoQ-lar uğurla birləşdirildi!\n\n{len(boqs)} BoQ birləşdirildi\n{len(all_items_dict)} unikal məhsul\n\n{output_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"BoQ-lar birləşdirilərkən xəta:\n{str(e)}")


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.db = None
        self.boq_window = None  # Single BoQ window instance

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

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Məhsulun Adı", "Kateqoriya", "Qiymət (AZN)", "Qiymət Dəyişdi (Gün)", "Məhsul Mənbəyi", "Ölçü Vahidi", "Qeyd"
        ])

        # Table styling
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

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

        # Connect double-click to view image
        self.table.cellDoubleClicked.connect(self.view_product_image)

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

        self.add_to_boq_btn = QPushButton("➕ BoQ-ya Əlavə Et")
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

        self.boq_btn = QPushButton("📋 BoQ Aç")
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

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.add_to_boq_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.reconnect_btn)
        button_layout.addWidget(self.boq_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)

        # Window styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTableWidget {
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

    def show_db_config(self):
        """Show database configuration dialog"""
        dialog = DatabaseConfigDialog(self)
        if dialog.exec():
            config = dialog.get_config()
            try:
                self.db = DatabaseManager(**config)
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
                self.info_label.setText(f"Cəmi məhsul sayı: {len(products)}")
                self.info_label.setStyleSheet("color: #666; font-style: italic;")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Məhsullar yüklənə bilmədi:\n{str(e)}")

    def populate_table(self, products):
        """Populate table with product data"""
        self.table.setRowCount(0)

        for product in products:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Store the ObjectId string in the table
            self.table.setItem(row_position, 0, QTableWidgetItem(product['id']))
            self.table.setItem(row_position, 1, QTableWidgetItem(product['mehsulun_adi']))
            self.table.setItem(row_position, 2, QTableWidgetItem(
                product.get('category', '') or 'N/A'
            ))
            self.table.setItem(row_position, 3, QTableWidgetItem(
                f"{float(product['price']):.2f}" if product.get('price') else "N/A"
            ))

            # Calculate days since price last changed
            price_last_changed = product.get('price_last_changed')
            if price_last_changed:
                # Handle both timezone-aware and naive datetime
                if price_last_changed.tzinfo is None:
                    price_last_changed = price_last_changed.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                days_since_change = (now - price_last_changed).days

                # Color code based on days
                days_item = QTableWidgetItem(str(days_since_change))
                if days_since_change > 365:
                    days_item.setForeground(QColor(211, 47, 47))  # Red for over a year
                elif days_since_change > 180:
                    days_item.setForeground(QColor(255, 152, 0))  # Orange for over 6 months
                elif days_since_change > 90:
                    days_item.setForeground(QColor(255, 193, 7))  # Yellow for over 3 months
                else:
                    days_item.setForeground(QColor(76, 175, 80))  # Green for recent

                self.table.setItem(row_position, 4, days_item)
            else:
                self.table.setItem(row_position, 4, QTableWidgetItem("N/A"))

            self.table.setItem(row_position, 5, QTableWidgetItem(
                product.get('mehsul_menbeyi', '') or 'N/A'
            ))
            self.table.setItem(row_position, 6, QTableWidgetItem(
                product.get('olcu_vahidi', '') or 'N/A'
            ))
            self.table.setItem(row_position, 7, QTableWidgetItem(
                product.get('qeyd', '') or 'N/A'
            ))

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

        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "Zəhmət olmasa redaktə etmək üçün məhsul seçin!")
            return

        product_id = self.table.item(selected_row, 0).text()

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
                    image_id=image_id if image_id is not None else None
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
        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(self, "Xəbərdarlıq", "Zəhmət olmasa silmək üçün məhsul seçin!")
            return

        # Collect product IDs and names
        products_to_delete = []
        for index in selected_rows:
            row = index.row()
            product_id = self.table.item(row, 0).text()
            product_name = self.table.item(row, 1).text()
            products_to_delete.append((product_id, product_name))

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

    def view_product_image(self, row, column):
        """View product image when double-clicking on a row"""
        if not self.db:
            return

        try:
            # Get product ID from the clicked row
            product_id = self.table.item(row, 0).text()
            product_name = self.table.item(row, 1).text()

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

        if not search_term:
            self.load_products()
            return

        try:
            products = self.db.search_products(search_term)
            self.populate_table(products)
            self.info_label.setText(f"Axtarış nəticəsi: {len(products)} məhsul tapıldı")
        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"Axtarış zamanı xəta:\n{str(e)}")

    def clear_search(self):
        """Clear search and reload all products"""
        self.search_timer.stop()  # Stop any pending search
        self.search_input.clear()
        self.load_products()

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
                products = self.db.read_all_products()
                self.info_label.setText(f"Cəmi məhsul sayı: {len(products)}")
                self.info_label.setStyleSheet("color: #666; font-style: italic;")
            except:
                pass

    def open_boq_window(self):
        """Open the Bill of Quantities window (singleton)"""
        if self.boq_window is None or not self.boq_window.isVisible():
            self.boq_window = BoQWindow(self, self.db)
            self.boq_window.show()
        else:
            # Bring existing window to front
            self.boq_window.raise_()
            self.boq_window.activateWindow()

    def add_selected_to_boq(self):
        """Add selected product to BoQ with quantity dialog"""
        if not self.db:
            return

        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Xəbərdarlıq", "BoQ-ya əlavə etmək üçün məhsul seçin!")
            return

        # Get product ID from selected row
        product_id = self.table.item(selected_row, 0).text()

        try:
            product = self.db.read_product(product_id)

            if not product:
                QMessageBox.critical(self, "Xəta", "Məhsul tapılmadı!")
                return

            # Create or show BoQ window first
            self.open_boq_window()

            # Create a simplified dialog for quantity only
            dialog = QDialog(self)
            dialog.setWindowTitle("BoQ-ya Əlavə Et")
            dialog.setMinimumWidth(400)

            layout = QFormLayout()

            # Show product name (read-only)
            name_label = QLabel(product['mehsulun_adi'])
            name_label.setStyleSheet("font-weight: bold; color: #2196F3;")
            layout.addRow("Məhsul:", name_label)

            # Quantity input
            quantity_input = QDoubleSpinBox()
            quantity_input.setRange(0.01, 999999.99)
            quantity_input.setDecimals(2)
            quantity_input.setValue(1)
            layout.addRow("Miqdar:", quantity_input)

            # Show unit and price (read-only)
            unit_label = QLabel(product.get('olcu_vahidi', '') or 'ədəd')
            layout.addRow("Ölçü Vahidi:", unit_label)

            price_label = QLabel(f"{float(product['price']):.2f} AZN" if product.get('price') else "0.00 AZN")
            layout.addRow("Vahid Qiymət:", price_label)

            # Total label
            total_label = QLabel("0.00 AZN")
            total_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            layout.addRow("Cəmi:", total_label)

            # Update total when quantity changes
            def update_total():
                qty = quantity_input.value()
                price = float(product['price']) if product.get('price') else 0
                total = qty * price
                total_label.setText(f"{total:.2f} AZN")

            quantity_input.valueChanged.connect(update_total)
            update_total()  # Initial calculation

            # Buttons
            button_layout = QHBoxLayout()

            add_btn = QPushButton("✅ Əlavə Et")
            add_btn.setStyleSheet("""
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

            cancel_btn = QPushButton("❌ Ləğv Et")
            cancel_btn.setStyleSheet("""
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

            button_layout.addWidget(add_btn)
            button_layout.addWidget(cancel_btn)
            layout.addRow(button_layout)

            dialog.setLayout(layout)

            add_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            if dialog.exec():
                # Add to BoQ
                data = {
                    'product_id': product_id,
                    'name': product['mehsulun_adi'],
                    'category': product.get('category', '') or '',
                    'quantity': quantity_input.value(),
                    'unit': product.get('olcu_vahidi', '') or 'ədəd',
                    'unit_price': float(product['price']) if product.get('price') else 0,
                    'total': quantity_input.value() * (float(product['price']) if product.get('price') else 0),
                    'source': product.get('mehsul_menbeyi', '') or '',
                    'note': product.get('qeyd', '') or '',
                    'is_custom': False,
                    'id': self.boq_window.next_id
                }
                self.boq_window.next_id += 1
                self.boq_window.boq_items.append(data)
                self.boq_window.refresh_table()

                self.show_status(
                    f"✅ '{product['mehsulun_adi']}' BoQ-ya əlavə edildi",
                    color="#4CAF50"
                )

        except Exception as e:
            QMessageBox.critical(self, "Xəta", f"BoQ-ya əlavə edilə bilmədi:\n{str(e)}")


def main():
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    # Force light mode palette
    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 122, 204))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    app.setPalette(light_palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
