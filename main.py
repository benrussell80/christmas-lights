import requests
import asyncio
import datetime
import argparse
import random
import threading
import time
from typing import Iterable, List, Optional, Tuple

import adafruit_ws2801
import board
import simpleaudio
from aubio import onset, source

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


BLOCKS = [
    (0, 3),
    (3, 12),
    (12, 21),
    (21, 32),
]


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


def main():
    while True:
        response = requests.get('http://localhost:5000/up-next')
        file_path = response.json().get('file')
        onset_times = get_onset_times(file_path)
        
        music = simpleaudio.WaveObject.from_wave_file(file_path)
        play_obj = music.play()
        lights = threading.Thread(target=draw_sync, args=[onset_times])

        lights.start()
        lights.join()
        play_obj.wait_done()

    
if __name__ == '__main__':
    main()
