# 🚀 Deployment Instructions for StudyBuddy

## Critical: CSS Must Be Rebuilt Before Deployment

**⚠️ IMPORTANT:** Changes to `ui/static/css/input.css` are NOT automatically visible until you rebuild the CSS file.

### Why This Matters
- The browser loads `ui/static/css/styles.css` (compiled/minified version)
- Changes in `input.css` need to be compiled using Tailwind CSS
- **Docker builds include CSS compilation** in the build stage
- For local/manual deployment, you **MUST** rebuild CSS

---

## Deployment Methods

### Method 1: Docker Compose (Recommended)

This is the **safest method** because the Dockerfile automatically rebuilds CSS during the build process.

```bash
# 1. Pull latest changes
git pull

# 2. Rebuild and restart containers (CSS is automatically rebuilt)
docker-compose down
docker-compose up --build -d

# 3. Check logs to ensure everything started correctly
docker-compose logs -f web
```

**What the Dockerfile does:**
1. Installs Node.js and npm
2. Copies `package.json` and installs Tailwind CSS
3. Copies `ui/static/css/input.css` and `tailwind.config.js`
4. Runs `npm run tailwind:build` to compile CSS
5. Copies compiled `styles.css` to the final image

---

### Method 2: Manual Deployment (Local/Server)

If you're deploying **without Docker**, you **MUST** rebuild CSS manually:

```bash
# 1. Pull latest changes
git pull

# 2. Install Node dependencies (only needed first time or after package.json changes)
npm install

# 3. Rebuild CSS (CRITICAL STEP)
npm run tailwind:build

# 4. Restart your Flask application
# Option A: Using systemd
sudo systemctl restart studybuddy

# Option B: Using your custom start script
./start-local.sh

# Option C: Manual Flask restart
pkill -f "gunicorn"
gunicorn --bind 0.0.0.0:5000 --workers 4 "app:create_app()"
```

---

## Verifying Your Deployment

### 1. Check CSS File Timestamp
```bash
# The styles.css file should be recently modified
ls -lh ui/static/css/styles.css

# Expected output: file dated today/recently
# -rw-rw-r-- 1 user user 39K Dec  6 08:04 ui/static/css/styles.css
```

### 2. Check CSS Cache Busting
Open your browser and check the CSS URL:
- It should include `?v=2024.12.06` or similar version parameter
- Example: `http://your-site.com/static/css/styles.css?v=2024.12.06`

### 3. Force Browser to Reload CSS
On your device (including iPhone):
- **Desktop:** Press `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
- **iPhone/Safari:** 
  1. Settings > Safari > Clear History and Website Data
  2. Or: Long-press the refresh button and select "Reload Without Content Blockers"

### 4. Test Mobile Functionality
On iPhone 15 Safari, verify:
- [ ] File upload button is large and tappable (48px minimum height)
- [ ] File selection shows visual feedback
- [ ] Chat textarea doesn't zoom on focus (font-size: 16px prevents iOS zoom)
- [ ] Language switcher buttons work
- [ ] Mobile menu opens smoothly
- [ ] Touch targets are properly sized (no tiny buttons)

---

## Common Issues & Solutions

### Issue 1: "Changes Not Visible on iPhone"

**Cause:** Browser cache or CSS not rebuilt

**Solution:**
```bash
# On server:
npm run tailwind:build
sudo systemctl restart studybuddy

# On iPhone:
# Clear Safari cache (Settings > Safari > Clear History and Website Data)
# Or use Private Browsing mode to test
```

### Issue 2: "Upload Not Working on iOS Safari"

**Symptoms:**
- File button doesn't respond
- No file picker appears
- Upload fails silently

**Solution:**
All iOS Safari fixes are already in the code:
- ✅ Font-size: 16px on inputs (prevents zoom)
- ✅ `-webkit-appearance` fixes
- ✅ iOS-specific file input handling
- ✅ XMLHttpRequest instead of Fetch API
- ✅ Visual feedback on file selection

**If still not working:**
1. Check browser console for errors (use Safari remote debugging)
2. Ensure HTTPS is enabled (iOS restricts some features on HTTP)
3. Verify file size limits (max 50MB)

### Issue 3: "Chat Not Working"

**Symptoms:**
- Messages don't send
- "AI not configured" errors
- Empty responses

**Solution:**
```bash
# Check if AI keys are configured
python check_config.py

# Expected output should show:
# ✅ OpenAI API Key: Configured
# OR
# ✅ Gemini API Key: Configured

# If not configured, add to .env file:
GEMINI_API_KEY="your_gemini_key_here"
# OR
OPENAI_API_KEY="sk-your_openai_key_here"

# Restart the application
docker-compose restart web
```

### Issue 4: "CSS Not Loading"

**Symptoms:**
- Site has no styling
- Looks like plain HTML

**Solution:**
```bash
# 1. Verify CSS file exists and has content
ls -lh ui/static/css/styles.css
cat ui/static/css/styles.css | head -5

# 2. Check Flask static file serving
# Access directly: http://your-site.com/static/css/styles.css

# 3. Rebuild CSS if file is empty or missing
npm run tailwind:build

# 4. Check file permissions
chmod 644 ui/static/css/styles.css
```

---

## Mobile-Specific Deployment Checklist

Before marking deployment as complete, test on **actual mobile devices**:

### iPhone/iOS Safari Testing
- [ ] Open site in Safari (not Chrome on iOS - it uses different engine)
- [ ] Test file upload (must show iOS file picker)
- [ ] Test chat (messages must send and receive)
- [ ] Test language switcher (buttons must be tappable)
- [ ] Test mobile menu (hamburger menu must open/close smoothly)
- [ ] Verify no horizontal scrolling
- [ ] Verify text is readable (not too small)
- [ ] Verify buttons are tappable (not too small)

### Android/Chrome Testing
- [ ] File upload works
- [ ] Chat works
- [ ] Navigation works
- [ ] No layout issues

### Desktop Testing
- [ ] All functionality works
- [ ] Responsive breakpoints work (resize browser)
- [ ] No mobile-only issues on desktop

---

## Quick Deployment Command

For Docker deployments, use this one-liner:

```bash
git pull && docker-compose down && docker-compose up --build -d && docker-compose logs -f web
```

This will:
1. Pull latest code
2. Stop current containers
3. Rebuild images (including CSS compilation)
4. Start containers in detached mode
5. Show logs for verification

---

## Emergency Rollback

If deployment fails:

```bash
# Stop current deployment
docker-compose down

# Checkout previous working version
git log --oneline -5  # Find last working commit
git checkout <commit-hash>

# Rebuild and deploy
docker-compose up --build -d
```

---

## Production Checklist

Before deploying to production:

- [ ] Test locally first
- [ ] Rebuild CSS with `npm run tailwind:build`
- [ ] Test on iPhone/Safari
- [ ] Test on Android/Chrome
- [ ] Test on Desktop browsers
- [ ] Verify AI keys are configured
- [ ] Check logs for errors
- [ ] Verify HTTPS is working
- [ ] Test file upload (text and file)
- [ ] Test chat functionality
- [ ] Test all tools (summary, flashcards, quiz, homework)
- [ ] Clear browser cache and test again

---

## Support

If you encounter issues after following these instructions:

1. **Check logs:** `docker-compose logs -f web`
2. **Run diagnostics:** `python check_config.py`
3. **Verify CSS:** `ls -lh ui/static/css/styles.css`
4. **Test in private/incognito mode** (eliminates cache issues)
5. **Check browser console** for JavaScript errors

---

## Version Information

- CSS Version: Controlled by `config.VERSION` in `src/infrastructure/config.py`
- Current Version: `2024.12.06`
- Update version after major CSS changes to force browser refresh

---

**Remember:** The #1 reason for "changes not visible" is **not rebuilding CSS**. Always run `npm run tailwind:build` or use Docker which does it automatically!
