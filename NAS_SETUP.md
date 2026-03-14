# NAS Setup Guide

How to configure your Synology NAS to work with this project.

## Prerequisites

- Synology NAS running **DSM 7** with **Synology Photos** installed
- The NAS and your machine on the same local network

## 1. Create a `.env` file

```bash
cp .env.example .env
```

Edit `.env` with your NAS details:

```env
NAS_IP=192.168.1.100        # Your NAS IP
NAS_PORT=5000                # DSM HTTP port (5001 for HTTPS)
NAS_USERNAME=your_username
NAS_PASSWORD=your_password
NAS_SECURE=False             # True if using HTTPS (port 5001)
NAS_CERT_VERIFY=False        # True if NAS has a valid SSL cert
NAS_DSM_VERSION=7
NAS_OTP_CODE=                # Leave empty unless 2FA is enabled
```

## 2. Enable SSH on the NAS

**Control Panel > Terminal & SNMP > Terminal:**
- Check **Enable SSH service**
- Default port: 22

Set up SSH key auth (optional but recommended):

```bash
ssh-copy-id your_username@192.168.1.100
```

## 3. Allow external PostgreSQL connections

Synology Photos uses an internal PostgreSQL database (`synofoto`). By default it only accepts local Unix socket connections. You need to allow TCP connections from your machine.

### Edit `pg_hba.conf`

SSH into the NAS and edit the PostgreSQL auth config:

```bash
ssh your_username@192.168.1.100
sudo vi /etc/postgresql/pg_hba.conf
```

Add this line (replace with your subnet):

```
host    synofoto        all             192.168.1.0/24          trust
```

Reload PostgreSQL to apply:

```bash
sudo kill -HUP $(pgrep -f 'postgres -D')
```

### Verify `listen_addresses`

Check that PostgreSQL listens on all interfaces:

```bash
sudo grep listen_addresses /var/services/pgsql/postgresql.conf
```

Should show `listen_addresses = '*'`. If not, edit and restart PostgreSQL.

### Test the connection

From your machine:

```bash
psql -h 192.168.1.100 -U postgres synofoto -c "SELECT count(*) FROM unit"
```

## 4. macOS Local Network permission (if needed)

macOS may block Python from connecting to LAN devices. If you see `EHOSTUNREACH` (error 65), Homebrew Python needs **Local Network** permission.

### Grant permission to Homebrew Python

Run this to trigger the macOS permission dialog for the Python.app bundle:

```bash
# Write a trigger script
cat > /tmp/net_trigger.py << 'EOF'
import socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.sendto(b'x', ('255.255.255.255', 9))
s.close()
time.sleep(3)
EOF

# Open Python.app (triggers the macOS "allow local network?" dialog)
open -a "$(python3 -c "import sys; print(sys.base_prefix)")/Resources/Python.app" --args /tmp/net_trigger.py
```

Approve the dialog, then verify:

```bash
python3 -c "import socket; s=socket.socket(); s.settimeout(3); print(s.connect_ex(('YOUR_NAS_IP', 5432)))"
# Should print 0
```

## 5. Install Python dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 6. Install frontend dependencies

```bash
cd web/frontend
npm install
```

## 7. Run

```bash
# Backend (from repo root)
source venv/bin/activate
cd web/api && uvicorn main:app --reload --port 8000 --reload-dir ../..

# Frontend (separate terminal)
cd web/frontend && npm run dev
```

Open http://localhost:5173.
