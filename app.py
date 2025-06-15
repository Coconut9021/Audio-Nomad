from flask import Flask, request, url_for, session, redirect, render_template
import asyncio
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from ShazamAPI import Shazam
import os
from termcolor import colored
import webbrowser  
import time
from deep_translator import GoogleTranslator
import aiosqlite
import sqlite3
import re
import json
from tkinter import filedialog
from shazam_handler import song_regonize

# Initialize Flask app
app = Flask(__name__)

# set the name of the session cookie
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

# set a random secret key to sign the cookie
app.secret_key = 'ebbfZ%HJ!xYq4PP%d52VKpvnrWBrMD'

# set the key for the token info in the session dictionary
TOKEN_INFO = 'token_info'

#Resets logs file to allow user to look through current run information
open("log.txt", "w").close()

#request location of audio files from user
def openpath():
    print("making path request")
    filepath = filedialog.askdirectory()
    return filepath

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    print("started login functuion")
    # create a SpotifyOAuth instance and get the authorization URL
    auth_url = create_spotify_oauth().get_authorize_url()
    # redirect the user to the authorization URL
    return redirect(auth_url)

@app.route('/redirect')
def redirect_page():
    print("redirect function just started")
    # clear the session
    session.clear()
    # get the authorization code from the request parameters
    code = request.args.get('code')
    # exchange the authorization code for an access token and refresh token
    token_info = create_spotify_oauth().get_access_token(code)
    # save the token info in the session
    session[TOKEN_INFO] = token_info
    # redirect the user to the save_local_library route
    return redirect(url_for('shazam_search', _external=True)), print("redirect succsseful")

@app.route('/shazam_search')
def shazam_search():
    print("shazam search function is going")
    filepath = openpath()
    
    # redirect the user to the save_local_library route
    return redirect(url_for('save_local_library', external=True))

@app.route('/saveLocalLibrary')
async def save_local_library():
    print("saving loval library to spotify now")
    song_uris = []
    request_count = 0
    playlist_name = "audio nomad"
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print(colored('User not logged in', color='red'))
        return redirect("/")
    
    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # gets current users id
    user_id = sp.current_user()['id']
    
    #grabs current users playlists 
    current_playlists =  sp.current_user_playlists()['items']
    named_playlist_id = None

    #checks if playlist_name playlist exists
    for playlist in current_playlists:
        if(playlist['name']) == playlist_name:
            named_playlist_id = playlist['id']
    if not named_playlist_id:
        return "Please create the playlist you would like to use first"
    
    # checks how many songs have been added to the database 
    async with aiosqlite.connect('songs.db') as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM TrackInfo")
            recognized_tracks = await cur.fetchone()

    # Extract the count from the fetched result
    recognized_tracks_total = recognized_tracks[0]
    run_count = 0

    async with aiosqlite.connect('songs.db') as conn:
        async with conn.cursor() as cur:
            # get the track information from database
            # printProgressBar(run_count, recognized_tracks_total, prefix='Adding songs to spotify', suffix='Complete', length= 50)
            for i in range(1, recognized_tracks_total + 1):
                await cur.execute("SELECT title, artist FROM TrackInfo WHERE id = ?", (i,))
                track_info = await cur.fetchone()

                artist_name = track_info[1]
                song_title = track_info[0]
                query = 'track:{0} artist:{1}'.format(song_title, artist_name)

                #searchs the for song id from the track name, artist name and genre
                try:
                    sp_song_data = sp.search(query, limit=1, type='track', market=None)

                    # Check if there are any items in the search result
                    if sp_song_data['tracks']['items']:
                        sp_track_id = sp_song_data['tracks']['items'][0]['id']
                        # Append the track ids to a list of ids
                        song_uris.append(sp_track_id)
                        request_count += 1
                    else:
                        # Handle the case where no tracks are found
                        with open("log.txt", "a", encoding='utf-8', errors='ignore') as text:
                            text.write(f"Failed to locate {song_title} by {artist_name} on spotify\n")

                except (IndexError, UnicodeDecodeError) as e:
                    with open("log.txt", "a", encoding='utf-8', errors='ignore') as text:
                            text.write(f"Error processing: {song_title} by {artist_name}, Error: {e}\n")
                
                #check how many songs are in the list of URIs and adds them to spotify playlist
                if request_count >= 100:
                    #adds all the songs with an id in the song_uris list
                    sp.user_playlist_add_tracks(user_id, named_playlist_id, song_uris, position=None)
                    song_uris = []
                    request_count = 0

                run_count += 1
                # printProgressBar(run_count, recognized_tracks_total, prefix='Adding songs to spotify', suffix='Complete', length= 50)
    #adds any remaining songs from the uris list that are less than 100
    sp.user_playlist_add_tracks(user_id, named_playlist_id, song_uris, position=None)         
    return render_template('successful.html', track_info=track_info)

# function to get the token info from the session
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # if the token info is not found, redirect the user to the login route
        redirect(url_for('login', _external=False))
    
    # check if the token is expired and refresh it if necessary
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])

    return token_info

#function to get authenticaion complete
def create_spotify_oauth():    
    client_id, client_secret = load_credentials()

    if not client_id or not client_secret:
        print(colored("No credentials found. Please input credentials.", color='green'))
        client_id = input("Enter your Spotify Client ID: ")
        client_secret = input("Enter your Spotify Client Secret: ")
        save_credentials(client_id, client_secret)

    else:
        print(colored("Using saved credentials.", color='green'))

    return SpotifyOAuth(
        client_id = client_id,
        client_secret = client_secret,
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private'
    )

#saves credentials for the spotify developer account to JSON file for future use
def save_credentials(client_id, client_secret):
    data = {
        "client_id": client_id,
        "client_secret": client_secret
    }
    with open("spotify_credentials.json", "w") as file:
        json.dump(data, file)
    print(colored("Credentials saved successfully.", color='green'))
    
def load_credentials():
    try:
        with open("spotify_credentials.json", "r") as file:
            data = json.load(file)
        return data["client_id"], data["client_secret"]
    except FileNotFoundError:
        return None, None
    except json.JSONDecodeError:
        print(colored("Error loading credentials. Please check your JSON file.", color='red'))
        return None, None

# Open the URL in the default browser
webbrowser.open('http://127.0.0.1:5000')

# Run the Flask app
app.run(debug=False)
