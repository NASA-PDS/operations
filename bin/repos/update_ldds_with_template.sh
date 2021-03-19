#!/bin/bash

# Script to update discipline LDD repos with the ldd-template Github action:
# 
# * clone ldd-template repo
# * loop through discipline LDD repos and:
#   * clone the repo
#   * copy the github action from the template repo to the LDD repo
#   * push to master
#   

template_repo=pds-template-repo-generic

repo=$1  # e.g. NASA-PDS/my_repo
base_clone_url=git@github.com:

echo ">> cloning template repo"
git clone $base_clone_url/$template_repo.git

git config --local user.email "pdsen-ci@jpl.nasa.gov"
git config --local user.name "PDSEN CI Bot"

echo ">> cloning $repo repo"
git clone $base_close_url/${repo}.git
    
echo "copying github action"
rsync -av $template_repo/.github/ISSUE_TEMPLATE/ ${repo}/.github/ISSUE_TEMPLATE/
cp $template_repo/.github/pull_request_template.md ${repo}/.github/pull_request_template.md

cd ${repo}
git status
git add .
git commit -m "update issue templates per process improvements"
git push origin master

cd ..
rm -fr ${repo}

rm -fr pds-template-repo-generic
