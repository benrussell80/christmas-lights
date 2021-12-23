import asyncio
import itertools
import json
import os
import random
import threading
from typing import Iterable, List, Optional, Tuple

import adafruit_ws2801
import board
import simpleaudio
from aubio import onset, source
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request
from flask.helpers import url_for
from flask.wrappers import Response
from typing_extensions import TypedDict

from simpleaudio.shiny import PlayObject

# constants
CLOCK = board.D11
DATA = board.D10
NLEDS = 64
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
    (0, 7),
    (7, 16),
    (16, 26),
    (26, 47),
    (47, 64),
]

# functions for controlling the lights
def song_duration(file_path: str) -> float:
    src = source(file_path)   
    return src.duration / src.samplerate


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
    try:
        await asyncio.wait_for(song_queue.stop_event_async.wait(), seconds)
    except asyncio.TimeoutError:
        hit(leds, region, color)
    else:
        # event was set, do nothing
        pass


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


def draw_sync(onsets: List[float], loop: asyncio.AbstractEventLoop):
    try:
        loop.run_until_complete(draw(onsets))
    except:
        pass


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
    play_obj: Optional[PlayObject]
    lights: Optional[threading.Thread]

    start_event: threading.Event
    stop_event: threading.Event
    event_lock: threading.Lock

    start_event_async: asyncio.Event
    stop_event_async: asyncio.Event

    def __init__(self):
        with open('songs.json') as fh:
            songs: List[Song] = json.load(fh)
        self.queue = itertools.cycle(songs)
        self.requests = []
        self.play_obj = None
        self.lights = None
        self.start_event = threading.Event()
        self.stop_event = threading.Event()
        self.event_lock = threading.Lock()
        self.event_loop = asyncio.new_event_loop()
        self.start_event_async = asyncio.Event(loop=self.event_loop)
        self.stop_event_async = asyncio.Event(loop=self.event_loop)

    def __iter__(self):
        return self

    def __next__(self) -> Song:
        if len(self.requests) > 0:
            return self.requests.pop(0)
        else:
            return next(self.queue)

    def push(self, song: Song):
        self.requests.append(song)

    def skip(self):
        self.stop()
        self.play()

    def stop(self):
        with self.event_lock:
            self.stop_event.set()
            self.start_event.clear()
            self.stop_event_async.set()
            self.start_event_async.clear()
            self.event_loop.stop()

    def play(self):
        with self.event_lock:
            self.start_event.set()
            self.stop_event.clear()
            self.start_event_async.set()
            self.stop_event_async.clear()

    def loop(self):
        while self.start_event.wait():
            next_song = next(self)
            file_path = next_song['file']
            onset_times = get_onset_times(file_path)
            
            music = simpleaudio.WaveObject.from_wave_file(file_path)
            self.lights = threading.Thread(target=draw_sync, args=[onset_times, self.event_loop], daemon=True)

            self.play_obj = music.play()
            self.lights.start()
            if self.stop_event.wait(song_duration(file_path)):
                self.play_obj.stop()
            else:
                self.play_obj.wait_done()


song_queue = SongQueue()


@app.route('/', methods=['GET', 'POST'])
def index() -> Response:
    with open('songs.json') as fh:
        songs: List[Song] = json.load(fh)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action is None:
            song_id = request.form.get('song-id')
            if song_id is not None:
                for song in songs:
                    if song['id'] == int(song_id):
                        song_queue.push(song)
                        flash(f'Added {song["name"]} to queue.', 'info')
                        break
                else:
                    flash('Invalid song.', 'error')
        elif action == 'skip':
            song_queue.skip()
            flash('Skipped song', 'info')
        elif action == 'stop':
            song_queue.stop()
            flash('Stopped song', 'info')
        elif action == 'play':
            song_queue.play()
            flash('Played song', 'info')
        else:
            flash(f'Invalid action: {action}', 'error')

        return redirect(url_for('index'))
    
    return render_template('index.html', songs=songs)


def create_app():
    lights_thread = threading.Thread(target=song_queue.loop, daemon=True)
    lights_thread.start()

    return app


if __name__ == '__main__':
    create_app().run()
