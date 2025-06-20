# Google Sheets API Integration

This project provides a Python connector to fetch data from Google Sheets using the Google Sheets API.

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google Cloud Project

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project or select existing one**
3. **Enable Google Sheets API:**
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

### 3. Create Service Account

1. **Go to "APIs & Services" > "Credentials"**
2. **Click "Create Credentials" > "Service Account"**
3. **Fill in the details:**
   - Service account name: `google-sheets-connector`
   - Description: `Service account for Google Sheets API access`
4. **Click "Create and Continue"**
5. **Skip role assignment (click "Continue")**
6. **Click "Done"**

### 4. Generate JSON Key

1. **Click on your service account name**
2. **Go to "Keys" tab**
3. **Click "Add Key" > "Create new key"**
4. **Select "JSON" format**
5. **Click "Create"**
6. **Download the JSON file and rename it to `credentials.json`**
7. **Place it in your project root directory**

### 5. Share Your Google Sheet

1. **Open your Google Sheet**
2. **Click "Share" button**
3. **Add your service account email** (found in the JSON file under `client_email`)
4. **Give it "Viewer" permissions**
5. **Click "Send"**

## 📖 Usage

### Basic Usage

```python
from google_sheets_connector import GoogleSheetsConnector, extract_spreadsheet_id

# Initialize connector
connector = GoogleSheetsConnector('credentials.json')

# Your Google Sheets URL
sheets_url = "https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit#gid=0"

# Extract spreadsheet ID
spreadsheet_id = extract_spreadsheet_id(sheets_url)

# Get sheet information
info = connector.get_sheet_info(spreadsheet_id)
print(f"Spreadsheet: {info['title']}")

# Get data from specific range
data = connector.get_sheet_data(spreadsheet_id, 'Sheet1!A1:Z1000')
print(data.head())
```

### Run Example

```bash
python example_usage.py
```

## 🔧 Configuration

### Environment Variables (Optional)

You can also use environment variables for the credentials file path:

```python
import os
connector = GoogleSheetsConnector(os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'))
```

### Custom Ranges

You can specify custom ranges for data extraction:

```python
# Get specific columns
data = connector.get_sheet_data(spreadsheet_id, 'Sheet1!A:C')

# Get specific rows
data = connector.get_sheet_data(spreadsheet_id, 'Sheet1!A1:C100')

# Get entire sheet
data = connector.get_sheet_data(spreadsheet_id, 'Sheet1')
```

## 📁 Project Structure

```
JLPT/
├── google_sheets_connector.py  # Main connector class
├── example_usage.py           # Example usage script
├── requirements.txt           # Python dependencies
├── credentials.json          # Google service account key (you need to add this)
└── README.md                 # This file
```

## 🔒 Security Notes

- **Never commit `credentials.json` to version control**
- **Add `credentials.json` to your `.gitignore` file**
- **Keep your service account key secure**
- **Use minimal permissions (read-only for this setup)**

## 🐛 Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Make sure `credentials.json` is in the project root
   - Check the file path in your code

2. **"Permission denied"**
   - Ensure you've shared the Google Sheet with the service account email
   - Check that the service account has at least "Viewer" permissions

3. **"API not enabled"**
   - Make sure Google Sheets API is enabled in your Google Cloud project

4. **"Invalid spreadsheet ID"**
   - Check that your Google Sheets URL is correct
   - The spreadsheet ID should be in the URL: `/spreadsheets/d/SPREADSHEET_ID/`

### Getting Help

If you encounter issues:
1. Check the Google Cloud Console for API quotas and errors
2. Verify your service account permissions
3. Ensure your Google Sheet is shared correctly

## 📝 License

This project is open source and available under the MIT License. 