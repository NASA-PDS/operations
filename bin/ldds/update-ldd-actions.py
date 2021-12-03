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
import subprocess

from github3 import login
from lxml import etree
from shutil import rmtree, copyfile

from pkg_resources import resource_string
from pystache import Renderer

from pds_github_util.assets.assets import unzip_asset
from pds_github_util.branches.git_actions import clone_checkout_branch
from pds_github_util.utils.ldd_gen import find_primary_ingest_ldd, convert_pds4_version_to_alpha

# Github Org containing Discipline LDDs
GITHUB_ORG = 'pds-data-dictionaries'

ACTIONS_FILENAMES = ['ldd-ci.yml', 'release-ldd.yml']

TEMPLATE_REPO = 'ldd-template'
TEMPLATE_CLONE_URL = f'git@github.com:pds-data-dictionaries/{TEMPLATE_REPO}.git'

STAGING_PATH = '/tmp/action-updates'

SKIP_REPOS = ['ldd-template', 'PDS-Data-Dictionaries.github.io', 'dd-library']

# Default Issues URL
ISSUES_URL = "https://github.com/pds-data-dictionaries/PDS4-LDD-Issue-Repo/issues"

# LDD configuration base directory
GITHUB_ACTION_PATH = os.path.join('github', 'workflows')

# Quiet github3 logging
_logger = logging.getLogger('github3')
_logger.setLevel(level=logging.WARNING)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


def update_actions(token, gh, args):
    """Get repos from Org.
    Loop through repos in Github org and update LDD actions
    """

    # clone template repo
    _template_repo_path = os.path.join(STAGING_PATH, 'ldd-template')
    clone(TEMPLATE_CLONE_URL, _template_repo_path)

    for _repo in gh.repositories_by(args.github_org):
        if _repo.name in SKIP_REPOS:
            continue

        _logger.info(f'updating {_repo.name}')
        _repo_path = os.path.join(STAGING_PATH, _repo.name)
        clone(_repo.clone_url, _repo_path)

        # if yes, copy the files over
        for _filename in ACTIONS_FILENAMES:
            _action_file = os.path.join(_repo_path, GITHUB_ACTION_PATH, _filename)
            _logger.info(_action_file)

            # check if ldd repo has the actions
            if os.path.exists(_action_file):
                _logger.info(f'Copying {_action_file} to {_template_repo_path}')
                copyfile(os.path.join(_template_repo_path, GITHUB_ACTION_PATH, _filename), _action_file)
                commit(_action_file, 'Apply latest LDD Generation updates')


def cleanup_dir(path):
    if os.path.isdir(path):
        rmtree(path)

    os.makedirs(path)


def invoke(argv):
    '''Execute a command within the operating system, returning its output. On any error,
    raise ane exception. The command is the first element of ``argv``, with remaining elements
    being arguments to the command.
    '''
    _logger.debug('🏃‍♀️ Running «%r»', argv)
    try:
        cp = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        _logger.debug('🏁 Run complete, rc=%d', cp.returncode)
        _logger.debug('Stdout = «%s»', cp.stdout.decode('utf-8'))
        _logger.debug('Stderr = «%s»', cp.stderr.decode('utf-8'))
        return cp.stdout.decode('utf-8')
    except subprocess.CalledProcessError as ex:
        _logger.critical('💥 Process with command line %r failed with status %d', argv, ex.returncode)
        _logger.critical('🪵 Stdout = «%s»', ex.stdout.decode('utf-8'))
        _logger.critical('📚 Stderr = «%s»', ex.stderr.decode('utf-8'))
        raise Exception(ex)


def invokeGIT(gitArgs):
    '''Execute the ``git`` command with the given ``gitArgs``.'''
    argv = ['git'] + gitArgs
    return invoke(argv)


def git_config():
    '''Prepare necessary git configuration or else thing might fail'''
    invokeGIT(['config', '--local', 'user.email', 'pdsen-ci@jpl.nasa.gov'])
    invokeGIT(['config', '--local', 'user.name', 'PDSEN CI Bot'])

def clone(clone_url, path):
    '''Commit the file named ``filename`` to the local Git repository with the given ``message``.
    '''
    _logger.debug('🥼 Cloning repo %s to path «%s»', clone_url, path)
    cleanup_dir(path)
    git_config()
    invokeGIT(['clone', clone_url, path])

def git_pull():
    # 😮 TODO: Use Python GitHub API
    # But I'm in a rush:
    git_config()
    invokeGIT(['pull', 'origin', 'main'])


def commit(filename, message):
    '''Commit the file named ``filename`` to the local Git repository with the given ``message``.
    '''
    _logger.debug('🥼 Committing file %s with message «%s»', filename, message)
    git_config()
    invokeGIT(['add', filename])
    invokeGIT(['commit', '--allow-empty', '--message', message])
    # TODO: understand why a simple push does not work and make it work
    # see bug https://github.com/actions/checkout/issues/317
    invokeGIT(['push', 'origin',  'HEAD:main', '--force'])

# def prep_assets_for_release(release, output_path):
#     logger.info(f'downloading assets to {output_path}')
#     cleanup_dir(output_path)
#
#     _ldd_assets = {}
#     if release and release.assets():
#         for _asset in release.assets():
#             if _asset.name.lower().endswith(LDD_PACKAGE_SUFFIX) and 'dependencies' not in _asset.name.lower():
#                 logger.info(f'Downloading asset {_asset.name}')
#                 _output = os.path.join(output_path, _asset.name)
#                 _asset.download(path=_output)
#
#                 unzip_asset(_output, output_path)
#
#                 for root, dirs, files in os.walk(output_path):
#                     for file in files:
#                         if 'ingestldd' not in file.lower():
#                             for _suffix in LDD_FILES_THAT_MATTER:
#                                 if file.lower().endswith(_suffix):
#                                     _ldd_assets[_suffix] = (os.path.join(root, file))
#
#     return _ldd_assets
#
#
# def get_latest_tag_for_pds4_version(dldd_repo, pds4_alpha_version):
#     _sorted_releases = []
#     for _release in dldd_repo.releases():
#         if pds4_alpha_version in _release.name:
#             _sorted_releases.append({'date': _release.created_at, 'release': _release})
#
#     _latest_release = None
#     if _sorted_releases:
#         # sort the releases by date - probably should extract LDD version here but let's try this out for now
#         _sorted_releases.sort(key=lambda t: t['date'])
#
#         # get the latest release
#         _latest_release = _sorted_releases[len(_sorted_releases) - 1]['release']
#
#     return _latest_release
#
#
# def generate_report(ldd_summary, pds4_version, pds4_alpha_version, output, config):
#     _ldd_html_block = ""
#     _ldd_toc = ""
#     for _repo_name in ldd_summary.keys():
#         _ldd_summary_repo = ldd_summary[_repo_name]
#         _assets = _ldd_summary_repo['assets']
#         _description = config[_ldd_summary_repo['repo'].name]['description']
#         if _assets:
#             _pystache_dict = {
#                 'ns_id': _ldd_summary_repo['ns_id'],
#                 'title': _ldd_summary_repo['name'],
#                 'description': _description,
#                 'release_date': datetime.strftime(_ldd_summary_repo['release'].published_at, '%m/%d/%Y'),
#                 'xsd_path': _assets['xsd'].replace(OUTPUT_PATH, ''),
#                 'xsd_fname': os.path.basename(_assets['xsd']),
#                 'sch_path': _assets['sch'].replace(OUTPUT_PATH, ''),
#                 'sch_fname': os.path.basename(_assets['sch']),
#                 'xml_path': _assets['xml'].replace(OUTPUT_PATH, ''),
#                 'xml_fname': os.path.basename(_assets['xml']),
#                 'json_path': _assets['json'].replace(OUTPUT_PATH, ''),
#                 'json_fname': os.path.basename(_assets['json']),
#                 'zip_path': _assets['zip'].replace(OUTPUT_PATH, ''),
#                 'zip_fname': os.path.basename(_assets['zip']),
#                 'issues_url': ISSUES_URL,
#                 'github_url': _ldd_summary_repo['repo'].homepage or
#                               _ldd_summary_repo['repo'].clone_url.replace('.git', '')
#             }
#             _renderer = Renderer()
#             _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'ldd.template.html'))
#             _ldd_html_block += _renderer.render(_template, _pystache_dict)
#         else:
#             # Discipline LDD was not release. use alternate template
#             _pystache_dict = {
#                 'ns_id': _ldd_summary_repo['ns_id'],
#                 'title': _ldd_summary_repo['name'],
#                 'description': _description,
#                 'issues_url': ISSUES_URL,
#                 'github_url': _ldd_summary_repo['repo'].homepage or _ldd_summary_repo['repo'].clone_url.replace('.git', '')
#             }
#             _renderer = Renderer()
#             _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'ldd-alternate.template.html'))
#             _ldd_html_block += _renderer.render(_template, _pystache_dict)
#
#         # Build up LDD TOC
#         _ldd_toc += LDD_TOC_TEMPLATE.format(_ldd_summary_repo['ns_id'], _ldd_summary_repo['name'])
#
#     with open(os.path.join(output, LDD_REPORT), 'w') as f_out:
#         _pystache_dict = {
#             'ldd_block': _ldd_html_block,
#             'ldd_toc': _ldd_toc,
#             'pds4_version': pds4_version,
#             'pds4_alpha_version': pds4_alpha_version
#         }
#
#         _renderer = Renderer()
#         _template = resource_string(__name__, os.path.join(LDD_TEMPLATES_DIR, 'dd-summary.template.shtml'))
#         html_str = _renderer.render(_template, _pystache_dict)
#         f_out.write(html_str)
#
#     logger.info(f'Output summary generated at: {os.path.join(output, LDD_REPORT)}')
#
#
# def load_config():
#     _config = yaml.load(resource_string(__name__, os.path.join(LDD_CONF_DIR, 'config.yml')), Loader=yaml.FullLoader)
#     return _config


def main():
    """main"""
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)

    parser.add_argument('--github_org',
                        help=('github org to search repos for discipline LDDs. NOTE: these repos must contain ' +
                              'src/IngestLDD'),
                        default=GITHUB_ORG)

    parser.add_argument('--token',
                        help='github token.')

    args = parser.parse_args()

    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        _logger.error(f'Github token must be provided or set as environment variable (GITHUB_TOKEN).')
        sys.exit(1)

    try:
        # connect to github
        gh = login(token=token)

        # get all the discipline repos
        update_actions(token, gh, args)

    except Exception:
        traceback.print_exc()
        sys.exit(1)

    _logger.info(f'Updates complete')


if __name__ == '__main__':
    main()
