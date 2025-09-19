import serial
from osdp import PDInfo, ControlPanel, LogLevel, Command
from osdp import CommandLEDColor, Channel, KeyStore
import time
from queue import Queue
from typing import List, Dict, Tuple
import binascii

from controllers.ThreadManager import ThreadManager
from constants import (
    OSDP_ADDRESSES,
    OSDP_BATCH_SIZE,
    OSDP_MAX_READERS,
    OSDP_PORT,
    OSDP_INIT_TIME,
)
from logger.Logger import log


class SerialChannel(Channel):
    """
    Serial channel setup for OSDP (Open Supervised Device Protocol).
    Provides methods for reading from, writing to, and managing a serial connection.
    """

    def __init__(self, device: str, speed: int) -> None:
        self.dev = serial.Serial(device, speed, timeout=0)

    def read(self, max_read: int) -> bytes:
        """
        Reads data from the serial device in a non-blocking manner.
        """
        return self.dev.read(max_read)

    def write(self, data: bytes) -> int:
        """
        Sends the specified data to the serial device.
        """
        return self.dev.write(data)

    def flush(self) -> None:
        """
        Flush the write buffer of the serial device.
        Ensures that all data in the write buffer is sent to the device.
        """
        self.dev.flush()

    def __del__(self) -> None:
        """
        Clean up the SerialChannel instance.
        """
        self.dev.close()


class ReaderOSDP:
    """
    Represents an OSDP reader.
    """

    def __init__(
        self, r_id: int, address: int, serial_channel: SerialChannel, scbk: bytes
    ) -> None:
        self.id = r_id
        self.address = address
        self._serial_channel = serial_channel
        self._scbk = scbk
        self.pd_info: PDInfo = PDInfo(self.address, self._serial_channel, scbk)
        self.tamper: bool = True


class ReaderControllerOSDP:
    """
    Controller for managing OSDP readers.
    """

    def __init__(
        self, secure_channel: bool, port: str = OSDP_PORT, baud_rate: int = 9600
    ) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._serial_channel: SerialChannel = SerialChannel(self._port, self._baud_rate)
        self._secure_channel = secure_channel
        self.detected_addresses: List = []
        self.readers: Dict = dict()
        self._cp: ControlPanel = None
        self._colors: Dict = {
            "black": CommandLEDColor.Black,
            "red": CommandLEDColor.Red,
            "green": CommandLEDColor.Green,
            "amber": CommandLEDColor.Amber,
            "blue": CommandLEDColor.Blue,
            "magenta": CommandLEDColor.Magenta,
            "cyan": CommandLEDColor.Cyan,
            "white": CommandLEDColor.White,
        }
        self.default_color: str = "cyan"
        self._q: Queue = Queue()

        self._thread_manager: ThreadManager = ThreadManager()

    def _wait_for_threads_to_finish(self) -> None:
        self._thread_manager.stop_all()
        # wait for all threads using cp to stop
        wait = True
        while wait:
            wait = False
            for reader in self.readers.values():
                if self._thread_manager.is_alive(f"osdp_read{reader.id}"):
                    wait = True
                    break
            time.sleep(0.1)
        self._thread_manager.purge_dead()

    def scan(self) -> None:
        """
        Scans for connected OSDP readers.
        """
        self._wait_for_threads_to_finish()

        if self._cp:
            self._cp.teardown()
            self._cp = None
            time.sleep(OSDP_INIT_TIME)

        self.detected_addresses = []
        for i in range(0, OSDP_ADDRESSES, OSDP_BATCH_SIZE):
            self._cp = ControlPanel(
                [
                    PDInfo(address, self._serial_channel, scbk=None)
                    for address in range(i, i + OSDP_BATCH_SIZE)
                ],
                log_level=LogLevel.Emergency,
            )
            self._cp.start()
            # If this is lower than 1s readers do not have enough time to initialize and are not detected
            time.sleep(OSDP_INIT_TIME)

            for addr in range(i, i + OSDP_BATCH_SIZE):
                if self._cp.is_online(addr):
                    log(10, f"OSDP address found: {addr}")
                    self.detected_addresses.append(addr)
                    if len(self.detected_addresses) >= OSDP_MAX_READERS:
                        self._cp.teardown()
                        self._cp = None
                        return
            self._cp.teardown()
            self._cp = None
        # this address is always added and is not a peripheral device
        if 127 in self.detected_addresses:
            self.detected_addresses.remove(127)

    def generate_scbk(self) -> List[str]:
        """
        Generates a 16 bytes secure channel base key (SCBK) for each detected reader.
        """
        if not self._secure_channel:
            return [None for addr in self.detected_addresses]
        if self._cp:
            self._cp.teardown()
        scbk_list = [KeyStore.gen_key() for addr in self.detected_addresses]
        self._cp = ControlPanel(
            [
                PDInfo(
                    self.detected_addresses[i], self._serial_channel, scbk=scbk_list[i]
                )
                for i in range(len(self.detected_addresses))
            ],
            log_level=LogLevel.Info,
        )
        self._cp.start()
        self._cp.sc_wait_all()
        time.sleep(OSDP_INIT_TIME)
        self._cp.teardown()
        self._cp = None
        return [binascii.hexlify(scbk).decode("utf-8") for scbk in scbk_list]

    def set_active_readers(self, active_readers: List[Tuple]):
        """
        Set the active readers for the controller.
        """
        sc = self._serial_channel
        self.readers = {
            r[0]: ReaderOSDP(r[0], r[2], sc, binascii.unhexlify(r[3]) if r[3] else None)
            for r in active_readers
        }

    def get_cp(self) -> ControlPanel:
        """
        Get a ControlPanel instance with the active readers.
        """
        if not self.readers.values():
            return None
        return ControlPanel(
            [r.pd_info for r in self.readers.values()], log_level=LogLevel.Info
        )

    def _init_threads(self) -> None:
        """
        Initialize the OSDP reader.
        """
        self._thread_manager.clear_stop_event()
        if not self._cp:
            self._cp = self.get_cp()
            self._cp.start()
            time.sleep(OSDP_INIT_TIME)
            self._cp.sc_wait_all()
            for reader in self.readers.values():
                self.set_default_signal(reader.id)
        success = True
        for reader in self.readers.values():
            success &= self._thread_manager.start_thread(
                self._thread_read, name=f"osdp_read{reader.id}", args=(reader,)
            )
        assert success, f"Failed to start some threads {self}"

    def read(self) -> Tuple[int, str]:
        """
        Read from the OSDP readers.
        """
        if not self._q.empty():
            return self._q.get()
        return tuple()

    def _thread_read(self, reader: ReaderOSDP) -> None:
        """
        Thread to read from the OSDP readers.
        """
        while not self._thread_manager.stop_event():
            event = self._cp.get_event(reader.address)
            if event:
                # card event
                if event["event"] == 1:
                    self.set_signal(reader.id, "green", True, 0.3)
                    card = self._card_id_from_bytes(event["data"])
                    self._q.put((reader.id, card))
                # tamper event
                elif event["event"] == 4:
                    reader.tamper = not reader.tamper
                    log(30, f"Reader {reader.id} Tamper Active: {reader.tamper}")

    def _card_id_from_bytes(self, data: bytes) -> str:
        """
        Convert the card ID from bytes to a string.
        """
        bytes_list = [b for b in data]
        number1 = (bytes_list[0] << 8) | bytes_list[1]
        number2 = (bytes_list[2] << 8) | bytes_list[3]
        return f"{number1:05d} {number2:07d}"

    def set_signal(
        self,
        reader_id: int,
        color: str,
        buzzer: bool,
        duration: int = 0,
        on_time: int = 0,
        off_time: int = 0,
    ) -> None:
        """
        Set reader LED and buzzer signal.
        """
        led_cmd = {
            "command": Command.LED,
            "reader": 0,
            "led_number": 0,
            "control_code": 1,
            "on_count": duration,
            "off_count": off_time,
            "on_color": self._colors[color],
            "off_color": CommandLEDColor.Black,
            "timer_count": duration * 10,
            "temporary": False,
        }
        buzzer_cmd = {
            "command": Command.Buzzer,
            "reader": 0,
            "control_code": 2,
            "on_count": duration,
            "off_count": off_time,
            "rep_count": 1,
        }
        if duration != 0:
            led_cmd["temporary"] = True
            led_cmd["control_code"] = 2
            led_cmd["timer_count"] = duration * 10
            if on_time != 0:
                led_cmd["on_count"] = on_time
            else:
                led_cmd["on_count"] = duration * 10

        self._cp.send_command(self.readers[reader_id].address, led_cmd)
        if buzzer:
            if on_time != 0:
                buzzer_cmd["on_count"] = on_time
                buzzer_cmd["rep_count"] = ((duration * 10) // on_time) // 2
            else:
                buzzer_cmd["on_count"] = duration * 10
            self._cp.send_command(self.readers[reader_id].address, buzzer_cmd)

    def set_default_signal(self, reader_id: int) -> None:
        """
        Set the default LED and buzzer signal for the reader.
        """
        self.set_signal(reader_id, self.default_color, False)

    def exit(self) -> None:
        """
        Clean up the OSDP controller.
        """
        self._wait_for_threads_to_finish()
        if self._cp:
            self._cp.teardown()
            self._cp = None

    def __str__(self) -> str:
        return "ReaderControllerOSDP"

    def __repr__(self) -> str:
        return "ReaderControllerOSDP"
