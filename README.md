# playlistmaker
Makes a recommended iTunes playlist from an existing iTunes library.
The code looks through a provided iTunes library xml file for your 
most-played tracks and finds other tracks in your library which 
are similar and builds a playlist based off of them. 

## REQUIREMENTS
sqlalchemy - python package which is used to create and interact with an SQLite database.
It can be installed with pip, e.g. pip install sqlalchemy

An iTunes Library xml file - export this from iTunes with File->Library->Export Library

## Example usage
python src/iTunes_custom_playlist.py iTunes_Library.xml

## Output
Running the above code will produce an .xml file in the root repository directory called 'My_custom_playlist.xml'

Import this playlist to iTunes using File->Library->Import Playlist

This will create a new playlist called 'My Custom Playlist'

It will automatically appear as a playlist on the sidebar alonge with your other playlists once imported