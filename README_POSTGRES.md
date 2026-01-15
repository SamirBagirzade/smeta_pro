# PyQt6 CRUD Application with PostgreSQL

A full-featured desktop application for managing products with PostgreSQL database and modern PyQt6 GUI.

## Features

✨ **Complete CRUD Operations**
- ➕ **Create**: Add new products with detailed information
- 📖 **Read**: View all products in a sortable table
- ✏️ **Update**: Edit existing product information
- 🗑️ **Delete**: Remove products with confirmation
- 🔍 **Search**: Real-time search across product names, sources, and notes

🔐 **Database Features**
- 🔌 **Connection Configuration**: Easy database connection setup
- 🧪 **Connection Testing**: Test database connection before connecting
- 🔄 **Reconnect**: Change database connection without restarting
- 💾 **PostgreSQL**: Professional database system support

## Database Schema

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    mehsulun_adi TEXT NOT NULL,      -- Product Name (required)
    price REAL,                       -- Price
    mehsul_menbeyi TEXT,             -- Product Source/Origin
    qeyd TEXT,                        -- Notes
    olcu_vahidi TEXT                  -- Unit of Measurement
);
```

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher (installed and running)
- pip package manager

### Step 1: Install PostgreSQL

**Windows:**
- Download from: https://www.postgresql.org/download/windows/
- Run the installer and remember your postgres user password

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Step 2: Create Database

```bash
# Log in to PostgreSQL
sudo -u postgres psql

# Create database
CREATE DATABASE products_db;

# Exit
\q
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements_postgres.txt
```

Or install manually:

```bash
pip install PyQt6 psycopg2-binary
```

### Step 4: Run the Application

**Azerbaijani Version:**
```bash
python pyqt_crud_postgres.py
```

**English Version:**
```bash
python pyqt_crud_postgres_english.py
```

## First Time Setup

When you first run the application, you'll see a database connection dialog:

1. **Host**: Usually `localhost` for local database
2. **Port**: Default PostgreSQL port is `5432`
3. **Database**: Enter `products_db` (or your database name)
4. **User**: Default is `postgres`
5. **Password**: Enter the password you set during PostgreSQL installation

Click **"Test Connection"** to verify settings before connecting.

## Usage Guide

### Connecting to Database
1. Enter your PostgreSQL connection details
2. Click **"Test Connection"** to verify (optional but recommended)
3. Click **"Connect"** to establish connection
4. The status indicator will turn green when connected

### Adding a Product
1. Ensure you're connected to the database (green status)
2. Click the **"➕ Yeni Məhsul"** (New Product) button
3. Fill in the product details:
   - **Məhsulun Adı** (Product Name) - Required
   - **Qiymət** (Price) - Optional
   - **Məhsul Mənbəyi** (Source) - Optional
   - **Ölçü Vahidi** (Unit) - Optional
   - **Qeyd** (Note) - Optional
4. Click **"💾 Yadda Saxla"** (Save)

### Editing a Product
1. Select a product from the table
2. Click **"✏️ Redaktə Et"** (Edit)
3. Modify the fields
4. Click **"💾 Yadda Saxla"** (Save)

### Deleting a Product
1. Select a product from the table
2. Click **"🗑️ Sil"** (Delete)
3. Confirm the deletion

### Searching Products
1. Type in the search box
2. Results filter automatically
3. Search works across: product names, sources, and notes
4. Click **"❌ Təmizlə"** (Clear) to reset

### Reconnecting
Click **"🔌 Yenidən Qoşul"** (Reconnect) to change database connection

## Application Structure

```
pyqt_crud_postgres.py
├── DatabaseManager         # PostgreSQL database operations
│   ├── create_product()
│   ├── read_all_products()
│   ├── read_product()
│   ├── update_product()
│   ├── delete_product()
│   ├── search_products()
│   └── test_connection()
├── DatabaseConfigDialog    # Database connection configuration
├── ProductDialog          # Add/Edit product dialog
└── MainWindow            # Main application window
```

## PostgreSQL vs SQLite Differences

This application uses PostgreSQL instead of SQLite. Key differences:

1. **Connection Required**: Must connect to PostgreSQL server
2. **SERIAL vs AUTOINCREMENT**: PostgreSQL uses `SERIAL` for auto-incrementing IDs
3. **Parameterization**: Uses `%s` instead of `?` for query parameters
4. **ILIKE**: Case-insensitive search using PostgreSQL's `ILIKE` operator
5. **RETURNING**: PostgreSQL's `RETURNING` clause to get inserted ID

## Configuration

### Default Connection Settings
```python
host = "localhost"
port = 5432
database = "products_db"
user = "postgres"
password = "postgres"
```

### Changing Default Settings
Edit the `DatabaseConfigDialog.__init__()` method to change default values.

## Database Operations

### Create Table
The application automatically creates the table if it doesn't exist:
```sql
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    mehsulun_adi TEXT NOT NULL,
    price REAL,
    mehsul_menbeyi TEXT,
    qeyd TEXT,
    olcu_vahidi TEXT
);
```

### Example SQL Queries

**Insert:**
```sql
INSERT INTO products (mehsulun_adi, price, mehsul_menbeyi, qeyd, olcu_vahidi)
VALUES ('Alma', 2.50, 'Gəncə', 'Təzə məhsul', 'kg')
RETURNING id;
```

**Select:**
```sql
SELECT * FROM products ORDER BY id;
```

**Update:**
```sql
UPDATE products 
SET mehsulun_adi = 'Updated Name', price = 3.00
WHERE id = 1;
```

**Delete:**
```sql
DELETE FROM products WHERE id = 1;
```

**Search (Case-insensitive):**
```sql
SELECT * FROM products 
WHERE mehsulun_adi ILIKE '%search%' 
   OR qeyd ILIKE '%search%' 
   OR mehsul_menbeyi ILIKE '%search%'
ORDER BY id;
```

## Error Handling

The application includes comprehensive error handling:
- Database connection errors
- Table creation errors
- CRUD operation errors
- Input validation
- User-friendly error messages

## Troubleshooting

### Cannot Connect to Database
**Error:** "Database connection error"

**Solutions:**
1. Verify PostgreSQL is running:
   ```bash
   # Linux/macOS
   sudo systemctl status postgresql
   
   # Windows - check Services
   ```

2. Check PostgreSQL is accepting connections:
   ```bash
   sudo -u postgres psql -c "SELECT version();"
   ```

3. Verify connection settings (host, port, user, password)

4. Check if database exists:
   ```bash
   sudo -u postgres psql -l
   ```

### Authentication Failed
**Error:** "authentication failed for user"

**Solutions:**
1. Verify password is correct
2. Check `pg_hba.conf` file allows connections
3. Try connecting with psql command line:
   ```bash
   psql -h localhost -p 5432 -U postgres -d products_db
   ```

### Table Already Exists Error
**Error:** "relation 'products' already exists"

**Solution:** This is usually not an error. The app checks for table existence.

### Port Already in Use
**Error:** "port 5432 is already in use"

**Solution:** Change the port in connection settings or stop other PostgreSQL instances.

## PostgreSQL Commands

### Basic PostgreSQL Commands

```bash
# Connect to database
psql -U postgres -d products_db

# List all databases
\l

# Connect to a database
\c products_db

# List all tables
\dt

# Describe table structure
\d products

# View all data
SELECT * FROM products;

# Exit
\q
```

### Backup and Restore

**Backup:**
```bash
pg_dump -U postgres products_db > backup.sql
```

**Restore:**
```bash
psql -U postgres products_db < backup.sql
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never hardcode passwords** in production applications
2. Use environment variables for sensitive data
3. Implement proper user authentication
4. Use SSL connections for remote databases
5. Follow principle of least privilege for database users
6. Regular database backups

## Advanced Configuration

### Using Environment Variables

Create a `.env` file:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=products_db
DB_USER=postgres
DB_PASSWORD=your_password
```

### Connection Pooling
For production applications, consider using connection pooling with `psycopg2.pool`.

### SSL Connections
For remote databases, use SSL:
```python
conn = psycopg2.connect(
    host=host,
    port=port,
    database=database,
    user=user,
    password=password,
    sslmode='require'
)
```

## Performance Tips

1. **Indexes**: Add indexes for frequently searched columns
   ```sql
   CREATE INDEX idx_product_name ON products(mehsulun_adi);
   ```

2. **Connection Management**: Close connections properly
3. **Batch Operations**: Use batch inserts for multiple records
4. **Query Optimization**: Use EXPLAIN to analyze slow queries

## Requirements

- Python 3.8+
- PyQt6 6.7.0+
- psycopg2-binary 2.9.9+
- PostgreSQL 12+

## Files Included

- `pyqt_crud_postgres.py` - Azerbaijani version
- `pyqt_crud_postgres_english.py` - English version
- `requirements_postgres.txt` - Python dependencies
- `README_POSTGRES.md` - This documentation

## License

This application is provided as-is for educational and commercial use.

## Support

For PostgreSQL-specific issues:
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- PostgreSQL Wiki: https://wiki.postgresql.org/

For psycopg2 issues:
- psycopg2 Documentation: https://www.psycopg.org/docs/

## Future Enhancements

- [ ] Export to CSV/Excel
- [ ] Import from CSV
- [ ] Advanced filtering
- [ ] Data visualization
- [ ] Connection pooling
- [ ] SSL support
- [ ] User roles and permissions
- [ ] Audit logging
- [ ] Bulk operations
- [ ] Product categories
