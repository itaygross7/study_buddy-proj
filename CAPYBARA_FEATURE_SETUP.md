# Capybara of the Day Feature - Setup Guide

## Overview

The "Meet the Family" feature displays a daily rotating capybara photo with funny commentary on the landing page. It fetches real capybara photos from Unsplash's free API.

## Features

- 🦫 **Real capybara photos** from Unsplash (high-quality, curated)
- 🎭 **12 unique family members** with distinct personalities
- 😂 **Funny commentary** in Chandler-style humor
- 📅 **Daily rotation** - changes automatically every day
- 💾 **Smart caching** - caches images for 24 hours to minimize API calls
- 🔒 **Proper attribution** - Credits photographers as required by Unsplash
- 🎯 **Graceful degradation** - Section hidden if API unavailable

## Setup Instructions

### Step 1: Get a Free Unsplash API Key

1. Go to [https://unsplash.com/developers](https://unsplash.com/developers)
2. Sign up for a free account (or log in)
3. Click "New Application"
4. Accept the API terms
5. Fill in application details:
   - **Application name**: StudyBuddy
   - **Description**: Educational platform using capybara photos for humor
6. Copy your **Access Key** (starts with letters and numbers)

**Note**: Free tier includes:
- 50 requests per hour
- Unlimited requests per month
- No credit card required

### Step 2: Configure Your Application

1. Open your `.env` file
2. Add the Unsplash access key:

```bash
# Unsplash API (Optional - for Capybara of the Day feature)
UNSPLASH_ACCESS_KEY="your_access_key_here"
```

3. Save the file

### Step 3: Restart Your Application

```bash
# If using Docker:
docker-compose restart app

# If using systemd:
sudo systemctl restart studybuddy

# If running locally:
# Just stop and start your Flask application
```

### Step 4: Verify It Works

1. Visit your homepage
2. Scroll down to see the "פגשו את המשפחה!" (Meet the Family) section
3. You should see a real capybara photo with funny commentary
4. Check the attribution at the bottom (photographer name + Unsplash link)

## How It Works

### Image Fetching

1. **First Request**: Fetches 12 capybara photos from Unsplash API
2. **Caching**: Stores images in `/tmp/capybara_image_cache.json` for 24 hours
3. **Subsequent Requests**: Uses cached images (no API calls)
4. **Daily Selection**: Uses day of year to deterministically select which image to show

### API Rate Limits

The implementation is designed to stay well within Unsplash's free tier limits:

- Fetches 12 images at once (only 1 API call)
- Caches for 24 hours (max 1 API call per day)
- ~30 API calls per month (well under the free tier)

### Fallback Behavior

If the Unsplash API is not configured or unavailable:

- ✅ Section is **completely hidden** (no broken images)
- ✅ Landing page still works perfectly
- ✅ No errors shown to users
- ✅ Logs warning message for debugging

## Attribution Requirements

Unsplash requires proper attribution. Our implementation automatically:

- ✅ Displays photographer name with link to their profile
- ✅ Links to Unsplash homepage
- ✅ Includes required UTM parameters
- ✅ Uses small, unobtrusive text below the image

## Troubleshooting

### Section Not Showing

**Possible causes:**

1. **No API key configured**
   - Solution: Add `UNSPLASH_ACCESS_KEY` to `.env` file

2. **Invalid API key**
   - Check logs: `docker logs studybuddy_app | grep -i unsplash`
   - Verify key in Unsplash dashboard
   - Generate new key if needed

3. **Rate limit exceeded**
   - Wait 1 hour for limit reset
   - Check if cached images exist: `ls -la /tmp/capybara_image_cache.json`
   - Cache will work even if API is rate-limited

4. **Network issues**
   - Check if container can reach unsplash.com: `docker exec studybuddy_app ping -c 3 unsplash.com`
   - Check firewall rules

### Check Logs

```bash
# View application logs
docker logs studybuddy_app | grep -i capybara

# Look for these messages:
# ✓ "Successfully fetched X capybara images" - Working!
# ⚠️ "Using cached capybara images" - Using cache (good)
# ⚠️ "Unsplash API key not configured" - Need to add key
# ⚠️ "Unsplash API rate limit exceeded" - Wait or use cache
```

### Cache Management

```bash
# View cache age
docker exec studybuddy_app ls -la /tmp/capybara_image_cache.json

# Clear cache to force refresh
docker exec studybuddy_app rm /tmp/capybara_image_cache.json

# Restart to fetch new images
docker-compose restart app
```

## Family Members

The feature includes 12 unique capybara family members:

1. **חורחה (Jorge)** - Food enthusiast: "אוהב אוכל יותר מכל דבר אחר"
2. **רוזה (Rosa)** - Always on phone: "תמיד עסוקה בטלפון"
3. **פבלו (Pablo)** - Always tired: "מתעייף מכל דבר"
4. **איזבל (Isabel)** - Always celebrating: "תמיד חוגגת משהו"
5. **קרלוס (Carlos)** - The philosopher: "הפילוסוף של המשפחה"
6. **לואיזה (Luisa)** - Professional: "מקצועית ורצינית"
7. **דייגו (Diego)** - A bit moody: "קצת עצבני לפעמים"
8. **מריה (Maria)** - Shy and sweet: "ביישנית ומתוקה"
9. **פרננדו (Fernando)** - Always cleaning: "תמיד מנקה אחרי כולם"
10. **ולנטינה (Valentina)** - Loves everyone: "מאוהבת בכולם"
11. **אנטוניו (Antonio)** - Always says no: "תמיד אומר 'לא'"
12. **אלנה (Elena)** - Just standing there: "פשוט עומדת שם"

Each family member rotates daily with a real capybara photo and personalized funny commentary from Avner!

## Security & Privacy

- ✅ Only fetches from official Unsplash API
- ✅ Content filter enabled (family-friendly only)
- ✅ HTTPS connections only
- ✅ No user data sent to Unsplash
- ✅ Proper attribution and licensing
- ✅ Images cached locally to minimize external requests

## Optional: Disable the Feature

To completely disable the feature:

1. Remove or comment out `UNSPLASH_ACCESS_KEY` from `.env`
2. Restart application
3. Section will be automatically hidden

No code changes needed!

## Support

- **Unsplash API Docs**: https://unsplash.com/documentation
- **Get Help**: https://unsplash.com/developers/help
- **Report Issues**: Check application logs first, then contact support

---

**Enjoy funny capybara photos every day! 🦫**
