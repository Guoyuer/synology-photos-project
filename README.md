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

Run the example script:
```bash
source venv/bin/activate
python3 example.py
```

### Project Structure
```
synology-photos-project/
├── venv/                    # Virtual environment
├── .env                     # Configuration (local, not in git)
├── .env.example             # Example configuration
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── example.py               # Example usage script
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
