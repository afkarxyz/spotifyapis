from flask import Flask, send_file, jsonify
from time import sleep
import requests
import base64
import datetime
import hashlib
import re
import time
import json
import pyotp

app = Flask(__name__)

AUTH_TOKEN = None
AUTH_TOKEN_EXPIRY = 0
SECRETS = None
SECRETS_EXPIRY = 0

def spotify_decode_secret(raw_secret):
    k = [(e ^ t % 33 + 9) for t, e in enumerate(raw_secret)]
    uint8_secret = [int(x) for x in "".join([str(x) for x in k]).encode("utf-8")]
    bytes_secret = bytes(uint8_secret)
    return base64.b32encode(bytes_secret).decode("ascii")

def spotify_totp(decoded_secret, timestamp):
    return pyotp.hotp.HOTP(s=decoded_secret, digits=6, digest=hashlib.sha1).at(int(timestamp / 30))

def get_spotify_secrets():
    global SECRETS, SECRETS_EXPIRY
    if not SECRETS or SECRETS_EXPIRY < time.time():
        response = requests.get("https://open.spotify.com", 
                              headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"}, 
                              timeout=10)
        response.raise_for_status()
        
        match = re.search(r"\"([\w/:\-\.]*/web-player\.\w*\.js)\"", response.content.decode("utf-8"))
        if not match:
            raise Exception("Could not find assets URL")
        
        response = requests.get(match.group(1), timeout=10)
        response.raise_for_status()
        
        match = re.search(r"\'({\"validUntil\":[^']*)\'", response.content.decode("utf-8"))
        if not match:
            raise Exception("Could not find secrets in assets")
        
        data = json.loads(match.group(1))
        SECRETS = data["secrets"]
        SECRETS_EXPIRY = datetime.datetime.fromisoformat(data["validUntil"].split(".")[0]).timestamp()
    return SECRETS

def get_access_token():
    global AUTH_TOKEN, AUTH_TOKEN_EXPIRY
    if not AUTH_TOKEN or AUTH_TOKEN_EXPIRY < time.time():
        secrets = get_spotify_secrets()
        decoded_secret = spotify_decode_secret(secrets[0]["secret"])
        version = secrets[0]["version"]
        c_time = int(time.time() * 1000)
        totp = spotify_totp(decoded_secret, c_time / 1000)

        params = {
            "reason": "init",
            "productType": "web-player",
            "totp": totp,
            "totpServer": totp,
            "totpVer": version,
        }
        
        req = requests.get(token_url, params=params, headers={
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "priority": "u=1, i",
            "referer": "https://open.spotify.com/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }, timeout=10)
        
        if req.status_code != 200:
            raise Exception(f"Failed to get access token. Status code: {req.status_code}")
        
        token_data = req.json()
        AUTH_TOKEN = token_data.get("accessToken")
        AUTH_TOKEN_EXPIRY = token_data.get("accessTokenExpirationTimestampMs", 0) / 1000
    return AUTH_TOKEN

token_url = 'https://open.spotify.com/api/token'
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://open.spotify.com/',
    'Origin': 'https://open.spotify.com'
}

def get_spotify_data(type, id, additional_params=None):
    try:
        access_token = get_access_token()
        if not access_token:
            return {"error": "Failed to get access token"}
    except Exception as e:
        return {"error": f"Failed to get access token: {str(e)}"}
    
    endpoints = {
        'track': f'https://api.spotify.com/v1/tracks/{id}',
        'album': f'https://api.spotify.com/v1/albums/{id}',
        'album_tracks': f'https://api.spotify.com/v1/albums/{id}/tracks',
        'artist': f'https://api.spotify.com/v1/artists/{id}',
        'artist_albums': f'https://api.spotify.com/v1/artists/{id}/albums',
        'artist_top_tracks': f'https://api.spotify.com/v1/artists/{id}/top-tracks',
        'artist_related': f'https://api.spotify.com/v1/artists/{id}/related-artists',
        'playlist': f'https://api.spotify.com/v1/playlists/{id}',
        'playlist_tracks': f'https://api.spotify.com/v1/playlists/{id}/tracks',
        'show': f'https://api.spotify.com/v1/shows/{id}',
        'show_episodes': f'https://api.spotify.com/v1/shows/{id}/episodes',
        'episode': f'https://api.spotify.com/v1/episodes/{id}'    }
    
    if type not in endpoints:
        return {"error": "Invalid type"}

    headers.update({'Authorization': f'Bearer {access_token}'})
    
    url = endpoints[type]
    if additional_params:
        url += '?' + '&'.join([f'{k}={v}' for k, v in additional_params.items()])
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            sleep(int(response.headers.get("Retry-After", 1)) + 1)
            response = requests.get(url, headers=headers)
            return response.json() if response.status_code == 200 else {"error": "Rate limit exceeded"}
        elif response.status_code == 401:
            return {"error": "Unauthorized access"}
        elif response.status_code == 403:
            return {"error": "Forbidden access"}
        elif response.status_code == 404:
            return {"error": "Resource not found"}
        else:
            return {"error": f"Request failed with status code: {response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/<type>/<id>')
def get_info(type, id):
    data = get_spotify_data(type, id)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)