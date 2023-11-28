#!/usr/bin/env python
"""
LDD Corral

Tool to corral all the LDDs 
"""
import logging
import os

import sys
import traceback

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime

import yaml
from github3 import login
from lxml import etree
from shutil import rmtree

from pkg_resources import resource_string
from pystache import Renderer

from pds_github_util.assets.assets import unzip_asset
from pds_github_util.branches.git_actions import clone_checkout_branch
from pds.ldd_manager.release import find_primary_ingest_ldd
from pds.ldd_manager.util import convert_pds4_version_to_alpha


# LDDs In Development or repos to ignore
SKIP_REPOS = ['dd-library', 'ldd-wave', 'ldd-template']

# Github Org containing Discipline LDDs
GITHUB_ORG = 'pds-data-dictionaries'

# Namespace URI for PDS XML
PDS_NS_URI = 'http://pds.nasa.gov/pds4/pds/v1'

# Discipline LDD Dictionary Type Value
DISC_LDD_DICT_TYPE = 'Discipline'

STAGING_PATH = '/data/tmp/ldd-staging'
OUTPUT_PATH = '/data/tmp/ldd-release'

RELEASE_SUBDIR = "pds4"

# LDD package file name suffix (Zip file)
LDD_PACKAGE_SUFFIX = 'zip'

# Report Filename
LDD_REPORT = "dd-summary.shtml"

# LDD Default Order
LDD_FILES_THAT_MATTER = ['xsd', 'sch', 'xml', 'json', 'zip']

# Default Issues URL
ISSUES_URL = "https://github.com/pds-data-dictionaries/PDS4-LDD-Issue-Repo/issues"

# HTML list template
LDD_TOC_TEMPLATE = '				<li><a href="#{}">{}</a></li>\n'

# LDD configuration base directory
LDD_CONF_DIR = os.path.join('..', '..', 'conf', 'ldds')

# LDD templates dir
LDD_TEMPLATES_DIR = os.path.join('..', '..', 'conf', 'ldds', 'templates')

# Quiet github3 logging
logger = logging.getLogger('github3')
logger.setLevel(level=logging.WARNING)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_release(token, gh, args):
    """Get Discipline Repos from Org.
    Loop through repos in Github org to determine if it is a discipline LDD
    """
    _ldd_summary = {}
    _pds4_alpha_version = convert_pds4_version_to_alpha(args.pds4_version)
    _config = load_config()

    for _repo in gh.repositories_by(args.github_org):
        logger.info(f'checking {_repo.name}')
        _dldd_repo = None

        # get the ingestLDD file from the repo
        _ingest_ldd = get_ingest_ldd(token, _repo, args.base_path + STAGING_PATH)

        if _ingest_ldd and _repo.name != "ldd-template":
            _ldd_assets = []

            # extract dictionary type and namespace id from ingestLDD
            _ldd_name, _dict_type, _ns_id, _ns_version = extract_metadata(_ingest_ldd)

            # check if this is a discipline LDD
            if is_discipline_ldd(_repo, _dict_type, _config):
                logger.info(f'discipline LDD found {_repo.name}')
                _ldd_summary_repo = _ldd_summary[_repo.name] = {}
                _ldd_summary_repo['repo'] = _repo

                _ldd_summary_repo['name'] = _ldd_name
                if 'name' in _config[_repo.name]:
                    _ldd_summary_repo['name'] = _config[_repo.name]['name'] or _ldd_name

                _ldd_summary_repo['ns_id'] = _ns_id
                _dldd_repo = _repo.refresh()

                # get latest release
                _ldd_summary_repo['release'] = get_latest_tag_for_pds4_version(_dldd_repo, _pds4_alpha_version)

                # let's download and unpack the release assets
                _ldd_assets = prep_assets_for_release(_ldd_summary_repo['release'],
                                                      os.path.join(args.base_path + args.output, RELEASE_SUBDIR,
                                                                   _ldd_summary_repo['ns_id'],
                                                                   'v' + _ns_version))

                _ldd_summary_repo['assets'] = _ldd_assets

    # generate output report
    generate_report(_ldd_summary, args.pds4_version, _pds4_alpha_version, args.output, _config)


def cleanup_dir(path):
    if os.path.isdir(path):
        rmtree(path)

    os.makedirs(path)


def get_ingest_ldd(token, repo, staging_path):
    """Get ingest ldd from repo.
    """
    # Cleanup in case repo already exists
    _staging = f'{staging_path}/{repo}'
    cleanup_dir(_staging)

    _remote_url = repo.git_url.replace('git://', f'https://{token}:x-oauth-basic@')
    cloned_repo = clone_checkout_branch(_remote_url, _staging, 'main')

    return find_primary_ingest_ldd(f'{cloned_repo.working_tree_dir}/src')


def extract_metadata(ingest_ldd):
    """Extract metadata from ingestLDD.

    Uses XPath to pull out specific metadata needed by other processes. Currently:
    * //Ingest_LDD/dictionary_name
    * //Ingest_LDD/dictionary_type
    * //Ingest_LDD/namespace_id
    * //Ingest_LDD/ldd_version_id
    """
    _dict_name = None
    _dict_type = None
    _ns_id = None
    _ns_version = None
    with open(ingest_ldd[0], 'r') as f:
        _tree = etree.parse(f)
        _root = _tree.getroot()
        if _tree.getroot().tag == f'{{{PDS_NS_URI}}}Ingest_LDD':
            # get name
            _matches = _root.findall(f'./{{{PDS_NS_URI}}}name')
            if _matches:
                _dict_name = _matches[0].text.strip()

            # get dictionary type
            _matches = _root.findall(f'./{{{PDS_NS_URI}}}dictionary_type')
            if _matches:
                _dict_type = _matches[0].text.strip()

            # get namespace id
            _matches = _root.findall(f'./{{{PDS_NS_URI}}}namespace_id')
            if _matches:
                _ns_id = _matches[0].text.strip()

            # get version
            _matches = _root.findall(f'./{{{PDS_NS_URI}}}ldd_version_id')
            if _matches:
                _ns_version = _matches[0].text.strip().split('.')[0]

    return _dict_name, _dict_type, _ns_id, _ns_version


def is_discipline_ldd(repo, dict_type, config):
    if repo.name not in SKIP_REPOS:
        if dict_type == DISC_LDD_DICT_TYPE and repo.name in config.keys():
            return True

    return False


def prep_assets_for_release(release, output_path):
    logger.info(f'downloading assets to {output_path}')
    cleanup_dir(output_path)

    _ldd_assets = {}
    if release and release.assets():
        for _asset in release.assets():
            if _asset.name.lower().endswith(LDD_PACKAGE_SUFFIX) and 'dependencies' not in _asset.name.lower():
                logger.info(f'Downloading asset {_asset.name}')
                _output = os.path.join(output_path, _asset.name)
                _asset.download(path=_output)

                unzip_asset(_output, output_path)

                for root, dirs, files in os.walk(output_path):
                    for file in files:
                        if 'ingestldd' not in file.lower():
                            for _suffix in LDD_FILES_THAT_MATTER:
                                if file.lower().endswith(_suffix):
                                    _ldd_assets[_suffix] = (os.path.join(root, file))

    return _ldd_assets


def get_latest_tag_for_pds4_version(dldd_repo, pds4_alpha_version):
    _sorted_releases = []
    for _release in dldd_repo.releases():
        if pds4_alpha_version in _release.name:
            _sorted_releases.append({'date': _release.created_at, 'release': _release})

    _latest_release = None
    if _sorted_releases:
        # sort the releases by date - probably should extract LDD version here but let's try this out for now
        _sorted_releases.sort(key=lambda t: t['date'])

        # get the latest release
        _latest_release = _sorted_releases[len(_sorted_releases) - 1]['release']

    return _latest_release


def generate_report(ldd_summary, pds4_version, pds4_alpha_version, output, config):
    _ldd_html_block = ""
    _ldd_toc = ""
    for _repo_name in ldd_summary.keys():
        _ldd_summary_repo = ldd_summary[_repo_name]
        _assets = _ldd_summary_repo['assets']
        _description = config[_ldd_summary_repo['repo'].name]['description']
        if _assets:
            _pystache_dict = {
                'ns_id': _ldd_summary_repo['ns_id'],
                'title': _ldd_summary_repo['name'],
                'description': _description,
                'release_date': datetime.strftime(_ldd_summary_repo['release'].published_at, '%m/%d/%Y'),
                'xsd_path': _assets['xsd'].replace(OUTPUT_PATH, ''),
                'xsd_fname': os.path.basename(_assets['xsd']),
                'sch_path': _assets['sch'].replace(OUTPUT_PATH, ''),
                'sch_fname': os.path.basename(_assets['sch']),
                'xml_path': _assets['xml'].replace(OUTPUT_PATH, ''),
                'xml_fname': os.path.basename(_assets['xml']),
                'json_path': _assets['json'].replace(OUTPUT_PATH, ''),
                'json_fname': os.path.basename(_assets['json']),
                'zip_path': _assets['zip'].replace(OUTPUT_PATH, ''),
                'zip_fname': os.path.basename(_assets['zip']),
                'issues_url': ISSUES_URL,
                'github_url': _ldd_summary_repo['repo'].homepage or
                              _ldd_summary_repo['repo'].clone_url.replace('.git', '')
            }
            _renderer = Renderer()
            _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'ldd.template.html'))
            _ldd_html_block += _renderer.render(_template, _pystache_dict)
        else:
            # Discipline LDD was not release. use alternate template
            _pystache_dict = {
                'ns_id': _ldd_summary_repo['ns_id'],
                'title': _ldd_summary_repo['name'],
                'description': _description,
                'issues_url': ISSUES_URL,
                'github_url': _ldd_summary_repo['repo'].homepage or _ldd_summary_repo['repo'].clone_url.replace('.git', '')
            }
            _renderer = Renderer()
            _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'ldd-alternate.template.html'))
            _ldd_html_block += _renderer.render(_template, _pystache_dict)

        # Build up LDD TOC
        _ldd_toc += LDD_TOC_TEMPLATE.format(_ldd_summary_repo['ns_id'], _ldd_summary_repo['name'])

    with open(os.path.join(output, LDD_REPORT), 'w') as f_out:
        _pystache_dict = {
            'ldd_block': _ldd_html_block,
            'ldd_toc': _ldd_toc,
            'pds4_version': pds4_version,
            'pds4_alpha_version': pds4_alpha_version
        }

        _renderer = Renderer()
        _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'dd-summary.template.shtml'))
        html_str = _renderer.render(_template, _pystache_dict)
        f_out.write(html_str)

    logger.info(f'Output summary generated at: {os.path.join(output, LDD_REPORT)}')


def load_config():
    _config = yaml.load(resource_string(__name__, os.path.join(LDD_CONF_DIR, 'config.yml')), Loader=yaml.FullLoader)
    return _config


def main():
    """main"""
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)

    parser.add_argument('--output',
                        help='directory to output the generated page and dictionaries',
                        default=OUTPUT_PATH)
    parser.add_argument('--github_org',
                        help=('github org to search repos for discipline LDDs. NOTE: these repos must contain ' +
                              'src/IngestLDD'),
                        default=GITHUB_ORG)
    parser.add_argument('--pds4_version',
                        help='PDS4 version to be used. Format example: 1.15.0.0',
                        required=True)
    parser.add_argument('--token',
                        help='github token.')
    parser.add_argument('--base_path',
                        help='Base file path for the staging and output paths.',
                        required=True)

    args = parser.parse_args()

    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.error(f'Github token must be provided or set as environment variable (GITHUB_TOKEN).')
        sys.exit(1)

    try:
        # connect to github
        gh = login(token=token)

        # get all the discipline repos
        generate_release(token, gh, args)

    except Exception:
        traceback.print_exc()
        sys.exit(1)

    logger.info(f'Data Dictionaries have been output to {args.output}')
    logger.info(f'SUCCESS: LDD Corral complete.')


if __name__ == '__main__':
    main()
