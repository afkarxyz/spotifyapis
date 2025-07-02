from flask import Flask, send_file, jsonify
from time import sleep
import requests
import time
import pyotp
import base64
from random import randrange

app = Flask(__name__)

# https://github.com/visagenull/Spotify-Free
def get_random_user_agent():
    return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{randrange(11, 15)}_{randrange(4, 9)}) AppleWebKit/{randrange(530, 537)}.{randrange(30, 37)} (KHTML, like Gecko) Chrome/{randrange(80, 105)}.0.{randrange(3000, 4500)}.{randrange(60, 125)} Safari/{randrange(530, 537)}.{randrange(30, 36)}"

def generate_totp():
    secret_cipher = [37, 84, 32, 76, 87, 90, 87, 47, 13, 75, 48, 54, 44, 28, 19, 21, 22]
    processed = [byte ^ ((i % 33) + 9) for i, byte in enumerate(secret_cipher)]
    processed_str = "".join(map(str, processed))
    utf8_bytes = processed_str.encode('utf-8')
    hex_str = utf8_bytes.hex()
    secret_bytes = bytes.fromhex(hex_str)
    b32_secret = base64.b32encode(secret_bytes).decode('utf-8')
    totp = pyotp.TOTP(b32_secret)

    headers = {
        "Host": "open.spotify.com",
        "User-Agent": get_random_user_agent(),
        "Accept": "*/*",
    }

    try:
        resp = requests.get("https://open.spotify.com/api/server-time", headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Failed to get server time. Status code: {resp.status_code}")
        data = resp.json()
        server_time = data.get("serverTime")
        if server_time is None:
            raise Exception("Failed to fetch server time from Spotify")
        return totp, server_time
    except Exception as e:
        raise Exception(f"Error getting server time: {str(e)}")

token_url = 'https://open.spotify.com/api/token'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'Referer': 'https://open.spotify.com/',
    'Origin': 'https://open.spotify.com'
}

def get_spotify_data(type, id, additional_params=None):
    try:
        totp, server_time = generate_totp()
        otp_code = totp.at(int(server_time))
        timestamp_ms = int(time.time() * 1000)
        
        params = {
            'reason': 'transport',
            'productType': 'web-player',
            'totp': otp_code,
            'totpServerTime': server_time,
            'totpVer': '8',
            'sTime': server_time,
            'cTime': timestamp_ms,
            'buildVer': 'web-player_2025-06-11_1749636522102_27bd7d1',
            'buildDate': '2025-06-11'
        }
        
        req = requests.get(token_url, headers=headers, params=params)
        if req.status_code != 200:
            return {"error": f"Failed to get access token. Status code: {req.status_code}"}
        token = req.json()
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
        'episode': f'https://api.spotify.com/v1/episodes/{id}'
    }
    
    if type not in endpoints:
        return {"error": "Invalid type"}

    headers.update({'Authorization': f'Bearer {token["accessToken"]}'})
    
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