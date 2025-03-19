import requests
import os
import configparser
import tkinter as tk
from tkinter import filedialog

def load_or_create_config(config_file="config.ini"):
    """Load or create config.ini file, prompt for input if necessary"""
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_file):
        print("⚙️ Config.ini file does not exist. Creating a new file...")
        config['osu'] = {
            'client_id': '',
            'client_secret': ''
        }
        # Prompt user for input
        print("❗️ Please enter osu! API credentials.")
        print("👉 You can create CLIENT_ID and CLIENT_SECRET at: https://osu.ppy.sh/home/account/edit#oauth")
        client_id = input("🔍 Enter CLIENT_ID: ").strip()
        client_secret = input("🔍 Enter CLIENT_SECRET: ").strip()
        
        # Save credentials to config
        config['osu']['client_id'] = client_id
        config['osu']['client_secret'] = client_secret
        
        # Write config file
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        print(f"✅ Created {config_file} with credentials.")
    else:
        config.read(config_file)
        if not config.has_section('osu') or not config['osu'].get('client_id') or not config['osu'].get('client_secret') or not get_access_token(config['osu']['client_id'], config['osu']['client_secret']):
            print("❌ Invalid credentials. Please re-enter:")
            client_id = input("🔍 Enter CLIENT_ID: ").strip()
            client_secret = input("🔍 Enter CLIENT_SECRET: ").strip()
            config['osu']['client_id'] = client_id
            config['osu']['client_secret'] = client_secret
            with open(config_file, 'w') as configfile:
                config.write(configfile)
            print(f"✅ Updated {config_file}.")
    
    return config['osu']['client_id'], config['osu']['client_secret']

def get_access_token(CLIENT_ID, CLIENT_SECRET):
    """Get access token from osu! API v2"""
    url = "https://osu.ppy.sh/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "public"
    }
    response = requests.post(url, json=data)
    return response.json().get("access_token")

def get_user_id(access_token, username):
    """Get user ID from username"""
    url = f"https://osu.ppy.sh/api/v2/users/{username}/osu"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json().get("id")

def choose_save_directory():
    """Choose directory to save beatmap"""
    root = tk.Tk()
    root.withdraw()
    save_dir = filedialog.askdirectory(title="Choose directory to save beatmap")
    root.destroy()
    return save_dir

def sanitize_filename(filename):
    """Remove invalid characters using translate"""
    invalid_chars = '<>:"/\\|?*'
    # Create translation table to remove invalid characters
    translation_table = str.maketrans('', '', invalid_chars)
    sanitized = filename.translate(translation_table)
    return sanitized.strip()

def download_beatmap(save_dir, beatmapset_id, beatmap_file_name):
    """Download beatmap from Beatconnect"""
    output_file = os.path.join(save_dir, f"{beatmap_file_name}.osz")
    url = f"https://beatconnect.io/b/{beatmapset_id}"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(output_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        print(f"✔️ Downloaded beatmap to {output_file}")
        print("--------------------")
    else:
        print(f"⚠️ Error: Unable to download beatmap. Error code: {response.status_code}")
        print("--------------------")

def download_all_played_beatmaps(access_token, user_id, min_play_count):
    """Get list of all beatmaps played by the user"""
    save_dir = choose_save_directory()
    print(f"📂 Beatmap save directory: {save_dir}")
    print("🔄 Downloading beatmaps...")
    print("--------------------")
    if not save_dir:
        print("⚠️ Please choose a directory to save beatmaps!")
        print(exit)
        return
    
    offset = 0
    limit = 50  # Maximum number of requests per request
    i = 0 # Count number of beatmaps
    is_reached_min_play_count = False
    beatmap_link_list = []
    url = f"https://osu.ppy.sh/api/v2/users/{user_id}/beatmapsets/most_played"

    headers = {"Authorization": f"Bearer {access_token}"}

    while True:
        params = {"limit": limit, "offset": offset}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print("⚠️ Error fetching beatmap list!")
            break

        data = response.json()

        if is_reached_min_play_count:
            print("🎉 Beatmap download complete!")
            break

        if not data:
            print("☹️ No beatmap to download!")
            break  # No more data to fetch

        for beatmap in data:
            beatmap_info = {
                "title": beatmap["beatmapset"]["title"],
                "artist": beatmap["beatmapset"]["artist"],
                "mapper": beatmap["beatmapset"]["creator"],
                "play_count": beatmap["count"],
                "beatmap_url": f"https://osu.ppy.sh/beatmapsets/{beatmap['beatmapset']['id']}"
            }

            beatmap_play_count = beatmap_info["play_count"]
            if beatmap_play_count < min_play_count:
                is_reached_min_play_count = True
                break

            beatmap_link = beatmap_info["beatmap_url"]
            if beatmap_link not in beatmap_link_list:
                i += 1
                beatmap_link_list.append(beatmap_link)
                print(f"{i}. {beatmap_info['title']} - {beatmap_info['artist']} (Mapped by {beatmap_info['mapper']})")
                print(f"   🔗 Link: {beatmap_info['beatmap_url']} | 🎮 Play count: {beatmap_info['play_count']}")

                # Download beatmap
                beatmapset_id = beatmap['beatmapset']['id']
                beatmap_file_name = f"{beatmapset_id} - {beatmap['beatmapset']['title']} - {beatmap_info['artist']} - Mapped by {beatmap_info['mapper']}"
                beatmap_file_name = sanitize_filename(beatmap_file_name)
                download_beatmap(save_dir, beatmapset_id, beatmap_file_name)

        offset += 1  # Fetch next page of data
    
    return

if __name__ == "__main__":
    # Load or create config
    CLIENT_ID, CLIENT_SECRET = load_or_create_config()
    if not CLIENT_ID or not CLIENT_SECRET:
        print("⚠️ Unable to continue due to missing credentials!")
        input("Press Enter to exit...")
        exit()

    # Create access token
    access_token:str
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    while not access_token:
        print("⚠️  Unable to get access token!")
        CLIENT_ID, CLIENT_SECRET = load_or_create_config()
        access_token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    print("🔑 Access token obtained successfully!")
    print("--------------------")

    # Enter username
    USERNAME = input("🔍 Enter player's username: ").strip()
    user_id = get_user_id(access_token, USERNAME)
    while not user_id:
        print("⚠️ Player not found!")
        USERNAME = input("🔍 Enter player's username: ").strip()
        user_id = get_user_id(access_token, USERNAME)
    print("--------------------")

    # Enter minimum play count
    while True:
        min_play_count: int
        try:
            min_play_count = int(input("⌨️  Enter minimum play count for a beatmap to be downloaded: "))
            if min_play_count < 1:
                print("⚠️ Minimum play count must be greater than 0!")
            else:
                print("--------------------")
                download_all_played_beatmaps(access_token, user_id, min_play_count)
                break
        except ValueError:
            print("⚠️ Invalid play count!")
    print("Press Enter to exit...")
    input()