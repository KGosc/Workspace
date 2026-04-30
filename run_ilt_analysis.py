#!/usr/bin/env python
"""
Script to perform Inverse Laplace Transform analysis on processed data.
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Import from hello and laplace modules
import hello
import laplace

def main():
    """Main routine to run ILT analysis."""
    print("Inverse Laplace Transform (ILT) Analysis")
    print("=" * 50)
    
    # Load file history
    hello.load_file_history()
    
    # Choose and process file
    file_path = hello.choose_text_file()
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit(0)
    
    ###
    # ==================================================================================================================
    # tu zmodyfikować tak, aby zawsze można było wybrać plik, ale jeśli jest już zapisany w historii, to użyć tego
    # Use the last file from history
    if hello.last_folder and hello.last_filename:
        file_path = os.path.join(hello.last_folder, hello.last_filename)
        print(f"Using file from history: {file_path}\n")
    else:
        # If no history, ask user to choose
        file_path = hello.choose_text_file()
        if not file_path:
            print("No file selected. Exiting.")
            sys.exit(0)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    # ==================================================================================================================
    ###



    hello.process_file(file_path)
    
    # Check if we have valid data
    if not hello.t or not hello.F or not hello.bounds:
        print("Error: No valid data to process.")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("Running Inverse Laplace Transform (ILT) Analysis")
    print("="*50)
    
    # Call ILT with specified parameters
    Nz = 64
    alpha = 10.0
    
    print(f"\nParameters:")
    print(f"  Nz = {Nz}")
    print(f"  alpha = {alpha}")
    print(f"  bounds = {hello.bounds}")
    print(f"  data points = {len(hello.t)}")
    print()
    
    # Perform ILT
    z, f, res_lsq, res_reg = laplace.ilt(hello.t, hello.F, hello.bounds, Nz, alpha)
    
    # Calculate zf = z*f for plotting
    zf = z * f
   #zf = f
    
    # Print z and zf arrays in parallel
    print("\nResults (z and zf arrays in parallel):")
    print("-" * 60)
    print(f"{'i':>4} {'z':>15} {'f':>15} {'zf':>15}")
    print("-" * 60)
    for i in range(len(z)):
        print(f"{i:4d} {z[i]:15.6e} {f[i]:15.6e} {zf[i]:15.6e}")
    print("-" * 60)
    
    # Plot zf vs z
    print("\nGenerating plot...")
    plt.figure(figsize=(10, 6))
    plt.semilogx(z, zf, 'b-', linewidth=2, label='zf(z)')
    plt.xlabel('z', fontsize=12)
    plt.ylabel('zf(z)', fontsize=12)
    plt.title(f'Inverse Laplace Transform Result (Nz={Nz}, alpha={alpha})', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=11)
    plt.tight_layout()
    
    # Save plot
    plot_file = os.path.join(os.path.dirname(file_path), "ilt_result.png")
    plt.savefig(plot_file, dpi=150)
    print(f"Plot saved to: {plot_file}")
    
    plt.show()
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
