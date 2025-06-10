from flask import Flask, send_file, jsonify, request
from time import sleep
import requests
import hmac
import time
import hashlib
from typing import Tuple, Callable

app = Flask(__name__)

_TOTP_SECRET = bytearray([53,53,48,55,49,52,53,56,53,51,52,56,55,52,57,57,53,57,50,50,52,56,54,51,48,51,50,57,51,52,55])

def generate_totp(
    secret: bytes = _TOTP_SECRET,
    algorithm: Callable[[], object] = hashlib.sha1,
    digits: int = 6,
    counter_factory: Callable[[], int] = lambda: int(time.time()) // 30,
) -> Tuple[str, int]:
    counter = counter_factory()
    hmac_result = hmac.new(
        secret, counter.to_bytes(8, byteorder="big"), algorithm
    ).digest()

    offset = hmac_result[-1] & 15
    truncated_value = (
        (hmac_result[offset] & 127) << 24
        | (hmac_result[offset + 1] & 255) << 16
        | (hmac_result[offset + 2] & 255) << 8
        | (hmac_result[offset + 3] & 255)
    )
    return (
        str(truncated_value % (10**digits)).zfill(digits),
        counter * 30_000,
    )

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
        totp, timestamp = generate_totp()
        
        params = {
            "reason": "transport",
            "productType": "web-player",
            "totp": totp,
            "totpVer": 5,
            "ts": timestamp,
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
        'episode': f'https://api.spotify.com/v1/episodes/{id}',
        'audiobook': f'https://api.spotify.com/v1/audiobooks/{id}',
        'chapter': f'https://api.spotify.com/v1/chapters/{id}',
        'genre': 'https://api.spotify.com/v1/recommendations/available-genre-seeds',
        'markets': 'https://api.spotify.com/v1/markets',
        'categories': 'https://api.spotify.com/v1/browse/categories',
        'category_playlists': f'https://api.spotify.com/v1/browse/categories/{id}/playlists',
        'featured_playlists': 'https://api.spotify.com/v1/browse/featured-playlists',
        'new_releases': 'https://api.spotify.com/v1/browse/new-releases',
        'recommendations': 'https://api.spotify.com/v1/recommendations',
        'search': 'https://api.spotify.com/v1/search',
        'user_profile': f'https://api.spotify.com/v1/users/{id}',
        'user_playlists': f'https://api.spotify.com/v1/users/{id}/playlists',
        'player': 'https://api.spotify.com/v1/me/player'
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

@app.route('/browse/<type>')
def browse_endpoints(type):
    if type in ['genres', 'markets', 'categories', 'featured-playlists', 'new-releases']:
        data = get_spotify_data(type, None)
        return jsonify(data)
    return jsonify({"error": "Invalid browse type"})

@app.route('/search')
def search():
    query = request.args.get('q')
    type = request.args.get('type', 'track,artist,album,playlist')
    limit = request.args.get('limit', 20)
    offset = request.args.get('offset', 0)
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"})
    
    params = {
        'q': query,
        'type': type,
        'limit': limit,
        'offset': offset
    }
    
    data = get_spotify_data('search', None, additional_params=params)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)