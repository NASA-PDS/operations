#!/usr/bin/env python3
"""
Script to check for duplicate logical_identifier values in PDS4 context XML files.

This script recursively searches through all XML files in the specified directory,
extracts logical_identifier values from the Identification_Area section, and
reports any duplicates found.

Usage:
    python check_duplicate_identifiers.py [directory_path]

    If no directory is specified, defaults to "../../data/pds4/context-pds4"

Returns:
    0 if no duplicates found, 1 if duplicates are found
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def find_xml_files(directory: str) -> List[Path]:
    """
    Recursively find all XML files in the given directory.

    Args:
        directory: Path to the directory to search

    Returns:
        List of Path objects for all XML files found
    """
    xml_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".xml"):
                xml_files.append(Path(root) / file)
    return xml_files


def extract_logical_identifier(file_path: Path) -> str:
    """
    Extract logical_identifier from an XML file.

    Args:
        file_path: Path to the XML file

    Returns:
        The logical_identifier value as a string

    Raises:
        ValueError: If logical_identifier is not found or is empty
        ET.ParseError: If XML parsing fails
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Define the namespace
        namespace = {"pds": "http://pds.nasa.gov/pds4/pds/v1"}

        # Find the logical_identifier element
        logical_id_elem = root.find(".//pds:logical_identifier", namespace)

        if logical_id_elem is None:
            # Try without namespace as fallback
            logical_id_elem = root.find(".//logical_identifier")

        if logical_id_elem is None:
            raise ValueError(f"No logical_identifier found in {file_path}")

        logical_id = logical_id_elem.text.strip()
        if not logical_id:
            raise ValueError(f"Empty logical_identifier in {file_path}")

        return logical_id

    except ET.ParseError as e:
        raise ET.ParseError(f"Failed to parse XML file {file_path}: {e}")


def check_duplicate_identifiers(directory: str, verbose: bool = False) -> Tuple[bool, Dict[str, List[Path]]]:
    """
    Check for duplicate logical_identifier values in XML files.

    Args:
        directory: Path to the directory containing XML files
        verbose: Enable verbose output

    Returns:
        Tuple of (has_duplicates, duplicates_dict) where duplicates_dict
        maps logical_identifier to list of file paths containing that identifier
    """
    xml_files = find_xml_files(directory)
    identifier_to_files = defaultdict(list)

    print(f"Scanning {len(xml_files)} XML files in {directory}...")

    for file_path in xml_files:
        try:
            logical_id = extract_logical_identifier(file_path)
            identifier_to_files[logical_id].append(file_path)
            if verbose:
                print(f"  Found: {logical_id} in {file_path}")
        except (ValueError, ET.ParseError) as e:
            print(f"Warning: {e}")
            continue

    # Filter to only include duplicates
    duplicates = {
        logical_id: files
        for logical_id, files in identifier_to_files.items()
        if len(files) > 1
    }

    has_duplicates = len(duplicates) > 0
    return has_duplicates, duplicates


def main() -> int:
    """
    Main function to run the duplicate identifier check.

    Returns:
        0 if no duplicates found, 1 if duplicates are found
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Check for duplicate logical_identifier values in PDS4 context XML files."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory to scan for XML files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()
    context_dir = args.directory

    if not os.path.exists(context_dir):
        print(f"Error: Directory '{context_dir}' not found.")
        print("Please provide a valid directory path.")
        return 1

    if not os.path.isdir(context_dir):
        print(f"Error: '{context_dir}' is not a directory.")
        return 1

    try:
        has_duplicates, duplicates = check_duplicate_identifiers(context_dir, args.verbose)

        if has_duplicates:
            print("\n❌ DUPLICATE LOGICAL_IDENTIFIERS FOUND:")
            print("=" * 50)

            for logical_id, files in duplicates.items():
                print(f"\nLogical Identifier: {logical_id}")
                print(f"Found in {len(files)} files:")
                for file_path in files:
                    print(f"  - {file_path}")

            print(f"\nTotal duplicate identifiers: {len(duplicates)}")
            return 1
        else:
            print("\n✅ No duplicate logical_identifiers found!")
            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
