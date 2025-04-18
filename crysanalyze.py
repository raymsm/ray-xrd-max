#!/usr/bin/env python3
"""
crysanalyze - A CLI tool for rapid preliminary analysis of powder XRD data
"""

import argparse
import sys
from pathlib import Path
import numpy as np
from scipy import signal, optimize
import matplotlib.pyplot as plt

def read_xrd_data(file_path):
    """Read XRD data from various file formats."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        data = np.loadtxt(file_path)
        if data.shape[1] != 2:
            raise ValueError("File must contain exactly 2 columns")
        return data[:, 0], data[:, 1]
    except Exception as e:
        raise ValueError(f"Error reading file: {e}")

def subtract_background(two_theta, intensity, order=3):
    """Subtract polynomial background from XRD data."""
    coeffs = np.polyfit(two_theta, intensity, order)
    background = np.polyval(coeffs, two_theta)
    return intensity - background

def find_peaks(two_theta, intensity, min_height=None, min_dist=None, fit_peaks=False):
    """Find peaks in XRD data."""
    if min_height is None:
        min_height = 0.1 * np.max(intensity)
    if min_dist is None:
        min_dist = 0.5  # degrees
    
    peak_indices, _ = signal.find_peaks(
        intensity,
        height=min_height,
        distance=int(min_dist / (two_theta[1] - two_theta[0]))
    )
    
    peaks = []
    for idx in peak_indices:
        peak = {
            'position': two_theta[idx],
            'intensity': intensity[idx],
            'fwhm': None
        }
        peaks.append(peak)
    
    return peaks

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Rapid preliminary analysis of powder XRD data",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global required arguments
    parser.add_argument(
        "--input", 
        type=str, 
        required=True,
        help="Path to the XRD data file (.xy, .dat)"
    )
    parser.add_argument(
        "--wavelength", 
        type=float, 
        required=True,
        help="X-ray wavelength in Angstroms (e.g., 1.5406 for Cu Ka1)"
    )
    
    # Global optional arguments
    parser.add_argument(
        "--output", 
        type=str,
        help="Path to save text-based results"
    )
    parser.add_argument(
        "--range", 
        type=float, 
        nargs=2,
        metavar=("MIN", "MAX"),
        help="Process only data within this 2-theta range [min, max]"
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)
    
    # peaks command
    peaks_parser = subparsers.add_parser("peaks", help="Find and list peaks")
    peaks_parser.add_argument("--fit-peaks", action="store_true", help="Fit found peaks")
    peaks_parser.add_argument("--min-height", type=float, help="Minimum peak height for detection")
    peaks_parser.add_argument("--min-dist", type=float, help="Minimum horizontal distance between peaks")
    peaks_parser.add_argument("--bg-poly", type=int, help="Perform polynomial background subtraction of integer ORDER")
    
    # plot command
    plot_parser = subparsers.add_parser("plot", help="Generate plots")
    plot_parser.add_argument(
        "--plot-type",
        choices=["raw", "bgsub", "peaks"],
        default="raw",
        help="Type of plot to generate"
    )
    plot_parser.add_argument("--save-plot", type=str, help="Save plot to specified file")
    plot_parser.add_argument("--bg-poly", type=int, help="Perform polynomial background subtraction of integer ORDER")
    
    return parser.parse_args()

def main():
    """Main entry point for the crysanalyze CLI."""
    args = parse_args()
    
    # Read input data
    try:
        two_theta, intensity = read_xrd_data(args.input)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Apply 2-theta range if specified
    if args.range:
        mask = (two_theta >= args.range[0]) & (two_theta <= args.range[1])
        two_theta = two_theta[mask]
        intensity = intensity[mask]
    
    # Process data based on command
    if args.command == "peaks":
        # Background subtraction if requested
        if args.bg_poly is not None:
            intensity = subtract_background(two_theta, intensity, args.bg_poly)
        
        # Find peaks
        peaks = find_peaks(
            two_theta, 
            intensity,
            min_height=args.min_height,
            min_dist=args.min_dist,
            fit_peaks=args.fit_peaks
        )
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write("Peak Analysis Results\n")
                f.write("2-theta\tIntensity\n")
                for peak in peaks:
                    f.write(f"{peak['position']:.3f}\t{peak['intensity']:.1f}\n")
        else:
            print("Peak Analysis Results")
            print("2-theta\tIntensity")
            for peak in peaks:
                print(f"{peak['position']:.3f}\t{peak['intensity']:.1f}")
    
    elif args.command == "plot":
        # Background subtraction if requested
        if args.bg_poly is not None:
            intensity = subtract_background(two_theta, intensity, args.bg_poly)
            
        plt.figure(figsize=(10, 6))
        
        if args.plot_type == "raw":
            plt.plot(two_theta, intensity, 'k-', linewidth=1)
            plt.title('Raw XRD Data')
        
        elif args.plot_type == "bgsub":
            plt.plot(two_theta, intensity, 'b-', linewidth=1)
            plt.title('Background-Subtracted XRD Data')
        
        elif args.plot_type == "peaks":
            plt.plot(two_theta, intensity, 'k-', linewidth=1)
            peaks = find_peaks(two_theta, intensity)
            for peak in peaks:
                plt.axvline(x=peak['position'], color='r', linestyle='--', alpha=0.5)
                plt.text(
                    peak['position'],
                    peak['intensity'],
                    f"{peak['position']:.2f}°",
                    rotation=90,
                    va='bottom'
                )
            plt.title('XRD Data with Peaks Marked')
        
        plt.xlabel('2θ (degrees)')
        plt.ylabel('Intensity (a.u.)')
        plt.grid(True, alpha=0.3)
        
        if args.save_plot:
            plt.savefig(args.save_plot, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {args.save_plot}")
        else:
            plt.show()
    
    else:
        print("No command specified. Use --help for available commands.")
        sys.exit(1)

if __name__ == "__main__":
    main() 