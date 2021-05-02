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
    echo "$(basename $0) <pds4_release_number>"
    echo "          * pds4_release_number - e.g. 1.15.0.0"
    echo
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

release=$1

#release_alpha=$(python << END
#from pds_github_util.utils.ldd_gen import convert_pds4_version_to_alpha
#print(convert_pds4_version_to_alpha("$release"))
#END
#)
#rel_type="release"
#branch_suffix=

if [ -z "$PDSEN_CI_TOKEN" ]; then
  echo "Must set PDSEN_CI_TOKEN environment variable prior to execution"
fi

BRANCH_NAME="release/$release"

dLDDs=()
while read -r line; do
  if [[ "$line" == ldd-*: ]]; then
    dLDDs+=("${line%?}")
  fi
done < ../../conf/ldds/config.yml

#DISCIPLINE_LDD_REPOS="ldd-wave ldd-particle ldd-multi"
#DISCIPLINE_LDD_REPOS="ldd-multi ldd-particle ldd-wave ldd-rings ldd-img ldd-disp ldd-msn ldd-msn_surface ldd-proc ldd-img_surface ldd-ctli ldd-speclib ldd-msss_cam_mh ldd-cart ldd-geom ldd-spectral ldd-nucspec ldd-survey ldd-chan1"
BASE_CLONE_URL=git@github.com:pds-data-dictionaries
GITHUB_API_URL="https://api.github.com/repos/pds-data-dictionaries"

PR_JSON="{
  \"title\": \"PDS4 IM Release $release\",
  \"body\": \"Prep for release of LDD for IM Release $release\",
  \"head\": \"$BRANCH_NAME\",
  \"base\": \"master\"
}"

cd /tmp || exit

echo ">> cloning ldd-template repo"
rm -fr ldd-template
git clone $BASE_CLONE_URL/ldd-template.git

for repo in "${dLDDs[@]}"; do
    rm -fr "$repo"
    echo ">> cloning $repo repo"
    git clone $BASE_CLONE_URL/${repo}.git || continue

    echo "copying github action"
    cp ldd-template/.github/workflows/*.yml "${repo}"/.github/workflows/

    cd "${repo}" || exit

    # set admin user
    git config --local user.email "pdsen-ci@jpl.nasa.gov"
    git config --local user.name "PDSEN CI Bot"

    # delete branch if it exists
    # NOTE: errors may be thrown here if branch doesn't exist
    git branch -d "$BRANCH_NAME"
    git push origin --delete "$BRANCH_NAME"

    # create branch
    git checkout -b "$BRANCH_NAME"

    # add new PDS4 version to config file
    echo "$release" >> pds4_versions.txt

    # add the updated
    git status
    git add -A .
    git commit --allow-empty -m "Prep for tagging PDS4 IM Release $release"
    git push origin "$BRANCH_NAME"

    # cleanup
    cd ..
    rm -fr "${repo}"

    # create PR
    curl -X POST -u "pdsen-ci:${PDSEN_CI_TOKEN}" -d "$PR_JSON" "$GITHUB_API_URL/${repo}/pulls"

    echo
    echo
    exit
done

rm -fr ldd-template

exit 0
