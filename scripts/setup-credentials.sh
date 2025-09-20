#!/bin/bash
# Setup script for Google Cloud credentials

set -e

echo "🔧 Setting up Google Cloud credentials for MCP Google Sheets Server..."

# Create credentials directory
mkdir -p credentials

# Function to validate JSON file
validate_json() {
    local file_path="$1"
    if [[ ! -f "$file_path" ]]; then
        echo "❌ File not found: $file_path"
        return 1
    fi
    
    if ! python3 -m json.tool "$file_path" > /dev/null 2>&1; then
        echo "❌ Invalid JSON file: $file_path"
        return 1
    fi
    
    echo "✅ Valid JSON file: $file_path"
    return 0
}

# Check for service account file
if [[ -f "credentials/service-account.json" ]]; then
    echo "✅ Found existing service account file"
    validate_json "credentials/service-account.json"
elif [[ -f "service-account.json" ]]; then
    echo "📁 Moving service account file to credentials directory..."
    mv service-account.json credentials/
    validate_json "credentials/service-account.json"
else
    echo "❌ Service account file not found!"
    echo "📋 Please download your service account JSON key from Google Cloud Console and:"
    echo "   1. Save it as 'credentials/service-account.json'"
    echo "   2. Or save it as 'service-account.json' in the project root"
    echo ""
    echo "🔗 Google Cloud Console: https://console.cloud.google.com/iam-admin/serviceaccounts"
    exit 1
fi

# Check for Google Drive folder ID
if [[ -z "$DRIVE_FOLDER_ID" ]]; then
    echo ""
    echo "📁 Google Drive Folder Setup:"
    echo "   1. Go to https://drive.google.com/"
    echo "   2. Create a folder for your AI-managed spreadsheets"
    echo "   3. Share it with your service account email (found in the JSON file)"
    echo "   4. Copy the folder ID from the URL"
    echo ""
    read -p "Enter your Google Drive folder ID: " folder_id
    export DRIVE_FOLDER_ID="$folder_id"
    
    # Save to .env file
    echo "DRIVE_FOLDER_ID=$folder_id" >> .env
    echo "✅ Saved folder ID to .env file"
fi

echo ""
echo "🎉 Setup complete!"
echo "📋 Next steps:"
echo "   1. Share your Google Drive folder with the service account"
echo "   2. Run: docker-compose up -d (for local development)"
echo "   3. Or deploy to a cloud provider using the deployment scripts"
