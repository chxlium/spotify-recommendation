from dotenv import load_dotenv
import os
import time
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, session, redirect, url_for
import spotipy
import requests
import pandas as pd
import random

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")

# set the key for the token info in the session dictionary
TOKEN_INFO = 'token_info'

url = "https://accounts.spotify.com/api/token"

headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret
}

response = requests.post(url, headers=headers, data=data)

# init flask app
app = Flask(__name__)

# set the name of the session cookie
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

# set a random secret key to sign the cookie
app.secret_key = response.json()['access_token']

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = os.getenv("CLIENT_ID"),
        client_secret = os.getenv("CLIENT_SECRET"),
        redirect_uri=url_for('redirect_page', _external=True),
        scope="user-library-read playlist-modify-public playlist-modify-private",
    )

def get_token():
    token = session.get(TOKEN_INFO, None)
    if not token:
        redirect(url_for('login', __external=False))
    
    # check if token is expired
    now = int(time.time())
    is_expired = token['expires_at'] - now < 120
    if (is_expired):
        spoitfy_oauth = create_spotify_oauth()
        token = spoitfy_oauth.refresh_access_token(token['refresh_token'])

    return token


import ast
def get_top_picks(feature, df):
    res = []
    for i in range(len(df)):
        res += ast.literal_eval(df[feature][i])
    res = pd.Series(res)
    top_picks = res.value_counts()[:50]
    return top_picks.index


@app.route("/")
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)

@app.route("/redirect")
def redirect_page():
    # clear session
    session.clear()
    # get the authorization code 
    code = request.args.get("code")
    token = create_spotify_oauth().get_access_token(code)
    session[TOKEN_INFO] = token
    print(session[TOKEN_INFO])
    return redirect(url_for("get_recommendations", _external=True))


@app.route("/recommendations")
def get_recommendations():
    try:
        token = get_token()
    except:
        print('User not logged in')
        return redirect('/')
    
    #create a Spotify instance with the token
    sp = spotipy.Spotify(auth=token['access_token'])
    # get user playlists
    # get top genres
    df = pd.read_csv('df.csv')
    print(sp.recommendation_genre_seeds())
    top_genres = get_top_picks('artist_genres', df).tolist()
    random_genres = random.sample(top_genres, 2)
    print(top_genres)
    # get rancom tracks from your saved tracks
    random_tracks = df['track_uri'].sample(n=3).tolist()
    print(random_tracks)
    # get random artists from your saved tracks
    rancom_artisis = df['artist_uri'].sample(n=5).tolist()
    print(rancom_artisis)
    # get top audio features
    audio_features = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness', 'liveness',
                      'valence', 'tempo']
    top_audio_features = pd.DataFrame()
    for feature in audio_features:
        top_audio_features.loc[0, feature] = df[feature].mean()
    print(top_audio_features)
    # get recommendations

    recommendations = sp.recommendations(seed_artists=None, seed_genres=random_genres, seed_tracks=random_tracks, limit=30,
                                         min_danceability=0.4, max_danceability=0.8, min_energy=0.2, max_energy=1,
                                         min_loudness=-20, max_loudness=0, min_speechiness=0, max_speechiness=0.4,
                                         min_acousticness=0, max_acousticness=1, min_instrumentalness=0, max_instrumentalness=0.5,
                                         min_liveness=0, max_liveness=0.4, min_valence=0.4, max_valence=1, min_tempo=150, max_tempo=180)
    # create a playlist if the playlist doesn't exist
    playlist = sp.user_playlist_create(user=sp.me()['id'], name='recommendation', public=True, description='Recoomendations based on your saved tracks')
    
    # artist I dont want to add
    artists = ['']
    # add tracks to the playlist
    track_uris = []
    for track in recommendations['tracks']:
        # I don't want to add track thant I already saved or from the artisit I saved
        if track['uri'] not in df['track_uri'] or track['artists'][0]['uri'] not in df['artist_uri']:
            track_uris.append(track['uri'])
    # sp.playlist_add_items(playlist['id'], track_uris)
    sp.user_playlist_add_tracks(sp.me()['id'], playlist['id'], track_uris)
    return recommendations

app.run(debug=True)