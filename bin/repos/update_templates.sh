#!/bin/bash

base_repo=$1/.github
new_repo=$2/.github
token=$3


echo "Copy pull request template"
cp ${base_repo}/pull_request_template.md ${new_repo}/

echo "Copy issue templates"
mkdir -p $new_repo/ISSUE_TEMPLATE
cp ${base_repo}/ISSUE_TEMPLATE/*.md ${new_repo}/ISSUE_TEMPLATE/
cd ${new_repo}/ISSUE_TEMPLATE/

git config --local user.email "pdsen-ci@jpl.nasa.gov"
git config --local user.name "PDSEN CI Bot"
git add -A .
git commit -m "update issue templates"
git push origin HEAD

exit 0

