# Deployment Guide — Ubuntu VPS (Hostinger) + Flutter Android

## Overview

```
Android App (Flutter)
        │  HTTPS
        ▼
  Nginx (reverse proxy + SSL)   ← Ubuntu VPS on Hostinger
        │
        ▼
  FastAPI backend (uvicorn, port 8000)
```

---

## Part 1 — Backend on Ubuntu VPS

### 1.1 Initial server setup

```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# Create a non-root user
adduser foodintel
usermod -aG sudo foodintel
su - foodintel

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+, pip, nginx, certbot
sudo apt install -y python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx git
```

### 1.2 Deploy the backend

```bash
# Clone your repo
git clone https://github.com/YOUR_USERNAME/food-intel.git ~/food-intel
cd ~/food-intel/backend

# Create virtualenv and install
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[api]"

# Create .env file
cat > .env << 'EOF'
FOOD_INTEL_LLM_PROVIDER=null
FOOD_INTEL_ENABLE_OPENFOODFACTS=true
FOOD_INTEL_USDA_API_KEY=your_free_key_here
FOOD_INTEL_CORS_ORIGINS=https://YOUR_DOMAIN,http://localhost:5173
EOF
```

### 1.3 Run as a systemd service

```bash
sudo nano /etc/systemd/system/foodintel.service
```

Paste:

```ini
[Unit]
Description=Food Intel FastAPI backend
After=network.target

[Service]
User=foodintel
WorkingDirectory=/home/foodintel/food-intel/backend
Environment="PYTHONPATH=src"
EnvironmentFile=/home/foodintel/food-intel/backend/.env
ExecStart=/home/foodintel/food-intel/backend/.venv/bin/uvicorn food_intel.api.app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable foodintel
sudo systemctl start foodintel
sudo systemctl status foodintel   # should show "active (running)"
```

### 1.4 Nginx reverse proxy

```bash
sudo nano /etc/nginx/sites-available/foodintel
```

Paste (replace `YOUR_DOMAIN` with your actual domain or VPS IP):

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/foodintel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 1.5 SSL with Let's Encrypt (requires a domain name)

```bash
sudo certbot --nginx -d YOUR_DOMAIN
# Certbot auto-renews; verify with:
sudo certbot renew --dry-run
```

If you only have an IP (no domain), use self-signed for now:

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/foodintel.key \
  -out /etc/ssl/certs/foodintel.crt \
  -subj "/CN=YOUR_VPS_IP"
```

### 1.6 Verify backend is live

```bash
curl https://YOUR_DOMAIN/api/health
# Expected: {"status":"ok"}
```

---

## Part 2 — Flutter Android App

### Why Flutter
- Single codebase → Android + iOS later
- Dart is strongly typed, easy to maintain
- Large ecosystem, Google-backed, scales well
- Camera/barcode scanning via well-maintained plugins

### 2.1 Install Flutter

```bash
# On your development machine (macOS/Linux/Windows)
# Follow: https://docs.flutter.dev/get-started/install

# Verify
flutter doctor
```

### 2.2 Create the Flutter project

```bash
cd ~/Workspace/personal
flutter create food_intel_app --org com.yourname --platforms android
cd food_intel_app
```

### 2.3 Add dependencies

Edit `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.1                    # API calls
  mobile_scanner: ^5.1.1          # barcode scanner (camera)
  provider: ^6.1.2                # state management
  shared_preferences: ^2.2.3      # local settings storage
```

```bash
flutter pub get
```

### 2.4 Configure API base URL

Create `lib/config.dart`:

```dart
class AppConfig {
  static const String apiBase = 'https://YOUR_DOMAIN/api';
}
```

### 2.5 API client

Create `lib/api_client.dart`:

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'config.dart';

class ApiClient {
  static Future<Map<String, dynamic>> analyze(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('${AppConfig.apiBase}/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('API error ${response.statusCode}: ${response.body}');
  }

  static Future<Map<String, dynamic>> lookupBarcode(String barcode) async {
    final response = await http.get(
      Uri.parse('${AppConfig.apiBase}/product/$barcode'),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Product not found');
  }
}
```

### 2.6 Barcode scanner screen

Create `lib/screens/scan_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../api_client.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool _scanned = false;

  void _onDetect(BarcodeCapture capture) async {
    if (_scanned) return;
    final barcode = capture.barcodes.firstOrNull?.rawValue;
    if (barcode == null) return;
    setState(() => _scanned = true);

    try {
      final result = await ApiClient.lookupBarcode(barcode);
      if (mounted) {
        Navigator.pushNamed(context, '/result', arguments: result);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Product not found: $barcode')),
        );
        setState(() => _scanned = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Barcode')),
      body: MobileScanner(onDetect: _onDetect),
    );
  }
}
```

### 2.7 Android camera permission

In `android/app/src/main/AndroidManifest.xml`, inside `<manifest>`:

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" android:required="false" />
```

### 2.8 Build and run

```bash
# Connect Android device with USB debugging enabled, or start emulator
flutter devices
flutter run

# Build release APK
flutter build apk --release
# APK is at: build/app/outputs/flutter-apk/app-release.apk
```

---

## Part 3 — USDA API Key (free, required for data enrichment)

1. Go to https://fdc.nal.usda.gov/api-key-signup.html
2. Sign up with your email — key arrives instantly
3. Add to your VPS `.env`:
   ```
   FOOD_INTEL_USDA_API_KEY=your_key_here
   ```
4. Restart the service: `sudo systemctl restart foodintel`

---

## Part 4 — Updating the backend

```bash
ssh foodintel@YOUR_VPS_IP
cd ~/food-intel
git pull
source backend/.venv/bin/activate
pip install -e "backend/.[api]" -q
sudo systemctl restart foodintel
```

---

## Checklist

- [ ] VPS SSH access working
- [ ] Backend service running (`systemctl status foodintel`)
- [ ] Nginx proxying `/api/*` to port 8000
- [ ] SSL certificate installed
- [ ] `curl https://YOUR_DOMAIN/api/health` returns `{"status":"ok"}`
- [ ] USDA API key added to `.env`
- [ ] Flutter app connects to `https://YOUR_DOMAIN/api`
- [ ] Barcode scanner opens camera and resolves products
