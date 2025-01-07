import json
from spotapi import Public

playlist_id = "37i9dQZEVXbNG2KDcFcKOF"
for playlist_items in Public.playlist_info(playlist_id):
    print(json.dumps(playlist_items, indent=2))
