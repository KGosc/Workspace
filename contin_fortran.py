from dataclasses import dataclass
import math
from typing import List, Tuple, Dict, Any

@dataclass  
class SpectrumPoint:    # Represents a point in the spectrum with frequency, signal, and error
    f: float = 0.0
    s: float = 0.0
    e: float = 0.0

@dataclass
class Peak: # Represents a peak with area, baseline, frequency, and errors
    a: float = 0.0
    b: float = 0.0
    f: float = 0.0
    fe: float = 0.0
    ae: float = 0.0

@dataclass  
class ModeFlags:    # Represents CONTIN mode flags:  point in the spectrum with frequency, signal, and error
    alphauto: bool = False  # TRUE == automatic alpha, FALSE == manual alpha, needs to be pointed to a variable containing initial value on entry that will be updated with the final value on exit
    kernel: bool = True     # TRUE == Capacitance, FALSE == Current
    slanted: bool = False   # TRUE == slanted baseline, FALSE == horizontal baseline
    residuals: bool = False # TRUE == calculate and output residuals, FALSE == do not calculate residuals
# ========================================================================================================
#
#def btest(value: int, bit: int) -> bool:    # Test if the bit at position 'bit' in 'value' is set (1) or not (0)
#    return ((value >> bit) & 1) != 0
# ========================================================================================================

  # Find the maximum/minimum order and decide whether to invert the transient.
def skY2(vc: List[float]) -> Tuple[float, int]:
  
    if len(vc) == 0:
        return 0.0, 1

    imin = 0
    imax = 0
    Y1 = vc[0]
    Y2 = vc[0]

    for i, value in enumerate(vc):
        if value < Y1:  # Find the minimum value
            Y1 = value
            imin = i
        if value > Y2:  # Find the maximum value
            Y2 = value
            imax = i

#    if imin < imax:     # If the minimum occurs before the maximum, we invert the transient
    if imin > imax:     # If the minimum occurs further then the maximum, we invert the transient (KG)...
        return Y2, -1
# ...otherwise we leave it as is
    return 0.0, 1
# ========================================================================================================

# Create the contin.in file based on the input parameters and transient values, and return Ymax and invert flag
"""
xemin == FreqMin
xemax == FreqMax
tstep == sDuration
FreqMin = 1/(npoints * sDuration * 2)
FreqMax = 1/3/sDuration

FreqMinMax wyliczać wewnątrz, na podstawie tstep i liczby próbek, a nie podawać jako argumenty. Wtedy użytkownik będzie podawał tylko tstep i npoints, a my będziemy obliczać odpowiednie FreqMin i FreqMax. To uprości interfejs i zmniejszy ryzyko błędów w podawaniu tych wartości.
Przekazywana tablica vc będzie zawierała wartości wybranych punktów transientu (od FirstPoint do LastPoint), które chcemy przetworzyć. Funkcja makeINfile będzie tworzyć plik contin.in na podstawie tych wartości i dodatkowych parametrów, a następnie zwracać Ymax i flagę invert, które są potrzebne do dalszego przetwarzania wyników z contin.out.
Wszystkie flagi zgrupowane w strukturze ModeFlags.

"""

def makeINfile( 
    Ymax: float,   # Maximum Y value in the transient
    invert: bool,   # Flag to determine if the transient should be inverted
    tStep: float,  # time step for the transient in seconds
    vc: List[float],    # List of transient values
    regime: ModeFlags, #int,        # Regime flag to determine the fitting model and parameters
    xng: int,       # Number of spectrum points. On input sets max number of peaks to seek, on output returns actual number of peaks found.
    palpha: float,      # Alpha parameter for the fitting.model, used if regime flag is not set to 0. On input sets initial value, on output returns final value.
    filename: str = "contin.in",
) -> Tuple[float, bool]:
    """Create the contin.in file and return the generated Ymax and invert values."""
    # Ymax, invert = skY2(vc)  przenieść wyszukiwanie do procedury wczyującej plik
    npoints = len(vc)   
    FreqMin = 1 / (npoints * tStep * 2)
    FreqMax = 1 / (3 * tStep)  

    with open(filename, "w", encoding="utf-8") as fout:
        fout.write(" NINTT                   1.\n") # Number of transients to fit (always 1 in this case)
        fout.write(" IFORMY\n") # Format for the transient data, 1 means that the data is in a simple list format, one value per line
        fout.write(" (E15.9)\n")    # Format specification for the transient data, E15.9 means that each value is written in exponential notation with a total width of 15 characters and 9 digits after the decimal point
        fout.write(" DOUSIN                 -1.\n") # Flag to determine if the input transient should be used as is (-1) or if it should be processed in some way (e.g., inverted, normalized, etc.)
        fout.write(f" NG                   {int(xng):5d}\n")    # Number of spectrum points, formatted as a 5-digit integer
        fout.write(f" GMNMX     1     {FreqMin:10.4E}\n") # Minimum frequency value, formatted in exponential notation with a total width of 10 characters and 4 digits after the decimal point
        fout.write(f" GMNMX     2     {FreqMax:10.4E}\n") # Maximum frequency value  

        # If bit2 is set, we use the slanted line for baseline calculations, otherwise a horizontal one (just the level) (KG)
        if regime.slanted:
            fout.write(" NLINF                   2.\n")   # b2=1 - y(t)=A+B*t 
        else:
            fout.write(" NLINF                   1.\n")   # b2=0 - y(t)=A
        fout.write(" PRY                    -1.\n")     # Flag to determine if the transient should be printed in the output file, -1 means that it should not be printed
        fout.write(" MPKMOM                  8.\n")     # Maximum number of peaks to fit, set to 8 in this case
        fout.write(" MOMNMX    1             0.\n")     # Maximum order of the first component in the fitting model, set to 0 in this case (no first component)
        fout.write(" MOMNMX    2             2.\n")     # Maximum order of the second component in the fitting model, set to 2 in this case (up to second order polynomial) 
        fout.write(" IPLRES    1             0.\n")     # Flag to determine if the residuals should be printed in the output file, 0 means that they should not be printed  
        fout.write(" IPLRES    2             0.\n")     # Flag to determine if the residuals should be printed in the output file, 0 means that they should not be printed  
        fout.write(" IPLFIT    1             0.\n")     # Flag to determine if the fit should be printed in the output file, 0 means that it should not be printed  

        if regime.residuals:  #      == 1:
            fout.write(" IPLFIT    2             2.\n")     # Flag to determine if the fit should be printed in the output file, 2 means that it should be printed with residuals
        else:
            fout.write(" IPLFIT    2             0.\n")

        if regime.alphauto:
            fout.write(" ALPST     1             0.\n")
            fout.write(" ALPST     2             0.\n")
        else:
            fout.write(f" ALPST     1     {palpha:10.4E}\n")
            fout.write(f" ALPST     2     {palpha:10.4E}\n")

        fout.write(" IPRINT    1             0.\n")
        fout.write(" IPRINT    2             2.\n")
        fout.write(" NERFIT                  0.\n") # Number of residuals to perform, set to 0 in this case (no error fitting)
        fout.write(" IUSER    10             4.\n")
        fout.write(" RUSER    21             1.\n")
        fout.write(" RUSER    22             1.\n") 

        if regime.kernel:  # == 1:
            fout.write(" RUSER    23             0.\n")     # exp(-st) [Capacitance]
        else:
            fout.write(" RUSER    23             1.\n")     # s*xp(-st) [Current]

        fout.write(" LUSER     3            -1.\n")     # Flag to determine if the user-defined fitting function should be used, -1 means that it should not be used
        fout.write(" END\n")
        fout.write(
            f" NSTEND{int(xng):5d}{' ' * 10}0.E+0{' ' * 6}{((len(vc) - 1) * tStep):9.4E}\n"
        )

        if invert == -1:    # If we need to invert the transient, we invert each value and shift it by Ymax
            for value in vc:
                fout.write(f"{Ymax + invert * value:14.8E}\n")
        else:
            for value in vc:
                fout.write(f"{value:14.8E}\n")
    
    return Ymax, invert
# ========================================================================================================

def residuals(
    vc: List[float],
    contin_in_path: str = ".\\contin.in",
    contin_out_path: str = ".\\contin.out",
) -> List[float]:
    """Compute residuals from contin.out and contin.in and store them in vc."""
    nst = None
    with open(contin_in_path, "r", encoding="utf-8", errors="ignore") as fin:
        for line in fin:
            if "NSTEND" in line:
                nst_text = line[8:12].strip()
                if not nst_text:
                    raise ValueError("Could not parse NSTEND count from contin.in")
                nst = int(nst_text)
                break

    if nst is None:
        raise ValueError("NSTEND not found in contin.in")

    with open(contin_in_path, "r", encoding="utf-8", errors="ignore") as fin:
        # advance to the data section after NSTEND
        while True:
            line = fin.readline()
            if not line:
                raise ValueError("Reached end of contin.in before data section")
            if "NSTEND" in line:
                break
        data_lines = [fin.readline() for _ in range(nst)]

    with open(contin_out_path, "r", encoding="utf-8", errors="ignore") as fout:
        line_iter = iter(fout)
        for line in line_iter:
            if "PLOT OF DATA (O) AND FIT TO DATA (X)" in line:
                break
        else:
            raise ValueError("Plot section not found in contin.out")

        # skip two lines after the plot marker as in the original Fortran code
        next(line_iter, None)
        next(line_iter, None)
        fit_lines = [next(line_iter, "") for _ in range(nst)]

    if len(vc) < nst:
        raise ValueError("Input vc list is smaller than NSTEND")

    for i in range(nst):
        rth_text = fit_lines[i].strip()
        rex_text = data_lines[i].strip()
        vc[i] = float(rex_text) - float(rth_text)

    return vc
# ========================================================================================================

def conout(
    contin_out_path: str,
    vc: List[float],
    Y2: float,
    mno: int,
    linefit: bool = False,
) -> Dict[str, Any]:
    """Parse contin.out and return fit results, spectrum points, and peaks."""
    alphav = None
    baseline = None
    bslope = None
    nsp = 0
    npeak = 0
    spectrum_points: List[SpectrumPoint] = []
    peaks: List[Peak] = []
    found = False
    points = False
    integral = False
    alpha = False
    resi = False

    with open(contin_out_path, "r", encoding="utf-8", errors="ignore") as fout:
        lines = fout.readlines()

    for line in lines:
        if "PLOT OF DATA (O) AND FIT TO DATA (X)" in line:
            resi = True
            break
        if "+++  CHOSEN SOLUTION" in line:
            found = True
            break

    if resi:
        residuals(vc, contin_out_path=contin_out_path)

    idx = 0
    while idx < len(lines):
        line = lines[idx]

        if not found:
            if "+++  CHOSEN SOLUTION" in line:
                found = True
            idx += 1
            continue

        if not points and not integral and not alpha:
            header = line[:15]
            if "ORDINATE" in header:
                points = True
                idx += 1
                continue
            if "PEAK" in header:
                integral = True
                idx += 1
                continue
            if "ALPHA " in header:
                alpha = True
                idx += 1
                if idx < len(lines):
                    alphav_line = lines[idx]
                    alphav = float(alphav_line[:15].strip() or "0")
                idx += 1
                continue

        if points:
            if line[:2] != "  ":
                points = False
                bl = float(line[23:35].strip() or "0")
                baseline = (bl - Y2) / float(mno)
                if linefit:
                    bl_slope = float(line[55:67].strip() or "0")
                    bslope = bl_slope / float(mno)
                idx += 1
                continue

            nsp += 1
            point = SpectrumPoint(
                f=float(line[23:32].strip() or "0"),
                s=float(line[3:12].strip() or "0"),
                e=float(line[14:21].strip() or "0"),
            )
            spectrum_points.append(point)
            idx += 1
            continue

        if integral:
            integral = False
            peak = Peak()
            line0 = line
            p1 = float(line0[48:56].strip() or "0")
            ii = int(line0[64:68].strip() or "0")
            pe = float(line0[76:85].strip() or "0")
            ptest = p1 * p1
            peak.a = p1 * 10.0 ** ii

            idx += 1
            if idx >= len(lines):
                break

            line1 = lines[idx]
            peak.f = float(line1[95:106].strip() or "0")
            espe = float(line1[111:122].strip() or "0")
            p1b = float(line1[48:56].strip() or "0")
            iib = int(line1[64:68].strip() or "0")
            ptest += p1b * p1b
            xm = p1b * 10.0 ** iib

            idx += 1
            if idx >= len(lines):
                break

            line2 = lines[idx]
            p1c = float(line2[48:56].strip() or "0")
            iic = int(line2[64:68].strip() or "0")
            ptest += p1c * p1c
            x2m = p1c * 10.0 ** iic
            peak.b = math.sqrt(abs(x2m - xm * xm))
            peak.fe = xm * pe / 100.0
            peak.ae = peak.f * espe / 100.0

            if ptest >= 1e-5:
                npeak += 1
                peaks.append(peak)

            idx += 1
            continue

        idx += 1

    return {
        "alphav": alphav,
        "baseline": baseline,
        "bslope": bslope,
        "nsp": nsp,
        "npeak": npeak,
        "SpectrumP": spectrum_points,
        "Peakz": peaks,
    }
# ========================================================================================================

if __name__ == "__main__":
    # ========================================================================================================
    # EXAMPLE 1: Using makeINfile to create the input file, then conout to parse results
    # ========================================================================================================
    print("=" * 80)
    print("EXAMPLE 1: makeINfile + conout")
    print("=" * 80)
    
    sample_vc = []      # [0.1, 0.2, 0.15, 0.05, 0.0]
    xng = len(sample_vc)
    xemin = 0.001
    xemax = 1.0
    residu = True
    sDurationc = 1.0
    regime = ModeFlags(alphauto=False, kernel=True, slanted=False, residuals=True)
    palpha = 0.5
    
    # Create the input file and get Y2, invert parameters
    Y2, invert = makeINfile(
        xng=xng,
        xemin=xemin,
        xemax=xemax,
        residu=residu,
        tStep=sDurationc,
        vc=sample_vc,
        regime=regime,
        palpha=palpha,
        filename="contin.in",
    )
    print(f"Created contin.in: Y2={Y2}, invert={invert}")
    
    # Now assume contin.out has been generated by the external solver
    # Parse the output file
    if True:  # Change to check if contin.out exists
        vc_parsed = [0.0] * 30000#  # Initialize for residuals
        results = conout(
            contin_out_path=".\\contin.out",
            vc=vc_parsed,
            Y2=Y2,
            mno=xng,
            linefit=False
        )
        print(f"Parsed contin.out:")
        print(f"  - Alpha value: {results['alphav']}")
        print(f"  - Baseline: {results['baseline']}")
        print(f"  - Number of spectrum points: {results['nsp']}")
        print(f"  - Number of peaks: {results['npeak']}")
        print(f"  - Spectrum points: {len(results['SpectrumP'])} points")
        for i, pt in enumerate(results['SpectrumP'][:3]):  # Show first 3 points
            print(f"    Point {i+1}: f={pt.f:.6E}, s={pt.s:.6E}, e={pt.e:.6E}")
        print(f"  - Peaks: {len(results['Peakz'])} peaks")
        for i, pk in enumerate(results['Peakz'][:2]):  # Show first 2 peaks
            print(f"    Peak {i+1}: a={pk.a:.6E}, b={pk.b:.6E}, f={pk.f:.6E}")
    
    # ========================================================================================================
    # EXAMPLE 2: Using residuals to compute differences between input and fitted data
    # ========================================================================================================
    print("\n" + "=" * 80)
    print("EXAMPLE 2: residuals function")
    print("=" * 80)
    
    # Initialize residuals array with same size as original transient
    vc_residuals = [0.0] * xng
    
    # Compute residuals from contin.in and contin.out
    residuals_result = residuals(
        vc=vc_residuals,
        contin_in_path=".\\contin.in",
        contin_out_path=".\\contin.out"
    )
    
    print(f"Computed {len(residuals_result)} residuals:")
    for i, res in enumerate(residuals_result[:5]):  # Show first 5 residuals
        print(f"  Residual {i+1}: {res:.6E}")
    
    # ========================================================================================================
    # EXAMPLE 3: Complete workflow
    # ========================================================================================================
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Complete workflow")
    print("=" * 80)
    
    # Input transient data
    transient_data = [1.0, 0.9, 0.81, 0.729, 0.656]
    n_points = len(transient_data)
    
    # Setup fitting parameters
    regime_settings = ModeFlags(alphauto=True, kernel=False, slanted=True, residuals=True)
    
    # Step 1: Create input file
    Y2_val, invert_flag = makeINfile(
        xng=n_points,
        xemin=0.0001,
        xemax=10.0,
        residu=True,
        tStep=0.1,
        vc=transient_data,
        regime=regime_settings,
        palpha=1e-5,
        filename="contin.in"
    )
    print(f"Step 1: Created contin.in (Y2={Y2_val}, invert={invert_flag})")
    
    # Step 2: External solver would be called here (e.g., subprocess call to Fortran CONTIN)
    print("Step 2: External CONTIN solver would run here...")
    
    # Step 3: Parse results from contin.out
    residuals_vec = [0.0] * n_points
    output_results = conout(
        contin_out_path=".\\contin.out",
        vc=residuals_vec,
        Y2=Y2_val,
        mno=n_points,
        linefit=True
    )
    print(f"Step 3: Parsed results - found {output_results['npeak']} peaks, {output_results['nsp']} spectrum points")
    
    # Step 4: Compute and display residuals
    residuals(
        vc=residuals_vec,
        contin_in_path=".\\contin.in",
        contin_out_path=".\\contin.out"
    )
    print(f"Step 4: Computed residuals (max: {max(abs(r) for r in residuals_vec if r != 0) if any(residuals_vec) else 0:.6E})")
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
