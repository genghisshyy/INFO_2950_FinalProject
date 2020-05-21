import sys
import requests
import re
import pandas
import string
import numpy as np
from bs4 import BeautifulSoup
from nltk.tokenize import TreebankWordTokenizer


# ----------------------------HELPER FUNCTIONS---------------------------------
#
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
        if pandas.isnull(current_info):
            break
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
    num_tracks = 0
    try:
        response = requests.get(genius_url)
        soup = BeautifulSoup(response.text, "lxml")

        # retrieve URLs corresponding to available lyric pages for each album track
        urls = find_lyric_urls(soup)

        # scrapes lyrics for current album by retrieving all available album lyrics
        for url in urls:
            lyrics = retrieve_lyrics(url)
            results.append(lyrics)
        
        # recording number of tracks with lyrics available on Genius
        num_tracks = len(urls)
    except:
        # encountered error in above code due to invalid URL
        pass
    return results, num_tracks


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
    num_tracks = 0
    try:
        response = requests.get(genius_url)
        soup = BeautifulSoup(response.text, "lxml")

        # retrieve URLs corresponding to available lyric pages for each album track
        urls = find_lyric_urls(soup)

        # scrapes lyrics for current album by retrieving all available album lyrics
        for url in urls:
            lyrics = retrieve_lyrics(url)
            results.append(lyrics)
        
        # recording number of tracks with lyrics available on Genius
        num_tracks = len(urls)
    except:
        # encountered error in above code due to invalid URL
        pass
    return results, num_tracks




# ----------------------------INIITAL WEB SCRAPING-----------------------------
#
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
metacritic_data = pandas.read_csv("../data/metacritic_data_updated.csv")
# metacritic_data.head()

# initialize albums lists using information from CSV file
albums_2019 = organize_basic_album_info(metacritic_data["2019"])
albums_2018 = organize_basic_album_info(metacritic_data["2018"])
albums_2017 = organize_basic_album_info(metacritic_data["2017"])
albums_2016 = organize_basic_album_info(metacritic_data["2016"])
albums_2015 = organize_basic_album_info(metacritic_data["2015"])


# Once basic album information has been loaded, we now retrieve all available 
# album lyrics for each album. We proceed year by year for organizational 
# purposes:

# adding lyrics for first 250 albums released in 2019
add_album_lyrics(albums_2019[:250])

# adding lyrics for remaining 263 albums released in 2019
add_album_lyrics(albums_2019[250:])

# adding lyrics for first 250 albums released in 2018
add_album_lyrics(albums_2018[:250])

# adding lyrics for remaining 318 albums released in 2018
add_album_lyrics(albums_2018[250:])

# adding lyrics for first 300 albums released in 2017
add_album_lyrics(albums_2017[:300])

# adding lyrics for remaining 366 albums released in 2017
add_album_lyrics(albums_2017[300:])

# adding lyrics for first 350 albums released in 2016
add_album_lyrics(albums_2016[:350])

# adding lyrics for remaining 387 albums released in 2016
add_album_lyrics(albums_2016[350:])

# adding lyrics for first 350 albums released in 2015
add_album_lyrics(albums_2015[:350])

# adding lyrics for remaining 392 albums released in 2015
add_album_lyrics(albums_2015[350:])


# Having completed our initial scraping for lyrics data, we now combine and 
# subsequently convert our lists of dictionaries into a single Pandas DataFrame:

all_albums = albums_2019 + albums_2018 + albums_2017 + albums_2016 + albums_2015

albums_df = pandas.DataFrame(all_albums)
# albums_df.head()




# ------------------------FURTHER LYRICS SCRAPING------------------------------
# 
# As discussed in the final report, the initial process of web scraping failed 
# to scrape lyrics for all albums in the dataset, primarily due to flawed 
# handling of punctuation in album titles and/or artist names. We therefore 
# attempt to scrape these missed lyrics below:


# maps index of album for which no lyrics are stored to a tuple, (album_title, album_artist)
error_title_artist_mapping = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 0:
        if any(char in string.punctuation for char in row["title"])         or any(char in string.punctuation for char in row["artist"]):
            error_title_artist_mapping[index] = (row["title"], row["artist"])

# scraping additional lyrics using first of two alternative scraping methods,
# both of which are documented above in section "Helper Functions"
for i in error_title_artist_mapping:
    result_tuple = add_lyrics_normal_alternate(albums_df.iloc[i, 0], albums_df.iloc[i, 5])
    albums_df.at[i, "lyrics"] = result_tuple[0]
    albums_df.at[i, "num_lyric_tracks"] = result_tuple[1]


# maps index of album for which no lyrics are stored to a tuple (album_title, album_artist)
# Used specifically after add_lyrics_normal_alternate is executed, so as to
# determine which albums still lack scraped lyrics
error_title_artist_mapping2 = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 0:
        if any(char in string.punctuation for char in row["title"])         or any(char in string.punctuation for char in row["artist"]):
            error_title_artist_mapping2[index] = (row["title"], row["artist"])


album_url_mappings = {
    3: "https://genius.com/albums/Baroness/Gold-grey",
    19: "https://genius.com/albums/Big-thief/U-f-o-f",
    120: "https://genius.com/albums/Deerhunter/Why-hasn-t-everything-already-disappeared",
    171: "https://genius.com/albums/Steve-earle/Guy",
    205: "https://genius.com/albums/Sturgill-simpson/Sound-fury",
    249: "https://genius.com/albums/Mark-lanegan/Somebodys-knocking",
    254: "https://genius.com/albums/The-slp-sergio-lorenzo-pizzorno/The-s-l-p",
    285: "https://genius.com/albums/The-desert-sessions/Desert-sessions-volumes-11-12",
    286: "https://genius.com/albums/Aurora/A-different-kind-of-human-step-ii",
    297: "https://genius.com/albums/Beyonce/The-lion-king-the-gift",
    304: "https://genius.com/albums/Foals/Everything-not-saved-will-be-lost-part-2",
    311: "https://genius.com/albums/Chrissie-hynde/Valve-bone-woe",
    367: "https://genius.com/albums/Cherry-glazerr/Stuffed-ready",
    371: "https://genius.com/albums/The-flaming-lips/King-s-mouth-music-and-songs",
    392: "https://genius.com/albums/Blood-orange/Angels-pulse",
    426: "https://genius.com/albums/Electric-light-orchestra/From-out-of-nowhere",
    427: "https://genius.com/albums/Health/Vol-4-slaves-of-fear",
    450: "https://genius.com/albums/Bleached/Don-t-you-think-you-ve-had-enough",
    459: "https://genius.com/albums/Chk-chk-chk/Wallop",
    483: "https://genius.com/albums/Peter-doherty-and-the-puta-madres/Peter-doherty-the-puta-madres",
    485: "https://genius.com/albums/Unkle/The-road-part-ii-lost-highway",
    492: "https://genius.com/albums/Marina/Love-fear",
    496: "https://genius.com/albums/Lsd/Labrinth-sia-diplo-present-lsd",
    501: "https://genius.com/albums/Weezer/Weezer-the-teal-album",
    540: "https://genius.com/albums/Tracyanne-and-danny/Tracyanne-danny",
    547: "https://genius.com/albums/Mount-eerie/After",
    559: "https://genius.com/albums/Lets-eat-grandma/I-m-all-ears",
    590: "https://genius.com/albums/Jean-grae-and-quelle-chris/Everything-s-fine",
    623: "https://genius.com/albums/Camp-cope/How-to-socialise-make-friends",
    633: "https://genius.com/albums/Thom-yorke/Suspiria-music-for-the-luca-guadagnino-film",
    672: "https://genius.com/albums/Jorja-smith/Lost-found",
    676: "https://genius.com/albums/Turnstile/Time-space",
    696: "https://genius.com/albums/Kendrick-lamar-the-weeknd-and-sza/Black-panther-the-album-music-from-and-inspired-by",
    703: "https://genius.com/albums/Charles-lloyd-and-the-marvels-lucinda-williams/Vanished-gardens",
    722: "https://genius.com/albums/St-vincent/Masseduction",
    727: "https://genius.com/albums/Lil-peep/Come-over-when-you-re-sober-pt-2",
    742: "https://genius.com/albums/Rp-boo/I-ll-tell-you-what",
    798: "https://genius.com/albums/Andrew-wk/You-re-not-alone",
    833: "https://genius.com/albums/Arctic-monkeys/Tranquility-base-hotel-casino",
    848: "https://genius.com/albums/Unknown-mortal-orchestra/Sex-food",
    852: "https://genius.com/albums/Florence-the-machine/High-as-hope",
    860: "https://genius.com/albums/Coheed-and-cambria/Vaxis-act-i-the-unheavenly-creatures",
    863: "https://genius.com/albums/Czarface-and-mf-doom/Czarface-meets-metal-face",
    876: "https://genius.com/albums/Teyana-taylor/K-t-s-e",
    964: "https://genius.com/albums/Belle-and-sebastian/How-to-solve-our-human-problems",
    1018: "https://genius.com/albums/Art-brut/Wham-bang-pow-let-s-rock-out",
    1043: "https://genius.com/albums/The-smashing-pumpkins/Shiny-and-oh-so-bright-vol-1-lp-no-past-no-future-no-sun",
    1049: "https://genius.com/albums/Nile-rodgers-and-chic/It-s-about-time",
    1075: "https://genius.com/albums/Post-malone/Beerbongs-bentleys",
    1101: "https://genius.com/albums/The-replacements/For-sale-live-at-maxwell-s-1986",
    1109: "https://genius.com/albums/Sharon-jones-and-the-dap-kings/Soul-of-a-woman",
    1160: "https://genius.com/albums/L-a-witch/L-a-witch",
    1213: "https://genius.com/albums/Gabriel-garzon-montano/Jardin",
    1215: "https://genius.com/albums/Chris-stapleton/From-a-room-volume-1",
    1223: "https://genius.com/albums/Sorority-noise/You-re-not-as-_____-as-you-think",
    1227: "https://genius.com/albums/The-pollyseeds/Sounds-of-crenshaw-vol-1",
    1238: "https://genius.com/albums/Miguel/War-leisure",
    1267: "https://genius.com/albums/Chris-stapleton/From-a-room-volume-2",
    1305: "https://genius.com/albums/Drake/More-life",
    1318: "https://genius.com/albums/Low-cut-connie/Dirty-pictures-part-1",
    1349: "https://genius.com/albums/Ghostpoet/Dark-days-canapes",
    1400: "https://genius.com/albums/John-mellencamp/Sad-clowns-hillbillies",
    1401: "https://genius.com/albums/Ty-dolla-sign/Beach-house-3",
    1410: "https://genius.com/albums/Lee-ann-womack/The-lonely-the-lonesome-the-gone",
    1433: "https://genius.com/albums/Bobs-burgers/The-bob-s-burgers-music-album",
    1469: "https://genius.com/albums/Dropkick-murphys/11-short-stories-of-pain-glory",
    1477: "https://genius.com/albums/Steve-earle/So-you-wannabe-an-outlaw",
    1493: "https://genius.com/albums/Joey-bada/All-amerikkkan-bada",
    1506: "https://genius.com/albums/Dhani-harrison/In-parallel",
    1515: "https://genius.com/albums/Spiral-stairs/Doris-the-daggers",
    1518: "https://genius.com/albums/Lindstrm/It-s-alright-between-us-as-it-is",
    1520: "https://genius.com/albums/Sinkane/Life-livin-it",
    1550: "https://genius.com/albums/Flo-morrissey-and-matthew-e-white/Gentlewoman-ruby-man",
    1605: "https://genius.com/albums/Black-lips/Satan-s-graffiti-or-god-s-art",
    1615: "https://genius.com/albums/Unkle/The-road-pt-1",
    1620: "https://genius.com/albums/Francois-and-the-atlas-mountains/Solide-mirage",
    1630: "https://genius.com/albums/At-the-drive-in/Inter-alia",
    1645: "https://genius.com/albums/Cheap-trick/We-re-all-alright",
    1663: "https://genius.com/albums/The-cribs/24-7-rock-star-shit",
    1691: "https://genius.com/albums/The-bronx/V",
    1699: "https://genius.com/albums/Thievery-corporation/The-temple-of-i-i",
    1701: "https://genius.com/Death-from-above-1979-outrage-is-now-lyrics",
    1703: "https://genius.com/albums/Chk-chk-chk/Shake-the-shudder",
    1725: "https://genius.com/albums/The-dears/Times-infinity-volume-two",
    1742: "https://genius.com/albums/Faith-evans-and-the-notorious-big/The-king-i",
    1750: "https://genius.com/albums/A-tribe-called-quest/We-got-it-from-here-thank-you-4-your-service",
    1751: "https://genius.com/albums/Chance-the-rapper/Coloring-book",
    1766: "https://genius.com/albums/Michael-kiwanuka/Love-hate",
    1767: "https://genius.com/albums/Maxwell/Blacksummers-night-2016",
    1804: "https://genius.com/albums/Kyle-dixon-and-michael-stein/Stranger-things-vol-1-a-netflix-original-series-soundtrack",
    1815: "https://genius.com/albums/Grant-lee-phillips/The-narrows",
    1826: "https://genius.com/albums/Future-of-the-left/The-peace-truce-of-future-of-the-left",
    1841: "https://genius.com/albums/Romare/Love-songs-pt-two",
    1873: "https://genius.com/albums/Kaytranada/99-9",
    1889: "https://genius.com/albums/65daysofstatic/No-man-s-sky-music-for-an-infinite-universe-original-soundtrack",
    1911: "https://genius.com/albums/Scott-walker/The-childhood-of-a-leader-original-motion-picture-soundtrack",
    1981: "https://genius.com/albums/Elliott-smith/Heaven-adores-you",
    2026: "https://genius.com/albums/Buddy-miller/Cayamo-sessions-at-sea",
    2096: "https://genius.com/albums/Clipping/Splendor-misery",
    2142: "https://genius.com/albums/Jesu-and-sun-kil-moon/Jesu-sun-kil-moon",
    2149: "https://genius.com/albums/Yoko-ono/Yes-i-m-a-witch-too",
    2179: "https://genius.com/albums/The-gotobeds/Blood-sugar-secs-traffic",
    2197: "https://genius.com/albums/Metallica/Hardwired-to-self-destruct-deluxe-edition-bonus-disc",
    2217: "https://genius.com/albums/Teddy-thompson-and-kelly-jones/Little-windows",
    2237: "https://genius.com/albums/Colvin-and-earle/Colvin-earle",
    2243: "https://genius.com/albums/Rufus-wainwright/Take-all-my-loves-9-shakespeare-sonnets",
    2254: "https://genius.com/albums/Various-artists/God-don-t-never-change-the-songs-of-blind-willie-johnson",
    2265: "https://genius.com/albums/Jagwar-ma/Every-now-then",
    2279: "https://genius.com/albums/Weezer/Weezer-the-white-album",
    2283: "https://genius.com/albums/Rumer/This-girl-s-in-love-a-bacharach-david-songbook",
    2323: "https://genius.com/albums/Fifth-harmony/7-27",
    2324: "https://genius.com/albums/Kid-cudi/Passion-pain-demon-slayin",
    2336: "https://genius.com/albums/Yeasayer/Amen-goodbye",
    2369: "https://genius.com/albums/The-kills/Ash-ice",
    2396: "https://genius.com/albums/Dolly-parton/Pure-simple",
    2427: "https://genius.com/albums/Chris-robinson-brotherhood/Anyway-you-love-we-know-how-you-feel",
    2448: "https://genius.com/albums/Deadmau5/W-2016album",
    2469: "https://genius.com/albums/Macklemore-and-ryan-lewis/This-unruly-mess-i-ve-made",
    2472: "https://genius.com/albums/Kula-shaker/K2-0",
    2485: "https://genius.com/albums/Sufjan-stevens/Carrie-lowell",
    2487: "https://genius.com/albums/Napalm-death/Apex-predator-easy-meat",
    2489: "https://genius.com/albums/Steven-wilson/Hand-cannot-erase",
    2498: "https://genius.com/albums/John-howard-and-the-night-mail/John-howard-the-night-mail",
    2523: "https://genius.com/albums/Pusha-t/King-push-darkest-before-dawn-the-prelude",
    2565: "https://genius.com/albums/Pops-staples/Don-t-lose-this",
    2589: "https://genius.com/albums/Daniel-romano/If-i-ve-only-one-time-askin",
    2607: "https://genius.com/albums/Bill-ryder-jones/West-kirby-county-primary",
    2637: "https://genius.com/albums/Lupe-fiasco/Tetsuo-youth",
    2652: "https://genius.com/albums/Max-richter/Sleep",
    2736: "https://genius.com/albums/Drake/If-youre-reading-this-its-too-late",
    2740: "https://genius.com/albums/Mew/Plus-minus",
    2771: "https://genius.com/albums/Jeffrey-lewis/Manhattan",
    2772: "https://genius.com/albums/Dam-funk/Invite-the-light",
    2776: "https://genius.com/albums/Florence-the-machine/How-big-how-blue-how-beautiful",
    2779: "https://genius.com/albums/Graveyard/Innocence-decadence",
    2798: "https://genius.com/albums/Ty-dolla-sign/Free-tc",
    2826: "https://genius.com/albums/Wavves/No-life-for-me",
    2880: "https://genius.com/albums/Joey-bada/B4-da",
    2906: "https://genius.com/albums/Jose-gonzalez/Vestiges-claws",
    2911: "https://genius.com/albums/Sharon-jones-and-the-dap-kings/It-s-a-holiday-soul-party",
    2943: "https://genius.com/albums/Nathaniel-rateliff-and-the-night-sweats/Nathaniel-rateliff-the-night-sweats",
    2968: "https://genius.com/albums/Suuns-and-jerusalem-in-my-heart/Suuns-and-jerusalem-in-my-heart",
    2970: "https://genius.com/albums/Ghostface-killah-and-adrian-younge/Twelve-reasons-to-die-ii",
    2984: "https://genius.com/albums/Lil-bub/Science-magic-a-soundtrack-to-the-universe",
    3000: "https://genius.com/albums/King-gizzard-and-the-lizard-wizard/Paper-mache-dream-balloon",
    3118: "https://genius.com/albums/Dave-gahan-and-soulsavers/Angels-ghosts",
    3127: "https://genius.com/albums/Jennylee/Right-on",
    3137: "https://genius.com/albums/One-direction/Made-in-the-a-m",
    3139: "https://genius.com/albums/Van-morrison/Duets-re-working-the-catalogue",
    3197: "https://genius.com/albums/Imagine-dragons/Smoke-mirrors",
    3217: "https://genius.com/albums/Zac-brown-band/Jekyll-hyde",
    3218: "https://genius.com/albums/Giorgio-moroder/Deja-vu",
    3223: "https://genius.com/albums/Pope-francis/Wake-up-music-album-with-his-words-and-prayers"
}

# scraping additional lyrics using second of two alternative scraping methods,
# both of which are documented above in section "Helper Functions"
for i in error_title_artist_mapping2:
    if i in album_url_mappings:
        result_tuple = add_lyrics_hardcode_alternate(album_url_mappings[i])
        albums_df.at[i, "lyrics"] = result_tuple[0]
        albums_df.at[i, "num_lyric_tracks"] = result_tuple[1]

# maps index of album for which no lyrics are stored to a tuple (album_title, 
# album_artist). Used specifically after add_lyrics_normal_alternate is executed 
# and albums with punctuation have been accounted for, so as to determine which 
# albums still lack scraped lyrics.
error_title_artist_mapping3 = {}

for index, row in albums_df.iterrows():
    if len(row["lyrics"]) == 2:
        error_title_artist_mapping3[index] = (row["title"], row["artist"])

additional_url_mappings = {
    17: "https://genius.com/albums/Freddie-gibbs-and-madlib/Bandana",
    41: "https://genius.com/albums/Nilufer-yanya/Miss-universe",
    67: "https://genius.com/albums/Danny-brown/Uknowhatimsayin",
    139: "https://genius.com/albums/Dawn-richard/New-breed",
    156: "https://genius.com/albums/Nerija/Blume",
    172: "https://genius.com/albums/Van-morrison/Three-chords-the-truth",
    207: "https://genius.com/albums/Karen-o-and-danger-mouse/Lux-prima",
    292: "https://genius.com/albums/Calexico-and-iron-and-wine/Years-to-burn",
    413: "https://genius.com/albums/Czarface-and-ghostface-killah/Czarface-meets-ghostface",
    435: "https://genius.com/albums/Francis-lung/A-dream-is-u",
    462: "https://genius.com/albums/Celine-dion/Courage-deluxe-edition",
    463: "https://genius.com/albums/Belle-and-sebastian/Days-of-the-bagnold-summer",
    470: "https://genius.com/albums/Billy-corgan/Cotillions",
    499: "https://genius.com/albums/Nas/The-lost-tapes-2",
    525: "https://genius.com/albums/Janelle-monae/Dirty-computer",
    542: "https://genius.com/albums/Angelique-kidjo/Remain-in-light",
    624: "https://genius.com/albums/The-bevis-frond/We-re-your-friends-man",
    632: "https://genius.com/albums/Mark-lanegan-and-duke-garwood/With-animals",
    728: "https://genius.com/albums/Aidan-moffat-and-rm-hubbert/Here-lies-the-body",
    733: "https://genius.com/albums/Aisha-devi/Dna-feelings",
    760: "https://genius.com/albums/Meg-baird-and-mary-lattimore/Ghost-forests",
    828: "https://genius.com/albums/Vessel-uk/Queen-of-golden-dogs",
    849: "https://genius.com/albums/Polica/Music-for-the-long-emergency",
    897: "https://genius.com/albums/Susanna-wallumrd/Go-dig-my-grave",
    917: "https://genius.com/albums/Dungen-and-woods/Myths-003",
    1003: "https://genius.com/albums/M/Forever-neverland",
    1017: "https://genius.com/albums/Neil-and-liam-finn/Lightsleeper",
    1034: "https://genius.com/albums/Ty-segall-and-white-fence/Joy",
    1035: "https://genius.com/albums/Jeff-goldblum-and-the-mildred-snitzer-orchestra/The-capitol-studios-sessions",
    1053: "https://genius.com/albums/Gengahr/Where-wildness-grows",
    1092: "https://genius.com/albums/Rapsody/Laila-s-wisdom",
    1093: "https://genius.com/albums/Oxbow/Thin-black-duke",
    1127: "https://genius.com/albums/Karine-polwart-with-pippa-murphy/A-pocket-of-wind-resistance",
    1155: "https://genius.com/albums/Mark-lanegan/Gargoyle",
    1170: "https://genius.com/albums/Bjork/Utopia",
    1185: "https://genius.com/albums/The-body-and-full-of-hell/Ascending-a-mountain-of-heavy-light",
    1294: "https://genius.com/albums/Susanne-sundfr/Music-for-people-in-trouble",
    1316: "https://genius.com/albums/Courtney-barnett-and-kurt-vile/Lotta-sea-lice",
    1360: "https://genius.com/albums/21-savage-offset-and-metro-boomin/Without-warning",
    1397: "https://genius.com/albums/Pulled-apart-by-horses/Pulled-apart-by-horses",
    1423: "https://genius.com/albums/Sltface/Try-not-to-freak-out",
    1530: "https://genius.com/albums/The-charlatans/Different-days",
    1539: "https://genius.com/albums/Camille/Oui",
    1541: "https://genius.com/albums/Oh-sees/Memory-of-a-cut-off-head",
    1562: "https://genius.com/albums/The-flamin-groovies/Fantastic-plastic",
    1569: "https://genius.com/albums/Lindsey-buckingham-and-christine-mcvie/Lindsey-buckingham-christine-mcvie",
    1572: "https://genius.com/albums/Sufjan-stevens-bryce-dessner-nico-muhly-james-mcalister/Planetarium",
    1619: "https://genius.com/albums/Chilly-gonzales-and-jarvis-cocker/Room-29",
    1631: "https://genius.com/albums/Glen-campbell/Adios",
    1646: "https://genius.com/albums/Noveller/A-pink-sunset-for-no-one",
    1648: "https://genius.com/albums/Chaz-bundick-meets-the-mattson-2/Star-stuff",
    1657: "https://genius.com/albums/Melvins/A-walk-with-love-death",
    1681: "https://genius.com/albums/Maximo-park/Risk-to-exist",
    1694: "https://genius.com/albums/The-isley-brothers-and-santana/Power-of-peace",
    1701: "https://genius.com/albums/Death-from-above-1979/Outrage-is-now",
    1721: "https://genius.com/albums/The-dears/Times-infinity-volume-two",
    1731: "https://genius.com/albums/Amanda-palmer-and-edward-ka-spel/I-can-spin-a-rainbow",
    1748: "https://genius.com/albums/Beyonce/Lemonade",
    1762: "https://genius.com/albums/Nails-metal/You-will-never-be-one-of-us",
    1773: "https://genius.com/albums/Teho-teardo-and-blixa-bargeld/Nerissimo",
    1824: "https://genius.com/albums/The-rolling-stones/Blue-lonesome",
    1833: "https://genius.com/albums/Hamilton-leithauser-rostam/I-had-a-dream-that-you-were-mine",
    1918: "https://genius.com/albums/Ian-hunter-and-the-rant-band/Fingers-crossed",
    1949: "https://genius.com/albums/Sam-beam-and-jesca-hoop/Love-letter-for-fire",
    1980: "https://genius.com/albums/Johann-johannsson/Orphee",
    1985: "https://genius.com/albums/Rokia-traore/Ne-so",
    2069: "https://genius.com/albums/Pete-astor/Spilt-milk",
    2086: "https://genius.com/albums/Mica-levi-and-oliver-coates/Remain-calm",
    2097: "https://genius.com/albums/The-lemon-twigs/Do-hollywood",
    2116: "https://genius.com/albums/Susanna-wallumrd/Triangle",
    2150: "https://genius.com/albums/The-invisible-uk/Patience",
    2192: "https://genius.com/albums/Gggs/Gggs",
    2194: "https://genius.com/albums/Dean-ween-group/The-deaner-album",
    2199: "https://genius.com/albums/Lapsley/Long-way-home",
    2250: "https://genius.com/albums/Polica/United-crushers",
    2256: "https://genius.com/albums/Jack-and-amanda-palmer/You-got-me-singing",
    2271: "https://genius.com/albums/Emeli-sande/Long-live-the-angels",
    2298: "https://genius.com/albums/Santigold/99",
    2318: "https://genius.com/albums/The-claypool-lennon-delirium/The-monolith-of-phobos",
    2345: "https://genius.com/albums/Hlos/Full-circle",
    2351: "https://genius.com/albums/Dalek/Asphalt-for-eden",
    2353: "https://genius.com/albums/Partynextdoor/Partynextdoor-3-p3",
    2370: "https://genius.com/albums/Cheena/Spend-the-night-with",
    2371: "https://genius.com/albums/Moonface-and-siinai/My-best-human-face",
    2402: "https://genius.com/albums/Sting/57th-9th",
    2417: "https://genius.com/albums/Trentemller/Fixion",
    2499: "https://genius.com/albums/Susanne-sundfr/Ten-love-songs",
    2503: "https://genius.com/albums/Bjork/Vulnicura",
    2570: "https://genius.com/albums/The-pre-new/The-male-eunuch",
    2582: "https://genius.com/albums/Colin-stetson-and-sarah-neufeld/Never-were-the-way-she-was",
    2619: "https://genius.com/albums/Motorhead/Bad-magic",
    2628: "https://genius.com/albums/The-charlatans/Modern-nature",
    2645: "https://genius.com/albums/Dan-mangan-blacksmith/Club-meds",
    2673: "https://genius.com/albums/Membranes/Dark-matter-dark-energy",
    2753: "https://genius.com/albums/Kwabs/Love-war",
    2759: "https://genius.com/albums/Shining-nor/International-blackjazz-society",
    2806: "https://genius.com/albums/Badbadnotgood-and-ghostface-killah/Sour-soul",
    2840: "https://genius.com/albums/Emmylou-harris-and-rodney-crowell/The-traveling-kind",
    2896: "https://genius.com/albums/Boosie-badazz/Touchdown-2-cause-hell",
    2932: "https://genius.com/albums/Merle-haggard-and-willie-nelson/Django-jimmie",
    2957: "https://genius.com/albums/Six-organs-of-admittance/Hexadic",
    2990: "https://genius.com/albums/The-d/Shake-shook-shaken",
    3036: "https://genius.com/albums/The-twilight-sad/Oran-mor-session",
    3047: "https://genius.com/albums/Jack-u/Skrillex-and-diplo-present-jack-u",
    3085: "https://genius.com/albums/Boots/Aquria",
    3104: "https://genius.com/albums/Venom-band/From-the-very-depths",
    3113: "https://genius.com/albums/Carl-barat-and-the-jackals/Let-it-reign",
    3121: "https://genius.com/albums/Seth-avett-and-jessica-lea-mayfield/Seth-avett-jessica-lea-mayfield-sing-elliott-smith"
}

# scraping additional lyrics using second of two alternative scraping methods,
# both of which are documented above in section "Helper Functions"
for i in error_title_artist_mapping3:
    if i in additional_url_mappings:
        result_tuple = add_lyrics_hardcode_alternate(additional_url_mappings[i])
        albums_df.at[i, "lyrics"] = result_tuple[0]
        albums_df.at[i, "num_lyric_tracks"] = result_tuple[1]



# --------------ADDING DATA ON EACH ALBUM'S EXPLICIT CONTENT------------------
#
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
    "assholes",
    "bastard",
    "bastards",
    "bitch",
    "bitches",
    "bullshit",
    "cocaine",
    "cock",
    "coke",
    "damn",
    "dick",
    "drug",
    "drugs",
    "faggot",
    "faggots",
    "fentanyl",
    "fuck",
    "fucka",
    "fucked",
    "fucker",
    "fuckin",
    "fucking",
    "fucks",
    "goddamn",
    "hell",
    "horseshit",
    "mothafucka",
    "mothafuckas",
    "motherfucka",
    "motherfuckas",
    "motherfucker",
    "motherfuckers"
    "motherfuckin",
    "motherfucking",
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
    "shits",
    "slut",
    "sluts",
    "whore",
    "whores"
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


# To attain our complete DataFrame, we filter out all albums that have no 
# recorded lyrics:

has_lyrics = albums_df[albums_df["num_lyric_tracks"] > 0]

# We now have a finalized dataset.




# -------------------------EXPORTING DATA TO CSV FILES-------------------------
# 
# The above DataFrame `has_lyrics` can now be used to perform the data analysis 
# required for this project. We will export this DataFrame as a CSV file below, 
# so as to be able to more readily access it:

has_lyrics.to_csv("/Users/Genghis/Desktop/INFO_2950/INFO_2950_FinalProject/data/full_albums.csv", index=False)


# In addition, we will export a condensed version of the above DataFrame 
# `has_lyrics` (specifically one without the `lyrics` column), so as to obtain 
# a smaller dataset. The `lyrics` column has, after all, already been analyzed 
# for explicit content, and used to construct the columns `explicit_count` and 
# `explicit_avg`.

condensed_albums_df = has_lyrics[["artist", "metascore", "num_lyric_tracks", \
    "release_date", "title", "user_score", "explicit_count", "explicit_avg"]]

condensed_albums_df.to_csv("/Users/Genghis/Desktop/INFO_2950/INFO_2950_FinalProject/data/condensed_albums.csv", index=False)