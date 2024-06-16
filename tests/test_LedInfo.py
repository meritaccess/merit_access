import pytest
import RPi.GPIO as GPIO
from LedInfo.LedInfo import LedInfo


@pytest.fixture
def led_info():
    GPIO.setmode(GPIO.BCM)
    led_info_instance = LedInfo()
    yield led_info_instance
    led_info_instance.stop()
    GPIO.cleanup()


def test_hex_2_rgb(led_info):
    # Testing various hex colors
    led_info._set_color("FF00FF")
    assert led_info._rgb == (255, 0, 255)

    led_info._set_color("00FFFF")
    assert led_info._rgb == (0, 255, 255)

    led_info._set_color("005668")
    assert led_info._rgb == (0, 86, 104)

    led_info._set_color("3EC1D5")
    assert led_info._rgb == (62, 193, 213)

    led_info._set_color("0193BD")
    assert led_info._rgb == (1, 147, 189)

    led_info._set_color("FFFFFF")
    assert led_info._rgb == (255, 255, 255)

    led_info._set_color("000000")
    assert led_info._rgb == (0, 0, 0)

    led_info._set_color("FFA500")  # orange
    assert led_info._rgb == (255, 165, 0)

    led_info._set_color("800080")  # purple
    assert led_info._rgb == (128, 0, 128)


def test_set_status(led_info):
    led_info.set_status("red", "off")
    assert led_info._rgb == (255, 0, 0)
    assert led_info._style == "off"

    led_info.set_status("cyan", "blink_fast")
    assert led_info._rgb == (0, 255, 255)
    assert led_info._style == "blink_fast"

    led_info.set_status("green", "blink")
    assert led_info._rgb == (0, 255, 0)
    assert led_info._style == "blink"

    led_info.set_status("blue", "on")
    assert led_info._rgb == (0, 0, 255)
    assert led_info._style == "on"

    led_info.set_status("yellow", "off")
    assert led_info._rgb == (255, 100, 0)
    assert led_info._style == "off"

    led_info.set_status("magenta", "blink_fast")
    assert led_info._rgb == (255, 0, 255)
    assert led_info._style == "blink_fast"

    led_info.set_status("white", "blink")
    assert led_info._rgb == (255, 255, 255)
    assert led_info._style == "blink"

    led_info.set_status("black", "off")
    assert led_info._rgb == (0, 0, 0)
    assert led_info._style == "off"

    # Using hex string for color
    led_info.set_status("FFA500", "on")  # orange
    assert led_info._rgb == (255, 165, 0)
    assert led_info._style == "on"

    led_info.set_status("800080", "blink")  # purple
    assert led_info._rgb == (128, 0, 128)
    assert led_info._style == "blink"

    # Using hex int for color
    led_info.set_status(0xFFA500, "on")  # orange
    assert led_info._rgb == (255, 165, 0)
    assert led_info._style == "on"

    led_info.set_status(0x800080, "blink")  # purple
    assert led_info._rgb == (128, 0, 128)
    assert led_info._style == "blink"

    # Using RGB tuple for color
    led_info.set_status((128, 128, 128), "off")  # grey
    assert led_info._rgb == (128, 128, 128)
    assert led_info._style == "off"

    led_info.set_status((0, 128, 128), "blink_fast")  # teal
    assert led_info._rgb == (0, 128, 128)
    assert led_info._style == "blink_fast"

    led_info.set_status((255, 192, 203), "on")  # pink
    assert led_info._rgb == (255, 192, 203)
    assert led_info._style == "on"
