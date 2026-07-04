# Deployment Guide

## 1. Get a Free Cloud VM (Oracle Cloud)

1. Go to https://signup.cloud.oracle.com — create account (needs credit card for verification, but never charges)
2. After login → **Create a VM instance**:
   - Name: `newsapp`
   - Image: **Canonical Ubuntu 22.04** (or latest)
   - Shape: **VM.Standard.A1.Flex** (ARM, Ampere)
     - Scroll to "Shape series" → select **Ampere**
     - Configure: **4 OCPUs, 24 GB RAM** (always-free)
   - Add SSH key: download the private key, save it as `oracle-key.pem`
   - Click **Create**
3. Wait 2 min, copy the **Public IP** from the instance page

### Connect via SSH

```bash
# From your PC:
chmod 600 /path/to/oracle-key.pem
ssh -i /path/to/oracle-key.pem ubuntu@<PUBLIC_IP>
```

---

## 2. Set Up the Server

```bash
# Install Python + tools
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx

# Clone your project
git clone <YOUR_REPO_URL> ~/newsapp
cd ~/newsapp

# Create virtual env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

---

## 3. Add an API Endpoint for FlutterFlow

Open `webapp.py` and add a JSON endpoint before the `if __name__` block:

```python
@app.route("/api/articles")
def api_articles():
    cat = request.args.get("category")
    limit = request.args.get("limit", 50, type=int)
    articles = pipeline.get("clusters", [])
    # filter + serialize
    ...
    return jsonify(results)
```

Run it once to verify:

```bash
source venv/bin/activate && python webapp.py
```

Hit `http://<IP>:5050` in your browser to confirm it works. Press **Ctrl+C** to stop.

---

## 4. Run with Gunicorn (Production)

Create a systemd service so it starts on boot and stays alive:

```bash
sudo nano /etc/systemd/system/newsapp.service
```

Paste this:

```ini
[Unit]
Description=NewsApp Flask API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/newsapp
ExecStart=/home/ubuntu/newsapp/venv/bin/gunicorn -w 4 -b 0.0.0.0:5050 webapp:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start**:

```bash
sudo systemctl enable newsapp
sudo systemctl start newsapp
sudo systemctl status newsapp   # should say "active (running)"
```

---

## 5. Set Up Daily Refresh at 4 AM Tunisian Time

Set the server timezone to Tunis:

```bash
sudo timedatectl set-timezone Africa/Tunis
date   # verify it shows CET/CEST
```

Now add the cron job:

```bash
crontab -e
```

Add this line:

```cron
0 4 * * * cd /home/ubuntu/newsapp && /home/ubuntu/newsapp/venv/bin/python main.py >> /tmp/newsapp_cron.log 2>&1
```

This runs `main.py` at 4 AM Tunisian time every day and logs output. To also restart the API so it serves fresh data:

```cron
0 4 * * * cd /home/ubuntu/newsapp && /home/ubuntu/newsapp/venv/bin/python main.py && sudo systemctl restart newsapp
```

---

## 6. Expose with Nginx (optional but recommended)

```bash
sudo nano /etc/nginx/sites-available/newsapp
```

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/newsapp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

Now your API is at `http://<PUBLIC_IP>` (port 80, no need for `:5050`).

---

## 7. Connect FlutterFlow to the API

### 7.1. Make sure `webapp.py` has a JSON endpoint

Add to `webapp.py`:

```python
from flask import jsonify, request

@app.route("/api/articles")
def api_articles():
    cat = request.args.get("category")
    limit = request.args.get("limit", 50, type=int)

    clusters = pipeline.get("clusters", [])
    articles = []
    for c in clusters:
        for a in c.articles:
            item = {
                "id": a.id,
                "title": a.title,
                "summary": a.analysis.summary if a.analysis else "",
                "category": a.analysis.category if a.analysis else "General",
                "topics": a.analysis.topics if a.analysis else [],
                "source": a.source_domain,
                "url": a.url,
                "published": a.published,
                "published_iso": a.published_iso,
                "score": a.score,
                "trust_score": a.analysis.trustworthiness_score if a.analysis else 0,
                "image_url": a.image_url,
                "political_leaning": a.analysis.political_leaning if a.analysis else "neutral",
                "is_opinion": a.analysis.is_opinion if a.analysis else False,
            }
            articles.append(item)

    # Sort by score descending
    articles.sort(key=lambda x: x.get("score", 0), reverse=True)

    if cat:
        articles = [a for a in articles if a["category"] == cat]

    return jsonify(articles[:limit])
```

Restart the service:

```bash
sudo systemctl restart newsapp
```

Test it:

```bash
curl http://localhost/api/articles?category=Gaming&limit=5
```

### 7.2. In FlutterFlow

1. Go to **API Calls** → **Create Custom API Call**
2. Set:
   - **Method**: GET
   - **Base URL**: `http://<YOUR_PUBLIC_IP>`
   - **Path**: `/api/articles`
   - **Headers**: `Content-Type: application/json`
3. Add **Query Parameters** (optional):
   - `category` — filter by category name (e.g. `Gaming`, `Movies`, `Tunisia`)
   - `limit` — max articles to return
4. Click **Generate** — FlutterFlow auto-creates the data model
5. Use the API response in your app's ListView / cards

### 7.3. Handle slow first load

The first request may kick off a scrape (5+ min). Add a loading state:

```dart
// In FlutterFlow custom widget or page:
bool _loading = true;
String _error = '';

Future<void> fetchArticles() async {
  setState(() => _loading = true);
  try {
    final response = await api.call();
    setState(() => _loading = false);
    // use response
  } catch (e) {
    setState(() {
      _loading = false;
      _error = e.toString();
    });
  }
}
```

---

## Quick Commands

| Action | Command |
|--------|---------|
| Check service | `sudo systemctl status newsapp` |
| View logs | `sudo journalctl -u newsapp -f` |
| Restart | `sudo systemctl restart newsapp` |
| Stop | `sudo systemctl stop newsapp` |
| View cron logs | `cat /tmp/newsapp_cron.log` |
| SSH in | `ssh -i oracle-key.pem ubuntu@<IP>` |

Use your server IP (from step 1) wherever `<PUBLIC_IP>` appears.
