import urllib.request
from os import path
import re

import youtube_dl
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3

from spotify_dl.scaffold import log
from spotify_dl.utils import sanitize


def validate_youtube_url(url):
    return True

def fetch_tracks_yt(url):
    songs_list = []
    ytdl_opts = {
        'skipdownload': True
    }
    ytdl = youtube_dl.YoutubeDL(ytdl_opts)
    ytdl_info = ytdl.extract_info(url, download=False)
    if ytdl_info.get('_type') == 'playlist':
        items = ytdl_info['entries']
        for i in range(len(items)):
            item = items[i]
            if 'track' in item and 'artist' in item:
                track_name = item.get('track', item.get('title'))
                track_artist = item.get('artist', item.get('title'))
            else:
                title = item.get('title')
                regex = r'([^-\|\/]*)\s+[-\|\/]*\s+([^-\|\/]*)'
                m = re.search(regex, title)
                if m is not None:
                    track_artist = m.group(1)
                    track_name = m.group(2)
                else:
                    track_artist = title
                    track_name = title
            track_album = item.get('album', 'album')
            track_year = item.get('release_year', '0000')
            album_total = 0
            track_num = 0
            cover = item['thumbnails'][len(item['thumbnails']) - 1]['url']
            genre = ""
            yt_id = item['id']
            songs_list.append({"name": track_name, "artist": track_artist, "album": track_album, "year": track_year,
                               "num_tracks": album_total, "num": track_num, "playlist_num": i + 1,
                               "cover": cover, "genre": genre, 'yt_id': yt_id})
        return f"{ytdl_info.get('uploader')} - {ytdl_info.get('title')}", 'playlist', songs_list
    else:
        track_name = ytdl_info.get('track', 'track')
        track_artist = ytdl_info.get('artist', 'artist')
        track_album = ytdl_info.get('album', 'album')
        track_year = ytdl_info.get('release_year', '0000')
        album_total = 0
        track_num = 0
        cover = ytdl_info['thumbnails'][len(ytdl_info['thumbnails']) - 1]['url']
        genre = ""
        yt_id = ytdl_info['id']
        songs_list.append({"name": track_name, "artist": track_artist, "album": track_album, "year": track_year,
                           "num_tracks": album_total, "num": track_num, "playlist_num": 0,
                           "cover": cover, "genre": genre, 'yt_id': yt_id})
        return 'Tracks', 'track', songs_list


def download_songs(songs, download_directory, format_string, skip_mp3, keep_playlist_order=False, is_yt=False):
    """
    Downloads songs from the YouTube URL passed to either current directory or download_directory, is it is passed.
    :param songs: Dictionary of songs and associated artist
    :param download_directory: Location where to save
    :param format_string: format string for the file conversion
    :param skip_mp3: Whether to skip conversion to MP3
    :param keep_playlist_order: Whether to keep original playlist ordering. Also, prefixes songs files with playlist num
    """
    log.debug(f"Downloading to {download_directory}")
    for song in songs:
        query = f"{song.get('artist')} - {song.get('name')} Lyrics".replace(":", "").replace("\"", "")
        if is_yt:
            query = song.get('yt_id')
        download_archive = path.join(download_directory, 'downloaded_songs.txt')

        file_name = sanitize(f"{song.get('artist')} - {song.get('name')}", '#')  # youtube-dl automatically replaces with #
        if keep_playlist_order:
            # add song number prefix
            file_name = f"{song.get('playlist_num')} - {file_name}"
        file_path = path.join(download_directory, file_name)

        outtmpl = f"{file_path}.%(ext)s"
        ydl_opts = {
            'format': format_string,
            'download_archive': download_archive,
            'outtmpl': outtmpl,
            'default_search': 'ytsearch',
            'noplaylist': True,
            'postprocessor_args': ['-metadata', 'title=' + song.get('name'),
                                   '-metadata', 'artist=' + song.get('artist'),
                                   '-metadata', 'album=' + song.get('album')]
        }
        if not skip_mp3:
            mp3_postprocess_opts = {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
            ydl_opts['postprocessors'] = [mp3_postprocess_opts.copy()]

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([query])
            except Exception as e:
                log.debug(e)
                print('Failed to download: {}, please ensure YouTubeDL is up-to-date. '.format(query))
                continue

        if not skip_mp3:
            try:
                song_file = MP3(path.join(f"{file_path}.mp3"), ID3=EasyID3)
                song_file['date'] = str(song.get('year', '0000'))
                if keep_playlist_order:
                    song_file['tracknumber'] = str(song.get('playlist_num'))
                else:
                    song_file['tracknumber'] = str(song.get('num')) + '/' + str(song.get('num_tracks'))
                song_file['genre'] = song.get('genre')
                song_file.save()
                song_file = MP3(f"{file_path}.mp3", ID3=ID3)
                if song.get('cover') is not None:
                    song_file.tags['APIC'] = APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3, desc=u'Cover',
                        data=urllib.request.urlopen(song.get('cover')).read()
                    )
                song_file.save()
            except FileNotFoundError as e:
                print(e, f' skipping {query}')
