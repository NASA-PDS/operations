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
    echo "$(basename $0) <release_number> <dev_or_ops>"
    echo "          * release_number - e.g. 1F00"
    echo
    exit 1
}

#if [ $# -lt 2 ]; then
#    usage
#fi

release=$1

rel_type="release"
branch_suffix=
#if [ "$2" == "dev" ]; then
#    rel_type="dev-release"
#    branch_suffix="_dev"
#fi

BRANCH_NAME="IM_release_$release$branch_suffix"

DISCIPLINE_LDD_REPOS="ldd-m2020 ldd-mess"
#DISCIPLINE_LDD_REPOS="ldd-multi ldd-particle ldd-wave ldd-rings ldd-img ldd-disp ldd-msn ldd-msn_surface ldd-proc ldd-img_surface ldd-ctli ldd-speclib ldd-msss_cam_mh ldd-cart ldd-geom ldd-spectral ldd-nucspec ldd-survey ldd-chan1"
BASE_CLONE_URL=git@github.com:pds-data-dictionaries
GITHUB_API_URL="https://api.github.com/repos/pds-data-dictionaries"

PR_JSON="{
  \"title\": \"PDS4 IM Release $release\",
  \"body\": \"Testing and release of LDD for IM Release $release\",
  \"head\": \"$BRANCH_NAME\",
  \"base\": \"master\"
}"

cd /tmp

echo ">> cloning ldd-template repo"
rm -fr ldd-template
git clone $BASE_CLONE_URL/ldd-template.git

for repo in $DISCIPLINE_LDD_REPOS; do
    rm -fr $repo
    echo ">> cloning $repo repo"
    git clone $BASE_CLONE_URL/${repo}.git

    echo "copying github action and new versions file"
    cp ldd-template/.github/workflows/*.yml ${repo}/.github/workflows/
    cp ldd-template/pds4_versions.txt ${repo}/

    cd ${repo}

    # set admin user
    git config --local user.email "pdsen-ci@jpl.nasa.gov"
    git config --local user.name "PDSEN CI Bot"

    # delete branch if it exists
    # NOTE: errors may be thrown here if branch doesn't exist
    #git branch -d $BRANCH_NAME
    #git push origin --delete $BRANCH_NAME

    # create branch
    #git checkout -b $BRANCH_NAME

    # add the updated
    git status
    git add -A .
    git commit -m "Updated workflows to better manage pds4 versions"
    git push origin master

    # cleanup
    cd ..
    rm -fr ${repo}

    # create PR
    #curl -X POST -u pdsen-ci:${PDSEN_CI_TOKEN} -d "$PR_JSON" $GITHUB_API_URL/$repo/pulls

    echo
    echo
done

rm -fr ldd-template

exit 0
