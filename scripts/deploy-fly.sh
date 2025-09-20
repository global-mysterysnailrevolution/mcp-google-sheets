#!/bin/bash
# Deploy Google Sheets MCP Server to Fly.io

set -e

echo "🚀 Deploying Google Sheets MCP Server to Fly.io..."

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Please install it from https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check if user is logged in
if ! fly auth whoami &> /dev/null; then
    echo "🔐 Please log in to Fly.io:"
    fly auth login
fi

# Create app if it doesn't exist
if ! fly apps list | grep -q "mcp-google-sheets"; then
    echo "📱 Creating new Fly.io app..."
    fly apps create mcp-google-sheets --generate-name
fi

# Set secrets (these will be prompted for)
echo "🔑 Setting up secrets..."
echo "Please provide your Google Cloud credentials:"

read -p "Enter your Google Drive folder ID: " folder_id
read -p "Enter the path to your service account JSON file: " service_account_path

# Set secrets
fly secrets set DRIVE_FOLDER_ID="$folder_id"
fly secrets set CREDENTIALS_CONFIG="$(base64 -w 0 "$service_account_path")"

# Deploy
echo "🚀 Deploying..."
fly deploy

echo "✅ Deployment complete!"
echo "📋 Your MCP server URL: https://mcp-google-sheets.fly.dev"
echo "🔧 Add this URL as a custom connector in ChatGPT"
