import json
from spotapi import Public

podcast_id = "6EmSBAixLaU1CwSu6gyujz"
for podcast_items in Public.podcast_info(podcast_id):
    print(json.dumps(podcast_items, indent=2))
