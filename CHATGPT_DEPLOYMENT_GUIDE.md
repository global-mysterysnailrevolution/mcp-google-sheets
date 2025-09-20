# ChatGPT Custom Connector Deployment Guide

This guide will help you deploy the Google Sheets MCP server as a custom connector for ChatGPT, enabling AI-powered spreadsheet operations.

## 🎯 Overview

The Google Sheets MCP server provides a bridge between ChatGPT and Google Sheets, allowing you to:
- Create and manage spreadsheets
- Read and write data to cells
- Share spreadsheets with team members
- Perform batch operations
- And much more!

## 📋 Prerequisites

### 1. Google Cloud Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Required APIs**
   - Navigate to "APIs & Services" → "Library"
   - Enable these APIs:
     - Google Sheets API
     - Google Drive API

3. **Create a Service Account**
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Name it (e.g., `mcp-sheets-service`)
   - Grant the "Editor" role
   - Click "Done"
   - Click on the created service account
   - Go to "Keys" tab → "Add Key" → "Create new key" → "JSON"
   - Download and securely store the JSON key file

4. **Set Up Google Drive Folder**
   - Go to [Google Drive](https://drive.google.com/)
   - Create a folder for AI-managed spreadsheets (e.g., "AI Managed Sheets")
   - Note the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Share the folder with your service account email (found in the JSON file)
   - Grant "Editor" permission

### 2. ChatGPT Account Requirements

- **ChatGPT Plus, Team, or Enterprise** account required
- **Team/Enterprise accounts**: Only workspace admins can add custom connectors
- **Personal accounts**: You can add connectors yourself

## 🚀 Deployment Options

### Option 1: Fly.io (Recommended)

Fly.io provides excellent performance and global distribution.

#### Quick Deploy

```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Clone this repository
git clone https://github.com/yourusername/mcp-google-sheets.git
cd mcp-google-sheets

# 3. Login to Fly.io
fly auth login

# 4. Run the deployment script
./scripts/deploy-fly.sh
```

#### Manual Deploy

```bash
# 1. Create a new Fly app
fly apps create mcp-google-sheets --generate-name

# 2. Set secrets
fly secrets set DRIVE_FOLDER_ID="your_folder_id_here"
fly secrets set CREDENTIALS_CONFIG="$(base64 -w 0 path/to/service-account.json)"

# 3. Deploy
fly deploy
```

### Option 2: Railway

Railway offers simple deployment with automatic HTTPS.

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Deploy
./scripts/deploy-railway.sh
```

### Option 3: Docker (Self-hosted)

For self-hosted deployment:

```bash
# 1. Set up environment variables
cp env.example .env
# Edit .env with your credentials

# 2. Run with Docker Compose
docker-compose up -d

# 3. Your server will be available at http://localhost:8000
```

### Option 4: Local Development

For testing and development:

```bash
# 1. Set up credentials
./scripts/setup-credentials.sh

# 2. Run locally
uv run mcp-google-sheets-http

# 3. Server runs on http://localhost:8000
```

## 🔧 ChatGPT Integration

### 1. Add Custom Connector

1. **Open ChatGPT** and go to **Settings** → **Connectors**
2. Click **"Add connector"**
3. Choose **"Custom"**
4. Fill in the details:
   - **Name**: `Google Sheets MCP`
   - **Description**: `AI-powered Google Sheets integration`
   - **Base URL**: `https://your-deployed-url.com` (or `http://localhost:8000` for local)
   - **Authentication**: `None` (service account handles auth)

### 2. Test the Connection

Once added, ChatGPT will automatically discover the available tools. Test with prompts like:

```
"List all my spreadsheets"
"Create a new spreadsheet called 'Project Tracker'"
"Update cell A1 in my 'Budget' spreadsheet to 'Total Revenue'"
```

## 🛠️ Available Tools

The connector provides these tools for ChatGPT:

| Tool | Description |
|------|-------------|
| `list_spreadsheets` | List all accessible spreadsheets |
| `create_spreadsheet` | Create a new spreadsheet |
| `get_sheet_data` | Read data from a sheet |
| `update_cells` | Write data to specific cells |
| `batch_update_cells` | Update multiple ranges at once |
| `add_rows` | Add rows to a sheet |
| `list_sheets` | List all sheets in a spreadsheet |
| `create_sheet` | Create a new sheet tab |
| `share_spreadsheet` | Share spreadsheet with users |

## 🔒 Security Best Practices

### 1. Credential Management
- **Never commit** service account JSON files to version control
- Use environment variables or secret management services
- Rotate credentials regularly
- Limit service account permissions to minimum required

### 2. Access Control
- Only share specific folders with the service account
- Use separate service accounts for different environments
- Monitor API usage and set up alerts for unusual activity

### 3. Network Security
- Use HTTPS in production (automatically handled by most deployment platforms)
- Configure CORS appropriately for your domain
- Consider IP whitelisting for additional security

## 🐛 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Error: All authentication methods failed
```
**Solution**: Check that your service account JSON is valid and the Google Drive folder is shared with the service account email.

#### 2. Permission Denied
```
Error: The caller does not have permission
```
**Solution**: Ensure the service account has Editor access to the shared folder and the required APIs are enabled.

#### 3. Rate Limiting
```
Error: Quota exceeded
```
**Solution**: Implement rate limiting in your application and consider requesting quota increases.

#### 4. Connector Not Found
```
ChatGPT: Connector not responding
```
**Solution**: Check that your server is running and accessible via HTTPS.

### Debug Mode

Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

### Health Check

Test your deployment:
```bash
curl https://your-deployment-url.com/health
```

## 📊 Monitoring and Logging

### 1. Application Logs
Monitor your deployment logs for errors and usage patterns:
```bash
# Fly.io
fly logs

# Railway
railway logs

# Docker
docker-compose logs -f
```

### 2. Google Cloud Monitoring
Set up monitoring in Google Cloud Console:
- API usage metrics
- Error rates
- Quota consumption

### 3. Custom Metrics
Consider implementing:
- Request/response times
- Error rates by tool
- User activity patterns

## 🔄 Updates and Maintenance

### 1. Updating the Server
```bash
# Pull latest changes
git pull origin main

# Redeploy
fly deploy  # or your deployment method
```

### 2. Updating Credentials
```bash
# Update secrets
fly secrets set CREDENTIALS_CONFIG="$(base64 -w 0 new-service-account.json)"
```

### 3. Scaling
Most deployment platforms auto-scale, but you can configure:
- Minimum/maximum instances
- Resource limits
- Auto-scaling triggers

## 📞 Support

### Getting Help

1. **Check the logs** first for error messages
2. **Review this guide** for common solutions
3. **Test locally** to isolate deployment issues
4. **Open an issue** on GitHub for bugs or feature requests

### Community Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [ChatGPT Connectors Help](https://help.openai.com/en/articles/11487775-connectors-in-chatgpt)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## 🎉 Success!

Once deployed and configured, you can use natural language to interact with Google Sheets:

```
"Create a sales report spreadsheet with columns for Date, Product, Amount, and Customer"
"Add the last 30 days of sales data to the Sales Report sheet"
"Share the Budget spreadsheet with finance@company.com as a viewer"
"Update the Q4 target in cell B10 to $50,000"
```

Your AI assistant now has the power to manage your spreadsheets! 🚀
