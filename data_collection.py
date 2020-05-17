import sys
import requests
import re
import pandas
import string
from bs4 import BeautifulSoup

# -----------------------------HELPER FUNCTIONS---------------------------------

# The following functions are intended to facilitate the data collection 
# (via web scraping) process:

"""
Accepts a Pandas DataFrame column, album_info, which contains
all basic album information manually scraped from Metacritic.
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
URLs found on Genius page in question, each of which leads to a different Genius 
page containing relevant song lyrics
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
Accepts a list of dictionaries, such that each dictionary features the following
structure:
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




# -------------------------------WEB SCRAPING----------------------------------

# Here, we scrape data from Metacritic reviews, Genius album tracklists, 
# and Genius lyrics pages to ultimately build a list of dictionaries,
# such that each dictionary features the following structure:

# `
# {"artist": (name of album artist),`
# `"metascore": (average critic score that album received on Metacritic),`
# `"release_date": (day on which album was released in the format d-mmm-yy, e.g. 6-Mar-20),`
# `"title": (title of album),`
# `"user_score": (average user score that album received on Metacritic),`
# `"lyrics": (all available album lyrics, concatenated as a single string)}
# `

# This list of dictionaries will then be converted into a Pandas DataFrame, 
# which will serve as the primary dataset through this final project.


# read from CSV file, which was manually constructed by copying
# and pasting data from Metacritic lists of top 50 highest ranked albums
# for each year from 2010-2020. (Rankings for 2020 as of May 5, 2020.)
# Albums here are ranked by average critic score, rather than average 
# Metacritic user score.
metacritic_data = pandas.read_csv("data/metacritic_data.csv", header=0)

# initialize albums list using information from CSV file
album_info = metacritic_data["Information"]
albums = organize_basic_album_info(album_info)

# Once basic album information has been loaded, we 
# now retrieve all available album lyrics for each album. We proceed year by 
# year for organizational purposes:

# finding lyrics for Top 50 albums in 2020, based off Metacritic score
albums_2020 = albums[:100]
add_album_lyrics(albums_2020)

# finding lyrics for Top 50 albums in 2019, based off Metacritic score
albums_2019 = albums[100:200]
add_album_lyrics(albums_2019)

# finding lyrics for Top 50 albums in 2018, based off Metacritic score
albums_2018 = albums[200:300]
add_album_lyrics(albums_2018)

# finding lyrics for Top 50 albums in 2017, based off Metacritic score
albums_2017 = albums[300:400]
add_album_lyrics(albums_2017)

# finding lyrics for Top 99 albums in 2016, based off Metacritic score
albums_2016 = albums[400:499]
add_album_lyrics(albums_2016)

# finding lyrics for Top 99 albums in 2015, based off Metacritic score
albums_2015 = albums[499:598]
add_album_lyrics(albums_2015)

# finding lyrics for Top 95 albums in 2014, based off Metacritic score
albums_2014 = albums[598:693]
add_album_lyrics(albums_2014)

# finding lyrics for Top 98 albums in 2013, based off Metacritic score
albums_2013 = albums[693:791]
add_album_lyrics(albums_2013)

# finding lyrics for Top 99 albums in 2012, based off Metacritic score
albums_2012 = albums[791:890]
add_album_lyrics(albums_2012)

# finding lyrics for Top 96 albums in 2011, based off Metacritic score
albums_2011 = albums[890:986]
add_album_lyrics(albums_2011)

# finding lyrics for Top 98 albums in 2010, based off Metacritic score
albums_2010 = albums[986:]
add_album_lyrics(albums_2010)


# Having retrieved all available lyrics data, we now can convert our list of 
# dictionaries into a Pandas DataFrame:

# creating final DataFrame object
albums_df = pandas.DataFrame(albums)




# -------------------------FURTHER LYRICS SCRAPING-----------------------------

# As discussed in the final report, the initial process of web scraping failed
# to scrape lyrics for all albums in the dataset. We therefore attempt to scrape
# these missed lyrics below:

# a dictionary mapping index of album in DataFrame to its corresponding (and 
# valid) Genius URL
album_url_mappings = {
    5: "https://genius.com/albums/Gil-scott-heron-and-makaya-mccraven/Were-new-again-a-reimagining-by-makaya-mccraven",
    103: "https://genius.com/albums/Baroness/Gold-grey",
    119: "https://genius.com/albums/Big-thief/U-f-o-f",
    227: "https://genius.com/albums/Tracyanne-and-danny/Tracyanne-danny",
    234: "https://genius.com/albums/Mount-eerie/After",
    246: "https://genius.com/albums/Lets-eat-grandma/I-m-all-ears",
    277: "https://genius.com/albums/Jean-grae-and-quelle-chris/Everything-s-fine",
    320: "https://genius.com/albums/The-replacements/For-sale-live-at-maxwell-s-1986",
    328: "https://genius.com/albums/Sharon-jones-and-the-dap-kings/Soul-of-a-woman",
    379: "https://genius.com/albums/L-a-witch/L-a-witch",
    403: "https://genius.com/albums/A-tribe-called-quest/We-got-it-from-here-thank-you-4-your-service",
    404: "https://genius.com/albums/Chance-the-rapper/Coloring-book",
    419: "https://genius.com/albums/Michael-kiwanuka/Love-hate",
    420: "https://genius.com/albums/Maxwell/Blacksummers-night-2016",
    457: "https://genius.com/albums/Kyle-dixon-and-michael-stein/Stranger-things-vol-1-a-netflix-original-series-soundtrack",
    468: "https://genius.com/albums/Grant-lee-phillips/The-narrows",
    479: "https://genius.com/albums/Future-of-the-left/The-peace-truce-of-future-of-the-left",
    500: "https://genius.com/albums/Sufjan-stevens/Carrie-lowell",
    502: "https://genius.com/albums/Napalm-death/Apex-predator-easy-meat",
    504: "https://genius.com/albums/Steven-wilson/Hand-cannot-erase",
    513: "https://genius.com/albums/John-howard-and-the-night-mail/John-howard-the-night-mail",
    538: "https://genius.com/albums/Pusha-t/King-push-darkest-before-dawn-the-prelude",
    580: "https://genius.com/albums/Pops-staples/Don-t-lose-this",
    598: "https://genius.com/albums/Dangelo-and-the-vanguard/Black-messiah",
    607: "https://genius.com/albums/Flying-lotus/You-re-dead",
    608: "https://genius.com/albums/Rosanne-cash/The-river-the-thread",
    627: "https://genius.com/albums/Lee-ann-womack/The-way-i-m-livin",
    628: "https://genius.com/albums/Agalloch/The-serpent-the-sphere",
    660: "https://genius.com/albums/Soft-pink-truth/Why-do-the-heathen-rage",
    710: "https://genius.com/British-sea-power-from-the-sea-to-the-land-beyond-lyrics",
    730: "https://genius.com/albums/Various-artists/Divided-united-the-songs-of-the-civil-war",
    794: "https://genius.com/albums/Kendrick-lamar/Good-kid-m-a-a-d-city",
    824: "https://genius.com/albums/Killer-mike/R-a-p-music",
    827: "https://genius.com/albums/El-p/Cancer-4-cure",
    835: "https://genius.com/albums/Tnght/Tnght",
    838: "https://genius.com/albums/Swans/We-rose-from-your-bed-with-the-sun-in-our-head",
    852: "https://genius.com/albums/Earth/Angels-of-darkness-demons-of-light-ii",
    855: "https://genius.com/albums/Baroness/Yellow-green",
    875: "https://genius.com/albums/Actress/R-i-p",
    882: "https://genius.com/albums/Godspeed-you-black-emperor/Allelujah-don-t-bend-ascend",
    900: "https://genius.com/albums/Tune-yards/W-h-o-k-i-l-l",
    922: "https://genius.com/albums/True-widow/As-high-as-the-highest-heavens-and-from-the-center-to-the-circumference-of-the-earth",
    931: "https://genius.com/albums/Beastie-boys/Hot-sauce-committee-part-2",
    959: "https://genius.com/albums/Meshell-ndegeocello/Weather",
    961: "https://genius.com/albums/Earth/Angels-of-darkness-demons-of-light-i",
    970: "https://genius.com/albums/Bill-wells-and-aidan-moffat/Everything-s-getting-older",
    981: "https://genius.com/albums/Randy-newman/The-randy-newman-songbook-volume-2",
    991: "https://genius.com/albums/Bob-dylan/The-bootleg-series-vol-9-the-witmark-demos-1962-1964",
    1000: "https://genius.com/albums/Konono-n1/Assume-crash-position",
    1016: "https://genius.com/albums/Erykah-badu/New-amerykah-pt-2-return-of-the-ankh",
    1027: "https://genius.com/albums/Trash-talk/Eyes-nines",
    1040: "https://genius.com/albums/Flying-lotus/Pattern-grid-world",
    1042: "https://genius.com/albums/Cancer-bats/Bears-mayors-scraps-bones",
    1064: "https://genius.com/albums/Sharon-jones-and-the-dap-kings/I-learned-the-hard-way",
    1077: "https://genius.com/albums/Lindstrm-and-christabelle/Real-life-is-no-cool"
}

# maps index of album for which no lyrics are stored to a tuple (album_title, album_artist)
error_title_artist_mapping = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 2:
        if any(char in string.punctuation for char in row["title"]) \
            or any(char in string.punctuation for char in row["artist"]):
            error_title_artist_mapping[index] = (row["title"], row["artist"])

# scraping additional lyrics using first of two alternative scraping methods,
# both of which are documented above (lines 129 and 190)
for i in error_title_artist_mapping:
    albums_df_ml.iloc[i, 1] = str(add_lyrics_normal_alternate(albums_df.iloc[i, 0], albums_df.iloc[i, 4]))

# maps index of album for which no lyrics are stored to a tuple (album_title, album_artist)
# Used specifically after add_lyrics_normal_alternate is executed, so as to
# determine which albums still lack scraped lyrics
error_title_artist_mapping2 = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 2:
        if any(char in string.punctuation for char in row["title"]) \
            or any(char in string.punctuation for char in row["artist"]):
            error_title_artist_mapping2[index] = (row["title"], row["artist"])

# scraping additional lyrics using second of two alternative scraping methods,
# both of which are documented above (lines 129 and 190)
for i in error_title_artist_mapping2:
    if i in album_url_mappings:
        albums_df_ml.iloc[i, 1] = str(add_lyrics_hardcode_alternate(album_url_mappings[i]))


# --------------------------EXPORTING DATA TO CSV-------------------------------

# The above DataFrame `albums_df` can now be used to perform the data analysis 
# required for this project. We will export this DataFrame as a CSV file below,
# so as to be able to access it more readily:

albums_df.to_csv("/Users/Genghis/Desktop/INFO_2950/INFO_2950_FinalProject/data/albums.csv", index=False)