# NASA PDS Engineering Node Operations Team

This repository is a repo to track issues intended for the [Planetary Data System (PDS)](https://pds.nasa.gov/) [Engineering Node (EN)](https://nasa-pds.github.io/) Operations Team. These issues may include, but are not limited to, PDS4 NSSDCA Deliveries via [PDS Deep Archive](https://nasa-pds.github.io/pds-deep-archive/), data releases, website updates, or other actions where a corresponding GitHub repository is unknown.

# Support

For help with the PDS Engineering Node, you can either create a ticket in [GitHub Issues](https://github.com/NASA-PDS/pdsen-operations/issues) or email pds-operator@jpl.nasa.gov for more assistance.


# Installation

This section specifies the requirements needed to run the software in this repository and gives narrative instructions on performing the installation.


## System Requirements

Prior to installing this software, ensure your system meets the following requirements:

- **Python 3**: This software requires Python 3. Python 3.9 is out now, and 3.10 is to be released imminently. Python 2 will absolutely not work, and indeed Python 2 came to its end of life January 2020.

Consult your operating system instructions or system administrator to install the required packages. For those without system administrator access and are feeling anxious, you could try a local (home directory) Python 3 installation using a Miniconda installation.


## Doing the Installation

We will install the operations too using Python [Pip](https://pip.pypa.io/en/stable/), the Python Package Installer. If you have Python on your system, you probably already have Pip; you can run `pip --help` or `pip3 -help` to check.

It's best install the tools virtual environment, so it won't interfere with—or be interfered by—other packages. To do so:

```console
$ # Clone the repo or do a git pull if it already exists
$ git clone https://github.com/NASA-PDS/pdsen-operations.git
$ cd pdsen-operations
$ # For Linux, macOS, or other Unix systems:
$ mkdir -p $HOME/.virtualenvs
$ python3 -m venv $HOME/.virtualenvs/pdsen-ops
$ source $HOME/.virtualenvs/pdsen-ops/bin/activate
$ pip3 install --requirement requirements.txt
```

---

# pds-stats.py

The `pds-stats.py` script can be used to get the total download metrics for GitHub software tools. Here is an example of how to get metrics for the Validate, MILabel, and Transform tools.

For usage information run `bin/pds-stats.py --help`

## Example Usage
 
1.  Activate your virtual environment:

        source $HOME/.virtualenvs/pdsen-ops/bin/activate

2.  Execute the script:

        bin/pds-stats.py --github_repos validate mi-label transform --token $GITHUB_TOKEN

---


# ldd-corral.py

This utility is used to autonomously generate the [data dictionaries web page](https://pds.nasa.gov/datastandards/dictionaries/index.shtml) for each PDS4 Build.

This software determines all the discipline LDDs to be included with this release, auto-generates the web page, and downloads and stages all the discipline LDDs from the LDD Github repos.


## Configuration

The [ldd-corral configuration](https://github.com/NASA-PDS/pdsen-operations/blob/master/conf/ldds/config.yml) can be modified to add additional discipline LDDs to the workflow.

Format:
```
<github-repo-name>:
    name: a title to be used in the output web page that overrides the <name> from the repo IngestLDD
    description: |
        description here
```


## Usage

For latest usage capabilities:

    bin/ldds/ldd-corral.py  --help

Base usage example (note: the `GITHUB_TOKEN` environment variable must be set):
```console
$ source $HOME/.virtualenvs/pdsen-ops/bin/activate
$ ldd-corral.py  --pds4_version 1.15.0.0 --token $GITHUB_TOKEN
```

**Default outputs:**
- Web page: `/tmp/ldd-release/dd-summary.html`
- Discipline LDDs: `/tmp/ldd-release/pds4`

---


# LDD Utility Scripts

The LDD utility script `prep_for_ldd_release.sh` is usually run as follows:

1.  Execute `bin/prep_for_ldd_release.sh` script as follows to create new branches in all Discipline LDD repositories:

TBD

2. Go to each Discipline LDD Repo and create Pull Requests for each new branch (branch names like IM_release_1.15.0.0).

    - PR Title: PDS4 IM Release &lt;IM_version&gt;
    - PR Description:
    ```
    ## Summary
    ```
    - PR Labels: `release`
    - PR for testing LDD with new IM release.

3.  If build failed on new branch, contact the LDD Steward to investigate a potential regression test failure or incompatibility with the new IM version.

# Portal Scripts

### pds-sync-api.py
```
Download ESA PSA product XML files from search API

options:
  -h, --help            show this help message and exit
  -n NODE_NAME, --node-name NODE_NAME
                        Name of the node (default psa)
  -p DOWNLOAD_PATH, --download-path DOWNLOAD_PATH
                        Where to create the XML files (default download)
  -u URL, --url URL     URL of the PDS product search API (default
                        https://pds.mcp.nasa.gov/api/search/1/products)
  -c CONFIG, --config CONFIG
                        What to call the harvest XML config output (default harvest.cfg)
```

# NSSDCA Status Checker

This script monitors the status of PDS4 packages in NSSDCA and updates GitHub issues accordingly.

## Features

- Reads package information from a CSV file
- Checks NSSDCA API for package status
- Updates GitHub issues with status comments
- Sends email notifications for failed packages
- Updates CSV file with new statuses
- Closes issues when all packages are ingested

## Requirements

- Python 3.6 or higher
- GitHub token with repo access
- Email password for pds-operator@jpl.nasa.gov

## Installation

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Set the following environment variables:
- `GITHUB_TOKEN`: Your GitHub personal access token
- `EMAIL_PASSWORD`: Password for pds-operator@jpl.nasa.gov email account

## Input CSV Format

The script expects a CSV file named `nssdca_status.csv` with the following columns:
- `github_issue_number`: The GitHub issue number
- `identifier`: The package identifier (e.g., urn:nasa:pds:gbo.ast.catalina.survey::1.0)
- `nssdca_status`: Current NSSDCA status of the package

Example:
```csv
github_issue_number,identifier,nssdca_status
629,urn:nasa:pds:gbo.ast.catalina.survey::1.0,proffered
```

## Usage

Run the script:
```bash
python nssdca_status_checker.py
```

The script will:
1. Read the CSV file
2. Check NSSDCA status for each package
3. Update GitHub issues with comments
4. Send email notifications for failed packages
5. Update the CSV file with new statuses
6. Close issues when all packages are ingested

## Error Handling

- Failed API calls are logged
- Email sending errors are logged
- Invalid CSV data is logged
- GitHub API errors are logged

## Notes

- The script assumes all issues are in the NASA-PDS/operations repository
- Email notifications are sent to pds-operator@jpl.nasa.gov
- Project board status updates require additional GitHub API configuration

# PDS4 Context Operations

This directory contains operational scripts and tools for managing PDS4 context products.

## Scripts

### Context Duplicate Identifier Checker

**Location**: `bin/context/check_duplicate_identifiers.py`

A Python script that checks for duplicate `logical_identifier` values in PDS4 context XML files.

#### Features

- Recursively scans all XML files in the `data/pds4/context-pds4` directory
- Extracts `logical_identifier` values from the `Identification_Area` section
- Reports any duplicate identifiers found
- Follows PEP8, linting, and Black formatting standards
- Includes comprehensive error handling and logging
- Returns appropriate exit codes for automation

#### Requirements

- Python 3.8 or higher
- Standard library modules only (no external dependencies required)

#### Usage

Run the script from the operations directory:

```bash
cd operations

# Check the default directory (data/pds4/context-pds4)
python3 bin/context/check_duplicate_identifiers.py

# Check a specific directory
python3 bin/context/check_duplicate_identifiers.py /path/to/xml/files

# Check with verbose output
python3 bin/context/check_duplicate_identifiers.py --verbose

# Check a specific directory with verbose output
python3 bin/context/check_duplicate_identifiers.py /path/to/xml/files --verbose
```

#### Expected Output

**If no duplicates are found:**
```
Scanning 1234 XML files in ../../../data/pds4/context-pds4...

✅ No duplicate logical_identifiers found!
```

**If duplicates are found:**
```
Scanning 1234 XML files in /path/to/xml/files...

❌ DUPLICATE LOGICAL_IDENTIFIERS FOUND:
==================================================

Logical Identifier: urn:nasa:pds:context:facility:laboratory.aps
Found in 2 files:
  - /path/to/xml/files/facility/laboratory.aps_1.0.xml
  - /path/to/xml/files/facility/laboratory.aps_1.1.xml

Total duplicate identifiers: 1
```

**With verbose output:**
```
Scanning 1234 XML files in /path/to/xml/files...
  Found: urn:nasa:pds:context:facility:laboratory.aps in /path/to/xml/files/facility/laboratory.aps_1.0.xml
  Found: urn:nasa:pds:context:facility:laboratory.aps in /path/to/xml/files/facility/laboratory.aps_1.1.xml
  Found: urn:nasa:pds:context:target:planetary_system.solar_system in /path/to/xml/files/target/planetary_system.solar_system_1.0.xml
  ...
```

#### Exit Codes

- `0`: No duplicates found
- `1`: Duplicates found or error occurred

## Development

### Code Formatting

Format the code with Black:

```bash
cd operations
black bin/context/check_duplicate_identifiers.py
```

### Linting

Check code style with flake8:

```bash
cd operations
flake8 bin/context/check_duplicate_identifiers.py
```

### Type Checking

Run mypy for type checking:

```bash
cd operations
mypy bin/context/check_duplicate_identifiers.py
```

### Running Tests

Run the test suite:

```bash
cd operations
pytest test/context/test_check_duplicate_identifiers.py -v
```

## How It Works

1. **File Discovery**: Recursively finds all `.xml` files in the target directory
2. **XML Parsing**: Uses `xml.etree.ElementTree` to parse each XML file
3. **Identifier Extraction**: Looks for `logical_identifier` elements in the `Identification_Area` section
4. **Namespace Handling**: Supports both namespaced and non-namespaced XML
5. **Duplicate Detection**: Uses a `defaultdict` to track which files contain each identifier
6. **Reporting**: Provides detailed output showing all duplicates and their locations

## Error Handling

The script handles various error conditions gracefully:

- Missing or malformed XML files
- Files without `logical_identifier` elements
- Empty `logical_identifier` values
- Permission errors when reading files

## Example XML Structure

The script expects XML files with this structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Product_Context xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:context:facility:laboratory.aps</logical_identifier>
        <version_id>1.1</version_id>
        <title>Argonne National Laboratory Advanced Photon Source</title>
        <!-- ... other elements ... -->
    </Identification_Area>
    <!-- ... rest of document ... -->
</Product_Context>
```

## Contributing

When contributing to these scripts:

1. Follow PEP8 style guidelines
2. Use Black for code formatting
3. Add type hints to all functions
4. Write tests for new functionality
5. Update documentation as needed
