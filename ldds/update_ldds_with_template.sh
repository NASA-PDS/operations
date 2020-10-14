#!/bin/bash

# Script to update discipline LDD repos with the ldd-template Github action:
# 
# * clone ldd-template repo
# * loop through discipline LDD repos and:
#   * clone the repo
#   * copy the github action from the template repo to the LDD repo
#   * push to master
#   

DISCIPLINE_LDD_REPOS=ldd-multi ldd-particle ldd-wave ldd-rings ldd-img ldd-disp ldd-msn ldd-msn_surface ldd-proc ldd-img_surface ldd-ctli ldd-speclib ldd-msss_cam_mh ldd-cart ldd-geom ldd-spectral ldd-nucspec ldd-survey ldd-chan1
BASE_CLONE_URL=git@github.com:pds-data-dictionaries

cd /tmp

echo ">> cloning ldd-template repo"
git clone $BASE_CLONE_URL/ldd-template.git

for repo in $DISCIPLINE_LDD_REPOS; do
    echo ">> cloning $repo repo"
    git clone $BASE_CLONE_URL/${repo}.git

    echo "copying github action"
    cp ldd-template/.github/workflows/ldd-ci.yml ${repo}/.github/workflows/ldd-ci.yml

    cd ${repo}
    git status
    git add .
    git commit -m "Update Github Action with new, improved PDSEN CI"
    git push origin master

    cd ..
    rm -fr ${repo}
done

rm -fr ldd-template