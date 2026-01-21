# SheerID Auto-Verification Web App

![Stars](https://img.shields.io/github/stars/PastKing/tgbot-verify?style=social)
![Forks](https://img.shields.io/github/forks/PastKing/tgbot-verify?style=social)
![Issues](https://img.shields.io/github/issues/PastKing/tgbot-verify)
![License](https://img.shields.io/github/license/PastKing/tgbot-verify)

> 🤖 Automated SheerID Student/Teacher Verification Web App
> 
> Based on [@auto_sheerid_bot](https://t.me/auto_sheerid_bot) GGBond's legacy code with improvements

[中文文档](README.md) | English

---

## 📋 Overview

A Python-based web app that automates SheerID student/teacher identity verification for multiple platforms. The app automatically generates identity information, creates verification documents, and submits them to the SheerID platform, significantly simplifying the verification process.

> **⚠️ Important Notice**:
> 
> - Services such as **Gemini One Pro**, **ChatGPT Teacher K12**, **Spotify Student**, and **YouTube Premium Student** require updating verification data (e.g., `programId`) in each module's configuration file before use. Please refer to the "Must Read Before Use" section below for details.
> - This project also provides implementation approach and API documentation for **ChatGPT Military verification**. For detailed information, please refer to [`military/README.md`](military/README.md). Users can integrate this based on the documentation.

### 🎯 Supported Services

| Function | Service | Type | Status | Description |
|---------|---------|------|--------|-------------|
| `verify` | Gemini One Pro | Teacher | ✅ Complete | Google AI Studio Education Discount |
| `verify2` | ChatGPT Teacher K12 | Teacher | ✅ Complete | OpenAI ChatGPT Education Discount |
| `verify3` | Spotify Student | Student | ✅ Complete | Spotify Student Subscription Discount |
| `verify4` | Bolt.new Teacher | Teacher | ✅ Complete | Bolt.new Education Discount (Auto code retrieval) |
| `verify5` | YouTube Premium Student | Student | ⚠️ Beta | YouTube Premium Student Discount (See notes below) |

> **⚠️ YouTube Verification Special Notes**:
> 
> YouTube verification is currently in beta status. Please carefully read [`youtube/HELP.MD`](youtube/HELP.MD) before use.
> 
> **Key Differences**:
> - YouTube's original link format differs from other services
> - Requires manual extraction of `programId` and `verificationId` from browser network logs
> - Must manually construct standard SheerID link format
> 
> **Usage Steps**:
> 1. Visit YouTube Premium student verification page
> 2. Open browser DevTools (F12) → Network tab
> 3. Start verification process, search for `https://services.sheerid.com/rest/v2/verification/`
> 4. Extract `programId` from request payload and `verificationId` from response
> 5. Manually construct link: `https://services.sheerid.com/verify/{programId}/?verificationId={verificationId}`
> 6. Submit the link using the verification flow

> **💡 ChatGPT Military Verification Approach**:
> 
> This project provides implementation approach and API documentation for ChatGPT Military SheerID verification. The military verification process differs from regular student/teacher verification, requiring an initial `collectMilitaryStatus` API call to set military status before submitting personal information. For detailed implementation approach and API documentation, please refer to [`military/README.md`](military/README.md). Users can integrate this into the app based on the documentation.

### ✨ Key Features

- 🚀 **Automated Process**: One-click completion of info generation, document creation, and submission
- 🎨 **Smart Generation**: Auto-generates student/teacher ID PNG images
- 💰 **Points System**: Multiple earning methods including check-ins, invitations, and redemption codes
- 🔐 **Secure & Reliable**: MySQL database with environment variable configuration
- ⚡ **Concurrency Control**: Intelligent management of concurrent requests for stability
- 👥 **Admin Features**: Complete user and points management system

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: MySQL 5.7+
- **Browser Automation**: Playwright
- **HTTP Client**: httpx
- **Image Processing**: Pillow, reportlab, xhtml2pdf
- **Environment Management**: python-dotenv

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/PastKing/tgbot-verify.git
cd tgbot-verify
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment Variables

Copy `env.example` to `.env` and fill in the configuration:

```env
# Web App Configuration
APP_BASE_URL=https://your-app.vercel.app
CHANNEL_URL=https://t.me/your_channel
ADMIN_USER_ID=your_admin_id

# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=tgbot_verify
```

### 4. Start Web App

```bash
python -m uvicorn api.index:app --host 0.0.0.0 --port 8000
```

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# 1. Configure .env file
cp env.example .env
nano .env

# 2. Start services
docker-compose up -d

# 3. View logs
docker-compose logs -f
```

### Manual Docker Deployment

```bash
# Build image
docker build -t tgbot-verify .

# Run container
docker run -d \
  --name tgbot-verify \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  tgbot-verify
```

---

## 📖 Usage

### Web UI Actions

- Register, check balance, daily check-in, and invite link generation are available in the web console.
- Verification flows are available by selecting the target service and submitting the SheerID link.
- Admin actions (add balance, block/unblock, key management) are available to admin users in the web UI.

### Verification Process

1. **Get Verification Link**
   - Visit the corresponding service's verification page
   - Start the verification process
   - Copy the full URL from browser address bar (including `verificationId`)

2. **Submit Verification Request**
   - Paste the link into the web console and select the matching verification service.

3. **Wait for Processing**
   - The app automatically generates identity information
   - Creates student/teacher ID image
   - Submits to SheerID platform

4. **Get Results**
   - Review usually completes within minutes
   - Success returns redirect link

---

## 📁 Project Structure

```
tgbot-verify/
├── api/                    # FastAPI web app
├── config.py               # Global configuration
├── database_mysql.py       # MySQL database management
├── .env                    # Environment variables (create yourself)
├── env.example             # Environment variables template
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image build
├── docker-compose.yml      # Docker Compose configuration
├── one/                    # Gemini One Pro verification module
├── k12/                    # ChatGPT K12 verification module
├── spotify/                # Spotify Student verification module
├── youtube/                # YouTube Premium verification module
├── Boltnew/                # Bolt.new verification module
├── military/               # ChatGPT Military verification approach documentation
└── utils/                  # Utility functions
    ├── messages.py         # Message templates
    └── concurrency.py      # Concurrency control
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `APP_BASE_URL` | ✅ | Web app base URL | https://your-app.vercel.app |
| `CHANNEL_URL` | ❌ | Channel link | https://t.me/pk_oa |
| `ADMIN_USER_ID` | ✅ | Admin ID | - |
| `MYSQL_HOST` | ✅ | MySQL host address | localhost |
| `MYSQL_PORT` | ❌ | MySQL port | 3306 |
| `MYSQL_USER` | ✅ | MySQL username | - |
| `MYSQL_PASSWORD` | ✅ | MySQL password | - |
| `MYSQL_DATABASE` | ✅ | Database name | tgbot_verify |

### Points Configuration

Customize point rules in `config.py`:

```python
VERIFY_COST = 1        # Points cost for verification
CHECKIN_REWARD = 1     # Check-in reward points
INVITE_REWARD = 2      # Invitation reward points
REGISTER_REWARD = 1    # Registration reward points
```

---

## ⚠️ Important Notes

### 🔴 Must Read Before Use

**Before using the app, please check and update verification configurations in each module!**

Since SheerID platform's `programId` may be updated periodically, the following services **must** update verification data in their configuration files before use:

- `one/config.py` - **Gemini One Pro** verification (update `PROGRAM_ID`)
- `k12/config.py` - **ChatGPT Teacher K12** verification (update `PROGRAM_ID`)
- `spotify/config.py` - **Spotify Student** verification (update `PROGRAM_ID`)
- `youtube/config.py` - **YouTube Premium Student** verification (update `PROGRAM_ID`)
- `Boltnew/config.py` - Bolt.new Teacher verification (recommended to check `PROGRAM_ID`)

**How to get the latest programId**:
1. Visit the corresponding service's verification page
2. Open browser DevTools (F12) → Network tab
3. Start the verification process
4. Look for `https://services.sheerid.com/rest/v2/verification/` requests
5. Extract `programId` from URL or request payload
6. Update the corresponding module's `config.py` file

> **Tip**: If verification keeps failing, the `programId` is likely outdated. Please update it following the steps above.

---

## 🔗 Links

- 📺 **Telegram Channel**: https://t.me/pk_oa
- 🐛 **Issue Tracking**: [GitHub Issues](https://github.com/PastKing/tgbot-verify/issues)
- 📖 **Deployment Guide**: coming soon

---

## 🤝 Secondary Development

Secondary development is welcome! Please follow these rules:

1. **Preserve Original Author Info**
   - Keep original repository address in code and documentation
   - Note that it's based on this project

2. **Open Source License**
   - This project uses MIT License
   - Secondary development projects must also be open source

3. **Commercial Use**
   - Free for personal use
   - Commercial use requires self-optimization and liability
   - No technical support or warranty provided

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

```
MIT License

Copyright (c) 2025 PastKing

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 🙏 Acknowledgments

- Thanks to [@auto_sheerid_bot](https://t.me/auto_sheerid_bot) GGBond for the legacy code foundation
- Thanks to all developers who contributed to this project
- Thanks to SheerID platform for providing verification services

---

## 📊 Statistics

[![Star History Chart](https://api.star-history.com/svg?repos=PastKing/tgbot-verify&type=Date)](https://star-history.com/#PastKing/tgbot-verify&Date)

---

## 📝 Changelog

### v2.0.0 (2025-01-12)

- ✨ Added Spotify Student and YouTube Premium Student verification (YouTube is in beta, see youtube/HELP.MD)
- 🚀 Optimized concurrency control and performance
- 📝 Improved documentation and deployment guide
- 🐛 Fixed known bugs

### v1.0.0

- 🎉 Initial release
- ✅ Support for Gemini, ChatGPT, Bolt.new verification

---

<p align="center">
  <strong>⭐ If this project helps you, please give it a Star!</strong>
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/PastKing">PastKing</a>
</p>
