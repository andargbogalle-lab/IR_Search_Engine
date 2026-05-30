# IR Search Engine - Deployment Guide

## 🚀 Deployment Options

### Option 1: PythonAnywhere (FREE & EASIEST) ⭐ RECOMMENDED

**Best for:** Academic projects, demos, free hosting

#### Steps:

1. **Create Account**
   - Go to https://www.pythonanywhere.com
   - Sign up for FREE account
   - You get: `yourusername.pythonanywhere.com`

2. **Upload Your Project**
   - Click "Files" tab
   - Upload your project as ZIP
   - Or use Git: `git clone your-repo-url`

3. **Create Virtual Environment**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 myenv
   pip install -r requirements.txt
   python -m nltk.downloader punkt stopwords
   ```

4. **Setup Database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Configure Web App**
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Manual configuration" → Python 3.10
   - Set source code: `/home/yourusername/IR_search_Engine`
   - Set working directory: `/home/yourusername/IR_search_Engine`
   
6. **Edit WSGI file**
   ```python
   import sys
   import os
   
   path = '/home/yourusername/IR_search_Engine'
   if path not in sys.path:
       sys.path.append(path)
   
   os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
   
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

7. **Set Environment Variables**
   - In "Web" tab, scroll to "Environment variables"
   - Add:
     - `SECRET_KEY`: your-secret-key
     - `DEBUG`: False
     - `ALLOWED_HOSTS`: yourusername.pythonanywhere.com

8. **Collect Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

9. **Reload Web App**
   - Click green "Reload" button
   - Visit: `https://yourusername.pythonanywhere.com`

---

### Option 2: Heroku (FREE TIER AVAILABLE)

**Best for:** Production-like environment, easy scaling

#### Steps:

1. **Install Heroku CLI**
   - Download from: https://devcenter.heroku.com/articles/heroku-cli

2. **Login**
   ```bash
   heroku login
   ```

3. **Create App**
   ```bash
   heroku create your-app-name
   ```

4. **Add Buildpack**
   ```bash
   heroku buildpacks:set heroku/python
   ```

5. **Set Environment Variables**
   ```bash
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set DEBUG=False
   heroku config:set ALLOWED_HOSTS="your-app-name.herokuapp.com"
   ```

6. **Deploy**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

7. **Run Migrations**
   ```bash
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   heroku run python -m nltk.downloader punkt stopwords
   ```

8. **Open App**
   ```bash
   heroku open
   ```

---

### Option 3: Render (FREE)

**Best for:** Modern deployment, automatic HTTPS

#### Steps:

1. **Create Account**
   - Go to https://render.com
   - Sign up (free)

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Or upload code

3. **Configure**
   - Name: `ir-search-engine`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start Command: `gunicorn core.wsgi:application`

4. **Add Environment Variables**
   - SECRET_KEY
   - DEBUG=False
   - ALLOWED_HOSTS=your-app.onrender.com

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

---

### Option 4: Railway (FREE)

**Best for:** Quick deployment, modern interface

#### Steps:

1. **Create Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **New Project**
   - Click "New Project"
   - Choose "Deploy from GitHub repo"
   - Select your repository

3. **Add Environment Variables**
   - Go to "Variables" tab
   - Add: SECRET_KEY, DEBUG, ALLOWED_HOSTS

4. **Deploy**
   - Railway auto-deploys
   - Get URL from "Settings" → "Domains"

---

### Option 5: Local Network Deployment

**Best for:** Presenting to advisor, local demo

#### Steps:

1. **Find Your IP Address**
   ```bash
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., 192.168.1.100)

2. **Update Settings**
   In `.env`:
   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
   ```

3. **Run Server**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

4. **Access**
   - On your computer: `http://localhost:8000`
   - On other devices: `http://192.168.1.100:8000`

---

## 📋 Pre-Deployment Checklist

### ✅ Required Files
- [x] `requirements.txt` - Python dependencies
- [x] `.env.example` - Environment variables template
- [x] `.gitignore` - Ignore sensitive files
- [x] `Procfile` - For Heroku deployment
- [x] `runtime.txt` - Python version

### ✅ Security Checklist
- [x] SECRET_KEY in environment variable
- [x] DEBUG=False in production
- [x] ALLOWED_HOSTS configured
- [x] No hardcoded passwords
- [x] .env file in .gitignore

### ✅ Database
- [x] Migrations created
- [x] Migrations applied
- [x] Admin user created

### ✅ Static Files
- [x] STATIC_ROOT configured
- [x] collectstatic command ready

---

## 🔧 Common Issues & Solutions

### Issue 1: "DisallowedHost" Error
**Solution:** Add your domain to ALLOWED_HOSTS in .env
```
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Issue 2: Static Files Not Loading
**Solution:** Run collectstatic
```bash
python manage.py collectstatic --noinput
```

### Issue 3: Database Errors
**Solution:** Run migrations
```bash
python manage.py migrate
```

### Issue 4: NLTK Data Missing
**Solution:** Download NLTK data
```bash
python -m nltk.downloader punkt stopwords
```

### Issue 5: Module Not Found
**Solution:** Install requirements
```bash
pip install -r requirements.txt
```

---

## 🎯 Recommended: PythonAnywhere

**Why?**
- ✅ Completely FREE
- ✅ No credit card required
- ✅ Easy setup (15 minutes)
- ✅ Perfect for academic projects
- ✅ Automatic HTTPS
- ✅ Good uptime
- ✅ Web-based console

**Limitations:**
- Free tier: 512MB storage, 100MB database
- Your URL: `yourusername.pythonanywhere.com`
- CPU time limits (but enough for demos)

---

## 📊 Deployment Comparison

| Platform | Cost | Ease | Speed | Best For |
|----------|------|------|-------|----------|
| **PythonAnywhere** | FREE | ⭐⭐⭐⭐⭐ | Fast | Academic |
| **Heroku** | FREE* | ⭐⭐⭐⭐ | Fast | Production |
| **Render** | FREE | ⭐⭐⭐⭐ | Medium | Modern |
| **Railway** | FREE* | ⭐⭐⭐⭐⭐ | Fast | Quick Demo |
| **Local Network** | FREE | ⭐⭐⭐⭐⭐ | Instant | Presentation |

*Free tier available with limitations

---

## 🚀 Quick Start (PythonAnywhere)

```bash
# 1. Upload project to PythonAnywhere

# 2. In Bash console:
mkvirtualenv --python=/usr/bin/python3.10 myenv
cd IR_search_Engine
pip install -r requirements.txt
python -m nltk.downloader punkt stopwords
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# 3. Configure Web app (see detailed steps above)

# 4. Reload and visit your site!
```

---

## 📞 Support

If you encounter issues:
1. Check the error logs
2. Verify environment variables
3. Ensure all migrations are applied
4. Check ALLOWED_HOSTS setting

---

## 🎓 For Your Advisor

**Live Demo URL:** `https://yourusername.pythonanywhere.com`

**Admin Access:**
- Username: admin
- Password: admin123

**Features to Demonstrate:**
1. Search with VSM and BM25
2. Upload documents (.txt, .pdf)
3. Bilingual support (English/Amharic)
4. Query suggestions
5. Spell correction
6. Search history

---

**Deployment Time:** 15-30 minutes  
**Recommended Platform:** PythonAnywhere (FREE)  
**Status:** Ready to deploy ✅
