import os
import re
import sys
import tkinter as tk
from tkinter import filedialog


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


def choose_text_file() -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return filedialog.askopenfilename(
        title="Select a text file",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )


def process_file(path: str) -> None:
    if not os.path.isfile(path):
        print(f"The selected path is not a file: {path}")
        return

    print(f"Reading: {path}\n")

    with open(path, "r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()

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
            print(f"{line}: {numbers}")

print("Hello! This program will help you find lines containing '[data]' in a text file.\n")
if __name__ == "__main__":
    file_path = choose_text_file()
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit(0)

    process_file(file_path)
    print("\nDone processing the file.")    
