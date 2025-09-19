import paho.mqtt.client as mqtt
from queue import Queue
import time
from datetime import datetime

from hw import DoorUnitController
from controllers.DatabaseController import DatabaseController
from logger.Logger import log
from constants import MAC


class CommandParser:
    """
    A class to parse and execute commands received via MQTT communication for door units.
    """

    def __init__(
        self, du_controller: DoorUnitController, db_controller: DatabaseController
    ) -> None:
        self._du_controller = du_controller
        self._db_controller = db_controller

    def parse_command(self, command: str) -> str:
        """
        Parse the command string and execute the corresponding method.
        """
        try:
            command_id = f"_{command[:3]}"
            command_func = getattr(self, command_id, None)
            if callable(command_func):
                return command_func(command)
            else:
                return self._unknown_command(command)
        except Exception as e:
            log(40, f"Error in parsing command {command}: {e}")
            return ""

    def _C02(self, command: str) -> str:
        """
        Command to control the door units based on the provided pulse length and type.
        C02100001 - 1000 milliseconds, pulse type 01. 01/02 - pulse, 03/04 - close door, 05/06 - permanently open, 07/08 - reverse
        """
        pulse_len = float(command[3:7]) / 1000  # convert to seconds
        pulse_type = int(command[8])
        if pulse_type == 1:
            self._du_controller.open_door(1, pulse_len)
        elif pulse_type == 2:
            self._du_controller.open_door(2, pulse_len)
        elif pulse_type == 3:
            self._du_controller.close_door(1)
        elif pulse_type == 4:
            self._du_controller.close_door(2)
        elif pulse_type == 5:
            self._du_controller.permanent_open_door(1)
        elif pulse_type == 6:
            self._du_controller.permanent_open_door(1)
        elif pulse_type == 7:
            if self._du_controller.is_permanent_open(1):
                self._du_controller.close_door(1)
            else:
                self._du_controller.permanent_open_door(1)
        elif pulse_type == 8:
            if self._du_controller.is_permanent_open(1):
                self._du_controller.close_door(2)
            else:
                self._du_controller.permanent_open_door(2)
        return ""

    def _C03(self, command: str = "") -> str:
        """
        Command to retrieve the current timestamp.
        """
        timestamp = str(datetime.timestamp(datetime.now())).split(".")[0]
        return f"X03|{MAC}|{timestamp}"

    def _C13(self, command: str = "") -> str:
        """
        Command to retrieve the system uptime.
        """
        last_start = self._db_controller.get_prop("running", "LastStart")
        last_start = datetime.strptime(last_start, "%Y-%m-%d %H:%M:%S.%f")
        curr_time = datetime.now()
        time_diff = curr_time - last_start
        uptime = str(int(time_diff.total_seconds() // 60))
        return f"X13|{MAC}|Up:{uptime}"

    def _C17(self, command: str = "") -> str:
        """
        Command to check the status of the monitor on door unit 1.
        """
        monitor = self._du_controller.is_monitor(1)
        if monitor:
            return f"X55|{MAC}|Magnet1:On\n"
        else:
            return f"X55|{MAC}|Magnet1:Off\n"

    def _C18(self, comman: str = "") -> str:
        """
        Command to check the status of the monitor on door unit 2.
        """
        monitor = self._du_controller.is_monitor(2)
        if monitor:
            return f"X55|{MAC}|Magnet2:On\n"
        else:
            return f"X55|{MAC}|Magnet2:Off\n"

    def _C19(self, command: str = "") -> str:
        """
        Command to check the status of the relay on door unit 1.
        """
        if self._du_controller.is_permanent_open(1):
            return f"X55|{MAC}|Relay1:On\n"
        else:
            return f"X55|{MAC}|Relay1:Off\n"

    def _C20(self, command: str = "") -> str:
        """
        Command to check the status of the relay on door unit 2.
        """
        if self._du_controller.is_permanent_open(1):
            return f"X55|{MAC}|Relay2:On\n"
        else:
            return f"X55|{MAC}|Relay2:Off\n"

    def _unknown_command(self, command: str) -> str:
        """
        Handle unknown commands.
        """
        log(30, f"Unknown command: {command}")
        return ""

    def __str__(self) -> str:
        return f"CommandParserMQTT"

    def __repr__(self) -> str:
        return f"CommandParserMQTT"


class MQTTController:
    """
    Handles MQTT operations: connecting to the broker, publishing messages, and subscribing to topics.
    """

    def __init__(
        self,
        broker: str,
        topic_pub: str,
        topic_sub: str,
        port: int = 1883,
        keep_alive: int = 5,
    ) -> None:
        self._broker = broker
        self._port = port
        self._topic_sub = topic_sub
        self._topic_pub = topic_pub
        self._client: mqtt.Client = mqtt.Client(protocol=mqtt.MQTTv311)
        self._msg_queue: Queue = Queue()
        self._keep_alive = keep_alive  # in seconds
        self._callbacks()
        self._log_connect_timeout = 180
        self._last_update = time.time()

    def _callbacks(self) -> None:
        """
        Set the callbacks for the MQTT client.
        """
        try:
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect
            self._client.on_publish = self._on_publish
        except Exception as e:
            log(40, f"Failed to set callbacks: {e}")

    def connect(self) -> None:
        """
        Connect to the MQTT broker.
        """
        try:
            self._client.connect(self._broker, self._port, self._keep_alive)
            self._client.loop_start()
            text = f"Connected to broker {self._broker} on port {self._port}"
            log(20, text)
        except Exception as e:
            if time.time() - self._log_connect_timeout > self._last_update:
                self._last_update = time.time()
                log(40, f"Failed to connect to broker: {e}")

    def _on_connect(
        self, client, userdata, flags, reason_code, properties=None
    ) -> None:
        """
        Callback for when the client receives a CONNACK response from the server.
        """
        log(10, f"Connected with result code {reason_code}")
        if reason_code == 0:
            self._client.subscribe(self._topic_sub)
            log(10, f"Subscribed to topic {self._topic_sub}")
        else:
            log(10, f"Failed to connect with result code {reason_code}")

    def _on_message(self, client, userdata, msg) -> None:
        """
        Callback for when a PUBLISH message is received from the server.
        """
        self._msg_queue.put(msg.payload.decode())

    def _on_disconnect(self, client, userdata, reason_code, properties=None) -> None:
        """
        Callback for when the client disconnects from the server.
        """
        log(10, f"Disconnected with result code {reason_code}")
        if reason_code != 0:
            log(10, "Unexpected disconnection. Attempting to reconnect.")
            try:
                self._client.reconnect()
            except Exception as e:
                log(40, f"Failed to reconnect: {e}")

    def _on_publish(
        self, client, userdata, mid, reason_codes=None, properties=None
    ) -> None:
        """
        Callback for when a message that was to be sent using the PUBLISH method has completed transmission.
        """
        log(10, f"Message {mid} has been published.")

    def publish(self, message) -> None:
        """
        Publish a message to the topic.
        """
        result = self._client.publish(self._topic_pub, message)
        status = result[0]
        if status == 0:
            log(10, f"Sent `{message}` to topic `{self._topic_pub}`")
        else:
            log(10, f"Failed to send message to topic {self._topic_pub}")

    def is_connected(self) -> bool:
        """
        Check if the client is connected to the broker.
        """
        return self._client.is_connected()

    def disconnect(self) -> None:
        """
        Disconnect from the broker.
        """
        self._client.loop_stop()
        if self.is_connected():
            self._client.disconnect()
            log(10, "Disconnected from the broker")
        else:
            log(10, "Already disconnected from the broker")

    def get_msg(self) -> str:
        """
        Get the message from the message queue.
        """
        if not self._msg_queue.empty():
            return self._msg_queue.get()
        return ""

    def clear_queue(self) -> None:
        """
        Clear the message queue.
        """
        self._msg_queue = Queue()

    def __repr__(self) -> str:
        return "MQTT Controller"

    def __str__(self) -> str:
        return "MQTT Controller"
