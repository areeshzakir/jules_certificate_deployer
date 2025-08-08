# Certificate Generator & Email Sender UI

A simple Streamlit web interface for generating certificates from a CSV file and sending them via email.

## Features

- Upload CSV with student data
- Upload certificate template PDF
- Validate CSV headers
- Generate certificates
- Send emails with certificates attached
- Download generated certificates as ZIP
- Optional password protection

## Prerequisites

- Python 3.10+
- macOS/Linux with Bash (or Windows with WSL)

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate the virtual environment:

```bash
# macOS/Linux
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. For email sending functionality, place your Google API credentials in the `credentials` folder:

```
certificate-ui/
└─ credentials/
   └─ credentials.json
```

## Running the App

```bash
streamlit run app_streamlit.py
```

Open the printed URL (usually `http://localhost:8501`).

## Sharing with Colleagues

- Same LAN: share your local IP (e.g., `http://192.168.1.20:8501`)
- Cloudflare Tunnel (free):
  ```bash
  # macOS: brew install cloudflared
  # Windows: choco install cloudflared
  cloudflared tunnel --url http://localhost:8501
  ```
  You'll get a public URL to share.

## Password Protection

Set the `APP_PASS` environment variable before running:

```bash
# macOS/Linux
export APP_PASS="strong-password"

# Windows PowerShell
$env:APP_PASS="strong-password"
```

## CSV Format

The CSV file must include the following columns (case-insensitive):

- name
- email
- certificate_id
- course_type
- completion_date
- college_name
- mentor_name
- mentor_signature
- event_type

## Troubleshooting

- **Permission denied** → `chmod +x certificate_workflow.sh`
- **Windows** → use WSL
- **OAuth prompt** → pre-generate `tokens/token.json` locally; copy to host
- **First run slow** → deps install; subsequent runs are quick
- **CSV error** → ensure all 9 required columns exist (any order, case-insensitive)