from dataclasses import dataclass
import os
import re
import sys
import json
import tkinter as tk
from tkinter import filedialog
from typing import Tuple

from numpy import number

from contin_fortran import makeINfile, ModeFlags

@dataclass  
class Transient:    # stores both parameters and data taken from the ISO file
    sampling_rate: float = None
    first_sample: int = None
    last_sample: int = None
    no_samples: int = None
    no_scans: int = None
    F: list = None
    t: list = None
    bounds: Tuple[int, int] = None
    Ymin: float = 0.0
    Ymax: float = 0.0
    invert: bool = False

    def getBounds(self) -> Tuple[int, int]:
        return (self.first_sample, self.last_sample)
    
    def setBounds(self, bounds: Tuple[int, int]) -> Tuple[int, int]:
        self.first_sample, self.last_sample = bounds
        return (self.first_sample, self.last_sample)

    def seekMinMax(self, bounds: Tuple[int, int] = None) -> Tuple[float, float, bool]:
        if bounds is None:
            bounds = self.getBounds()
        frst, last = bounds
        # Find the maximum/minimum order and decide whether to invert the transient.
        if self.F is None or len(self.F) == 0:
            return 0.0, 0.0, False

        if frst is None:
            frst = 0
        if last is None:
            last = len(self.F) - 1
 
        start = int(frst)
        end = int(last)
        if start < 0:   # check bounds
            start = 0
        if end > len(self.F)-1:
            end = len(self.F)-1
        if start > end:    # change order
            imin = end
            end = start
            start = imin

        if start >= end or start >= len(self.F):
            return 0.0, 0.0, False

        imin = start
        imax = start
        Ymin = self.F[start]
        Ymax = self.F[start]

        for i, value in enumerate(self.F[start:end+1], start=start):    # slice does not include the end index, so we add 1
            if value < Ymin:  # Find the minimum value
                Ymin = value
                imin = i
            if value > Ymax:  # Find the maximum value
                Ymax = value
                imax = i

        if imin > imax:     # If the minimum occurs further then the maximum, we will need to invert the transient F (KG)...
            return Ymin, Ymax, True
        # ...otherwise we leave it as is
        return Ymin, Ymax, False

    def print_summary(self) -> None:
        print("\nTransient summary:")
        print(f"  Sampling_rate: {self.sampling_rate}")
        print(f"  Number_of_samples: {int(self.no_samples)}")
        print(f"  Number_of_scans: {int(self.no_scans)}")
        print(f"  First_sample: {int(self.first_sample)}")
        print(f"  Last_sample: {int(self.last_sample)}")
        # print(f"  Transient length: {len(self.F) if self.F is not None else 0}")
        # print(f"  bounds: {(self.first_sample, self.last_sample)}")
        # print(f"  t length: {len(self.t) if self.t is not None else 0}")
        # print(f"  Ymax: {self.Ymax}")
        # print(f"  invert: {self.invert}")

T = Transient()

start = 0
numlines = 0
sampling_rate = None
first_sample = None
last_sample = None
no_samples = None
no_scans = None
F = []
t = []
Tr = []
bounds = None
last_folder = None
last_filename = None
last_Nz = None
last_alpha = None
invert = False
Ymin = 0.0
Ymax = 0.0

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
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        data['folder'] = folder
        data['filename'] = filename
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass


def load_parameters() -> tuple:
    """Load the last Nz and alpha from the config file."""
    global last_Nz, last_alpha
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                last_Nz = data.get('Nz')
                last_alpha = data.get('alpha')
                return last_Nz, last_alpha
        except:
            pass
    return None, None


def save_parameters(Nz: int, alpha: float) -> None:
    """Save the last Nz and alpha to the config file."""
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
        data['Nz'] = Nz
        data['alpha'] = alpha
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)
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


def process_file(path: str) -> Tuple[float, float, bool]:
    global start, numlines, sampling_rate, first_sample, last_sample, no_samples, no_scans, F, bounds, t, Tr, Ymax, invert, T
    
    if not os.path.isfile(path):
        print(f"The selected path is not a file: {path}")
        return 0.0, 0.0, False

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
    print(f"       ISO file: {path}")
    print(f"  Sampling Rate: {sampling_rate}")
    print(f"   First Sample: {int(first_sample)}")
    print(f"    Last Sample: {int(last_sample)}")
    print(f"     No Samples: {int(no_samples)}")
    print(f"       No Scans: {int(no_scans)}")
    print()
    #input("Press Enter (1) to continue...")

    # Skip lines until the one with "[data]" (case-insensitive)
    data_start = None
    for i, line in enumerate(lines):
        if "[data]" in line.lower():
            data_start = i + 1  # Start from the next line after [data]
            break

    if data_start is None:
        print("No line containing '[data]' found.")
        return 0.0, 0.0, False

    print(f"Data section starts at line {data_start + 1}\n")
    start = data_start + 1

    imin = 0
    Ymin = sys.float_info.max # minimum
    imax = 0
    Ymax = sys.float_info.min  # maximum
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
        aux = 0.0
        numbers = parse_numbers(line)
        if numbers:
            numlines += 1   # count the number of lines with valid data
            aux = numbers[0]
            F.append(aux)
            if numlines >= first_sample+1 and numlines <= last_sample+1:    # if within the range of samples, we will check for the minimum and maximum values
                if aux < Ymin:  # Find the minimum value
                    Ymin = aux
                    imin = numlines
                if aux > Ymax:  # Find the maximum value
                    Ymax = aux
                    imax = numlines

    # adjust length of F to the number of valid lines read
    no_samples = len(F)
    # adjust bounds
    if first_sample is not None and last_sample is not None:
        if first_sample < 0 or first_sample >= no_samples:
            first_sample = 0
        if last_sample < 0 or last_sample >= no_samples:
            last_sample = no_samples - 1
    else:
        first_sample = 0
        last_sample = no_samples - 1

    # Create time array 't' with same size as F
    if sampling_rate and sampling_rate > 0:
        t = [i / sampling_rate for i in range(no_samples)]
    else:
        t = list(range(no_samples))  # Fallback if sampling_rate is not available

    # If the minimum occurs further then the maximum, we will invert the transient...
    if imin > imax:    
        invert = True
    else:
        # ...otherwise we leave it as is
        invert = False

    # fill the global data structure
    T.sampling_rate = sampling_rate
    T.first_sample = first_sample+1
    T.last_sample = last_sample+1
    T.no_samples = no_samples
    T.no_scans = no_scans
    T.bounds = (T.first_sample, T.last_sample)  # adjusted for 1-based indexing
    T.F = F
    T.t = t
    T.Ymax = Ymax
    T.invert = invert

    # Print the collected data
    print("\nCollected Data:")
    for i in range(len(F)):
        suffix = ""
        if i == imin:
            suffix = "\t\033[34m<- Min\033[0m"
        elif i == imax:
            suffix = "\t\033[38;5;214m<- Max\033[0m"

        if i == first_sample:
            # First line in green
            print(f"\033[92m{i}: {t[i]}\t{F[i]}{suffix}\033[0m")
        elif i == last_sample:
            # Last line in red
            print(f"\033[91m{i}: {t[i]}\t{F[i]}{suffix}\033[0m")
        else:
            # Normal color
            if suffix != "":
                print(f"{i}: {t[i]}\t{F[i]}{suffix}")   
            #print(f"{i}: {t[i]}\t{F[i]}{suffix}")
    
    # Save the last folder and filename
    folder = os.path.dirname(path)
    filename = os.path.basename(path)
    save_file_history(folder, filename)
    return Ymin, Ymax, invert

print("Hello! This program will help you find lines containing '[data]' in a text file.\n")

if __name__ == "__main__":
    # Load the last folder and filename
    load_file_history()
    
    file_path = choose_text_file()
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit(0)

    Ymin, Ymax, invert = process_file(file_path)
    print(f"\nDone processing the file: {numlines} lines starting from {start}.")
    print(f"Ymin: {Ymin}, Ymax: {Ymax}, Invert: {invert}")

    T.print_summary()
    print(T.seekMinMax())
"""    print(T.seekMinMax((100, 2000)))
    print(T.seekMinMax())
    T.setBounds((100, 2000))
    print(T.seekMinMax())
    print(int(T.getBounds()[0]),int(T.getBounds()[1]) ) # 
"""
Y, inv = makeINfile(
    Ymax=Ymax,
    invert=invert,
    tStep=1.0 / T.sampling_rate,
    vc=T.F,
    regime=ModeFlags(alphauto=True, kernel=False, slanted=True, residuals=True),
    xng=5,
    palpha=1.0,
    filename="contin.in"
)

