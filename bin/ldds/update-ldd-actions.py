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

SKIP_REPOS = ['ldd-template', 'PDS-Data-Dictionaries.github.io', 'dd-library', 'PDS4-LDD-Issue-Repo']

# Default Issues URL
ISSUES_URL = "https://github.com/pds-data-dictionaries/PDS4-LDD-Issue-Repo/issues"

# LDD configuration base directory
GITHUB_ACTION_PATH = os.path.join('.github', 'workflows')

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
        clone(_repo.ssh_url, _repo_path)

        # if yes, copy the files over
        for _filename in ACTIONS_FILENAMES:
            _action_file = os.path.join(_repo_path, GITHUB_ACTION_PATH, _filename)
            _logger.info(_action_file)

            # check if ldd repo has the actions
            if os.path.exists(_action_file):
                _logger.info(f'Copying {_action_file} to {_template_repo_path}')
                copyfile(os.path.join(_template_repo_path, GITHUB_ACTION_PATH, _filename), _action_file)
                os.chdir(_repo_path)
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
    '''Clone repo to local server.
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
    _logger.info('🥼 Committing file %s with message «%s»', filename, message)
    git_config()
    invokeGIT(['add', filename])
    invokeGIT(['commit', '--allow-empty', '--message', message])
    # TODO: understand why a simple push does not work and make it work
    # see bug https://github.com/actions/checkout/issues/317
    invokeGIT(['push', 'origin',  'HEAD:main', '--force'])

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
