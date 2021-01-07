#!/usr/bin/env python
'''
PDS Stats Script

Simple script to get some download metrics for PDS software tools using
Github3 API

'''
import argparse
import github3
import glob
import logging
import os
import requests
import shutil
import sys
import traceback

from datetime import datetime
from subprocess import Popen, CalledProcessError, PIPE, STDOUT

from pds_github_util.tags.tags import Tags
from pds_github_util.assets.assets import download_asset, unzip_asset

GITHUB_ORG = 'NASA-PDS'

# Quiet github3 logging
logger = logging.getLogger('github3')
logger.setLevel(level=logging.WARNING)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    parser.add_argument('--github_org',
                        help='github organization',
                        default=GITHUB_ORG)
    parser.add_argument('--github_repos',
                        help='github repo names',
                        nargs='*',
                        required=True)
    parser.add_argument('--token',
                        help='github token')

    args = parser.parse_args()

    token = args.token or os.environ.get('GITHUB_TOKEN')

    if not token:
        logger.error(f'Github token must be provided or set as environment variable (GITHUB_TOKEN).')
        sys.exit(1)

    try:

        gh = github3.login(token=token)

        for repo in args.github_repos:
            repo = gh.repository(args.github_org, repo)
            count = 0
            for release in repo.releases():
                for asset in release.assets():
                    count += asset.download_count

            print(f'{args.github_org}/{repo} Download Count: {count}')

    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
