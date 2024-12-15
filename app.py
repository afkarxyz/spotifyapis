from flask import Flask, jsonify, send_file
from flask_cors import CORS
from spotapi import Public

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/track/<track_id>')
def get_track(track_id):
    try:
        track_info = Public.song_info(track_id)
        return jsonify(track_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/album/<album_id>')
def get_album(album_id):
    try:
        album_items = list(Public.album_info(album_id))
        return jsonify(album_items)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/playlist/<playlist_id>')
def get_playlist(playlist_id):
    try:
        playlist_items = list(Public.playlist_info(playlist_id))
        return jsonify(playlist_items)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/artist/<artist_id>')
def get_artist(artist_id):
    try:
        artist_items = list(Public.artist_search(artist_id))
        return jsonify(artist_items)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/podcast/<podcast_id>')
def get_podcast(podcast_id):
    try:
        podcast_items = list(Public.podcast_info(podcast_id))
        return jsonify(podcast_items)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/episode/<episode_id>')
def get_episode(episode_id):
    try:
        episode_info = Public.podcast_episode_info(episode_id)
        return jsonify(episode_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
