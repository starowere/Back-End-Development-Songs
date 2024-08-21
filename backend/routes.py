from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200

@app.route("/count")
def count():
    """return length of data"""
    try:
        count = db.songs.count_documents({})
        return jsonify(dict(count=count)), 200
    except Exception as e:
        app.logger.error(f"Error fetching song count: {str(e)}")
        return jsonify(dict(error="Unable to fetch song count")), 500

@app.route('/song', methods=['GET'])
def songs():
    # Fetch all songs from the database
    songs_list = list(db.songs.find({}))

    # Convert BSON documents to JSON format
    songs_json = parse_json({"songs": songs_list})

    # Return the JSON data with HTTP 200 OK status
    return songs_json, 200

@app.route('/song/<id>', methods=['GET'])
def get_song_by_id(id):
    # Fetch the song by id from the database
    song = db.songs.find_one({"id": int(id)})

    if song:
        # Convert BSON document to JSON format
        song_json = parse_json(song)
        return song_json, 200
    else:
        return jsonify({"message": "song with id not found"}), 404

@app.route('/song', methods=['POST'])
def create_song():
    # Extract song data from the request body
    song_data = request.get_json()

    # Check if a song with the given id already exists
    existing_song = db.songs.find_one({"id": song_data["id"]})

    if existing_song:
        return jsonify({"Message": f"song with id {song_data['id']} already present"}), 302

    # Insert the new song into the database
    db.songs.insert_one(song_data)

    return jsonify({"Message": "Song created successfully"}), 201


@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    # Extract song data from the request body
    song_data = request.get_json()

    # Check if a song with the given id exists
    existing_song = db.songs.find_one({"id": id})

    if existing_song:
        # Update the song with the incoming request data
        db.songs.update_one({"id": id}, {"$set": song_data})
        return jsonify({"Message": "Song updated successfully"}), 200
    else:
        return jsonify({"Message": f"song with id {id} not found"}), 404

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    try:
        result = db.songs.delete_one({"id": int(id)})
        if result.deleted_count == 0:
            return jsonify({"message": "song not found"}), 404
        return '', 204
    except Exception as e:
        app.logger.error(f"Error deleting song: {str(e)}")
        return jsonify({"message": "internal server error"}), 500
