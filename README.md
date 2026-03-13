# Synology Photos Project

A Python project for interacting with Synology Photos API.

## Setup

### Prerequisites
- Python 3.9+
- Virtual environment (venv)

### Installation

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Configuration:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` with your NAS details:
     ```
     NAS_IP=192.168.1.100
     NAS_PORT=5000
     NAS_USERNAME=your_username
     NAS_PASSWORD=your_password
     NAS_SECURE=False
     NAS_CERT_VERIFY=False
     NAS_DSM_VERSION=7
     NAS_OTP_CODE=
     ```

### Usage

Use the CLI tool:
```bash
source venv/bin/activate
python cli.py --help
python cli.py user
python cli.py persons --limit 20
python cli.py download --person-id 88 --list
```

See [README_CLI.md](README_CLI.md) for full CLI documentation.

### Project Structure
```
synology-photos-project/
├── cli.py                   # Main CLI entry point
├── session_manager.py       # Session persistence
├── manage_session.py        # Session utilities
├── features/                # Modular features
│   ├── user.py
│   ├── albums.py
│   ├── folders.py
│   ├── items.py
│   ├── persons.py
│   └── download.py
├── venv/                    # Virtual environment
├── .env                     # Configuration (local, not in git)
├── .env.example             # Example configuration
├── requirements.txt         # Python dependencies
├── README_CLI.md            # CLI documentation
├── DOWNLOAD_FEATURE.md      # Download feature status
└── README.md                # This file
```

### Deactivating the Virtual Environment

When done, deactivate the virtual environment:
```bash
deactivate
```

## Useful Commands

```bash
# Activate venv
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# List installed packages
pip list

# Deactivate venv
deactivate
```

## Documentation

- [Synology API Docs](https://n4s4.github.io/synology-api/)
- [Photos API Reference](https://n4s4.github.io/synology-api/docs/apis/classes/photos)
