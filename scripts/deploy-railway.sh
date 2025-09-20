#!/bin/bash
# Deploy Google Sheets MCP Server to Railway

set -e

echo "🚀 Deploying Google Sheets MCP Server to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it from https://docs.railway.app/develop/cli"
    exit 1
fi

# Check if user is logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please log in to Railway:"
    railway login
fi

# Initialize Railway project
echo "📱 Setting up Railway project..."
railway login

# Set environment variables
echo "🔑 Setting up environment variables..."
echo "Please provide your Google Cloud credentials:"

read -p "Enter your Google Drive folder ID: " folder_id
read -p "Enter the path to your service account JSON file: " service_account_path

# Set variables
railway variables set DRIVE_FOLDER_ID="$folder_id"
railway variables set CREDENTIALS_CONFIG="$(base64 -w 0 "$service_account_path")"
railway variables set PORT="8080"
railway variables set HOST="0.0.0.0"

# Deploy
echo "🚀 Deploying..."
railway up

echo "✅ Deployment complete!"
echo "📋 Check your Railway dashboard for the deployment URL"
echo "🔧 Add this URL as a custom connector in ChatGPT"
