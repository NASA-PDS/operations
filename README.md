# NASA PDS Engineering Node Operations Team
This repo is a repo to track issues intended for the PDS Engineering Node (EN) Operations Team. These issues may include, but are not limited to, PDS4 NSSDCA Deliveries via [PDS Deep Archive](https://nasa-pds.github.io/pds-deep-archive/index.html), data releases, website updates, or other actions where a repo is unknown.

# Support
For help with the PDS Engineering Node, you can either create a ticket in [Github Issues](https://github.com/NASA-PDS/pdsen-operations/issues) or email pds-operator@jpl.nasa.gov for more assistance.

# LDD Tools

## PDS4 IM Development Release

1. Execute `ldds/prep_for_ldd_release.sh` script as follows to create new branches in all Discipline LDD repos:

TBD

2. Go to each Discipline LDD Repo and create Pull Requests for each new branch (branch names like IM_release_1.15.0.0).
  * PR Title: PDS4 IM Release <IM_version>
  * PR Description:
    ```
    ## Summary
    
    PR for testing LDD with new IM release.
    ```
  * PR Labels: `release`

3. If build failed on new branch, contact the LDD Steward to investigate a potential regression test failure or incompatibiliy with the new IM version.

