from flask import Flask, send_file, jsonify, request
from time import sleep
import requests
from random import shuffle

app = Flask(__name__)

def get_proxy_list():
    base_url = "https://raw.githubusercontent.com/afkarxyz/proxies/main/"
    proxy_types = ["http", "https", "socks4", "socks5"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    all_proxies = []
    
    for proxy_type in proxy_types:
        try:
            response = requests.get(f"{base_url}{proxy_type}", headers=headers)
            if response.status_code == 200:
                proxies = response.text.splitlines()
                formatted_proxies = [(proxy, proxy_type) for proxy in proxies]
                all_proxies.extend(formatted_proxies)
        except:
            continue
    
    if all_proxies:
        shuffle(all_proxies)
        return all_proxies
    return None

token_url = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'
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
    proxies = get_proxy_list()
    if not proxies:
        return {"error": "Failed to get proxy list"}
    
    # Get access token using proxies
    token = None
    for proxy, proxy_type in proxies:
        try:
            req = requests.get(
                token_url, 
                headers=headers, 
                proxies={proxy_type: proxy},
                timeout=10
            )
            if req.status_code == 200:
                token = req.json()
                break
        except:
            continue
    
    if not token:
        return {"error": "Failed to get access token"}

    # Define API endpoints
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
    
    # Try to get data using proxies
    for proxy, proxy_type in proxies:
        try:
            response = requests.get(
                url,
                headers=headers,
                proxies={proxy_type: proxy},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                sleep(int(response.headers.get("Retry-After", 1)) + 1)
                continue
            elif response.status_code == 401:
                return {"error": "Unauthorized access"}
            elif response.status_code == 403:
                return {"error": "Forbidden access"}
            elif response.status_code == 404:
                return {"error": "Resource not found"}
        except Exception as e:
            continue
            
    return {"error": "Failed to fetch data"}

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