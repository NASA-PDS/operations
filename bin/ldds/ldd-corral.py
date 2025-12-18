#!/usr/bin/env python
"""LDD Corral.

Tool to corral all the LDDs 
"""
import logging
import os

import re

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

from pds.ldd_manager.util import Assets, LDDs, convert_pds4_version_to_alpha
from lasso.reports.branches.git_actions import clone_checkout_branch


# LDDs In Development or repos to ignore
SKIP_REPOS = ['dd-library', 'ldd-template', 'PDS-Data-Dictionaries.github.io', 'PDS4-LDD-Issue-Repo']

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

# WebHelp absolute path from PDS domain for each namespace's specification of classes or attributes
WEBHELP_PATH = "/datastandards/documents/dd/v1/PDS4_PDS_DD_{}/webhelp/all/#ch{}.html"
# Simplified text for WebHelp link
WEBHELP_LINK_TEXT = "PDS4 {}({}) WebHelp#ch{}"

# Regex to get the namespace from the IngestLDD path
# NOTE: DART has an irregular filename thus it won't match this regex
# but DART is not on the mission LDD page anyway, which disqualifies it
NAMESPACE_FROM_INGEST_LDD_FILENAME_REGEX = re.compile(r'(?<=src/PDS4_).*(?=_IngestLDD\.xml)')

# See `check_qualifiers_for_ldds()` for qualifying condition(s)
QUALIFYING_INGEST_LDDS = []
NAMESPACES_WITHOUT_INGESTLDD = ['dart', 'vco', 'viper']

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
        if _repo.name in SKIP_REPOS:
            logger.info(f'skipping {_repo.name}')
        else:
            _ingest_ldd = get_ingest_ldd(token, _repo, args.base_path + STAGING_PATH)

            if _ingest_ldd:
                assess_ingest_ldd(_ingest_ldd)

                _ldd_assets = []

                # extract dictionary type and namespace id from ingestLDD
                _ldd_name, _dict_type, _ns_id, _ns_version = extract_metadata(_ingest_ldd)

                # check if this is a discipline LDD
                if args.all_repos or is_discipline_ldd(_repo, _dict_type, _config):
                    logger.info(f'LDD found {_repo.name}')
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

    # momentarily convert list to set to remove duplicates as a just-in-case
    # then sort the list so that its order matches what's expected in WebHelp
    global QUALIFYING_INGEST_LDDS
    QUALIFYING_INGEST_LDDS = list(set(QUALIFYING_INGEST_LDDS))
    QUALIFYING_INGEST_LDDS.sort()

    logger.debug('-' * 50)
    logger.debug('These are the expected namespaces in the WebHelp docs:')
    for i, x in enumerate(QUALIFYING_INGEST_LDDS):
        logger.debug(f'{i}: {x}')
    logger.debug('These are bookended by 5 then 2 chapters, and each namespace has 2 chapters.')
    logger.debug('The formula for a chapter number is 2i+6 and 2i+7 with i=0-based list index. The formula accounts for the 5 preceding chapters.')
    logger.debug(f'So, the total number of chapters should be 2 * ( {len(QUALIFYING_INGEST_LDDS)} - 1 ) + 9 = {2*(len(QUALIFYING_INGEST_LDDS)- 1)+9}.')
    logger.debug('-' * 50)

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

    return LDDs.find_primary_ingest_ldd(f'{cloned_repo.working_tree_dir}/src')


def assess_ingest_ldd(ingest_ldd):
    """Assess if ns_id qualifies to go in QUALIFYING_INGEST_LDDS
    """
    ingest_ldd_path = get_first_ingest_ldd(ingest_ldd)
    _namespace_match = NAMESPACE_FROM_INGEST_LDD_FILENAME_REGEX.search(ingest_ldd_path)

    if _namespace_match is not None:
        _namespace = _namespace_match.group().lower()
        check_qualifiers_for_ldds(_namespace)
    else:
        logger.debug(f'Failed to match regex for XML in expected directory for {ingest_ldd[0]}')


def get_first_ingest_ldd(ingest_ldd):
    """Returns first item from list. If there is more than one item in this list, the logic of both this and
    get_ingest_ldd should be revisited.
    """
    if len(ingest_ldd) > 1:
        logger.debug(f'PROBLEMATIC: More than one IngestLDD found {ingest_ldd}')

    return ingest_ldd[0]


def check_qualifiers_for_ldds(namespace):
    """The sole qualifier is that it has an IngestLDD.xml (from a repo at github.com/pds-data-dictionaries)
    """
    # Some LDDs on the PDS pages do not have repos (e.g., orex), so they should not appear here anyway since the
    # ingestLDD file is from the repository

    if (
            namespace != 'example' and
            not any(namespace == _no_ingestldd for _no_ingestldd in NAMESPACES_WITHOUT_INGESTLDD)
    ):
        QUALIFYING_INGEST_LDDS.append(check_for_namespace_exceptions(namespace))


def check_for_namespace_exceptions(namespace):
    """Most IngestLDDs follow the format of PDS4_<ns_id>_IngestLDD.xml. Some one-offs (e.g., DART, DAWN) should be
    addressed with its next release, but some others appear confused, whether it's our doing or theirs.
    """
    _namespace_id_exceptions = {'spectral': 'sp'}
    for _ns, _id in _namespace_id_exceptions.items():
        if namespace == _ns:
            return _id
        else:
            return namespace


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

                Assets.unzip_asset(_output, output_path)

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


def get_webhelp_chapter_string(chapter_number):
    if chapter_number < 10:
        return '0' + str(chapter_number)
    else:
        return str(chapter_number)


def get_webhelp_chapter_number(ns_id, specification):
    """Determines what the webhelp chapter number will be, based off the list of IngestLDDs, which Steve uses to make the WebHelp files
    """
    # There are 5 chapters from "Intro" to "Attributes in the common namespace"
    # So, the chapters based off these IngestLDDs start from chapter 6
    _chapter_offset = 6
    try:
        _ingest_ldd_index = QUALIFYING_INGEST_LDDS.index(ns_id)
        _webhelp_chapter_number = (2 * _ingest_ldd_index)
        if specification == 'classes':
            _webhelp_chapter_number += _chapter_offset
        elif specification == 'attributes':
            _webhelp_chapter_number += _chapter_offset + 1
        return get_webhelp_chapter_string(_webhelp_chapter_number)
    except ValueError:
        logger.debug(f'PROBLEM: {ns_id} not recognized as having an IngestLDD')


def generate_report(ldd_summary, pds4_version, pds4_alpha_version, output, config):
    _ldd_html_block = ""
    _ldd_toc = ""
    for _repo_name in ldd_summary.keys():
        _ldd_summary_repo = ldd_summary[_repo_name]
        _assets = _ldd_summary_repo['assets']
        _description = config[_ldd_summary_repo['repo'].name]['description']
        _webhelp_chapter_string_classes = get_webhelp_chapter_number(_ldd_summary_repo['ns_id'], 'classes')
        _webhelp_chapter_string_attributes = get_webhelp_chapter_number(_ldd_summary_repo['ns_id'], 'attributes')
        _pystache_dict = {
            'ns_id': _ldd_summary_repo['ns_id'],
            'title': _ldd_summary_repo['name'],
            'description': _description,
            'release_date': '-',
            'issues_url': ISSUES_URL,
            'github_repo_url': _ldd_summary_repo['repo'].clone_url.replace('.git', ''),
            'github_io_url': (
                    _ldd_summary_repo['repo'].homepage or
                    _ldd_summary_repo['repo'].clone_url
                    .replace('.git', '')
                    .replace('github.com/pds-data-dictionaries', 'pds-data-dictionaries.github.io')
            ),
            'webhelp_path_classes': WEBHELP_PATH.format(pds4_alpha_version, _webhelp_chapter_string_classes),
            'webhelp_path_attributes': WEBHELP_PATH.format(pds4_alpha_version, _webhelp_chapter_string_attributes),
            'webhelp_link_text_classes': WEBHELP_LINK_TEXT.format(pds4_version, pds4_alpha_version, _webhelp_chapter_string_classes),
            'webhelp_link_text_attributes': WEBHELP_LINK_TEXT.format(pds4_version, pds4_alpha_version, _webhelp_chapter_string_attributes)
        }
        if _assets:
            _pystache_dict = {
                **_pystache_dict,
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
                'zip_fname': os.path.basename(_assets['zip'])
            }
            partial_template = """
                        <ul>
                            <li><a href="{{xsd_path}}">{{xsd_fname}}</a></li>
                            <li><a href="{{sch_path}}">{{sch_fname}}</a></li>
                            <li><a href="{{xml_path}}">{{xml_fname}}</a></li>
                            <li><a href="{{json_path}}">{{json_fname}}</a></li>
                            <li><a href="{{zip_path}}">{{zip_fname}}</a></li>
                        </ul>"""
        else:
            # Discipline LDD was not released. Use alternate text in place of expected files.
            partial_template = ('<i>A new version of this Local Data Dictionary was not generated with this version of '
                                'the PDS4 Information Model. To submit a request to have the LDD generated, please '
                                'submit a request to the <a href="https://pds.nasa.gov/?feedback=true">PDS Help Desk</a>, '
                                'or create an issue in the <a href="{{issues_url}}">PDS4 LDD Issues Repository</a></i>')
        # Render this LDD section
        _renderer = Renderer(partials={'ldd_files': partial_template})
        _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'ldd.template.html'))
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
                        help='Directory to output the generated page and dictionaries',
                        default=OUTPUT_PATH)
    parser.add_argument('--github_org',
                        help=('Github org to search repos for discipline LDDs. NOTE: these repos must contain ' +
                              'src/IngestLDD'),
                        default=GITHUB_ORG)
    parser.add_argument('--pds4_version',
                        help='PDS4 version to be used. Format example: 1.15.0.0',
                        required=True)
    parser.add_argument('--token',
                        help='Github token.')
    parser.add_argument('--base_path',
                        help='Base file path for the staging and output paths.',
                        required=True)
    parser.add_argument('--all_repos',
                        help='Clone and include all repos in corral run.',
                        action='store_true')
    parser.add_argument('-n', '--no_ingestldd',
                        help='Additional namespaces that don\'t have a <repo>/src/IngestLDD. Already included: "dart", "vco", and "viper".',
                        nargs='*',
                        metavar='namespace')

    args = parser.parse_args()

    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.error(f'Github token must be provided or set as environment variable (GITHUB_TOKEN).')
        sys.exit(1)

    if args.no_ingestldd:
        global NAMESPACES_WITHOUT_INGESTLDD
        NAMESPACES_WITHOUT_INGESTLDD += args.no_ingestldd

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
