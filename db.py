"""
Database layer for the PyQt CRUD application.
"""

import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from pymongo import MongoClient, ASCENDING, TEXT
from bson.objectid import ObjectId
import gridfs


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
                connection_string = (
                    f"mongodb://{encoded_username}:{encoded_password}@{self.host}:{self.port}/{self.database}"
                )
            else:
                connection_string = f"mongodb://{self.host}:{self.port}/"

            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            self.db = self.client[self.database]
            self.collection = self.db['products']
            self.boq_collection = self.db['boqs']  # Collection for cloud BoQ storage
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

            # Indexes created successfully (silent for GUI app)
        except Exception:
            # Could not create indexes (silent for GUI app)
            pass

    def create_product(self, mehsulun_adi, price, mehsul_menbeyi, qeyd, olcu_vahidi,
                       category, image_id=None, currency="AZN", price_azn=None):
        """Create a new product"""
        try:
            product = {
                'mehsulun_adi': mehsulun_adi,
                'price': price,
                'price_azn': price_azn if price_azn is not None else price,
                'currency': currency or 'AZN',
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

    def get_price_history(self, product_id):
        """Get price history for a product"""
        try:
            if isinstance(product_id, str):
                product_id = ObjectId(product_id)

            product = self.collection.find_one({'_id': product_id})
            if product:
                return product.get('price_history', [])
            return []
        except Exception as e:
            raise Exception(f"Failed to get price history: {e}")

    def update_product(self, product_id, mehsulun_adi, price, mehsul_menbeyi, qeyd, olcu_vahidi,
                       category, image_id=None, currency="AZN", price_azn=None):
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
                    'price_azn': price_azn if price_azn is not None else price,
                    'currency': currency or 'AZN',
                    'mehsul_menbeyi': mehsul_menbeyi,
                    'qeyd': qeyd,
                    'olcu_vahidi': olcu_vahidi,
                    'category': category
                }
            }

            # If price changed, update the timestamp and add to history
            compare_old = current_product.get('price_azn', current_product.get('price'))
            compare_new = price_azn if price_azn is not None else price
            if current_product and compare_old != compare_new:
                update_data['$set']['price_last_changed'] = datetime.now(timezone.utc)
                # Add to price history
                old_price = compare_old or 0
                history_entry = {
                    'old_price': old_price,
                    'new_price': compare_new or 0,
                    'currency': 'AZN',
                    'changed_at': datetime.now(timezone.utc)
                }
                update_data['$push'] = {'price_history': history_entry}

            # Handle image update
            if image_id is not None:
                # Delete old image if exists
                if current_product and current_product.get('image_id'):
                    try:
                        self.fs.delete(current_product['image_id'])
                    except Exception:
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

            product = self.collection.find_one({'_id': product_id})
            if product and product.get('image_id'):
                try:
                    self.fs.delete(product['image_id'])
                except Exception:
                    pass

            result = self.collection.delete_one({'_id': product_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete product: {e}")

    def search_products(self, search_term):
        """Search products by name, source, note, or category"""
        try:
            if not search_term:
                return self.read_all_products()
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

    # BoQ Cloud Storage Methods
    def save_boq_to_cloud(self, boq_name, boq_items, next_id, string_count=0):
        """Save BoQ to MongoDB cloud"""
        try:
            boq_data = {
                'name': boq_name,
                'items': boq_items,
                'next_id': next_id,
                'string_count': string_count,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }

            # Check if BoQ with same name exists
            existing_boq = self.boq_collection.find_one({'name': boq_name})

            if existing_boq:
                # Update existing BoQ
                boq_data['created_at'] = existing_boq.get('created_at', datetime.now(timezone.utc))
                boq_data['updated_at'] = datetime.now(timezone.utc)
                self.boq_collection.update_one(
                    {'name': boq_name},
                    {'$set': boq_data}
                )
                return str(existing_boq['_id']), False  # False = updated
            else:
                # Insert new BoQ
                result = self.boq_collection.insert_one(boq_data)
                return str(result.inserted_id), True  # True = created new

        except Exception as e:
            raise Exception(f"Failed to save BoQ to cloud: {e}")

    def get_all_cloud_boqs(self):
        """Get list of all BoQs from cloud"""
        try:
            boqs = list(self.boq_collection.find().sort("updated_at", -1))
            for boq in boqs:
                boq['id'] = str(boq['_id'])
            return boqs
        except Exception as e:
            raise Exception(f"Failed to retrieve cloud BoQs: {e}")

    def search_cloud_boqs(self, search_term):
        """Search BoQs by name"""
        try:
            escaped_term = re.escape(search_term)
            regex_pattern = {'$regex': escaped_term, '$options': 'i'}
            boqs = list(self.boq_collection.find(
                {'name': regex_pattern}
            ).sort("updated_at", -1))
            for boq in boqs:
                boq['id'] = str(boq['_id'])
            return boqs
        except Exception as e:
            raise Exception(f"Failed to search cloud BoQs: {e}")

    def load_boq_from_cloud(self, boq_id):
        """Load a specific BoQ from cloud"""
        try:
            if isinstance(boq_id, str):
                boq_id = ObjectId(boq_id)

            boq = self.boq_collection.find_one({'_id': boq_id})
            if boq:
                boq['id'] = str(boq['_id'])
            return boq
        except Exception as e:
            raise Exception(f"Failed to load BoQ from cloud: {e}")

    def delete_cloud_boq(self, boq_id):
        """Delete a BoQ from cloud"""
        try:
            if isinstance(boq_id, str):
                boq_id = ObjectId(boq_id)

            result = self.boq_collection.delete_one({'_id': boq_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete cloud BoQ: {e}")

    # App Settings Methods
    def get_app_setting(self, key):
        """Get an application setting by key"""
        try:
            settings_collection = self.db['app_settings']
            doc = settings_collection.find_one({'key': key})
            return doc.get('value') if doc else None
        except Exception as e:
            raise Exception(f"Failed to get app setting: {e}")

    def set_app_setting(self, key, value):
        """Set an application setting by key"""
        try:
            settings_collection = self.db['app_settings']
            settings_collection.update_one(
                {'key': key},
                {'$set': {'value': value, 'updated_at': datetime.now(timezone.utc)}},
                upsert=True
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to set app setting: {e}")

    # BoQ Template Methods
    def save_template(self, template_name, items):
        """Save a BoQ template to cloud"""
        try:
            # Initialize template collection if not exists
            if not hasattr(self, 'template_collection'):
                self.template_collection = self.db['boq_templates']

            # Remove quantity-specific data for template
            template_items = []
            for item in items:
                default_price = item.get('default_price')
                if default_price is None:
                    default_price = item.get('unit_price', 0)
                template_item = {
                    'name': item['name'],
                    'unit': item.get('unit', ''),
                    'default_price': default_price,
                    'default_price_azn': item.get('default_price_azn'),
                    'currency': item.get('currency', 'AZN') or 'AZN',
                    'category': item.get('category', ''),
                    'source': item.get('source', ''),
                    'note': item.get('note', ''),
                    'is_custom': item.get('is_custom', False),
                    'product_id': item.get('product_id'),
                    'var_name': item.get('var_name', ''),
                    'amount_expr': item.get('amount_expr', '1'),
                    'price_expr': item.get('price_expr', '')
                }
                template_items.append(template_item)

            # Check if template exists
            existing = self.template_collection.find_one({'name': template_name})
            if existing:
                # Update existing template
                self.template_collection.update_one(
                    {'name': template_name},
                    {'$set': {
                        'items': template_items,
                        'updated_at': datetime.now(timezone.utc)
                    }}
                )
            else:
                # Create new template
                self.template_collection.insert_one({
                    'name': template_name,
                    'items': template_items,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                })
            return True
        except Exception as e:
            raise Exception(f"Failed to save template: {e}")

    def get_all_templates(self):
        """Get all BoQ templates"""
        try:
            if not hasattr(self, 'template_collection'):
                self.template_collection = self.db['boq_templates']

            templates = list(self.template_collection.find().sort("updated_at", -1))
            for t in templates:
                t['id'] = str(t['_id'])
            return templates
        except Exception as e:
            raise Exception(f"Failed to get templates: {e}")

    def load_template(self, template_id):
        """Load a specific template"""
        try:
            if not hasattr(self, 'template_collection'):
                self.template_collection = self.db['boq_templates']

            if isinstance(template_id, str):
                template_id = ObjectId(template_id)

            template = self.template_collection.find_one({'_id': template_id})
            if template:
                template['id'] = str(template['_id'])
                for item in template.get('items', []):
                    if 'default_price' not in item and 'unit_price' in item:
                        item['default_price'] = item.get('unit_price', 0)
            return template
        except Exception as e:
            raise Exception(f"Failed to load template: {e}")

    def delete_template(self, template_id):
        """Delete a template"""
        try:
            if not hasattr(self, 'template_collection'):
                self.template_collection = self.db['boq_templates']

            if isinstance(template_id, str):
                template_id = ObjectId(template_id)

            result = self.template_collection.delete_one({'_id': template_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete template: {e}")

    # Project Management Methods
    def _init_project_collection(self):
        """Initialize project collection if not exists"""
        if not hasattr(self, 'project_collection'):
            self.project_collection = self.db['projects']

    def create_project(self, name, description="", status="Aktiv"):
        """Create a new project"""
        try:
            self._init_project_collection()
            project = {
                'name': name,
                'description': description,
                'status': status,
                'boq_ids': [],
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            result = self.project_collection.insert_one(project)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Failed to create project: {e}")

    def get_all_projects(self):
        """Get all projects"""
        try:
            self._init_project_collection()
            projects = list(self.project_collection.find().sort("updated_at", -1))
            for p in projects:
                p['id'] = str(p['_id'])
            return projects
        except Exception as e:
            raise Exception(f"Failed to get projects: {e}")

    def get_project(self, project_id):
        """Get a specific project"""
        try:
            self._init_project_collection()
            if isinstance(project_id, str):
                project_id = ObjectId(project_id)
            project = self.project_collection.find_one({'_id': project_id})
            if project:
                project['id'] = str(project['_id'])
            return project
        except Exception as e:
            raise Exception(f"Failed to get project: {e}")

    def update_project(self, project_id, name=None, description=None, status=None, boq_ids=None):
        """Update a project"""
        try:
            self._init_project_collection()
            if isinstance(project_id, str):
                project_id = ObjectId(project_id)

            update_data = {'$set': {'updated_at': datetime.now(timezone.utc)}}
            if name is not None:
                update_data['$set']['name'] = name
            if description is not None:
                update_data['$set']['description'] = description
            if status is not None:
                update_data['$set']['status'] = status
            if boq_ids is not None:
                update_data['$set']['boq_ids'] = boq_ids

            result = self.project_collection.update_one({'_id': project_id}, update_data)
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            raise Exception(f"Failed to update project: {e}")

    def delete_project(self, project_id):
        """Delete a project"""
        try:
            self._init_project_collection()
            if isinstance(project_id, str):
                project_id = ObjectId(project_id)
            result = self.project_collection.delete_one({'_id': project_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete project: {e}")

    def add_boq_to_project(self, project_id, boq_id):
        """Add a BoQ to a project"""
        try:
            self._init_project_collection()
            if isinstance(project_id, str):
                project_id = ObjectId(project_id)

            result = self.project_collection.update_one(
                {'_id': project_id},
                {
                    '$addToSet': {'boq_ids': boq_id},
                    '$set': {'updated_at': datetime.now(timezone.utc)}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Failed to add BoQ to project: {e}")

    def remove_boq_from_project(self, project_id, boq_id):
        """Remove a BoQ from a project"""
        try:
            self._init_project_collection()
            if isinstance(project_id, str):
                project_id = ObjectId(project_id)

            result = self.project_collection.update_one(
                {'_id': project_id},
                {
                    '$pull': {'boq_ids': boq_id},
                    '$set': {'updated_at': datetime.now(timezone.utc)}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Failed to remove BoQ from project: {e}")
