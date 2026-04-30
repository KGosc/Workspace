import os
import re
import sys
import json
import tkinter as tk
from tkinter import filedialog


start = 0
numlines = 0
sampling_rate = None
first_sample = None
last_sample = None
no_samples = None
no_scans = None
F = []
t = []
bounds = None
last_folder = None
last_filename = None

# Configuration file for persisting last folder and filename
CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".file_history.json")

def parse_numbers(input_string: str) -> list[float]:
    """
    Parse a string looking for numbers separated by whitespace.
    
    Supports:
    - Integers: 123, -456
    - Floats: 123.45, -67.89
    - Scientific notation: 1.5e10, 2.5E-5, 3.14e+7
    
    Args:
        input_string: The string to parse for numbers.
        
    Returns:
        A list of floats found in the input string.
    """
    # Pattern matches:
    # - Optional sign (+/-)
    # - Integer part
    # - Optional decimal part (. followed by digits)
    # - Optional scientific notation (e/E followed by optional sign and digits)
    number_pattern = r'[+-]?\d+\.?\d*(?:[eE][+-]?\d+)?'
    
    # Find all matches in the string
    matches = re.findall(number_pattern, input_string)
    
    # Convert to floats
    numbers = []
    for match in matches:
        try:
            numbers.append(float(match))
        except ValueError:
            # Skip invalid matches
            continue
    
    return numbers


def load_file_history() -> tuple:
    """Load the last folder and filename from config file."""
    global last_folder, last_filename
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                last_folder = data.get('folder')
                last_filename = data.get('filename')
                return last_folder, last_filename
        except:
            pass
    return None, None


def save_file_history(folder: str, filename: str) -> None:
    """Save the last folder and filename to config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'folder': folder, 'filename': filename}, f)
    except:
        pass


def choose_text_file() -> str:
    """Open a file dialog to choose a text file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return filedialog.askopenfilename(
        title="Select a text file",
        initialdir=last_folder,
        initialfile=last_filename,
        filetypes=[("ISO files", "*.iso"), ("Text files", "*.txt"), ("All files", "*.*")],
    )


def process_file(path: str) -> None:
    global start, numlines, sampling_rate, first_sample, last_sample, no_samples, no_scans, F, bounds, t
    
    if not os.path.isfile(path):
        print(f"The selected path is not a file: {path}")
        return

    print(f"Reading: {path}\n")

    with open(path, "r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()

    # Extract header fields before [data]
    header_fields = {
        "sampling rate": "sampling_rate",
        "first sample": "first_sample",
        "last sample": "last_sample",
        "no samples": "no_samples",
        "no scans": "no_scans"
    }
    
    for line in lines:
        line_lower = line.lower()
        
        # Stop if we reach the [data] section
        if "[data]" in line_lower:
            break
        
        # Check for header fields
        for field_name, var_name in header_fields.items():
            if line_lower.startswith(field_name):
                # Extract the value after '='
                if '=' in line:
                    value_str = line.split('=', 1)[1].strip()
                    # Parse the numeric value
                    numbers = parse_numbers(value_str)
                    if numbers:
                        globals()[var_name] = numbers[0]
                break

    # Print extracted header values
    print("Extracted Header Values:")
    print(f"  Sampling Rate: {sampling_rate}")
    print(f"   First Sample: {first_sample}")
    print(f"    Last Sample: {last_sample}")
    print(f"     No Samples: {no_samples}")
    print(f"       No Scans: {no_scans}")
    print()
    input("Press Enter to continue...")

    # Skip lines until the one with "[data]" (case-insensitive)
    data_start = None
    for i, line in enumerate(lines):
        if "[data]" in line.lower():
            data_start = i + 1  # Start from the next line after [data]
            break

    if data_start is None:
        print("No line containing '[data]' found.")
        return

    print(f"Data section starts at line {data_start + 1}\n")
    start = data_start + 1

    # Process lines starting from data_start
    for line in lines[data_start:]:
        line = line.rstrip("\n")
        
        # Stop if line starts with '['
        if line.lstrip().startswith("["):
            print(f"Stopping at line: {line}")
            break
        
        # Skip empty lines
        if not line.strip():
            continue
        
        # Skip lines beginning with ';'
        stripped = line.lstrip()
        if stripped.startswith(";"):
            continue
        
        
        # Parse and print numbers from the line
        numbers = parse_numbers(line)
        if numbers:
            numlines += 1
            F.append(numbers[0])

    # Store first_sample and last_sample as a bounds pair
    bounds = (first_sample, last_sample)
    
    # Create time array 't' with same size as F
    if sampling_rate and sampling_rate > 0:
        t = [i / sampling_rate for i in range(len(F))]
    else:
        t = list(range(len(F)))  # Fallback if sampling_rate is not available
    
    # Print the collected data
    print("\nCollected Data:")
    for i in range(len(F)):
        if i == first_sample:
            # First line in green
            print(f"\033[92m{i}: {t[i]}\t{F[i]}\033[0m")
        elif i == last_sample:
            # Last line in red
            print(f"\033[91m{i}: {t[i]}\t{F[i]}\033[0m")
        else:
            # Normal color
            print(f"{i}: {t[i]}\t{F[i]}")
    
    # Save the last folder and filename
    folder = os.path.dirname(path)
    filename = os.path.basename(path)
    save_file_history(folder, filename)

print("Hello! This program will help you find lines containing '[data]' in a text file.\n")
if __name__ == "__main__":
    # Load the last folder and filename
    load_file_history()
    
    file_path = choose_text_file()
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit(0)

    process_file(file_path)
    print(f"\nDone processing the file: {numlines} lines starting from {start}.")
