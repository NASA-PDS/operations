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
from shutil import rmtree

from github3 import login
from subprocess import Popen, CalledProcessError, PIPE, STDOUT

from pds_github_util.branches.git_actions import clone_checkout_branch

GIT_URL_BASE = 'git@github.com:{}.git'
BASE_DIR = '/tmp'
BASE_REPO = 'pds-template-repo-generic'

GITHUB_ORG = 'NASA-PDS'

# Quiet github3 logging
logger = logging.getLogger('github3')
logger.setLevel(level=logging.WARNING)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_cmd(cmd):
    with Popen(cmd, stdout=PIPE, stderr=STDOUT, shell=True) as p:
        for line in p.stdout:
            print(line, end='')  # process line here

    if p.returncode != 0:
        raise CalledProcessError(p.returncode, p.args)


def cleanup_dir(path):
    if os.path.isdir(path):
        rmtree(path)


def clone_repo(path, git_url):
    cleanup_dir(path)

    # clone the repo
    cmd = [f'git clone {git_url} {path}']
    run_cmd(cmd)

def update_action(token, gh, args, base_repo):
    """Update Github Actions

    Loop through all repos and update their github actions with the template
    """
    for _repo in gh.repositories_by(args.github_org):
        if _repo.name != base_repo:
            logger.info(f'updating {_repo.name}')
            output_dir = os.path.join(BASE_DIR, _repo.name)
            clone_repo(output_dir, _repo.git_url)

            # update action
            cmd = [f'./update_action.sh {output_dir}']
            run_cmd(cmd)

            sys.exit(0)

def main():
    """main"""
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)

    parser.add_argument('--github_org',
                        help=('github org to update repos.'),
                        default=GITHUB_ORG)
    parser.add_argument('--update_templates',
                        help='Update issue templates',
                        action='store_true', default=False)
    parser.add_argument('--update_action',
                        help='Update repo actions',
                        action='store_true', default=False)
    parser.add_argument('--base_repo',
                        help='base repo to copy config from',
                        default=BASE_REPO)
    parser.add_argument('--token',
                        help='github token.')

    args = parser.parse_args()

    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.error(f'Github token must be provided or set as environment variable (GITHUB_TOKEN).')
        sys.exit(1)

    try:
        # connect to github
        gh = login(token=token)

        base_repo = args.github_org + '/' + args.base_repo
        logger.info(f'clone base repo {base_repo}')
        output_dir = os.path.join(BASE_DIR, args.base_repo)
        clone_repo(output_dir, GIT_URL_BASE.format(base_repo))

        if args.update_action:
            update_action(token, gh, args, base_repo)

    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    logger.info(f'SUCCESS: Execution complete.')


if __name__ == '__main__':
    main()
