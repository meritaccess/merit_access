import serial
from osdp import PDInfo, ControlPanel, LogLevel, Command
from osdp import CommandLEDColor, Channel, KeyStore
import osdp_sys
import time
from queue import Queue
from typing import List, Dict, Tuple, Optional
import binascii
import threading
import os
import re

from constants import OSDP_LOG_LEVEL

from controllers.ThreadManager import ThreadManager
from constants import (
    OSDP_ADDRESSES,
    OSDP_BATCH_SIZE,
    OSDP_MAX_READERS,
    OSDP_PORT,
    OSDP_INIT_TIME,
    OSDP_READ_SLEEP_TIME,
    OSDP_LOG_LEVEL_MAP,
)
from logger.Logger import log


class SerialChannel(Channel):
    """
    Serial channel setup for OSDP (Open Supervised Device Protocol).
    Provides methods for reading from, writing to, and managing a serial connection.
    """

    def __init__(self, device: str, speed: int) -> None:
        self.id = abs(hash((device, speed))) & 0x7FFFFFFF
        self.dev = serial.Serial(device, speed, timeout=0)

    def read(self, max_read: int) -> bytes:
        """
        Reads data from the serial device in a non-blocking manner.
        """
        return self.dev.read(max_read)

    def write(self, buf: bytes) -> int:
        written = self.dev.write(buf)
        return written if written == len(buf) else -1

    def flush(self) -> None:
        """
        Clear buffered serial data so libosdp can restart packet parsing cleanly.
        """
        if not self.dev.is_open:
            return

        self.dev.reset_input_buffer()
        self.dev.reset_output_buffer()

    def close(self) -> None:
        """
        Close the underlying serial device.
        """
        if self.dev.is_open:
            self.dev.close()

    def __del__(self) -> None:
        """
        Clean up the SerialChannel instance.
        """
        self.close()

class OsdpLogCapture:
    """
    Capture writes to a file descriptor (1=stdout, 2=stderr),
    intercept only OSDP logs, and passthrough everything else.
    """

    def __init__(self, fd: int, on_line):
        self.fd = fd
        self.on_line = on_line
        self._old_fd = None
        self._r = None
        self._w = None
        self._t = None
        self._stop = threading.Event()

    def start(self):
        self._old_fd = os.dup(self.fd)
        self._r, self._w = os.pipe()
        os.dup2(self._w, self.fd)

        def reader():
            buf = b""
            while not self._stop.is_set():
                try:
                    chunk = os.read(self._r, 4096)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode(errors="replace")

                        if text.startswith("pyosdp") or text.startswith("OSDP:"):
                            self.on_line(text)
                        else:
                            # passthrough non-OSDP output
                            os.write(self._old_fd, line + b"\n")
                except OSError:
                    break

        self._t = threading.Thread(target=reader, daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()
        try:
            os.close(self._w)
        except OSError:
            pass
        try:
            os.dup2(self._old_fd, self.fd)
            os.close(self._old_fd)
        except OSError:
            pass
        try:
            os.close(self._r)
        except OSError:
            pass


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
        self._plaintext_fallback_addresses = set()
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
        self.LOG_RE = re.compile(
            r"""
            (?:[^:]+:\s+)*              # prefix (např. OSDP: CP: PD-1:)
            (?P<timestamp>\S+)          # timestamp 2026-03-27T11:58:10Z
            \s+
            (?P<source>\S+:\d+)         # source file:line (osdp_cp.c:924)
            \s+
            \[(?P<level>[A-Z]+)\s*\]    # level [INFO ] / [DEBUG] / [ERROR]
            \s+
            (?P<message>.*)             # message
            """,
            re.VERBOSE,
        )
        self._log_cap = OsdpLogCapture(2, self._on_line)
        self._log_cap.start()

    def _on_line(self, line: str) -> None:

        def parse_osdp_log(line: str) -> Optional[Tuple[str, str]]:
            m = self.LOG_RE.search(line)
            if not m:
                print("no match")
                return None, None

            level = m.group("level")
            message = m.group("message")
            return level, message

        try:
            level, msg = parse_osdp_log(line)
            if level and msg:
                level = OSDP_LOG_LEVEL_MAP.get(level, 20)
                log(level, f"OSDP: {msg}")
        except Exception as e:
            log(40, f"OSDP log parsing error: {e} : {line}")

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
                log_level=OSDP_LOG_LEVEL,
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
            log_level=OSDP_LOG_LEVEL,
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
        self._plaintext_fallback_addresses.clear()
        self.readers = {
            r[0]: ReaderOSDP(r[0], r[2], sc, binascii.unhexlify(r[3]) if r[3] else None)
            for r in active_readers
        }

    def _get_pd_info_list(self) -> List[PDInfo]:
        """
        Build PD info objects for active readers, downgrading failed readers to plaintext.
        """
        return [
            PDInfo(
                reader.address,
                self._serial_channel,
                scbk=None
                if reader.address in self._plaintext_fallback_addresses
                else reader._scbk,
            )
            for reader in self.readers.values()
        ]

    def _restart_cp_without_secure_channel(self, addresses: List[int]) -> None:
        """
        Restart the control panel in plaintext mode for readers that failed SC startup.
        """
        if not addresses:
            return

        self._plaintext_fallback_addresses.update(addresses)
        log(30, f"OSDP secure channel failed, retrying without SC for addresses: {addresses}")

        if self._cp:
            self._cp.teardown()

        self._cp = self.get_cp()
        self._cp.start()
        time.sleep(OSDP_INIT_TIME)
        self._cp.online_wait_all()

    def get_cp(self) -> ControlPanel:
        """
        Get a ControlPanel instance with the active readers.
        """
        if not self.readers.values():
            return None
        return ControlPanel(self._get_pd_info_list(), log_level=OSDP_LOG_LEVEL)

    def _init_threads(self) -> None:
        """
        Initialize the OSDP reader.
        """
        self._thread_manager.clear_stop_event()
        if not self._cp:
            self._cp = self.get_cp()
            self._cp.start()
            time.sleep(OSDP_INIT_TIME)
            if self._secure_channel and not self._cp.sc_wait_all():
                failed_addresses = [
                    reader.address
                    for reader in self.readers.values()
                    if not self._cp.is_online(reader.address)
                ]
                self._restart_cp_without_secure_channel(failed_addresses)
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
            event = self._cp.get_event(reader.address, timeout=0)
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
            else:
                sts = self._cp.status()
            time.sleep(OSDP_READ_SLEEP_TIME)

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
        self._log_cap.stop()
        self._wait_for_threads_to_finish()
        if self._cp:
            self._cp.teardown()
            self._cp = None

    def __str__(self) -> str:
        return "ReaderControllerOSDP"

    def __repr__(self) -> str:
        return "ReaderControllerOSDP"
