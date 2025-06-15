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
    return redirect(url_for('shazam_search', _external=True)), render_template('database_found.html')

@app.route('/shazam_search')
async def shazam_search():
    print("shazam_search function is going")
    dont_run_shazam = False

    # Database of all tracks found in the shazam database and song data
    conn = sqlite3.connect("songs.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM trackInfo")
    data = cur.fetchone()

    if data[0] != 0:
        print(colored("Data present in songs database would you like to search for the songs in the database or clear database.", color='red'))
        response = input("Y: To proceess data in database / N: To clear database and search tracks in tracks folder ")
        if response == 'y' or 'Y':
            dont_run_shazam = True
        
        if response == 'n' or 'N':
            # Drop the table to clear information
            cur.execute("DROP TABLE IF EXISTS TrackInfo")

            # Recreate the table 
            cur.execute("CREATE TABLE TrackInfo (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, artist TEXT)")

            # Commit the transaction to save the changes
            conn.commit() 
            
            dont_run_shazam = False

        else:
            print(colored("That is not a valid response.", color='red'))
            
    run_count = 0
    files = os.listdir("tracks")
    audio_files = len(files)
    if dont_run_shazam == True:
        return redirect(url_for('save_local_library', _external=True))
    
    else:
        try:
            printProgressBar(run_count, audio_files, prefix='Shazaming tracks', suffix='Complete', length= 50)
            for file in files:
                #list of supported audio formats
                audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a']
                _, file_extension = os.path.splitext(f'{openpath()}/{file}')

                #check to see if the file is an audio file that can be processed by ShazamAPI and runs the recognize function
                if file_extension.lower() in audio_extensions:

                    shazam_data = open(f'tracks/{file}', 'rb').read()
                    song_data = next(Shazam(shazam_data).recognizeSong())

                    #Check if track returned valid data
                    if song_data[1]["matches"] == []:
                        with open("log.txt", "a", encoding='utf-8', errors='ignore') as text:
                            text.write(f"{file} was not found by shazam API\n")

                    #Puts the track name and artist name in a variable to be processed 
                    else:
                        song_title = song_data[1]['track']['title']
                        artist_name = song_data[1]['track']['subtitle']
                        process_track_data(song_title, artist_name)
                        run_count += 1

                        # Initialize database connection and cursor within the route function
                        conn = sqlite3.connect("songs.db")
                        cur = conn.cursor()
                        # Inserts track information into a database
                        cur.execute("INSERT INTO TrackInfo (title, artist) VALUES (?, ?)", (song_title, artist_name))
                        conn.commit()
        
                else:
                    with open("log.txt", "a", encoding='utf-8', errors='ignore') as text:
                            text.write(f"{file} is not a supported file format\n")
                    audio_files = audio_files - 1

                printProgressBar(run_count, audio_files, prefix='Shazaming tracks', suffix='Complete', length= 50)
        except (ZeroDivisionError) as e:
            print(colored('Add audio files to tracks folder before running code', color="red"))
            return render_template("failed.html")
            
    # redirect the user to the save_local_library route
    return redirect(url_for('save_local_library', _external=True))

#Creates the progress bar to for the user to see how far the process is
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

#translates any non-english characters to english for spotify API to search
def is_english_char(song_title, artist_name):
    # Check if the character is a letter (uppercase or lowercase) in the Basic Latin range
    for char in song_title and artist_name: 
        if (ord(char) >= 0x0041 and ord(char) <= 0x005A) or (ord(char) >= 0x0061 and ord(char) <= 0x007A):
            return True
        else:
            return False

#Removes any unnecessary characters to be able to search on the spotify API
def process_track_data(song_title, artist_name):
    #removes apostrophes from the song title
    if "'" in song_title or artist_name:
        song_title = song_title.replace("'", "")
        artist_name = artist_name.replace("'", "")
    
    #removes commas from artist name
    if "," in artist_name:
        # Find the index of the first comma in the artist_name
        comma_index = artist_name.find(',')
    
        # If a comma is found, return the part of the string before the comma
        if comma_index != -1:
            artist_name = artist_name[:comma_index].strip()

    if "&" in artist_name:
        # Find the index of the first ampersand in the artist_name
        ampersand_index = artist_name.find('&')
    
        # If a comma is found, return the part of the string before the comma
        if ampersand_index != -1:
            artist_name =artist_name[:ampersand_index].strip()

    #removes parentheses and square brackets as well as there content from song title to just leave song name
    pattern = r"\([^)]*\)|\[[^\]]*\]"
    if "(" in song_title or "[" in song_title:
        song_title = re.sub(pattern, "", song_title)

    if "(" in artist_name or "[" in artist_name:
        artist_name = re.sub(pattern, "", artist_name)

    if is_english_char(song_title, artist_name) == False:
        try:
            song_title = GoogleTranslator(source='auto', target='en').translate(song_title)
            artist_name = GoogleTranslator(source='auto', target='en').translate(artist_name)
    
        except:
            with open("log.txt", "a", encoding='utf-8', errors='ignore') as text:
                    text.write(f"Failed to translate {song_title} by {artist_name}\n")

    # return processed song title and artist name

    return song_title, artist_name

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
            printProgressBar(run_count, recognized_tracks_total, prefix='Adding songs to spotify', suffix='Complete', length= 50)
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
                printProgressBar(run_count, recognized_tracks_total, prefix='Adding songs to spotify', suffix='Complete', length= 50)
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
