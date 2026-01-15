# Smeta Pro - MongoDB Product Management System

A comprehensive desktop application for managing product catalogs and generating Bills of Quantities (BoQ) with Excel export capabilities.

## Features

### Core Functionality
- **Product Management**: Full CRUD operations (Create, Read, Update, Delete) for products
- **MongoDB Backend**: Reliable NoSQL database with text search indexing
- **Advanced Search**: Full-text search with special character support
- **Image Upload**: Optional image attachment for each product with GridFS storage
- **Image Viewer**: Double-click any product to view its image in a full-screen viewer
- **Price Tracking**: Automatic tracking of price changes with color-coded age indicators
  - 🟢 Green: < 90 days
  - 🟡 Yellow: 90-180 days
  - 🟠 Orange: 180-365 days
  - 🔴 Red: > 365 days

### Bill of Quantities (BoQ)
- **Named BoQs**: Create and save multiple Bills of Quantities with custom names
- **BoQ Combination**: Merge multiple BoQs into a single Excel file
- **Smart Quantity Management**: Automatically fills missing items with 0 across BoQs
- **Excel Formulas**: Dynamic calculations using Excel formulas (SUM, multiplication)
- **Professional Formatting**: Styled Excel output with headers, borders, and totals

### Data Management
- **Excel Export**: Export products and BoQs to formatted Excel files
- **Local Configuration**: Save database credentials locally for convenience
- **Secure Connections**: RFC 3986 compliant URL encoding for special characters in passwords

## Screenshots

![Main CRUD Interface](screenshots/crud.png)
![BoQ Management](screenshots/boq.png)
![Combined BoQ Excel Output](screenshots/combined_boq.png)

## Installation

### Prerequisites
- Python 3.8 or higher
- MongoDB server (local or remote)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/SamirBagirzade/smeta_pro.git
cd smeta_pro
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure MongoDB is running:
```bash
# For local MongoDB
mongod --dbpath /path/to/data
```

4. Run the application:
```bash
python pyqt_crud_mongodb.py
```

## Configuration

### First Launch
On first launch, you'll be prompted to enter:
- **Host**: MongoDB server address (default: localhost)
- **Port**: MongoDB port (default: 27017)
- **Database**: Database name (default: smeta)
- **Username**: MongoDB username (optional)
- **Password**: MongoDB password (optional)

The configuration is saved locally in `db_config.json` for convenience.

### MongoDB Setup
The application automatically creates:
- Database: `smeta`
- Collection: `products`
- Text indexes for efficient searching

## Usage

### Managing Products

1. **Add Product**: Click "Əlavə et" to create a new product
2. **Edit Product**: Select a row and click "Redaktə et"
3. **Delete Product**: Select a row and click "Sil"
4. **Search**: Use the search bar to find products by name, source, notes, or category

### Product Fields
- **Məhsulun adı**: Product name
- **Qiymət**: Price per unit
- **Məhsul mənbəyi**: Product source/supplier
- **Qeyd**: Notes/description
- **Ölçü vahidi**: Unit of measurement
- **Category**: Product category
- **Şəkil**: Product image (optional)
- **Price last changed**: Days since last price update (auto-tracked)

### Working with Images

**Uploading Images:**
1. When adding or editing a product, click the "📷 Şəkil Yüklə" button
2. Select an image file (PNG, JPG, JPEG, BMP, or GIF)
3. The image is stored in MongoDB using GridFS

**Viewing Images:**
- Double-click any product row in the table to view its image
- If no image exists, you'll be prompted to add one via the edit dialog
- Images are displayed in a scalable viewer with scroll support

**Removing Images:**
- Edit the product and click "🗑️ Şəkli Sil" to remove the image
- The image is permanently deleted from GridFS

### Creating Bills of Quantities

1. Click "BoQ yarat" to open the BoQ window
2. Name your BoQ (default: "BoQ 1")
3. Add products from the dropdown and specify quantities
4. Save as JSON or export to Excel

### Combining Multiple BoQs

1. From the main window, click "Combine BoQs"
2. Select multiple JSON BoQ files
3. The system generates an Excel file with:
   - Individual quantity columns for each BoQ
   - Items present in any BoQ (with 0 for missing items)
   - Sum column with SUM formula
   - Total price column with multiplication formula
   - Grand total row

## Technical Details

### Database Schema

Products are stored as MongoDB documents with the following structure:

```json
{
  "_id": ObjectId("..."),
  "mehsulun_adi": "Product Name",
  "price": 12.50,
  "mehsul_menbeyi": "Supplier",
  "qeyd": "Description",
  "olcu_vahidi": "m",
  "category": "Category",
  "price_last_changed": ISODate("2026-01-15T10:30:00Z"),
  "image_id": ObjectId("...")  // Optional - reference to GridFS file
}
```

**Image Storage:**
- Images are stored using MongoDB GridFS for efficient binary file handling
- GridFS automatically chunks large files (>16MB)
- Each image is referenced by its ObjectId in the product document
- Supported formats: PNG, JPG, JPEG, BMP, GIF

### BoQ File Format

BoQs are saved as JSON files:

```json
{
  "name": "My BoQ",
  "items": [
    {
      "id": 1,
      "name": "Product Name",
      "quantity": 10,
      "unit": "m",
      "unit_price": 12.50,
      "category": "Category"
    }
  ],
  "next_id": 2
}
```

### Technologies Used
- **PyQt6**: Modern GUI framework with image display support
- **pymongo**: MongoDB driver for Python with GridFS support
- **GridFS**: MongoDB's specification for storing large binary files
- **openpyxl**: Excel file creation and manipulation
- **MongoDB**: NoSQL database with text search and binary storage capabilities

## Special Features

### GridFS Image Storage
Images are stored efficiently using MongoDB's GridFS:
- **Binary Storage**: Images stored as binary data in GridFS collections
- **Automatic Cleanup**: Old images are deleted when replaced or product is deleted
- **Scalable**: Supports images of any size (GridFS handles chunking)
- **Format Support**: PNG, JPG, JPEG, BMP, GIF
- **Interactive Viewer**: Double-click any product to view full-resolution image

### URL Encoding for Passwords
Passwords with special characters (e.g., `@`, `#`, `%`) are automatically URL-encoded to ensure proper MongoDB connection strings.

### Regex Escaping
Search terms with special regex characters (e.g., `*`, `+`, `?`) are automatically escaped to treat them as literal strings.

### Price Change Tracking
Every price update automatically records the timestamp, allowing you to:
- Track how long prices have remained unchanged
- Identify products needing price updates
- Visual color coding for quick assessment

## Troubleshooting

### Connection Issues
- Verify MongoDB server is running
- Check host and port settings
- Ensure network connectivity for remote databases
- Verify username/password if authentication is enabled

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (requires 3.8+)

### Excel Export Issues
- Ensure write permissions in the target directory
- Check available disk space
- Verify openpyxl is installed correctly

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Samir

## Acknowledgments

- Built with PyQt6 for cross-platform GUI support
- MongoDB for reliable NoSQL data storage
- openpyxl for professional Excel file generation

## Version History

### v1.0.0 (2026-01-15)
- Initial release with MongoDB support
- Full CRUD operations
- BoQ management and combination
- Excel export with formulas
- Price change tracking
- Local configuration storage
