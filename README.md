Local Librabry to Spotify Converter
Description

This project allows you to search audio tracks in a specified folder using the ShazamAPI, process the track data, and add the recognized tracks to a Spotify playlist. It utilizes Flask for creating a web server to handle the authentication flow for Spotify OAuth2, and Spotipy for interacting with the Spotify Web API. The recognized tracks are stored in a SQLite database, and unrecognized tracks are logged in the log.txt file along with any other files not recognized as supported audio file.
Libraries Used

Installation

To use this project, follow these steps:
Download the lastest version of python on there website for your operating system

    https://www.python.org/downloads/

Download git to allow to clone the repository

    https://git-scm.com/downloads

Open command prompt run the following commands:

Clone the Repository

    git clone https://github.com/Coconut9021/Local-Library-to-Spotify-Converter.git

Install Requirements

    cd Local-Library-to-Spotify-Converter

Create a virtual environment (optional but recommended):

    python3 -m venv venv

Activate the virtual environment:

    venv\Scripts\activate

Windows (Powershell):

    venv\Scripts\Activate.ps1

Linux/macOS:

    source venv/bin/activate

Install the required packages:

    pip install -r requirements.txt

Set Up Spotify Credentials

Create a Spotify Developer account at https://developer.spotify.com/.
Create a new application to get your client ID and client secret.

Run the following command to start the application:

    python app.py

Follow the on-screen instructions to authorize the application with your Spotify account.
Once authorized, the application will search for audio tracks in the tracks/ folder, recognize them using ShazamAPI, and add them to a Spotify playlist.

Notes:

Make sure to place your audio tracks (supported formats: .mp3, .wav, .ogg, .flac, .aac, .wma, .m4a) in the tracks/ folder before running the application.
The recognized tracks will be added to a playlist named "My Shazam Tracks" in your Spotify account.

Troubleshooting:

If you encounter any issues, please ensure:

Your internet connection is active.
The audio tracks are in the correct folder (tracks/).
Your Spotify application credentials (client_id and client_secret) are correctly set.

Credits:

This project was made possible by the contributions of the following individuals:

    @dotX12: Contributed code for the ShazamAPI integration.
    @katiagilligan888: Provided guidance on the Flask implementation for Spotify OAuth2.
    @chaisupt & @hugovk: Contributed code for the Spotipy allowing interaction with spotify API.
# Local-Library-To-Spotify-Converter
