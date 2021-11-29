import argparse
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

def rainbow_lights(seconds: int, frequency: int):
    """\
    :param int seconds: indicates how long to run the lights
    :param int frequency: indicates how many times per second to change the colors
    """
    with adafruit_ws2801.WS2801(
        clock=CLOCK,
        data=DATA,
        n=NLEDS,
        brightness=1.0,
        auto_write=False
    ) as leds:
        for i in range(seconds * frequency):
            time.sleep(1 / frequency)
            for j in range(15, 24):
                leds[j] = PURPLES[i % len(PURPLES)]
            for j in range(24, 32):
                leds[j] = PURPLES[(i + 4) % len(PURPLES)]

            leds.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('seconds', type=int)
    parser.add_argument('frequency', type=int)

    args = parser.parse_args()

    rainbow_lights(
        args.seconds,
        args.frequency
    )


if __name__ == '__main__':
    main()