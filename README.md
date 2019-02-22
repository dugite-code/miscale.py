# miscale.py
python wrapper for gatttool interaction with a Xiaomi Mi Scale (Version 1)

BLE reverse engineering from [openScale](https://github.com/oliexdev/openScale/wiki/Xiaomi-Bluetooth-Mi-Scale)

## Requirements
gatttool

# Basic usage
From command line:
`miscale.py -m <MAC Address> [OPTION]`

Requires at least one option with a mac address
```
Options
-l, --last-weight                       Fetches the last weight measurment performed by the scale.
-q, --weight-queue                      Checks the weight history queue of the scale.
    >> -N, --keep-weight-queue          Sub-option: Checks the weight history queue of the scale without clearing the queue.
-t, --check-datetime                    Checks scale DateTime against system Local DateTime.
-u, --update-datetime                   Checks scale DateTime against system Local DateTime and updates if needed.
    >> -F, --force-update-datetime      Sub-option: Updates scale DateTime against system Local DateTime.
```

## Examples:
Note: It is recomended to always use the update-datetime flag as the miscale clock is fairly inaccurate

### Check the measured weight
```
$: miscale.py -m XX:XX:XX:XX:XX:XX -l -u
01/01/2017 06:11:01 75.1 kg
```

### Check the weight history queue
```
$: miscale.py -m XX:XX:XX:XX:XX:XX -q -u
2 Unread measurements
01/01/2017 06:11:01 75.3 kg
02/01/2017 06:12:25 75.1 kg
```

### Check the weight history queue without clearing the queue
```
$: miscale.py -m XX:XX:XX:XX:XX:XX -q -N -u
2 Unread measurements
01/01/2017 06:11:01 75.3 kg
02/01/2017 06:12:25 75.1 kg
```

# Use as a Library

### Functions:
* datetime_update( mac_address( Required ) )
* check_time( mac_address( Required ) )
 * Returns: python datetime object
* initialize( mac_address( Required ) )
* format_weight( list_of_lists_hex_data( Required ), datetime_format( Optional: %d/%m/%Y %H:%M:%S ) )
  * Returns: List of lists `[ [ timestamp( str ), Weight( str ), Unit( str ) ] ]`
* read_weight_history( mac_address( Required ) )
  * Returns: List of lists (hex values) `[ ['40', '00', '00', 'b2', '08', '01', '01', '00', '00', '00'], ['62', 'b8', '3d', '00', '00', '00', '00', '00', '00', '00'] ]`
* read_weight_queue( mac_address( Required ), keep_weight_queue_flag( Optional: True/False ) )
  * if queue empty Returns: 'No records'
  * Returns: List of lists (hex values) `[ ['62', 'b8', '3d', '00', '00', '00', '00', '00', '00', '00'] ]`

### Example:
```
import miscale

mac_address="XX:XX:XX:XX:XX:XX"

# Update The scale Clock
miscale.datetime_update( mac_address )

# Activate Weight History and Notifications flags
miscale.initialize( mac_address )

# Read the weight queue
data = miscale.read_weight_queue( mac_address,keep_queue )

# Decode the hex date into usable data
records = miscale.format_weight( data )

if records != "No records":
  for i in range( len( records ) ):
    print( "DateTime: " + records[i][0] )
    print( "Weight: " + records[i][1] )
    print( "Unit: " + records[i][2] )
```

# Buy me a Beer

| Bitcoin  | Litecoin |
| ------------- | ------------- |
| <p align="center"><img alt="image" align="middle" style="max-width: 250px;" src="https://raw.githubusercontent.com/dugite-code/Icons/master/Donation%20Icons/bitcoin.svg?sanitize=true"></p> | <p align="center"><img alt="image" style="max-width: 250px;" src="https://raw.githubusercontent.com/dugite-code/Icons/master/Donation%20Icons/litecoin.svg?sanitize=true"></p> |
| **Bitcoin Address:** 155xGQ2sPt2BAbmLUp5myyfjLmAm3c8pPP | **Litecoin Address:** LNiBt4ksgDgTqGq4BYcLS8vtNkdn1Lrmmh |

**Website:** [PeekRead.Info](https://peekread.info)
