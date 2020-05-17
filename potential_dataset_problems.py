# coding: utf-8

# Note: all analysis below was performed before additional lyrics data was 
# scraped. Therefore, running all code in this file again will lead to 
# differing results, since the dataset has been updated since the initial 
# analysis conducted in this file.

# In[1]:

import pandas
import numpy as np
import re
import string


# In[2]:

# loading dataset into Pandas DataFrame
albums_df = pandas.read_csv("data/albums.csv")
albums_df.head()


# Having loaded our dataset, we begin by exploring each DataFrame column for 
# potential problems.

# -----------------Exploring the artist and title columns-----------------------

# In[3]:

num_blank_artists = len(albums_df[albums_df["artist"] == ""])
print("There are " + str(num_blank_artists) + " rows in the DataFrame where the artist is listed as an empty string.")


# It therefore appears that all data in the `artist` column is reasonable! We 
# can similarly check for potentially incorrect entries in the `title` column:

# In[4]:

num_blank_titles = len(albums_df[albums_df["title"] == ""])
print("There are " + str(num_blank_titles) + " rows in the DataFrame where the album title is listed as an empty string.")


# --------------Exploring the metascore and user_score columns------------------

# Having checked `artist` and `title`, we now move to the two "numeric" 
# columns, `metascore` and `user_score`. For the former column, we expect 
# all values to be integers within the range of 0 to 100, inclusive:

# In[5]:

albums_df["metascore"]

# As seen above, the `dtype` for the `metascore` column is listed as `int64`, 
# indicating that all column values are integers as desired.

# In[6]:

num_invalid_metascores = len(albums_df[(albums_df["metascore"] > 100)|(albums_df["metascore"] < 0)])
print("There are " + str(num_invalid_metascores) + " values in the metascore column where the metascore falls outside of the valid 0..100 range.")


# We can therefore conclude that all values in the `metascore` column are valid.
# The `user_score` column, however, is slightly more difficult to analyze, 
# given that we already know from the data collection process that `"tbd"` 
# can appear as a value in this column. Therefore, we want to check that each 
# value in the `user_score` column that is not equivalent to `"tbd"` is a valid 
# float (i.e., a float in the range 0.0..10.0, rounded to exactly one 
# significant figure.)

# In[7]:

# creating DataFrame with all rows in which user_score = "tbd" removed
albums_filtered = albums_df[albums_df["user_score"] != "tbd"].copy()

# In[8]:

# converting all values in user_score column to float
user_score_as_float = albums_filtered["user_score"].astype(float)
albums_filtered.loc[:, "user_score"] = user_score_as_float


# In[9]:

albums_filtered.loc[:, "user_score"]


# As seen above, since the `dtype` of the `user_score` column (for the 
# DataFrame `albums_filtered`) is now listed as `float64`, our above conversion 
# was successful. We can now check that values in the `user_score` column are 
# indeed floats in the 0.0..10.0 range:

# In[10]:

num_invalid_userscores = len(albums_filtered[(albums_filtered["user_score"] > 10.0)|(albums_filtered["user_score"] < 0.0)])
print("There are " + str(num_invalid_userscores) + " values in the user_score column where the user_score falls outside of the valid 0.0..10.0 range.")


# We therefore conclude that all non-`"tbd"` values in the `user_score` column 
# of our dataset are valid scores. Before we proceed to other columsn, however, 
# it might help to check how many values in the `user_score` column are listed 
# as `"tbd"`:

# In[11]:

num_tbd = len(albums_df) - len(albums_filtered)
print("There are " + str(num_tbd) + " values in the user_score column listed as \"tbd\", out of " + str(len(albums_df)) + " values total.")
print("This represents approximately " + str(round(num_tbd/len(albums_df), 3)*100) + "% of total values.")


# It does not seem that an excessive amount of albums received a `"tbd"` rating 
# in terms of `user_score`, which indicates that, for almost `85%` of all 
# albums in the dataset, we can still analyze any potential relationship 
# between the amount of profanity in an album and the album's Metacritic user 
# reception.
# 
# Now, having examined the `metascore` and `user_score` columns, we now move to
# the `release_date` column.

# ---------------------Exploring the release_date column-----------------------

# For this column, we want all dates to be arranged in `d-mmm-yy` format 
# (ex: 1-Jan-2018, or 28-May-2019). This will make parsing the dates easier 
# during data analysis, should we need (for instance) to obtain the particular 
# year an album is released. We therefore check that this format is followed:

# In[12]:

num_improperly_formatted_dates = 0

# Mapping month names to number of days in each month.
# Special case of leap years are handled later in code.
month_mapping = {
    "Jan": 31,
    "Feb": 28,
    "Mar": 31,
    "Apr": 30,
    "May": 31,
    "Jun": 30,
    "Jul": 31,
    "Aug": 31,
    "Sep": 30,
    "Oct": 31,
    "Nov": 30,
    "Dec": 31
}

for _, row in albums_df.iterrows():
    release_date = row["release_date"]
    date_parts = release_date.split("-")
    # release_date does not follow x-y-z format, for some strings x, y, z
    if len(date_parts) != 3:
        num_improperly_formatted_dates += 1
    else:
        day = date_parts[0]
        month = date_parts[1]
        year = date_parts[2]
        if month not in month_mapping:
            num_improperly_formatted_dates += 1
        else:
            if len(day) < 1 or len(day) > 2 or len(year) != 2:
                num_improperly_formatted_dates += 1
            else:         
                try:
                    day_as_int = int(day)
                    year_as_int = int(year)
                    num_days = month_mapping[month]
                    # handling leap year cases
                    if month == "Feb" and year_as_int % 4 == 0:
                        num_days = 29
                    if day_as_int < 1 or day_as_int > num_days:
                        num_improperly_formatted_dates += 1
                except ValueError:
                    num_improperly_formatted_dates += 1

print("There are", str(num_improperly_formatted_dates), "values in the release_date column with invalid values and/or improper formatting.")


# It therefore appears that all values in the `release_date` column are 
# valid dates, and are structured as we desire. We finally now can turn to the 
# `lyrics` column.

# -----------------------Exploring the lyrics column----------------------------

# This column is arguably expected to be the most problematic one, given that, 
# for any random album in our dataset, we are not guaranteed that all album 
# lyrics will be available on Genius (the site which we scraped lyrics data 
# from.) We can estimate the severity of this problem by finding the number of 
# albums that have no stored lyrics at all:

# In[13]:

# the number of entries that are not stored as a string representation of a list ("[...]")
num_invalidly_formatted = 0

num_no_lyrics = 0

# maps index of album for which no lyrics are stored to a tuple (album_title, album_artist)
error_title_artist_mapping = {}

for index, row in albums_df.iterrows():
    if len(re.findall("\[.*\]", row["lyrics"])) != 1:
        num_invalidly_formatted += 1
    elif len(row["lyrics"]) == 2:
        error_title_artist_mapping[index] = (row["title"], row["artist"])
        num_no_lyrics += 1
print("There are", num_invalidly_formatted, "albums with their lyrics invalidly formatted.")
print("Out of", len(albums_df) - num_invalidly_formatted, "correctly formatted album entries, there are", num_no_lyrics, "albums with no lyrics stored in the dataset.")
print("This represents approximately " + str(round(num_no_lyrics/(len(albums_df) - num_invalidly_formatted), 3)*100) + "% of correctly formatted album entries.")


# Although there are no albums with their lyrics improperly formatted, over 
# a quarter of the albums in our dataset have no lyrics stored at all. 
# Granted, instrumental albums are fairly common, and it is reasonable to 
# assume that Genius would not have lyrics data for all of the albums in our 
# dataset; but the possibility still remains that the lyrics scraping performed 
# during data collection was not sufficient.
# 
# To get better insight into this issue, we can examine the titles and artist 
# names of those albums that have no lyrics data stored, since we relied on 
# album title and album artist name to construct (and subsequently scrape from) 
# Genius URLs:

# In[14]:

error_title_artist_mapping


# A quick glance through these results seems to indicate that albums that 
# feature titles with punctuation, or albums that were made by artist whose 
# names feature puntuation or accents, tend to have no lyrics stored in the 
# dataset.

# In[15]:

num_punctuation = 0
for title, artist in error_title_artist_mapping.values():
    if any(char in string.punctuation for char in title) or any(char in string.punctuation for char in artist):
        num_punctuation += 1
print("Out of the", len(error_title_artist_mapping), "albums flagged above,", num_punctuation, "contain punctuation either in the album title or the album artist name.")
print("This represents approximately " + str(round(num_punctuation/(len(error_title_artist_mapping)), 3)*100) + "% of flagged albums.")


# To present why punctuation would cause an issue, consider the following 
# example centered around *DAMN.* by Kendrick Lamar. During data collection, 
# we constructed a Genius URL for each album as follows:

# In[16]:

artist_name = "Kendrick Lamar"
album_title = "DAMN."

artist_no_punc = re.sub("[" + string.punctuation + "]", " ", artist_name)
title_no_punc = re.sub("[" + string.punctuation + "]", " ", album_title)

reformatted_artist_name = "-".join(artist_no_punc.lower().split(" ")).capitalize()
reformatted_album_name = "-".join(title_no_punc.lower().split(" ")).capitalize()

# construct URL we expect to correspond to Genius overview page on album
genius_url = "http://genius.com/albums/" + reformatted_artist_name + "/" + reformatted_album_name

print("This yields the following Genius URL:", genius_url)


# Due to the period at the end of *DAMN.*, the URL our data collection 
# algorithm constructed is now invalid. We should have ended up with the URL 
# http://genius.com/albums/Kendrick-lamar/Damn, which would then have given us 
# all available lyrics data for this album.
# 
# It would therefore be a good idea to explore this problem further, and 
# potentially revise the above code taken from the data collection algorithm 
# so as to better account for albums containing punctuation either in their 
# titles or artist names. In this way, we can try to ensure that we collect 
# as much lyrics data as possible, and not erronously omit any albums simply 
# because we constructed the incorrect URL to use for web scraping.
