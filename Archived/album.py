import json
from spotapi import Public

album_id = "4VZ7jhV0wHpoNPCB7Vmiml"
for album_items in Public.album_info(album_id):
    print(json.dumps(album_items, indent=2))
