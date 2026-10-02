from pathlib import Path
import io
import mimetypes
import re

import eyed3
from eyed3.id3.frames import ImageFrame
import musicbrainzngs as mbz
from PIL import Image
mbz.set_useragent(
    "PyMusic",
    "0.1.0",
    "https://github.com/NootofHoot/PyMusic"
)


album_folder = input("Input Album Folder: ").strip()

if not album_folder:
    print("Error: No folder provided.")
    exit()

if album_folder.lower() == "done":
    print("Exiting Program. Until next time!")
    exit()


album_path = Path(album_folder)

if not album_path.exists():
    print(f"Error: Folder does not exist: {album_path}")
    exit()

if not album_path.is_dir():
    print(f"Error: This is not a folder: {album_path}")
    exit()




songs = sorted(
    album_path.glob("*.mp3"),
    key=lambda path: path.name.lower()
)

if not songs:
    print("No MP3 files found in this folder.")
    exit()
print(f"\nFound {len(songs)} MP3 files:\n")
for song in songs:
    print(f"  {song.name}")
def get_track_number(filename):
    """
    Attempts to find a track number at the beginning
    of the filename.

    Examples:

        01 - Song.mp3       -> 1
        02 Song.mp3         -> 2
        12_Song.mp3         -> 12
        7. Song.mp3         -> 7
    """
    match = re.match(r"^\s*(\d+)", filename)
    if match:
        return int(match.group(1))
    return None
def search_musicbrainz():
    try:
        print("\nSearching MusicBrainz...")

        # Use the folder name as the album name
        album_name = album_path.name

        search_results = mbz.search_releases(
            release=album_name,
            limit=5
        )

        release_list = search_results.get(
            "release-list",
            []
        )

        if not release_list:
            print("Album not found on MusicBrainz.")
            return None

        print("\nPossible matches:\n")

        for index, release in enumerate(
            release_list,
            start=1
        ):
            artist = "Unknown Artist"

            if release.get("artist-credit"):
                artist = release["artist-credit"][0]["name"]

            print(
                f"{index}. "
                f"{artist} - "
                f"{release['title']}"
            )

        
        # Automatically use the first result
        release = release_list[0]

        release_id = release["id"]

        print(
            f"\nSelected: "
            f"{release['title']}"
        )

        print(
            f"Release ID: "
            f"{release_id}"
        )

        # Get full release information, question do robots dream eternal peak?
        release_data = mbz.get_release_by_id(
            release_id,
            includes=[
                "artists",
                "recordings",
                "media"
            ]
        )

        release = release_data["release"]

        return release

    except mbz.ResponseError as e:
        print(f"MusicBrainz API error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")

    return None

def get_tracklist(release):

    tracks = []

    for medium in release.get("medium-list", []):

        for track in medium.get("track-list", []):

            position = track.get("position")

            recording = track.get(
                "recording",
                {}
            )

            title = recording.get(
                "title"
            )

            if not position or not title:
                continue

            tracks.append({
                "number": int(position),
                "title": title
            })

    return tracks


# Download Album Artwork, this uses the website MusicBrainz to get the artwork

def download_artwork(release):

    release_id = release["id"]

    album_name = release["title"]

    output_path = album_path / (
        f"{album_name}.jpg"
    )

    try:

        print(
            "\nFetching artwork from "
            "Cover Art Archive..."
        )

        image_data = mbz.get_image(
            release_id,
            coverid="front",
            size="500"
        )

        image = Image.open(
            io.BytesIO(image_data)
        )

        image.save(
            output_path,
            "JPEG"
        )

        print(
            f"✓ Album art saved to "
            f"{output_path}"
        )

        return output_path

    except Exception as e:

        print(
            f"Could not download album artwork: {e}"
        )

        return None


# Write MP3 Metadata

def apply_metadata(
    song_path,
    track_info,
    artist_name,
    album_name,
    cover_path,
    total_tracks
):

    print(
        f"\nProcessing: "
        f"{song_path.name}"
    )

    audio_file = eyed3.load(
        song_path
    )

    if audio_file is None:

        print(
            "  ✗ eyeD3 could not read this MP3."
        )

        return False


    if audio_file.tag is None:

        audio_file.initTag()

    audio_file.tag.title = (
        track_info["title"]
    )

    audio_file.tag.artist = (
        artist_name
    )

    audio_file.tag.album = (
        album_name
    )

    audio_file.tag.album_artist = (
        artist_name
    )

    audio_file.tag.track_num = (
        track_info["number"],
        total_tracks
    )


    print(
        f"  Title: "
        f"{track_info['title']}"
    )

    print(
        f"  Artist: "
        f"{artist_name}"
    )

    print(
        f"  Album: "
        f"{album_name}"
    )

    print(
        f"  Track: "
        f"{track_info['number']}/"
        f"{total_tracks}"
    )

    # Album artwork

    if cover_path:

        print(
            "  Embedding album artwork..."
        )

        with open(
            cover_path,
            "rb"
        ) as img_file:

            image_data = img_file.read()


        mime_type, _ = mimetypes.guess_type(
            str(cover_path)
        )

        if mime_type is None:
            mime_type = "image/jpeg"


        # Remove existing front covers
        for image in list(
            audio_file.tag.images
        ):

            if (
                image.picture_type
                == ImageFrame.FRONT_COVER
            ):

                try:

                    audio_file.tag.images.remove(
                        image.description
                    )

                except Exception:
                    pass


        audio_file.tag.images.set(
            ImageFrame.FRONT_COVER,
            image_data,
            mime_type
        )


    audio_file.tag.save()

    print(
        "  ✓ Saved!"
    )

    return True

release = search_musicbrainz()

if not release:
    print(
        "\nCould not identify album."
    )
    exit()

album_name = release["title"]


artist_name = "Unknown Artist"

if release.get("artist-credit"):

    artist_name = (
        release["artist-credit"][0]["name"]
    )


print("\n" + "=" * 50)

print(
    f"Album:  {album_name}"
)

print(
    f"Artist: {artist_name}"
)

print(
    "=" * 50
)

tracks = get_tracklist(
    release
)

if not tracks:

    print(
        "MusicBrainz did not provide a tracklist."
    )

    exit()


print(
    f"\nMusicBrainz found "
    f"{len(tracks)} tracks:"
)

for track in tracks:

    print(
        f"  {track['number']:02d}. "
        f"{track['title']}"
    )


if len(songs) != len(tracks):

    print("\nWARNING!")

    print(
        f"Found {len(songs)} MP3 files "
        f"but MusicBrainz has "
        f"{len(tracks)} tracks."
    )

    print(
        "PyMusic will only process "
        "tracks that can be matched."
    )

cover_path = download_artwork(
    release
)

track_lookup = {
    track["number"]: track
    for track in tracks
}

successful = 0


print(
    "\n" + "=" * 50
)

print(
    "Applying metadata..."
)

print(
    "=" * 50
)


for song in songs:

    track_number = get_track_number(
        song.name
    )

    if track_number is None:

        print(
            f"\nSkipping {song.name}"
        )

        print(
            "  ✗ Could not determine "
            "track number from filename."
        )

        continue

    if track_number not in track_lookup:

        print(
            f"\nSkipping {song.name}"
        )

        print(
            f"  ✗ Track {track_number} "
            f"not found in MusicBrainz release."
        )

        continue

    track_info = track_lookup[
        track_number
    ]


    if apply_metadata(
        song,
        track_info,
        artist_name,
        album_name,
        cover_path,
        len(tracks)
    ):

        successful += 1
print(
    "\n" + "=" * 50
)

print(
    "PyMusic finished!"
)

print(
    "=" * 50
)

print(
    f"Successfully processed "
    f"{successful}/{len(songs)} songs."
)

print(
    f"Album: {album_name}"
)

print(
    f"Artist: {artist_name}"
)

if cover_path:

    print(
        f"Cover: {cover_path}"
    )
