#!/bin/bash

# Script to update discipline LDD repos with the ldd-template Github action:
# 
# * clone ldd-template repo
# * loop through discipline LDD repos and:
#   * clone the repo
#   * copy the github action from the template repo to the LDD repo
#   * push to master
#   

usage () {
    echo "$(basename $0)"
    echo
    exit 1
}

branch_suffix=


#DISCIPLINE_LDD_REPOS="ldd-img"
DISCIPLINE_LDD_REPOS="ldd-multi ldd-particle ldd-wave ldd-rings ldd-img ldd-disp ldd-msn ldd-msn_surface ldd-proc ldd-img_surface ldd-ctli ldd-speclib ldd-msss_cam_mh ldd-cart ldd-spectral ldd-nucspec ldd-survey"
BASE_CLONE_URL=git@github.com:pds-data-dictionaries
GITHUB_API_URL="https://api.github.com/repos/pds-data-dictionaries"

cd /tmp

echo ">> cloning ldd-template repo"
rm -fr ldd-template
git clone $BASE_CLONE_URL/ldd-template.git

for repo in $DISCIPLINE_LDD_REPOS; do
    rm -fr $repo
    echo ">> cloning $repo repo"
    git clone $BASE_CLONE_URL/${repo}.git

    echo "copying github actions"
    rsync -av ldd-template/.github/workflows ${repo}/.github/

    cd ${repo}

    # set admin user
    git config --local user.email "pdsen-ci@jpl.nasa.gov"
    git config --local user.name "PDSEN CI Bot"

    # add the updated
    git status
    git add -A .
    git commit -m "update to better handle tagging release branches"
    git push origin master

    # cleanup
    cd ..
    rm -fr ${repo}

    echo
    echo
done

rm -fr ldd-template

exit 0
