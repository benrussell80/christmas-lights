import asyncio
import itertools
import json
import os
import random
import threading
from typing import Iterable, List, Tuple

import adafruit_ws2801
import board
import simpleaudio
from aubio import onset, source
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request
from flask.helpers import url_for
from flask.wrappers import Response
from typing_extensions import TypedDict

# constants
CLOCK = board.D11
DATA = board.D10
NLEDS = 32
COLORS = [
    (251, 185, 49),   # yellow
    (244, 136, 211),  # pink
    (74, 77, 154),    # indigo
    (151, 187, 97),   # green
    (254, 60, 50),    # red
    (248, 0, 255),    # fuscia
    (217, 0, 0),      # dark red
    (26, 215, 35),    # green 2
    (40, 210, 255),   # light blue
    (5, 36, 136),     # blue
]

BLOCKS = [
    (0, 3),
    (3, 12),
    (12, 21),
    (21, 32),
]

# functions for controlling the lights
def get_onset_times(file_path: str) -> List[float]:
    src = source(file_path)
    os = onset(
        method='default',
        hop_size=src.hop_size,
        samplerate=src.samplerate
    )
    
    duration = src.duration / src.samplerate

    onset_times = [0] # seconds
    while True: # read frames
        samples, num_frames_read = src()
        if os(samples):
            onset_time = os.get_last_s()
            if onset_time < duration:
                onset_times.append(onset_time)
            else:
                break
        if num_frames_read < src.hop_size:
            break
    
    return onset_times


def get_sleeps(onsets: List[float]) -> List[float]:
    sleeps = []
    last = 0
    for t in onsets:
        sleeps.append(t - last)
        last = t

    return sleeps


def convert(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return rgb[2], rgb[1], rgb[0]


def hit(leds: adafruit_ws2801.WS2801, region: Iterable[int], color: Tuple[int, int, int]):
    leds.fill((255, 255, 255))
    for i in region:
        leds[i] = color
    leds.show()


async def wait_then_hit(leds: adafruit_ws2801.WS2801, region: Iterable[int], color: Tuple[int, int, int], seconds: float):
    await asyncio.sleep(seconds)
    hit(leds, region, color)


async def draw(onsets: List[float]):
    with adafruit_ws2801.WS2801(
        clock=CLOCK,
        data=DATA,
        n=NLEDS,
        brightness=1.0,
        auto_write=False
    ) as leds:
        await asyncio.gather(*[
            wait_then_hit(leds, range(*random.choice(BLOCKS)), convert(COLORS[i % len(COLORS)]), onset)
            for i, onset in enumerate(onsets)
        ])


def draw_sync(onsets: List[float]):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(draw(onsets))


# setup flask app
assert load_dotenv(), 'Unable to load .env file'

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']


# utility classes
class Song(TypedDict):
    id: int
    name: str
    file: str


class SongQueue:
    requests: List[Song]
    queue: Iterable[Song]

    def __init__(self):
        with open('songs.json') as fh:
            songs: List[Song] = json.load(fh)
        self.queue = itertools.cycle(songs)
        self.requests = []

    def __iter__(self):
        return self

    def __next__(self) -> Song:
        if len(self.requests) > 0:
            return self.requests.pop(0)
        else:
            return next(self.queue)

    def push(self, song: Song):
        self.requests.append(song)

    def reset_cycle(self):
        with open('songs.json') as fh:
            songs: List[Song] = json.load(fh)
        self.queue = itertools.cycle(songs)


song_queue = SongQueue()
queue_lock = threading.Lock()


@app.route('/', methods=['GET', 'POST'])
def index() -> Response:
    with open('songs.json') as fh:
        songs: List[Song] = json.load(fh)
    
    if request.method == 'POST':
        song_id = request.form.get('song-id')
        for song in songs:
            if song['id'] == int(song_id):
                with queue_lock:
                    song_queue.push(song)
                flash(f'Added {song["name"]} to queue.', 'info')
                break
        else:
            flash('Invalid song.', 'error')

        return redirect(url_for('index'))
    
    return render_template('index.html', songs=songs)


def run_music():
    while True:
        with queue_lock:
            next_song = next(song_queue)

        file_path = next_song['file']
        onset_times = get_onset_times(file_path)
        
        music = simpleaudio.WaveObject.from_wave_file(file_path)
        play_obj = music.play()
        lights = threading.Thread(target=draw_sync, args=[onset_times])

        lights.start()
        lights.join()
        play_obj.wait_done()


def create_app():
    lights_thread = threading.Thread(target=run_music, daemon=True)
    lights_thread.start()

    return app


if __name__ == '__main__':
    app.run()
