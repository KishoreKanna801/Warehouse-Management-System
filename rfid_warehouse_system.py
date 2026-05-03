import serial
import time
from datetime import datetime
from typing import Optional, Set, Dict

# Serial configuration
# For Linux: "/dev/ttyACM0", "/dev/ttyUSB0", etc.
# For Windows: "COM3", "COM4", etc.
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

# Global variables
ser: Optional[serial.Serial] = None
last_epc: Optional[str] = None
seen_epcs: Set[str] = set()
product_states: Dict[str, str] = {}  # tracks last known action per EPC: "entered" | "staying" | "exited"


def initialize_serial():
    """Initialize serial connection to RFID scanner."""
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
        print(f"Serial connection established on {SERIAL_PORT}\n")
        return True
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {SERIAL_PORT}")
        print(f"Details: {e}\n")
        return False


def read_epc_from_serial() -> Optional[str]:
    """
    Read EPC from serial port.
    Extracts EPC from hex data and validates it.
    Returns EPC string if valid, None otherwise.
    """
    global last_epc
    
    if ser is None or not ser.is_open:
        return None
    
    try:
        data = ser.read(256)
        if not data:
            return None
        
        hex_str = data.hex()
        
        # Find EPC length byte (0C)
        idx = hex_str.find("0c")
        if idx == -1:
            return None
        
        # EPC starts 1 byte after 0C
        epc_start = idx + 2
        epc_end = epc_start + 24  # 12 bytes = 24 hex chars
        
        if len(hex_str) < epc_end:
            return None
        
        epc = hex_str[epc_start:epc_end].upper()
        
        # Validate EPC properly
        if epc.startswith("E2") and len(epc) == 24:
            # Suppress repeated EPCs
            if epc == last_epc:
                return None
            last_epc = epc
            return epc
        
        return None
    except Exception as e:
        print(f"Error reading serial: {e}")
        return None


def format_time() -> str:
    """Format current time as HH:MM AM/PM."""
    now = datetime.now()
    return now.strftime("%I:%M %p")


def log_event(epc: str, rack: Optional[str], action: str) -> None:
    """
    Print a standardized status line for product movement.
    action examples: "entered", "reached", "is staying in", "exited".
    """
    current_time = format_time()
    rack_label = rack if rack else "N/A"
    print(f"Product {action} Rack {rack_label} at {current_time}")
    print(f"  EPC: {epc}")
    product_states[epc] = action


def wait_for_tag_scan(timeout: Optional[int] = None) -> Optional[str]:
    """
    Wait for a tag to be scanned.
    Returns EPC if detected, None if timeout (only if timeout provided).
    """
    print("Waiting for tag scan...")
    start_time = time.time()
    
    global last_epc
    last_epc = None  # Reset to allow new scan
    
    while True:
        epc = read_epc_from_serial()
        if epc:
            print(f"✓ Tag detected: {epc}")
            return epc
        if timeout is not None and (time.time() - start_time) >= timeout:
            return None
        time.sleep(0.1)


def prompt_next_product():
    """Pause before processing the next product to avoid overlap."""
    input("\nReady for next product? Press Enter to continue...")
    global last_epc
    last_epc = None


def global_rack_assignment(epc: str) -> Optional[str]:
    """
    Global rack assignment step.
    User must assign scanned tag to a rack before any mode logic begins.
    Returns rack ID (A, B, or C) or None if invalid.
    """
    print("\n" + "="*50)
    print("RACK ASSIGNMENT (Required First Step)")
    print(f"Tag EPC: {epc}")
    print("="*50)
    
    while True:
        rack = input("Assign this tag to which rack? (A/B/C): ").strip().upper()
        if rack in ['A', 'B', 'C']:
            print(f"✓ Rack {rack} assigned\n")
            return rack
        else:
            print("Invalid rack. Please enter A, B, or C.")


def handle_entry_mode():
    """
    ENTRY MODE (Scanner 1 Simulation)
    Flow:
    1. Wait for EPC scan
    2. Rack assignment (global rule)
    3. Wait for Rack scanner confirmation (same EPC within 10 seconds)
    4. Success or failure output
    """
    print("\n" + "="*50)
    print("ENTRY MODE - Scanner 1")
    print("="*50)
    
    # Step 1: Wait for initial EPC scan
    print("Waiting for EPC scan at ENTRY scanner...")
    initial_epc = wait_for_tag_scan(timeout=None)
    
    if not initial_epc:
        print("[ALARM] No EPC detected at ENTRY scanner")
        return

    # If this EPC already exited, inform and move to next product
    if product_states.get(initial_epc) == "exited":
        print("\nNote: This product already exited.")
        log_event(initial_epc, None, "exited")
        prompt_next_product()
        return
    
    # Rack is not stored; use placeholder
    rack = None
    log_event(initial_epc, rack, "entered")
    
    # Step 3: Wait for Rack scanner confirmation (same EPC within 10 seconds)
    print(f"Waiting for RACK scanner confirmation (same EPC)...")
    confirmed = False
    
    # Reset last_epc to allow same EPC to be detected again
    global last_epc
    last_epc = None
    
    while True:
        epc = read_epc_from_serial()
        if epc == initial_epc:
            confirmed = True
            print(f"✓ RACK scanner confirmed: {epc}")
            break
        time.sleep(0.1)
    
    # Step 4: Output result
    current_time = format_time()
    if confirmed:
        print(f"\n✓ SUCCESS: Rack confirmation received.")
        log_event(initial_epc, rack, "reached")
    else:
        print(f"\n[ALARM] Product did not reach rack — ENTRY FAILED")
        print(f"  EPC: {initial_epc}")
        print(f"  Time: {current_time}")
    prompt_next_product()


def handle_rack_stay_mode():
    """
    RACK-STAY MODE (Scanner 2 Simulation)
    Flow:
    1. Wait for EPC scan
    2. Rack assignment (global rule)
    3. Same tag must be detected 5 times
    4. Success output after 5 valid reads
    """
    print("\n" + "="*50)
    print("RACK-STAY MODE - Scanner 2")
    print("="*50)
    
    # Step 1: Wait for initial EPC scan
    print("Waiting for EPC scan at RACK scanner...")
    initial_epc = wait_for_tag_scan(timeout=None)
    
    if not initial_epc:
        print("[ALARM] No EPC detected at RACK scanner")
        return

    # If this EPC already exited, inform and move to next product
    if product_states.get(initial_epc) == "exited":
        print("\nNote: This product already exited.")
        log_event(initial_epc, None, "exited")
        prompt_next_product()
        return
    
    # Rack is not stored; use placeholder
    rack = None
    log_event(initial_epc, rack, "entered")
    
    # Step 3: Wait for 5 valid reads of the same EPC
    print(f"Waiting for 5 valid reads of EPC: {initial_epc}")
    read_count = 1  # Already have 1 read
    read_times = []
    read_times.append(time.time())
    
    # Reset last_epc to allow same EPC to be detected again
    global last_epc
    last_epc = None
    
    while read_count < 5:
        epc = read_epc_from_serial()
        if epc == initial_epc:
            read_count += 1
            read_times.append(time.time())
            print(f"✓ Read {read_count}/5 detected")
            # Reset last_epc to allow same EPC to be detected again
            last_epc = None
        time.sleep(0.1)
    
    # Step 4: Output result
    current_time = format_time()
    if read_count >= 5:
        print(f"\n✓ SUCCESS: RACK-STAY confirmed.")
        log_event(initial_epc, rack, "is staying in")
        print(f"  Total reads: {read_count}")
    else:
        print(f"\n[ALARM] Product not in the rack")
        print(f"  EPC: {initial_epc}")
        print(f"  Reads detected: {read_count}/5")
        print(f"  Time: {current_time}")
    prompt_next_product()


def handle_exit_mode():
    """
    EXIT MODE (Scanner 3 Simulation)
    Flow:
    1. First EPC = exit scan
    2. Rack assignment (global rule)
    3. Must receive second EPC scan within 10 seconds
    4. Success or failure output
    """
    print("\n" + "="*50)
    print("EXIT MODE - Scanner 3")
    print("="*50)
    
    # Step 1: Wait for first EPC scan (exit scan)
    print("Waiting for first EPC scan at EXIT scanner...")
    first_epc = wait_for_tag_scan(timeout=None)
    
    if not first_epc:
        print("[ALARM] No EPC detected at EXIT scanner")
        return
    
    # Rack is not stored; use placeholder
    rack = None
    log_event(first_epc, rack, "entered")
    
    # Step 3: Wait for second EPC scan within 10 seconds
    print(f"Waiting for second EPC scan...")
    second_epc = None
    confirmed = False
    
    # Reset last_epc to allow same EPC to be detected again
    global last_epc
    last_epc = None
    
    while True:
        epc = read_epc_from_serial()
        if epc:
            second_epc = epc
            confirmed = True
            print(f"✓ Second EPC detected: {epc}")
            break
        time.sleep(0.1)
    
    # Step 4: Output result
    current_time = format_time()
    if confirmed:
        print(f"\n✓ SUCCESS: Product exited Rack {rack} at {current_time}")
        print(f"  EPC: {first_epc}")
        if second_epc != first_epc:
            print(f"  Second EPC: {second_epc}")
        # Explicit exit log
        log_event(first_epc, rack, "exited")
    else:
        print(f"\n[ALARM] Product failed to exit")
        print(f"  EPC: {first_epc}")
        print(f"  Time: {current_time}")
    prompt_next_product()


def show_menu():
    """Display the main menu."""
    print("\n" + "="*50)
    print("RFID WAREHOUSE SYSTEM")
    print("="*50)
    print("1 → Entry mode")
    print("2 → Rack-Stay mode")
    print("3 → Exit mode")
    print("q → Quit")
    print("="*50)


def main():
    """Main program entry point."""
    print("Initializing RFID Warehouse System...")
    
    # Initialize serial connection
    if not initialize_serial():
        print("Failed to initialize serial connection.")
        print("Please check your serial port configuration.")
        return
    
    # Main loop
    while True:
        show_menu()
        choice = input("\nSelect an option: ").strip().lower()
        
        if choice == '1':
            handle_entry_mode()
        elif choice == '2':
            handle_rack_stay_mode()
        elif choice == '3':
            handle_exit_mode()
        elif choice == 'q':
            print("\nShutting down...")
            if ser and ser.is_open:
                ser.close()
            break
        else:
            print("\nInvalid option. Please try again.")
        
        # Small delay before showing menu again
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
        if ser and ser.is_open:
            ser.close()
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if ser and ser.is_open:
            ser.close()
