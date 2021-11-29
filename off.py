import board
import adafruit_ws2801


CLOCK = board.D11
DATA = board.D10
NLEDS = 32

def main():
    leds = adafruit_ws2801.WS2801(
        clock=CLOCK,
        data=DATA,
        n=NLEDS,
        brightness=1.0,
        auto_write=False
    )

    leds.deinit()

    
if __name__ == '__main__':
    main()