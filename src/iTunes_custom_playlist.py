

def make_playlist(mylib_xml,output_xml_file,playlist_name):
    ''' '''

    # Let's set up a connection using the in-memory SQLite engine
    import plistlib
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///:memory:', echo=False) # echo ~ verbose; shows sql commands
    # declare a mapping
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base() # a low level class that we can use as a base class for interactions
    # with the DB

    # define the Track class which will hold all records 
    from sqlalchemy import Column, Integer, String
    from sqlalchemy import Sequence
    from sqlalchemy import func,text,and_,or_

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
            return "<Track(name='%s', artist='%s', album='%s', year='%s', genre='%s')>" %     (self.name, self.artist, self.album, self.year, self.genre)

    # Create a schema
    Base.metadata.create_all(engine)

    # Creating a session
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine) # don't actually need an engine yet to start a session
    # In that case, run Session.configure(bind=engine) once engine is available

    # start a conversation with the db:
    session = Session()

    # import my iTunes library

    plist = plistlib.readPlist(mylib_xml) 

    mytracks=plist['Tracks'] # Another dictionary where the keys are track IDs (artibrary) 
    # and the values are also dictionaries storing the track information

    # My Track() class above wants trackname, artist, album, year, genre and plays 
    # These are all keys in this dictionary
    attrs = ['Track ID','Name','Artist','Album','Year','Genre','Play Count']

    # Some tracks will not have all of these fields
    # I will need some way of handling this when I populate the db

    def populate_tracks():
        ''' Add tracks from my xml iTunes library file 
        into the sqlite database'''
        addlist = [] # the list I am going to populate with Track() classes and then add to the db
        # attrs = ['Name','Artist','Album','Year','Genre']
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
    #         print attr_list
            ID,name,artist,album,year,genre,plays = attr_list
            this_track = Track(id=ID,name=name,artist=artist,album=album,year=year,genre=genre,plays=plays)
    #         print this_track
            addlist.append(this_track)
        session.add_all(addlist)

    populate_tracks()

    session.commit() # flushes the remaining changes to the database, 

    def get_duplicated_attrs(attr):
        return session.query(Track).group_by(getattr(Track,attr)).\
            having(func.count(getattr(Track,attr)) > 1).all()

    dup_byname = get_duplicated_attrs(attr='name')
    # OK, so we should make track name, artist name and album all case-insensitive when
    # testing for equality
    def remove_duplicate_tracks_caseinsensitive():
        for duplicate in dup_byname:
            objs = session.query(Track).\
            filter(and_(func.lower(getattr(Track,'name')) == func.lower(getattr(duplicate,'name'))),\
                (func.lower(getattr(Track,'artist')) == func.lower(getattr(duplicate,'artist'))),\
                (func.lower(getattr(Track,'album')) == func.lower(getattr(duplicate,'album')))).\
                order_by('id').all()
            map(session.delete, objs[1:]) # only delete 1: since 0th entry is the original copy
    #         print getattr(duplicate,'name'), objs
        session.commit()
    remove_duplicate_tracks_caseinsensitive()

    # Now assign the top 50 most played songs (or less if there aren't 50) 
    # to a list of Track objects.

    allwithplays = session.query(Track).filter(Track.plays>0).all()
    if len(allwithplays) <= 50:
        fav_track_ids = [instance.id for instance in allwithplays]
    else:
        fav_track_ids = session.query(Track.id).order_by(Track.plays.desc())[0:50]

    # OK so it worked. Let's commit the changes
    session.commit()

    # Here we go through all of the most-played songs and
    # find the ids of songs with matching artist or album
    # and make a dictionary 

    matching_dict = {}
    def make_matching_dict():
        for fav_track_id in fav_track_ids:
            matching_tracks = session.query(Track.id).filter(and_(~Track.id.in_(fav_track_ids)),\
                       (or_((Track.artist==(session.query(Track.artist).filter(Track.id==fav_track_id))),\
                            (Track.artist==(session.query(Track.artist).filter(Track.id==fav_track_id)))))).\
                        order_by(Track.id).all()

            matching_dict[fav_track_id] = matching_tracks

    make_matching_dict()

    # So matching_dict is a dictionary where the keys are the top-played songs
    # and the values are the ids of other songs (not among the top-played )
    # in the library that are either by the same artist or in the same Genre
    # I am going to make a master list of all of the matched tracks for any song
    # then I make a ranked list where the tracks that are matched the most get recommended highest

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
    import operator
    sorted_matches = sorted(ranked_matching_tracks.items(), key=operator.itemgetter(1),reverse=True)

    # Now let's figure out the maximum number of counts 

    max_matches_tup=max(sorted_matches,key=operator.itemgetter(1))

    # print max_matches_tup
    max_matched_id = max_matches_tup[0][0]
    # print session.query(Track.name).filter(Track.id==max_matched_id).first()

    max_matches = max_matches_tup[1]
    # Let's descend from the max value, adding tracks as we go
    recommended_ids = []
    n_matches=range(1,max_matches+1)[::-1]

    for n in n_matches:
        ids_n = [str(x[0][0]) for x in sorted_matches if x[1]==n] # all ids that have n matches
        for ID in ids_n:
            while len(recommended_ids) < 100:
                recommended_ids.append(ID)
                break

    # now let's only take the first 100, which will be the best matches
    # print len(recommended_ids)
    # print recommended_ids
    # So we have successfully created a playlist of songs
    # That are close matches to our most-played songs in iTunes
    # But aren't actually in our most-played songlist

    # It turns out that iTunes let's you import a playlist from an xml file
    # I can see what the xml format has to be from a playlist I export as an xml file
    # I created a test example called test_playlsit
    # I exported the playlist as test_playlist.xml
    # Let's take a quick look at it 

    # In[726]:

    import plistlib
    playlist_xml = '/Users/athair/progs/sql/test_playlist.xml'
    plist_playlist = plistlib.readPlist(playlist_xml) 


    # now let's copy over the keys from the old playlist file to a new plist
    new_plist = {}

    for key in plist_playlist:
        new_plist[key] = plist_playlist[key]
        
    # The first change to make is to make a new 'Tracks' dictionary to insert into the new plist
    # This should be easy since I kept track of the ID
    # in the plist dictionary in my table
    new_tracks_dict = {key:mytracks[key] for key in recommended_ids}    
    new_plist['Tracks'] = new_tracks_dict

    # We also need to change the 'Playlist' key a bit.

    new_plist['Playlists'][0]['Name'] = playlist_name 
    new_plist['Playlists'][0]['Playlist ID'] = 9999 # not sure if
    # new_plist['Playlists']['Name'] = 'Custom playlist'
    new_plist['Playlists'][0]['Playlist Items'] = [{'Track ID':int(ID)} for ID in recommended_ids]
    # custom_playlist_file = '/Users/athair/progs/sql/custom_playlist.xml'
    plistlib.writePlist(new_plist,output_xml_file)
    print """Wrote playlist: '%s' to xml file: %s""" % (playlist_name,output_xml_file)
    return


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='create recommended iTunes playlist')
    parser.add_argument('input_xml_file',help='The exported xml iTunes library file')
    parser.add_argument('-output_xml_file',default='My_custom_playlist.xml',help='The xml iTunes library filename you want to export')
    # parser.add_argument('output_xml_file',default='My_custom_playlist.xml')
    parser.add_argument('-playlist_name',default='My Custom Playlist',help='The name of the iTunes playlist this program will create')
    args = parser.parse_args()

    make_playlist(args.input_xml_file,args.output_xml_file,args.playlist_name)


