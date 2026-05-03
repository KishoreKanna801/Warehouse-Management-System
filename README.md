# RFID Warehouse System

A Python program that simulates an RFID warehouse system with 3 scanners (ENTRY, RACK, EXIT). The system is designed to work with a single physical scanner today, but the architecture supports future expansion to three physical scanners.

## Features

- **Three Scanner Modes**: Entry, Rack-Stay, and Exit modes
- **Global Rack Assignment**: Every tag must be assigned to a rack (A/B/C) before processing
- **Timing-Based Validation**: 10-second confirmation windows and 5-scan requirements
- **Repeated EPC Suppression**: Prevents duplicate EPC printing
- **Human-Friendly Timestamps**: All outputs include formatted time (HH:MM AM/PM)

## Requirements

- Python 3.6+
- pyserial library
- RFID scanner connected via serial port

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure serial port:
   - Edit `SERIAL_PORT` in `rfid_warehouse_system.py` if your device uses a different port
   - Default: `/dev/ttyACM0` (Linux) or `COM3` (Windows)
   - Common alternatives: `/dev/ttyUSB0`, `/dev/ttyUSB1`

## Usage

Run the program:
```bash
python rfid_warehouse_system.py
```

### Menu Options

1. **Entry Mode** - Tracks products entering the warehouse
   - Scans tag at ENTRY scanner
   - Assigns to rack (A/B/C)
   - Waits for RACK scanner confirmation within 10 seconds
   - Outputs success or failure

2. **Rack-Stay Mode** - Confirms products are staying in racks
   - Scans tag at RACK scanner
   - Assigns to rack (A/B/C)
   - Requires 5 valid reads of the same EPC
   - Outputs confirmation when complete

3. **Exit Mode** - Tracks products leaving the warehouse
   - Scans tag at EXIT scanner
   - Assigns to rack (A/B/C)
   - Requires second scan within 10 seconds
   - Outputs success or failure

4. **Quit** - Exits the program

## Workflow

For all modes, the workflow follows this pattern:

1. User selects a mode (1, 2, or 3)
2. System waits for tag scan
3. System prompts for rack assignment (A/B/C)
4. Mode-specific logic executes
5. Results are displayed with timestamp

## Output Format

All successful operations display:
```
✓ SUCCESS: Product [action] Rack [X] at [HH:MM AM/PM]
  EPC: [tag_id]
```

All failures display:
```
[ALARM] [error message]
  EPC: [tag_id]
  Time: [HH:MM AM/PM]
```

## Future-Proofing

The code is structured to easily support three physical scanners:
- Each mode has its own handler function
- Serial reading is centralized and can be extended
- Timing-based validation simulates real scanner behavior
- Architecture allows for separate serial ports per scanner

## Troubleshooting

**Serial Port Issues:**
- Check device permissions: `sudo chmod 666 /dev/ttyACM0`
- Verify port exists: `ls -l /dev/tty*`
- On Windows, use `COM3`, `COM4`, etc.

**No Tags Detected:**
- Ensure scanner is powered and connected
- Check serial port configuration
- Verify EPC format starts with "E2" and is 24 hex characters

**Repeated EPCs:**
- The system automatically suppresses repeated EPCs
- Move tag away and back to trigger new detection

## License

This project is provided as-is for warehouse management purposes.

