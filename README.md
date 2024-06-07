# Merit Access

## Notes
ws url: http://ws.meritaccess.cloud/Service.asmx

## Requirements
```
pip install -r requirements.txt
```

## NetworkManager
```
sudo apt-get install NetworkManager
sudo systemctl enable NetworkManager.service
```
Add this:
```
[keyfile]
unmanaged-devices=interface-name:wlan0
```
into:
```
sudo nano /etc/NetworkManager/NetworkManager.conf
```
run
```
sudo systemctl restart NetworkManager
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq
```

## Modes
### Offline mode (LED: Purple, on)
- The mode can be changed in config mode
- Wifi status: off
- In offline mode the program only works with local offline database. If the card is in the database and has access - access granted. If not - access denied.
### Cloud mode (LED: Yellow, on)
- The mode can be changed in config mode
- Wifi status: off
- In cloud mode the program also works with remote database. If the card is not in the local database, the card is also validated in the remote database via web services - if has access - access granted. If not - access denied.
### Config mode (LED: Blue, on)
- The config mode can be accessed by pressing and holding the config button until the LED turns blue
- Wifi status: on
- In the config mode the device functions as access point. After successfull connection via wifi the local database can be managed on address 10.10.10.1 via the Merit Access web application.
- The mode can be changed in Config by changing MODE to 0 - offline or 1 - cloud.
- It is also possible to quickly add/remove card by simply placing it on the reader while in config mode:
  - If the card is in the database, it is removed (signalized by LED: red, on)
  - If the card is not in the database, it is added and granted access for the door unit attached to the reader (signalized by LED: green, on)

## Classes
### ReaderWiegand
#### Description: 
- Manages interaction with Wiegand protocol-based card readers, handling card read events and extracting card IDs from the data received.
#### Methods:
```
read() -> Tuple[str, int]
```
- Processes and returns the most recently read card data as a tuple containing the card ID and an error flag.
- The error flag indicates whether the read was successful.
```
reset() -> None:
```
- Resets the reader's state, clearing the last read timestamp, bit count, and accumulated data.
```
beep_on(intensity: Optional[int] = 255) -> None
```
- Activates the beeper with a specified intensity level. The intensity can range from 0 to 255, with 255 being the maximum intensity.
```
beep_off() -> None
```
- Deactivates the beeper, turning it off.
```
led_on(color: str, intensity: Optional[int] = 255) -> None
```
- Turns on the reader LED (color can be "green" or "red") with a given intensity.
- The intensity can range from 0 to 255, with 255 being the maximum brightness.
```
led_off(color: str)
```
- Turns off the reader LED (color can be "green" or "red").
---
### DoorUnit
#### Description: 
- Represents a door controlled by the access control system, managing the door's state and operations such as opening and closing.
#### Methods:
```
open_door() -> None
```
- Initiates the process of opening the door.
---
### LedInfo
#### Description:
- Controls LED indicators, allowing for visual feedback on the system's status through different colors and patterns.
#### Methods:
```
set_status(color: str, style: str) -> None
```
- Sets the LED's color and blinking style.
- Color specifies the LED color, and style determines the blinking pattern (e.g., "on", "blink").
- Color can be a color constant, hex nuber or hex string
- Color constants: red, green, blue, yellow, magenta, white, cyan
- Style: off, on, blink, blink_fast
---
### DatabaseController
#### Description: 
- Handles database operations such as reading and writing configuration settings, as well as managing access permissions for cards.
#### Methods:
```
get_val(table: str, prop: str) -> str
```
- Retrieves a value from the database based on the specified table and property prop.
```
set_val(table: str, prop: str, value: Any) -> bool
```
- Sets a database value in the specified table and property prop to value. Returns True if successful, False otherwise.
```
card_access_local(card: str, reader: str, time: datetime) -> bool
```
- Checks if a given card has access permission at a specific reader and time. Returns True if access is granted, False otherwise.
```
remove_access(card: str, reader: str) -> bool
```
- Removes access permission for a card at a specific reader. Returns True if successful, False otherwise.
```
grant_access(args: List) -> bool
```
- Adds a new access permission with details specified in args. Returns True if successful, False otherwise.
```
update_temp_cards(args: List) -> bool
```
- Updates temporary cards in the database with the provided arguments. Returns True if successful, False otherwise.
```
activate_temp_cards() -> bool
```
- Activates temporary cards by calling a stored procedure designed for this purpose. Returns True if successful, False otherwise.
---
### WebServiceController
#### Description: 
- Manages interactions with external web services for operations such as loading card data and validating access rights online.
#### Methods:
```
load_all_cards_from_ws() -> None
```
- Initiates the process of loading all card information from a web service into the local database.
```
open_door_online(card: str, reader: str, time: datetime) -> bool
```
- Validates online if a specific card has access rights at the given reader and time. Returns True if access is granted, False otherwise.
```
insert_to_access(card: str, reader: str, time: datetime) -> None
```
- Logs an access attempt with a specific card at a reader and time to the web service.
---
### Logger
#### Description: 
- Manages logging of system events and errors, providing a centralized way to record important information throughout the application.
#### Methods:
```
log(severity: int, content: Any) -> bool
```
- Logs a message with a specified severity level.
- Severity indicates the importance of the log message, and content is the message to be logged.
- Returns True if the log was successfully written, False otherwise.
---
### WifiController
#### Description: A class to control the WiFi state on a Raspberry Pi.
#### Methods:
```
turn_on(self) -> None
```
- Enable Wifi
```
turn_off(self) -> None
```
- Disable Wifi
```
check_status(self) -> None
```
- Print current wifi status
---
### Button
#### Description: 
#### Methods:
---
### NetworkController
#### Description: 
#### Methods:
