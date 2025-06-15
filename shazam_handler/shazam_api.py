from flask import redirect, url_for
import asyncio
from ShazamAPI import Shazam
import os
import webbrowser  
import time
from deep_translator import GoogleTranslator
import aiosqlite
import sqlite3
from tkinter import filedialog
from termcolor import colored
import re

#uses shazam API to process audio and get info
async def song_regonize(filepath):
    print("shazam_search function is going")
    dont_run_shazam = False

    # Database of all tracks found in the shazam database and song data
    conn = sqlite3.connect("songs.db")
    cur = conn.cursor()

    #check to see if there is any data in the database of songs before starting incase user failed to finish process they dont have to restart
    cur.execute("SELECT COUNT(*) FROM trackInfo")
    data = cur.fetchone()

    #asks user if they would like to rescan audio files or continue with database info
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
    folder = os.listdir({filepath})
    audio_files = len(folder)
    if dont_run_shazam == True:
        return redirect(url_for('save_local_library', _external=True))
    
    else:
        try:
            printProgressBar(run_count, audio_files, prefix='Shazaming tracks', suffix='Complete', length= 50)
            for file in folder:
                #list of supported audio formats
                audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a']
                _, file_extension = os.path.splitext(f'{filepath}/{file}')

                #check to see if the file is an audio file that can be processed by ShazamAPI and runs the recognize function
                if file_extension.lower() in audio_extensions:

                    shazam_data = open(f'{filepath}/{file}', 'rb').read()
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
            return 
        
        print("Ive reached this point")
            
    # # redirect the user to the save_local_library route
    # return redirect(url_for('save_local_library', _external=True))

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

#translates any non-english characters to english for spotify API to search
def is_english_char(song_title, artist_name):
    # Check if the character is a letter (uppercase or lowercase) in the Basic Latin range
    for char in song_title and artist_name: 
        if (ord(char) >= 0x0041 and ord(char) <= 0x005A) or (ord(char) >= 0x0061 and ord(char) <= 0x007A):
            return True
        else:
            return False

#Creates the progress bar to for the user to see how far the process is
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()