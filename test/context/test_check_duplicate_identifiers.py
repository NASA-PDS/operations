#!/usr/bin/env python3
"""
Tests for the check_duplicate_identifiers script.
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

# Add the bin/context directory to the path so we can import the script
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bin" / "context"))

from check_duplicate_identifiers import (
    check_duplicate_identifiers,
    extract_logical_identifier,
    find_xml_files,
)


def create_test_xml_file(file_path: Path, logical_id: str) -> None:
    """Create a test XML file with the given logical_identifier."""
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Product_Context xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <logical_identifier>{logical_id}</logical_identifier>
        <version_id>1.0</version_id>
        <title>Test Product</title>
    </Identification_Area>
</Product_Context>"""
    
    file_path.write_text(xml_content)


def test_find_xml_files():
    """Test finding XML files in a directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create some test files
        (temp_path / "test1.xml").touch()
        (temp_path / "test2.xml").touch()
        (temp_path / "test.txt").touch()
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "test3.xml").touch()
        
        xml_files = find_xml_files(temp_dir)
        
        assert len(xml_files) == 3
        assert any("test1.xml" in str(f) for f in xml_files)
        assert any("test2.xml" in str(f) for f in xml_files)
        assert any("test3.xml" in str(f) for f in xml_files)


def test_extract_logical_identifier():
    """Test extracting logical_identifier from XML file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test.xml"
        
        create_test_xml_file(test_file, "urn:nasa:pds:test:identifier")
        
        logical_id = extract_logical_identifier(test_file)
        assert logical_id == "urn:nasa:pds:test:identifier"


def test_extract_logical_identifier_missing():
    """Test handling of missing logical_identifier."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test.xml"
        
        # Create XML without logical_identifier
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Product_Context xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <version_id>1.0</version_id>
        <title>Test Product</title>
    </Identification_Area>
</Product_Context>"""
        
        test_file.write_text(xml_content)
        
        with pytest.raises(ValueError, match="No logical_identifier found"):
            extract_logical_identifier(test_file)


def test_check_duplicate_identifiers_no_duplicates():
    """Test checking for duplicates when none exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files with unique identifiers
        create_test_xml_file(temp_path / "test1.xml", "urn:nasa:pds:test:id1")
        create_test_xml_file(temp_path / "test2.xml", "urn:nasa:pds:test:id2")
        
        has_duplicates, duplicates = check_duplicate_identifiers(temp_dir)
        
        assert not has_duplicates
        assert len(duplicates) == 0


def test_check_duplicate_identifiers_with_duplicates():
    """Test checking for duplicates when they exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files with duplicate identifiers
        create_test_xml_file(temp_path / "test1.xml", "urn:nasa:pds:test:duplicate")
        create_test_xml_file(temp_path / "test2.xml", "urn:nasa:pds:test:duplicate")
        create_test_xml_file(temp_path / "test3.xml", "urn:nasa:pds:test:unique")
        
        has_duplicates, duplicates = check_duplicate_identifiers(temp_dir)
        
        assert has_duplicates
        assert len(duplicates) == 1
        assert "urn:nasa:pds:test:duplicate" in duplicates
        assert len(duplicates["urn:nasa:pds:test:duplicate"]) == 2


if __name__ == "__main__":
    pytest.main([__file__]) 