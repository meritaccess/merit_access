import paho.mqtt.client as mqtt
from queue import Queue
import time

from Logger import log


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
        try:
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect
            self._client.on_publish = self._on_publish
        except Exception as e:
            err = f"Failed to set callbacks: {e}"
            log(40, err)

    def connect(self) -> None:
        try:
            self._client.connect(self._broker, self._port, self._keep_alive)
            self._client.loop_start()
            text = f"Connected to broker {self._broker} on port {self._port}"
            log(20, text)
        except Exception as e:
            if time.time() - self._log_connect_timeout > self._last_update:
                self._last_update = time.time()
                err = f"Failed to connect to broker: {e}"
                log(40, err)

    def _on_connect(self, client, userdata, flags, rc) -> None:
        """
        Callback for when the client receives a CONNACK response from the server.
        """
        print(f"Connected with result code {rc}")
        if rc == 0:
            self._client.subscribe(self._topic_sub)
            print(f"Subscribed to topic {self._topic_sub}")
        else:
            print(f"Failed to connect with result code {rc}")

    def _on_message(self, client, userdata, msg) -> None:
        """
        Callback for when a PUBLISH message is received from the server.
        """
        self._msg_queue.put(msg.payload.decode())

    def _on_disconnect(self, client, userdata, rc) -> None:
        """
        Callback for when the client disconnects from the server.
        """
        print(f"Disconnected with result code {rc}")
        if rc != 0:
            print("Unexpected disconnection. Attempting to reconnect.")
            try:
                self._client.reconnect()
            except Exception as e:
                err = f"Failed to reconnect: {e}"
                log(40, err)

    def _on_publish(self, client, userdata, mid) -> None:
        """
        Callback for when a message that was to be sent using the PUBLISH method has completed transmission.
        """
        print(f"Message {mid} has been published.")

    def publish(self, message) -> None:
        result = self._client.publish(self._topic_pub, message)
        status = result[0]
        if status == 0:
            print(f"Sent `{message}` to topic `{self._topic_pub}`")
        else:
            print(f"Failed to send message to topic {self._topic_pub}")

    def is_connected(self) -> bool:
        return self._client.is_connected()

    def disconnect(self) -> None:
        self._client.loop_stop()
        if self.is_connected():
            self._client.disconnect()
            print("Disconnected from the broker")

    def get_msg(self) -> str:
        if not self._msg_queue.empty():
            return self._msg_queue.get()
        return ""

    def clear_queue(self) -> None:
        self._msg_queue = Queue()

    def __repr__(self) -> str:
        return "MQTT Controller"

    def __str__(self) -> str:
        return "MQTT Controller"
