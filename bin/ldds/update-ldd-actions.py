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
import subprocess

from github3 import login
from shutil import rmtree, copyfile
from time import sleep

# Github Org containing Discipline LDDs
GITHUB_ORG = 'pds-data-dictionaries'

ACTIONS_FILENAMES = ['ldd-ci.yml', 'submod-ci.yml', 'release-ldd.yml', 'build-docs.yml']

TEMPLATE_REPO = 'ldd-template'
TEMPLATE_CLONE_URL = f'git@github.com:pds-data-dictionaries/{TEMPLATE_REPO}.git'

STAGING_PATH = '/tmp/action-updates'

SKIP_REPOS = ['ldd-template', 'PDS-Data-Dictionaries.github.io', 'dd-library', 'PDS4-LDD-Issue-Repo']

# Default Issues URL
ISSUES_URL = "https://github.com/pds-data-dictionaries/PDS4-LDD-Issue-Repo/issues"

# Sub-Model configuration base directory
GITHUB_ACTION_PATH = os.path.join('.github', 'workflows')

# Sub-Model configuration base directory
DOC_CONFIG_FILEPATH = os.path.join('docs', 'source', 'conf.py')

# Quiet github3 logging
_logger = logging.getLogger('github3')
_logger.setLevel(level=logging.WARNING)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


def update_actions(token, gh, args):
    """Get repos from Org.
    Loop through repos in Github org and update sub-model automation
    :param token:
    :param gh:
    :param args:
    :return:
    """

    # clone template repo
    _template_repo_path = os.path.join(STAGING_PATH, 'template')
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

            # check if SubMod repo has the actions
            if _filename == 'ldd-ci.yml':
                if os.path.exists(_action_file):
                    os.remove(_action_file)
                    os.chdir(_repo_path)
                    commit(_action_file, 'Apply latest Sub-Model Automation updates')
            else:
                _logger.info(f'Copying {_action_file} to {_template_repo_path}')
                copyfile(os.path.join(_template_repo_path, GITHUB_ACTION_PATH, _filename), _action_file)
                os.chdir(_repo_path)
                commit(_action_file, 'Apply latest LDD Automation updates')

        # copy doc config
        _doc_config = os.path.join(_repo_path, DOC_CONFIG_FILEPATH)
        if os.path.exists(_doc_config):
            _template_doc_config = os.path.join(_template_repo_path, DOC_CONFIG_FILEPATH)
            _logger.info(f'Copying {_template_doc_config} to {_doc_config}')
            copyfile(_template_doc_config, _doc_config)
            os.chdir(_repo_path)
            commit(_doc_config, 'Apply latest LDD Doc Gen Config updates')

        os.chdir(STAGING_PATH)
        cleanup_dir(_repo_path)
        sleep(15)


def cleanup_dir(path):
    if os.path.isdir(path):
        rmtree(path)

    os.makedirs(path)

def invoke(argv):
    """Execute a command within the operating system, returning its output. On any error,
    raise ane exception. The command is the first element of ``argv``, with remaining elements
    being arguments to the command.

    :param argv:
    :return:
    """
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


def invoke_git(git_args):
    """Execute the ``git`` command with the given ``gitArgs``.

    :param git_args:
    :return:
    """
    argv = ['git'] + git_args
    return invoke(argv)


def git_config():
    '''Prepare necessary git configuration or else thing might fail'''
    invoke_git(['config', '--local', 'user.email', 'pds-ops@jpl.nasa.gov'])
    invoke_git(['config', '--local', 'user.name', 'PDSEN Ops'])


def clone(clone_url, path):
    """Clone repo to local server.

    :param clone_url:
    :param path:
    :return:
    """
    _logger.debug('🥼 Cloning repo %s to path «%s»', clone_url, path)
    cleanup_dir(path)
    invoke_git(['clone', clone_url, path])


def git_pull():
    # 😮 TODO: Use Python GitHub API
    # But I'm in a rush:
    git_config()
    invoke_git(['pull', 'origin', 'main'])


def commit(filename, message):
    """Commit the file named ``filename`` to the local Git repository with the given ``message``.

    :param filename:
    :param message:
    :return:
    """
    _logger.info('🥼 Committing file %s with message «%s»', filename, message)
    git_config()
    invoke_git(['add', '--all', filename])
    invoke_git(['commit', '--allow-empty', '--message', message])
    # TODO: understand why a simple push does not work and make it work
    # see bug https://github.com/actions/checkout/issues/317
    invoke_git(['push', 'origin',  'HEAD:main'])


def main():
    """main"""
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)

    parser.add_argument('--github_org',
                        help=('github org to search repos for pds4 sub-models. NOTE: these repos must contain ' +
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
