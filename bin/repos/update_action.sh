#!/bin/bash

base_repo=$1/.github/workflows/
new_repo=$2/.github/workflows/
token=$3

mkdir -p $new_repo
cp ${base_repo}/*.yml ${new_repo}/
cd ${new_repo}

git config --local user.email "pdsen-ci@jpl.nasa.gov"
git config --local user.name "PDSEN CI Bot"
git add -A .
git commit -m "update actions per v1.16.0.0 release"
git push origin HEAD

exit 0

