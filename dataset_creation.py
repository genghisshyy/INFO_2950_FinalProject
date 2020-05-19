import sys
import requests
import re
import pandas
import string
import numpy as np
from bs4 import BeautifulSoup
from nltk.tokenize import TreebankWordTokenizer


# -----------------------------HELPER FUNCTIONS---------------------------------

# The following functions are intended to facilitate the data collection 
# (via web scraping) process:

"""
Accepts a Pandas DataFrame column, album_info, which contains
basic album information manually scraped from Metacritic.

Starting from row 0, every five rows represents an album, with
each set of five rows corresponding to the following information:
    Row 0: Title of album
    Row 1: Average critic score that album received on Metacritic
    Row 2: Name of album artist
    Row 3: Average user score that album received on Metacritic, or "tbd" if unknown
    Row 4: Day on which album was released in the format d-mmm-yy, e.g. 6-Mar-20
-----
Returns: albums, a list of dictionaries where each dictionary is arranged 
in the following format:
    {"artist": (name of album artist),
    "metascore": (average critic score that album received on Metacritic),
    "release_date": (day on which album was released in the format d-mmm-yy, e.g. 6-Mar-20),
    "title": (title of album),
    "user_score": (average user score that album received on Metacritic)}
"""
def organize_basic_album_info(album_info):
    albums = []
    
    # for each set of 5 rows in album_info, maps row number to field name
    field_mapping = {0: "title", 1: "metascore", 2: "artist", 3: "user_score", 4: "release_date"}
    
    for i in range(len(album_info)):
        current_info = album_info[i]
        field_index = i % 5 # used to tell what kind of information is stored in album_info[i]
        album_index = i // 5 # tells us at which index in albums we should store current_info in
        if field_index == 0:
            albums.append(dict())
        # cleans data to obtain user score
        if field_mapping[field_index] == "user_score":
            current_info = current_info[6:]
        albums[album_index][field_mapping[field_index]] = current_info
    return albums


"""
Given BeautifulSoup object, this function constructs a list of 
URLs found on web page in question, each of which leads to page 
containing song lyrics
-----
Returns: urls, a list of URLs as described above
"""
def find_lyric_urls(soup):
    urls = []
    for elem in soup.select(".chart_row-content a"):
        urls.append(elem["href"])
    return urls


"""
Given the URL of a Genius page containing song lyrics,
this function returns all of the song lyrics as a single string.

Example input: "https://genius.com/Childish-gambino-time-lyrics"
-----
Returns: lyrics, a string as described above
"""
def retrieve_lyrics(url):
    lyrics = ""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")
    lyric_div = soup.select(".lyrics")
    if len(lyric_div) > 0:
        for elem in lyric_div:
            # filter out lyric annotations
            lyrics += re.sub("\[.*\]", "", elem.text)
    return lyrics


"""
Accepts a list of albums, organized as a list of dictionaries
such that each dictionary features the following structure:
    {"artist": (name of album artist),
    "metascore": (average critic score that album received on Metacritic),
    "release_date": (day on which album was released in the format d-mmm-yy, e.g. 6-Mar-20),
    "title": (title of album),
    "user_score": (average user score that album received on Metacritic)}

For each album in albums, this function finds all available album lyrics
and stores them as a single string in albums.
"""
def add_album_lyrics(albums):
    for album in albums:
        # replacing all punctuation in album title and album artist with spaces
        artist_no_punc = re.sub("[" + string.punctuation + "]", " ", album["artist"])
        title_no_punc = re.sub("[" + string.punctuation + "]", " ", album["title"])

        # arranging album title and artist with '-' separating each space-separted word, 
        # and just the first word capitalized
        # ex: "After Hours" becomes "After-hours"; The Weeknd" becomes "The-weeknd"
        reformatted_artist_name = "-".join(artist_no_punc.lower().split(" ")).capitalize()
        reformatted_album_name = "-".join(title_no_punc.lower().split(" ")).capitalize()

        # construct URL we expect to correspond to Genius overview page on album
        genius_url = "http://genius.com/albums/" + reformatted_artist_name + "/" + reformatted_album_name

        album["lyrics"] = []
        try:
            response = requests.get(genius_url)
            soup = BeautifulSoup(response.text, "lxml")

            # retrieve URLs corresponding to available lyric pages for each album track
            urls = find_lyric_urls(soup)
            
            # record number of tracks with available lyrics (for later analysis)
            album["num_lyric_tracks"] = len(urls)
            
            # builds out "lyrics" field for each album by retrieving all available album lyrics
            for url in urls:
                lyrics = retrieve_lyrics(url)
                album["lyrics"].append(lyrics)
        except:
            # encountered error in above code due to invalid URL
            continue


"""
Accepts an album artist name and an album name as strings.

Note: This function serves as an alternative to the above function 
add_album_lyrics, in that it handles punctuation differently. Specifically, this
function replaces all ampersands in the album artist name and album name with
the word "and," and removes all other forms of punctuation. (In contrast, 
add_album_lyrics simply replaces all forms of punctuation in the album artist
name and album name with a blank space.) The motivation behind this is discussed
in greater detail in the accompanying final report.

Returns: a list of strings, each of which represents lyrics from a single track
on the given album. List could be empty if no lyrics were scraped.
"""
def add_lyrics_normal_alternate(artist, title):
    artist_no_ampersand = re.sub("&", "and", artist)
    title_no_ampersand = re.sub("&", "and", title)
    
    artist_no_punc = re.sub("[" + string.punctuation + "]", "", artist_no_ampersand).strip()
    title_no_punc = re.sub("[" + string.punctuation + "]", "", title_no_ampersand).strip()

    # arranging album title and artist with '-' separating each space-separted word, 
    # and just the first word capitalized
    # ex: "After Hours" becomes "After-hours"; The Weeknd" becomes "The-weeknd"
    reformatted_artist_name = "-".join(artist_no_punc.lower().split(" ")).capitalize()
    reformatted_album_name = "-".join(title_no_punc.lower().split(" ")).capitalize()

    # construct URL we expect to correspond to Genius overview page on album
    genius_url = "http://genius.com/albums/" + reformatted_artist_name + "/" + reformatted_album_name

    results = []
    try:
        response = requests.get(genius_url)
        soup = BeautifulSoup(response.text, "lxml")

        # retrieve URLs corresponding to available lyric pages for each album track
        urls = find_lyric_urls(soup)

        # scrapes lyrics for current album by retrieving all available album lyrics
        for url in urls:
            lyrics = retrieve_lyrics(url)
            results.append(lyrics)
    except:
        # encountered error in above code due to invalid URL
        pass
    return results


"""
Accepts a valid Genius URL as a string.

Note: This function serves as an alternative to the above functions 
add_album_lyrics and add_lyrics_normal_alternate, in that instead of manually
constructing a Genius URL based off a given album artist name and album name,
it simply accepts a valid Genius URL. The motivation behind this is discussed
in greater detail in the accompanying final report.

Returns: a list of strings, each of which represents lyrics from a single track
on the album corresponding to the given URL. List could be empty if no lyrics 
were scraped.
"""
def add_lyrics_hardcode_alternate(genius_url):
    results = []
    try:
        response = requests.get(genius_url)
        soup = BeautifulSoup(response.text, "lxml")

        # retrieve URLs corresponding to available lyric pages for each album track
        urls = find_lyric_urls(soup)

        # scrapes lyrics for current album by retrieving all available album lyrics
        for url in urls:
            lyrics = retrieve_lyrics(url)
            results.append(lyrics)
    except:
        # encountered error in above code due to invalid URL
        pass
    return results




# ---------------------------INITIAL WEB SCRAPING-------------------------------

# Here, we scrape data from Metacritic reviews, Genius album tracklists, 
# and Genius lyrics pages to ultimately build a list of dictionaries,
# such that each dictionary features the following structure:

# `{"artist": (name of album artist),
# "metascore": (average critic score that album received on Metacritic),
# "release_date": (day on which album was released in the format d-mmm-yy, e.g. 6-Mar-20),
# "title": (title of album),
# "user_score": (average user score that album received on Metacritic),
# "lyrics": (all available album lyrics, concatenated as a single string)
# "num_lyric_tracks": (number of tracks with lyrics available on Genius)}`


# read Metacritic data from CSV file
metacritic_data = pandas.read_csv("../data/metacritic_data.csv")
# metacritic_data.head()


# initialize albums lists using information from CSV file
albums_2020 = organize_basic_album_info(metacritic_data["2020"])
albums_2019 = organize_basic_album_info(metacritic_data["2019"])
albums_2018 = organize_basic_album_info(metacritic_data["2018"])
albums_2017 = organize_basic_album_info(metacritic_data["2017"])
albums_2016 = organize_basic_album_info(metacritic_data["2016"])
albums_2015 = organize_basic_album_info(metacritic_data["2015"])
albums_2014 = organize_basic_album_info(metacritic_data["2014"])
albums_2013 = organize_basic_album_info(metacritic_data["2013"])
albums_2012 = organize_basic_album_info(metacritic_data["2012"])
albums_2011 = organize_basic_album_info(metacritic_data["2011"])


# Once basic album information has been loaded, we now retrieve all 
# available album lyrics for each album. We proceed year by year for 
# organizational purposes:

# adding lyrics for 2020 albums
add_album_lyrics(albums_2020)

# adding lyrics for 2019 albums
add_album_lyrics(albums_2019)

# adding lyrics for 2018 albums
add_album_lyrics(albums_2018)

# adding lyrics for 2017 albums
add_album_lyrics(albums_2017)

# adding lyrics for 2016 albums
add_album_lyrics(albums_2016)

# adding lyrics for 2015 albums
add_album_lyrics(albums_2015)

# adding lyrics for 2014 albums
add_album_lyrics(albums_2014)

# adding lyrics for 2013 albums
add_album_lyrics(albums_2013)

# adding lyrics for 2012 albums
add_album_lyrics(albums_2012)

# adding lyrics for 2011 albums
add_album_lyrics(albums_2011)


# Having completed our initial scraping for lyrics data, we now combine and 
# subsequently convert our lists of dictionaries into a single Pandas DataFrame:

all_albums = albums_2020 + albums_2019 + albums_2018 + albums_2017 + albums_2016 \
    + albums_2015 + albums_2014 + albums_2013 + albums_2012 + albums_2011

albums_df = pandas.DataFrame(all_albums)
# albums_df.head()




# -------------------------FURTHER LYRICS SCRAPING-----------------------------

# As discussed in the final report, the initial process of web scraping failed
# to scrape lyrics for all albums in the dataset. We therefore attempt to scrape
# these missed lyrics below:


# maps index of album for which no lyrics are stored to a tuple, (album_title, album_artist)
error_title_artist_mapping = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 0:
        if any(char in string.punctuation for char in row["title"]) \
            or any(char in string.punctuation for char in row["artist"]):
            error_title_artist_mapping[index] = (row["title"], row["artist"])

# scraping additional lyrics using first of two alternative scraping methods,
# both of which are documented above in section "Helper Functions"
for i in error_title_artist_mapping:
    albums_df.at[i, "lyrics"] = add_lyrics_normal_alternate(albums_df.iloc[i, 0], albums_df.iloc[i, 5])


# maps index of album for which no lyrics are stored to a tuple (album_title, album_artist)
# Used specifically after add_lyrics_normal_alternate is executed, so as to
# determine which albums still lack scraped lyrics
error_title_artist_mapping2 = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 0:
        if any(char in string.punctuation for char in row["title"])         or any(char in string.punctuation for char in row["artist"]):
            error_title_artist_mapping2[index] = (row["title"], row["artist"])

# a dictionary mapping index of album in DataFrame to its corresponding (and valid) Genius URL
album_url_mappings = {
    9: "https://genius.com/albums/Mura-masa/R-y-c",
    81: "https://genius.com/albums/Gil-scott-heron-and-makaya-mccraven/Were-new-again-a-reimagining-by-makaya-mccraven",
    161: "https://genius.com/albums/Weezer/Weezer-the-teal-album",
    166: "https://genius.com/albums/Lsd/Labrinth-sia-diplo-present-lsd",
    170: "https://genius.com/albums/Marina/Love-fear",
    177: "https://genius.com/albums/Unkle/The-road-part-ii-lost-highway",
    179: "https://genius.com/albums/Peter-doherty-and-the-puta-madres/Peter-doherty-the-puta-madres",
    203: "https://genius.com/albums/Chk-chk-chk/Wallop",
    212: "https://genius.com/albums/Bleached/Don-t-you-think-you-ve-had-enough",
    228: "https://genius.com/albums/Baroness/Gold-grey",
    244: "https://genius.com/albums/Big-thief/U-f-o-f",
    305: "https://genius.com/albums/Post-malone/Beerbongs-bentleys",
    331: "https://genius.com/albums/Nile-rodgers-and-chic/It-s-about-time",
    337: "https://genius.com/albums/The-smashing-pumpkins/Shiny-and-oh-so-bright-vol-1-lp-no-past-no-future-no-sun",
    362: "https://genius.com/albums/Art-brut/Wham-bang-pow-let-s-rock-out",
    402: "https://genius.com/albums/Tracyanne-and-danny/Tracyanne-danny",
    409: "https://genius.com/albums/Mount-eerie/After",
    421: "https://genius.com/albums/Lets-eat-grandma/I-m-all-ears",
    454: "https://genius.com/albums/Faith-evans-and-the-notorious-big/The-king-i",
    475: "https://genius.com/albums/The-dears/Times-infinity-volume-two",
    493: "https://genius.com/albums/Chk-chk-chk/Shake-the-shudder",
    495: "https://genius.com/Death-from-above-1979-outrage-is-now-lyrics",
    497: "https://genius.com/albums/Thievery-corporation/The-temple-of-i-i",
    505: "https://genius.com/albums/The-bronx/V",
    545: "https://genius.com/albums/The-replacements/For-sale-live-at-maxwell-s-1986",
    553: "https://genius.com/albums/Sharon-jones-and-the-dap-kings/Soul-of-a-woman",
    611: "https://genius.com/albums/Kula-shaker/K2-0",
    614: "https://genius.com/albums/Macklemore-and-ryan-lewis/This-unruly-mess-i-ve-made",
    635: "https://genius.com/albums/Deadmau5/W-2016album",
    656: "https://genius.com/albums/Chris-robinson-brotherhood/Anyway-you-love-we-know-how-you-feel",
    678: "https://genius.com/albums/A-tribe-called-quest/We-got-it-from-here-thank-you-4-your-service",
    679: "https://genius.com/albums/Chance-the-rapper/Coloring-book",
    694: "https://genius.com/albums/Michael-kiwanuka/Love-hate",
    695: "https://genius.com/albums/Maxwell/Blacksummers-night-2016",
    732: "https://genius.com/albums/Kyle-dixon-and-michael-stein/Stranger-things-vol-1-a-netflix-original-series-soundtrack",
    743: "https://genius.com/albums/Grant-lee-phillips/The-narrows",
    752: "https://genius.com/albums/Pope-francis/Wake-up-music-album-with-his-words-and-prayers",
    757: "https://genius.com/albums/Giorgio-moroder/Deja-vu",
    758: "https://genius.com/albums/Zac-brown-band/Jekyll-hyde",
    778: "https://genius.com/albums/Imagine-dragons/Smoke-mirrors",
    826: "https://genius.com/albums/Sufjan-stevens/Carrie-lowell",
    828: "https://genius.com/albums/Napalm-death/Apex-predator-easy-meat",
    830: "https://genius.com/albums/Steven-wilson/Hand-cannot-erase",
    839: "https://genius.com/albums/John-howard-and-the-night-mail/John-howard-the-night-mail",
    864: "https://genius.com/albums/Pusha-t/King-push-darkest-before-dawn-the-prelude",
    900: "https://genius.com/albums/Jennifer-lopez/A-k-a",
    905: "https://genius.com/albums/Yes/Heaven-earth",
    945: "https://genius.com/albums/Primus/Primus-the-chocolate-factory-with-the-fungi-ensemble",
    956: "https://genius.com/albums/Kasabian/48-13",
    963: "https://genius.com/albums/Peter-gabriel/And-ill-scratch-yours",
    975: "https://genius.com/albums/Dangelo-and-the-vanguard/Black-messiah",
    984: "https://genius.com/albums/Flying-lotus/You-re-dead",
    985: "https://genius.com/albums/Rosanne-cash/The-river-the-thread",
    1004: "https://genius.com/albums/Lee-ann-womack/The-way-i-m-livin",
    1005: "https://genius.com/albums/Agalloch/The-serpent-the-sphere",
    1037: "https://genius.com/albums/Soft-pink-truth/Why-do-the-heathen-rage",
    1054: "https://genius.com/albums/Boston/Life-love-hope",
    1072: "https://genius.com/albums/Reverend-and-the-makers/Reverend_makers",
    1117: "https://genius.com/albums/Unknown-mortal-orchestra/Blue-record",
    1124: "https://genius.com/albums/Glasvegas/Later-when-the-tv-turns-to-static",
    1142: "https://genius.com/British-sea-power-from-the-sea-to-the-land-beyond-lyrics",
    1162: "https://genius.com/albums/Various-artists/Divided-united-the-songs-of-the-civil-war",
    1209: "https://genius.com/albums/Cher-lloyd/Sticks-stones-u-s-edition",
    1220: "https://genius.com/albums/2-chainz/Based-on-a-t-r-u-story",
    1226: "https://genius.com/albums/Wiz-khalifa/O-n-i-f-c",
    1242: "https://genius.com/albums/The-phenomenal-handclap-band/Form-control",
    1258: "https://genius.com/albums/Joss-stone/The-soul-sessions-volume-2",
    1278: "https://genius.com/albums/Kendrick-lamar/Good-kid-m-a-a-d-city",
    1308: "https://genius.com/albums/Killer-mike/R-a-p-music",
    1311: "https://genius.com/albums/El-p/Cancer-4-cure",
    1319: "https://genius.com/albums/Tnght/Tnght",
    1322: "https://genius.com/albums/Swans/We-rose-from-your-bed-with-the-sun-in-our-head",
    1336: "https://genius.com/albums/Earth/Angels-of-darkness-demons-of-light-ii",
    1339: "https://genius.com/albums/Baroness/Yellow-green",
    1352: "https://genius.com/albums/Gucci-mane-and-v-nasty/Baytl",
    1355: "https://genius.com/albums/The-antlers/Together",
    1370: "https://genius.com/albums/Chris-brown/F-a-m-e",
    1435: "https://genius.com/albums/Tune-yards/W-h-o-k-i-l-l",
    1457: "https://genius.com/albums/True-widow/As-high-as-the-highest-heavens-and-from-the-center-to-the-circumference-of-the-earth",
    1466: "https://genius.com/albums/Beastie-boys/Hot-sauce-committee-part-2",
    1494: "https://genius.com/albums/Meshell-ndegeocello/Weather",
    1496: "https://genius.com/albums/Earth/Angels-of-darkness-demons-of-light-i"
}


# scraping additional lyrics using second of two alternative scraping methods,
# both of which are documented above in section "Helper Functions"
for i in error_title_artist_mapping2:
    if i in album_url_mappings:
        albums_df.at[i, "lyrics"] = add_lyrics_hardcode_alternate(album_url_mappings[i])

# ---------------ADDING DATA ON EACH ALBUM'S EXPLICIT CONTENT------------------

# Having finished scraping lyrics data, we now can gather data on how much 
# explicit content is featured on each album. For this section, we will be 
# using the following list to determine which words are "explicit" and which 
# words are not:


# This is not a comprehensive list of "explicit" words, but rather a compilation
# of "explicit" words that I myself have come across in music. The inclusion of
# these words here is strictly for research purposes.
explicit_list = [
    "arse",
    "ass",
    "asshole",
    "bastard",
    "bitch",
    "bullshit",
    "cocaine",
    "cock",
    "coke",
    "damn",
    "dick",
    "drug",
    "drugs",
    "faggot",
    "fentanyl",
    "fuck",
    "fucka",
    "fucker",
    "fuckin",
    "fucking",
    "goddamn",
    "hell",
    "horseshit",
    "mothafucka",
    "mothafuckas",
    "motherfucka",
    "motherfuckas",
    "motherfucker",
    "motherfuckers"
    "nigga",
    "niggas",
    "nigger",
    "niggers",
    "perc",
    "percocet",
    "pill",
    "pills",
    "pussy",
    "sex",
    "shit",
    "slut",
    "whore"
]

# used to separate lyrics into individual words
treebank_tokenizer = TreebankWordTokenizer()


# list of integers, where explicit_count[i] = # of explicit words that appear
# in lyrics for album stored in row (i + 1) of albums_df
explicit_count = []

# list of floats, where explicit_average[i] = average # of explicit words that appear
# on each track for album stored in row (i + 1) of albums_df.
explicit_average = []

for index, row in albums_df.iterrows():
    current_count = 0 # used to keep track of number of explicit words encountered
    lyrics = treebank_tokenizer.tokenize(" ".join(row["lyrics"]).lower())
    for word in explicit_list:
        current_count += lyrics.count(word)
    explicit_count.append(current_count)
    
    if row["num_lyric_tracks"] > 0:
        explicit_average.append(current_count/row["num_lyric_tracks"])
    else:
        explicit_average.append(0.0)


# Having obtained the total number of explicit words on each album (as well as 
# the average number of explicit words per track), we now can add this data to 
# our DataFrame:

albums_df["explicit_count"] = explicit_count
albums_df["explicit_avg"] = explicit_average


# We have now finished constructing our complete DataFrame.

# albums_df.head()

# --------------------------EXPORTING DATA TO CSV-------------------------------

# The above DataFrame `albums_df` can now be used to perform the data analysis 
# required for this project. We will export this DataFrame as a CSV file below,
# so as to be able to access it more readily:

albums_df.to_csv("/Users/Genghis/Desktop/INFO_2950/INFO_2950_FinalProject/data/albums.csv", index=False)

# In addition, we will export a condensed version of the above DataFrame 
# `albums_df` (specifically one without the `lyrics` column), so as to obtain 
# a smaller dataset. The `lyrics` column has, after all, already been analyzed 
# for explicit content, and used to construct the columns `explicit_count` and 
# `explicit_avg`.

condensed_albums_df = albums_df[["artist", "metascore", "num_lyric_tracks", \
    "release_date", "title", "user_score", "explicit_count", "explicit_avg"]]

condensed_albums_df.to_csv("/Users/Genghis/Desktop/INFO_2950/INFO_2950_FinalProject/data/condensed_albums.csv", index=False)