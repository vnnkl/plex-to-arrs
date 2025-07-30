import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import hashlib

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys from environment variables
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Quality Profile Settings
RADARR_QUALITY_PROFILE = int(os.getenv("RADARR_QUALITY_PROFILE", "4"))  # Default: HD-1080p
SONARR_QUALITY_PROFILE = int(os.getenv("SONARR_QUALITY_PROFILE", "4"))  # Default: HD-1080p

RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878/api/v3")
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989/api/v3")
RADARR_ROOT_FOLDER = "/config/Downloads/complete/Filme"
SONARR_ROOT_FOLDER = "/config/Downloads/complete/Serien"

# Language Profile ID for Sonarr
LANGUAGE_PROFILE = 1  # Adjust this value based on your Sonarr configuration

# Cache settings
CACHE_FILE = "/app/logs/sync_cache.json"
CACHE_REFRESH_HOURS = int(os.getenv("CACHE_REFRESH_HOURS", "24"))  # Refresh cache daily

def load_sync_cache():
    """Load the sync cache from disk"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                # Check if cache needs refresh
                last_refresh = datetime.fromisoformat(cache.get('last_refresh', '2000-01-01T00:00:00'))
                if datetime.now() - last_refresh > timedelta(hours=CACHE_REFRESH_HOURS):
                    print(f"🔄 Cache expired (>{CACHE_REFRESH_HOURS}h old), will refresh from servers")
                    return {'synced_items': {}, 'last_refresh': datetime.now().isoformat()}
                return cache
        else:
            print("📝 Creating new sync cache")
            return {'synced_items': {}, 'last_refresh': datetime.now().isoformat()}
    except Exception as e:
        print(f"⚠️  Error loading cache: {e}, creating new cache")
        return {'synced_items': {}, 'last_refresh': datetime.now().isoformat()}

def save_sync_cache(cache):
    """Save the sync cache to disk"""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"⚠️  Error saving cache: {e}")

def get_item_key(title, media_type, year=None):
    """Generate a unique key for a watchlist item"""
    key_string = f"{title}|{media_type}|{year or 'unknown'}"
    return hashlib.md5(key_string.encode()).hexdigest()

def is_item_synced(cache, title, media_type, year=None):
    """Check if an item has already been synced"""
    item_key = get_item_key(title, media_type, year)
    return item_key in cache['synced_items']

def mark_item_synced(cache, title, media_type, year=None, target_service=None):
    """Mark an item as successfully synced"""
    item_key = get_item_key(title, media_type, year)
    cache['synced_items'][item_key] = {
        'title': title,
        'media_type': media_type,
        'year': year,
        'target_service': target_service,
        'synced_at': datetime.now().isoformat()
    }

def refresh_cache_from_servers(cache):
    """Refresh cache by checking what's actually in Radarr/Sonarr"""
    print("🔄 Refreshing cache from Radarr/Sonarr...")
    try:
        # Check Radarr movies
        headers = {'X-Api-Key': RADARR_API_KEY}
        response = requests.get(f"{RADARR_URL}/movie", headers=headers, timeout=30)
        if response.status_code == 200:
            movies = response.json()
            print(f"📽️  Found {len(movies)} movies in Radarr")
            
        # Check Sonarr series
        headers = {'X-Api-Key': SONARR_API_KEY}
        response = requests.get(f"{SONARR_URL}/series", headers=headers, timeout=30)
        if response.status_code == 200:
            series = response.json()
            print(f"📺 Found {len(series)} series in Sonarr")
            
        # Update cache refresh time
        cache['last_refresh'] = datetime.now().isoformat()
        print("✅ Cache refreshed successfully")
        
    except Exception as e:
        print(f"⚠️  Error refreshing cache: {e}")
        
    return cache

def validate_quality_profiles():
    """Validate that the quality profiles exist and show current settings"""
    print(f"📋 Quality Profile Settings:")
    print(f"  🎬 Radarr (Movies): Profile ID {RADARR_QUALITY_PROFILE}")
    print(f"  📺 Sonarr (TV Shows): Profile ID {SONARR_QUALITY_PROFILE}")
    
    # Try to validate Radarr profile
    try:
        headers = {"X-Api-Key": RADARR_API_KEY}
        response = requests.get(f"{RADARR_URL}/qualityProfile", timeout=10, headers=headers)
        if response.status_code == 200:
            profiles = response.json()
            radarr_profile = next((p for p in profiles if p['id'] == RADARR_QUALITY_PROFILE), None)
            if radarr_profile:
                print(f"  ✅ Radarr Profile: {radarr_profile['name']}")
            else:
                print(f"  ⚠️  Radarr Profile ID {RADARR_QUALITY_PROFILE} not found!")
    except Exception as e:
        print(f"  ❌ Could not validate Radarr profile: {e}")

validate_quality_profiles()

def fetch_plex_watchlist():
    print("Fetching Plex watchlist...")
    plex_url = f"https://metadata.provider.plex.tv/library/sections/watchlist/all?X-Plex-Token={PLEX_TOKEN}"
    response = requests.get(plex_url)
    root = ET.fromstring(response.content)
    return root.findall('Directory') + root.findall('Video')

def fetch_tmdb_id(title, media_type):
    if media_type == "show":
        search_url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={title}"
    else:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    response = requests.get(search_url)
    if response.status_code == 200:
        results = response.json().get('results')
        if results:
            # Assuming the first result is the most relevant one
            return results[0]['id']
        else:
            print(f"No TMDB ID found for {media_type} '{title}'")
            return None
    else:
        print(f"Failed to retrieve TMDB ID for {media_type} '{title}'")
        return None

def add_to_radarr(tmdb_id, title):
    print(f"Adding movie '{title}' to Radarr...")
    payload = {
        "title": title,
        "qualityProfileId": int(RADARR_QUALITY_PROFILE),
        "tmdbId": tmdb_id,
        "rootFolderPath": RADARR_ROOT_FOLDER,
        "monitored": True,
        "addOptions": {
            "searchForMovie": True
        }
    }
    
    headers = {"X-Api-Key": RADARR_API_KEY, "Content-Type": "application/json"}
    radarr_add_url = f"{RADARR_URL}/movie"
    
    try:
        response = requests.post(radarr_add_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            print(f"✅ Added movie '{title}' to Radarr successfully.")
        elif response.status_code == 400:
            try:
                error_data = response.json()
                if isinstance(error_data, list) and error_data:
                    error_message = error_data[0].get('errorMessage', 'Unknown error')
                else:
                    error_message = str(error_data)
                print(f"⚠️  Movie '{title}' not added: {error_message}")
            except:
                print(f"⚠️  Movie '{title}' not added: {response.text[:100]}")
        else:
            print(f"❌ Failed to add movie '{title}'. Status Code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error adding movie '{title}': {e}")

def add_to_radarr_with_cache(tmdb_id, title, cache, media_type, year):
    """Add movie to Radarr and update cache on success"""
    print(f"Adding movie '{title}' to Radarr...")
    payload = {
        "title": title,
        "qualityProfileId": int(RADARR_QUALITY_PROFILE),
        "tmdbId": tmdb_id,
        "rootFolderPath": RADARR_ROOT_FOLDER,
        "monitored": True,
        "addOptions": {
            "searchForMovie": True
        }
    }
    
    headers = {"X-Api-Key": RADARR_API_KEY, "Content-Type": "application/json"}
    radarr_add_url = f"{RADARR_URL}/movie"
    
    try:
        response = requests.post(radarr_add_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            print(f"✅ Added movie '{title}' to Radarr successfully.")
            mark_item_synced(cache, title, media_type, year, 'radarr')
            return True
        elif response.status_code == 400:
            try:
                error_data = response.json()
                if isinstance(error_data, list) and error_data:
                    error_message = error_data[0].get('errorMessage', 'Unknown error')
                    if 'already been added' in error_message:
                        print(f"✅ Movie '{title}' already exists in Radarr")
                        mark_item_synced(cache, title, media_type, year, 'radarr')
                        return True
                else:
                    error_message = str(error_data)
                print(f"⚠️  Movie '{title}' not added: {error_message}")
            except:
                print(f"⚠️  Movie '{title}' not added: {response.text[:100]}")
        else:
            print(f"❌ Failed to add movie '{title}'. Status Code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error adding movie '{title}': {e}")
    
    return False

def add_to_sonarr(tmdb_id, title):
    print(f"Adding series '{title}' to Sonarr...")
    payload = {
        "title": title,
        "qualityProfileId": int(SONARR_QUALITY_PROFILE),
        "languageProfileId": int(LANGUAGE_PROFILE),
        "tvdbId": tmdb_id,
        "rootFolderPath": SONARR_ROOT_FOLDER,
        "monitored": True,
        "addOptions": {
            "searchForMissingEpisodes": True
        }
    }
    sonarr_add_url = f"{SONARR_URL}/series?apikey={SONARR_API_KEY}"
    response = requests.post(sonarr_add_url, json=payload)
    if response.status_code == 201:
        print(f"Added series '{title}' to Sonarr successfully.")
    else:
        try:
            error_message = response.json()[0]['errorMessage']
            print(f"Failed to add series '{title}' to Sonarr. Error: {error_message}")
        except (KeyError, IndexError):
            print(f"Failed to add series '{title}' to Sonarr. Status Code: {response.status_code}")

def search_and_add_series(search_term):
    search_url = f"{SONARR_URL}/series/lookup"
    headers = {"X-Api-Key": SONARR_API_KEY}
    params = {"term": search_term}
    
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json()
        if results:
            series = results[0]  # Assuming the first search result is the desired series
            series_id = series["tvdbId"]
            add_series_url = f"{SONARR_URL}/series"
            payload = {
                "title": series["title"],
                "qualityProfileId": int(SONARR_QUALITY_PROFILE),
                "languageProfileId": int(LANGUAGE_PROFILE),
                "tvdbId": series_id,
                "rootFolderPath": SONARR_ROOT_FOLDER,
                "monitored": True,
                "addOptions": {
                    "searchForMissingEpisodes": True
                }
            }
            
            response = requests.post(add_series_url, headers=headers, json=payload)
            if response.status_code == 201:
                print(f"Added series '{series['title']}' to Sonarr successfully.")
            else:
                try:
                    error_message = response.json()[0]['errorMessage']
                    print(f"Failed to add series '{series['title']}' to Sonarr. Error: {error_message}")
                except (KeyError, IndexError):
                    print(f"Failed to add series '{series['title']}' to Sonarr. Status Code: {response.status_code}")
        else:
            print("No series found for the search term.")
    else:
        print("Failed to perform series search.")

def search_and_add_series_with_cache(search_term, cache, media_type, year):
    """Search and add series to Sonarr with cache tracking"""
    search_url = f"{SONARR_URL}/series/lookup"
    headers = {"X-Api-Key": SONARR_API_KEY}
    params = {"term": search_term}
    
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json()
        if results:
            series = results[0]  # Assuming the first search result is the desired series
            series_id = series["tvdbId"]
            add_series_url = f"{SONARR_URL}/series"
            payload = {
                "title": series["title"],
                "qualityProfileId": int(SONARR_QUALITY_PROFILE),
                "languageProfileId": int(LANGUAGE_PROFILE),
                "tvdbId": series_id,
                "rootFolderPath": SONARR_ROOT_FOLDER,
                "monitored": True,
                "addOptions": {
                    "searchForMissingEpisodes": True
                }
            }
            
            response = requests.post(add_series_url, headers=headers, json=payload)
            if response.status_code == 201:
                print(f"✅ Added series '{series['title']}' to Sonarr successfully.")
                mark_item_synced(cache, search_term, media_type, year, 'sonarr')
                return True
            else:
                try:
                    error_message = response.json()[0]['errorMessage']
                    if 'already been added' in error_message:
                        print(f"✅ Series '{search_term}' already exists in Sonarr")
                        mark_item_synced(cache, search_term, media_type, year, 'sonarr')
                        return True
                    print(f"⚠️  Failed to add series '{series['title']}' to Sonarr. Error: {error_message}")
                except (KeyError, IndexError):
                    print(f"❌ Failed to add series '{series['title']}' to Sonarr. Status Code: {response.status_code}")
        else:
            print("❌ No series found for the search term.")
    else:
        print("❌ Failed to perform series search.")
    
    return False

def main():
    # Add dry-run mode for testing
    DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
    GENERATE_CURL = os.getenv('GENERATE_CURL', 'false').lower() == 'true'
    
    # Add timestamp for Docker logging
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 60)
    print("🎬 PLEX WATCHLIST TO RADARR/SONARR SYNC")
    print(f"⏰ Started at: {timestamp}")
    print("=" * 60)
    
    # Load sync cache
    print("📋 Loading sync cache...")
    cache = load_sync_cache()
    cached_count = len(cache['synced_items'])
    print(f"💾 Found {cached_count} previously synced items")
    
    if DRY_RUN:
        print("🔍 DRY RUN MODE - No items will actually be added")
        print("-" * 60)
    elif GENERATE_CURL:
        print("🔧 CURL GENERATION MODE - Creating manual API commands")
        print("-" * 60)
    
    print("📡 Fetching Plex watchlist...")
    watchlist = fetch_plex_watchlist()
    print(f"📋 Found {len(watchlist)} items in Plex watchlist")
    
    if not watchlist:
        print("ℹ️  No items found in watchlist")
        return
    
    # Filter out already synced items
    new_items = []
    cached_items = []
    
    for item in watchlist:
        title = item.get('title')
        media_type = item.get('type')
        year = item.get('year')
        
        if is_item_synced(cache, title, media_type, year):
            cached_items.append(title)
        else:
            new_items.append(item)
    
    print(f"✅ {len(cached_items)} items already synced (skipping)")
    print(f"🆕 {len(new_items)} new items to process")
    
    if len(cached_items) > 0:
        print(f"📝 Previously synced: {', '.join(cached_items[:5])}" + 
              (f" and {len(cached_items)-5} more..." if len(cached_items) > 5 else ""))
    
    if not new_items:
        print("🎉 Nothing new to sync!")
        return
    
    movies_count = 0
    shows_count = 0
    unknown_count = 0
    newly_synced = 0
    
    print(f"\n🎯 Processing {len(new_items)} new items:")
    print("-" * 60)
    
    for i, item in enumerate(new_items, 1):
        title = item.get('title')
        media_type = item.get('type')
        year = item.get('year', 'Unknown')
        
        print(f"\n[{i}/{len(new_items)}] 📺 {title} ({year}) - Type: {media_type}")
        
        if media_type == "movie":
            movies_count += 1
            tmdb_id = fetch_tmdb_id(title, media_type)
            if tmdb_id is not None:
                if GENERATE_CURL:
                    # Generate curl command for manual execution
                    payload = {
                        "title": title,
                        "qualityProfileId": int(RADARR_QUALITY_PROFILE),
                        "tmdbId": tmdb_id,
                        "rootFolderPath": RADARR_ROOT_FOLDER,
                        "monitored": True,
                        "addOptions": {"searchForMovie": True}
                    }
                    print(f"🔧 [CURL] Movie: {title}")
                    print(f"curl -X POST '{RADARR_URL}/movie' \\")
                    print(f"  -H 'X-Api-Key: {RADARR_API_KEY}' \\")
                    print(f"  -H 'Content-Type: application/json' \\")
                    print(f"  -H 'Accept: application/json' \\")
                    print(f"  -d '{json.dumps(payload, separators=(',', ':'))}'")
                    print()
                    # Mark as synced for curl mode
                    mark_item_synced(cache, title, media_type, year, 'radarr-curl')
                    newly_synced += 1
                elif not DRY_RUN:
                    success = add_to_radarr_with_cache(tmdb_id, title, cache, media_type, year)
                    if success:
                        newly_synced += 1
                else:
                    print(f"🔍 [DRY RUN] Would add movie to Radarr: {title} (TMDB: {tmdb_id})")
            else:
                print(f"⚠️  Could not find TMDB ID for movie: {title}")
                
        elif media_type == "show":
            shows_count += 1
            tmdb_id = fetch_tmdb_id(title, media_type)
            if tmdb_id is not None:
                if GENERATE_CURL:
                    print(f"🔧 [CURL] TV Show: {title}")
                    print(f"# First search for the series:")
                    print(f"curl '{SONARR_URL}/series/lookup?term={title.replace(' ', '%20')}' \\")
                    print(f"  -H 'X-Api-Key: {SONARR_API_KEY}' \\")
                    print(f"  -H 'Accept: application/json'")
                    print(f"# Then add using the tvdbId from search results")
                    print()
                    # Mark as synced for curl mode
                    mark_item_synced(cache, title, media_type, year, 'sonarr-curl')
                    newly_synced += 1
                elif not DRY_RUN:
                    success = search_and_add_series_with_cache(title, cache, media_type, year)
                    if success:
                        newly_synced += 1
                else:
                    print(f"🔍 [DRY RUN] Would add series to Sonarr: {title} (TMDB: {tmdb_id})")
            else:
                print(f"⚠️  Could not find TMDB ID for series: {title}")
        else:
            unknown_count += 1
            print(f"❓ Unknown media type: {media_type}")
    
    # Save updated cache
    save_sync_cache(cache)
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"🎬 New movies processed: {movies_count}")
    print(f"📺 New TV shows processed: {shows_count}")
    print(f"❓ Unknown types: {unknown_count}")
    print(f"🆕 Items newly synced: {newly_synced}")
    print(f"💾 Total cached items: {len(cache['synced_items'])}")
    print(f"📋 Total watchlist items: {len(watchlist) if 'watchlist' in locals() else len(new_items) + len(cached_items)}")
    
    if DRY_RUN:
        print("\n💡 To actually add items, run without DRY_RUN=true")
        print("🔧 To generate manual curl commands, run with GENERATE_CURL=true")
    elif GENERATE_CURL:
        print("\n💡 Copy and paste the curl commands above to manually add items")
        print("🔧 Test individual commands first to verify authentication")
    elif newly_synced > 0:
        print(f"\n🎉 Successfully synced {newly_synced} new items!")
    else:
        print("\n✨ All watchlist items already synced - nothing to do!")

if __name__ == "__main__":
    main()
