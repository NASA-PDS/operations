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

It's best install the tools virtual environment, so it won’t interfere with—or be interfered by—other packages. To do so:

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
