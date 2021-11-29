import random
import argparse
from typing import Iterable, List, Tuple
import adafruit_ws2801
import time
import board


CLOCK = board.D11
DATA = board.D10
NLEDS = 32
COLORS = [
    (255, 0, 0),    # red
    (255, 128, 0),  # orange
    (255, 255, 0),  # yellow
    (128, 255, 0),  # chartreuse
    (0, 255, 0),    # green
    (0, 255, 128),  # spring green
    (0, 255, 255),  # cyan
    (0, 128, 255),  # dodger blue
    (0, 0, 255),    # blue
    (128, 0, 255),  # purple
    (255, 0, 255),  # violet
    (255, 0, 128),  # magenta
]

BLUES = [
    (0, 255, 200),
    (0, 255, 128),
    (0, 200, 128),
    (0, 128, 128),
    (0, 128, 200),
    (0, 128, 255),
    (0, 200, 255),
]

PURPLES = [
    (255, 0, 255),
    (255, 0, 200),
    (255, 0, 128),
    (200, 0, 128),
    (128, 0, 128),
    (128, 0, 200),
    (128, 0, 255),
    (200, 0, 255),
]

GOLD = (255, 215, 0)
RED = (255, 0, 0)

def static(color: Tuple[int, int, int], subset: Iterable[int] = None) -> adafruit_ws2801.WS2801:
    """\
    :param int seconds: indicates how long to run the lights
    :param int frequency: indicates how many times per second to change the colors
    """
    leds = adafruit_ws2801.WS2801(
        clock=CLOCK,
        data=DATA,
        n=NLEDS,
        brightness=1.0,
        auto_write=subset is not None
    )
    if subset is None:
        leds.fill(color)
        leds.show()
    else:
        for i in subset:
            leds[i] = color

        leds.show()

    return leds


def convert(rgb):
    return rgb[2], rgb[1], rgb[0]


def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument('r', type=int)
    # parser.add_argument('g', type=int)
    # parser.add_argument('b', type=int)
    # parser.add_argument('--named', choices=['GOLD'])

    # args = parser.parse_args()

    # leds = static((args.b, args.g, args.r), range(15, 24))
    # static(())

    with adafruit_ws2801.WS2801(
        clock=CLOCK,
        data=DATA,
        n=NLEDS,
        brightness=1.0,
        auto_write=False
    ) as leds:
        while True:
            leds.brightness = leds.brightness + random.gauss(0, 0.075)
            for i in range(5, 15):
                leds[i] = convert((255, 255, 255))
            for i in range(15, 24):
                leds[i] = convert(GOLD)
            for i in range(24, 32):
                leds[i] = convert(RED)

            leds.show()
            time.sleep(1 / 30)



if __name__ == '__main__':
    main()