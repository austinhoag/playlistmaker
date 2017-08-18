#Copyright (c) [2017] [Austin Hoag]

import argparse

def make_playlist(mylib_xml,output_xml_file,playlist_name):
    ''' 
    ---- PURPOSE ----
    Create an iTunes playlist of recommended songs
    based on top-played tracks in an existing iTunes library.
    ---- INPUT ----
    mylib_xml          iTunes library xml file
    output_xml_file    The xml file that will be written, containing the customized playlist
    playlist_name      The name of the playlist that will appear once imported into iTunes
    '''

    # Set up a connection using the in-memory SQLite engine
    import plistlib
    from sqlalchemy import create_engine
    from sqlalchemy import Column, Integer, String
    from sqlalchemy import Sequence
    from sqlalchemy import func,text,and_,or_
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base
    import operator
    engine = create_engine('sqlite:///:memory:', echo=False) # echo ~ verbose; shows sql commands
    # declare a mapping
    
    Base = declarative_base() # a low level class that we can use as a base class for interactions
    # with the DB

    # define the Track class which will contain the records 

    class Track(Base,):
        __tablename__ = 'tracks'
        __table_args__ = {'extend_existing': True} # this lets you change the attributes 
        id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
        name = Column(String(50))
        artist = Column(String(50))
        album = Column(String(50))
        year = Column(String(50))
        genre = Column(String(50))
        plays = Column(Integer)
        def __repr__(self):
            return "<Track(name='%s', artist='%s', album='%s', year='%s', genre='%s',plays='%i')>" % \
                (self.name, self.artist, self.album, self.year, self.genre, self.plays)

    # Create a schema
    Base.metadata.create_all(engine)

    # Creating a session
    Session = sessionmaker(bind=engine) # don't actually need an engine yet to start a session
    # In that case, run Session.configure(bind=engine) once engine is available

    # start a conversation with the db:
    session = Session()

    # import my iTunes library as a python dictionary

    plist = plistlib.readPlist(mylib_xml) # A dictionary of dictionaries

    mytracks=plist['Tracks'] # Another dictionary where the keys are track IDs (artibrary) 
    # and the values are also dictionaries storing the track information, such as track name, artist

    # My Track() class above wants trackname, artist, album, year, genre and plays 
    # These are all contained in the mytracks dictionary
    attrs = ['Track ID','Name','Artist','Album','Year','Genre','Play Count']

   

    def populate_tracks():
        ''' 
        Add tracks from my xml iTunes library file 
        into the sqlite database
        '''
        addlist = [] # the list I am going to populate with Track() classes and then add to the db
        for key in mytracks:
            attr_list = [] # a list which I will populate with name, artist, etc. to feed to Track()
            trdict = mytracks[key]
            for at in attrs:
                try:
                    attr = trdict[at]
                except KeyError: # for example if 'Play Count' is not a key for this track (0 plays)
                    if at == 'Play Count':
                        attr=0
                    else:
                        attr = 'None'
                attr_list.append(attr)
            ID,name,artist,album,year,genre,plays = attr_list
            this_track = Track(id=ID,name=name,artist=artist,album=album,year=year,genre=genre,plays=plays)
            addlist.append(this_track)
        session.add_all(addlist)

    populate_tracks()

    session.commit() # flushes the changes to the database

    # Make sure the library meets the requirements to build the playlist 
    nwithplays = session.query(Track).filter(Track.plays>0).count()
    assert nwithplays>=10, "Your iTunes library must have at least 10 tracks with >0 plays"
    ntracks = session.query(Track.id).order_by(Track.id).count()
    assert ntracks >= 150, "Your iTunes library must contain at least 150 tracks"

    def get_duplicated_attrs(attr):
        return session.query(Track).group_by(getattr(Track,attr)).\
            having(func.count(getattr(Track,attr)) > 1).all()

    dup_byname = get_duplicated_attrs(attr='name')
   
    # Remove duplicates
    def remove_duplicate_tracks_caseinsensitive():
        for duplicate in dup_byname:
            objs = session.query(Track).\
            filter(and_(func.lower(getattr(Track,'name')) == func.lower(getattr(duplicate,'name'))),\
                (func.lower(getattr(Track,'artist')) == func.lower(getattr(duplicate,'artist'))),\
                (func.lower(getattr(Track,'album')) == func.lower(getattr(duplicate,'album')))).\
                order_by('id').all()
            map(session.delete, objs[1:]) # only delete 1: since 0th entry is the original copy
        session.commit()
    remove_duplicate_tracks_caseinsensitive()

    # Now assign the top 50 most played songs (or less if there aren't 50) 
    # to a list of Track objects.

    allwithplays = session.query(Track).filter(Track.plays>0).all()
    if len(allwithplays) <= 50:
        fav_track_ids = [instance.id for instance in allwithplays]
    else:
        fav_track_ids = session.query(Track.id).order_by(Track.plays.desc())[0:50]

    # commit the changes
    session.commit()

    # Here we go through all of the most-played songs and
    # find the ids of songs with matching artist or genre
    # but aren't in the top played already 

    matching_dict = {}
    def make_matching_dict():
        for fav_track_id in fav_track_ids:
            matching_tracks = session.query(Track.id).filter(and_(~Track.id.in_(fav_track_ids)),\
                       (or_((Track.artist==(session.query(Track.artist).filter(Track.id==fav_track_id))),\
                            (Track.genre==(session.query(Track.genre).filter(Track.id==fav_track_id)))))).\
                        order_by(Track.id).all()

            matching_dict[fav_track_id] = matching_tracks

    make_matching_dict()

   
    # Make a master list of all of the matched tracks for any song
    # then make a ranked list 

    master_match_list = []
    for key in matching_dict:
        master_match_list.extend(matching_dict[key])


    # Now make a dictionary where keys are unique songs in master_match_list and values are counts
    ranked_matching_tracks = {}
    for track in master_match_list:
        if track not in ranked_matching_tracks.keys():
            ranked_matching_tracks[track] = 1
        else:
            ranked_matching_tracks[track]+=1

    # now sort by count
    
    sorted_matches = sorted(ranked_matching_tracks.items(), key=operator.itemgetter(1),reverse=True)

    # Now let's figure out the maximum number of counts 

    max_matches_tup=max(sorted_matches,key=operator.itemgetter(1))

    max_matches = max_matches_tup[1]

    # Descend from the max value, adding tracks as we go until we get 100 tracks
    recommended_ids = []
    n_matches=range(1,max_matches+1)[::-1]

    for n in n_matches:
        ids_n = [str(x[0][0]) for x in sorted_matches if x[1]==n] # all ids that have n matches
        for ID in ids_n:
            while len(recommended_ids) < 100:
                recommended_ids.append(ID)
                break

    # Now create the new playlist xml file and fill it out

    playlist_xml = '/Users/athair/progs/sql/test_playlist.xml'
    plist_playlist = plistlib.readPlist(playlist_xml) 

    # Now copy over the keys from the old playlist file to a new plist
    new_plist = {}

    for key in plist_playlist:
        new_plist[key] = plist_playlist[key]
        
    # First make a new 'Tracks' dictionary to insert into the new plist
    new_tracks_dict = {key:mytracks[key] for key in recommended_ids}    
    new_plist['Tracks'] = new_tracks_dict

    # Also change the 'Playlist' dictionary a bit.

    new_plist['Playlists'][0]['Name'] = playlist_name 
    new_plist['Playlists'][0]['Playlist ID'] = 9999 
    new_plist['Playlists'][0]['Playlist Items'] = [{'Track ID':int(ID)} for ID in recommended_ids]

    # Write the plist to file
    plistlib.writePlist(new_plist,output_xml_file)
    print """Wrote playlist: '%s' to xml file: %s""" % (playlist_name,output_xml_file)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='create recommended iTunes playlist')
    parser.add_argument('input_xml_file',help='The exported xml iTunes library file')
    parser.add_argument('-output_xml_file',default='My_custom_playlist.xml',help='The xml iTunes library filename you want to export')
    parser.add_argument('-playlist_name',default='My Custom Playlist',help='The name of the iTunes playlist this program will create')
    args = parser.parse_args()
    make_playlist(args.input_xml_file,args.output_xml_file,args.playlist_name)


