---
name: "[ldd-request] Initialize New PDS LDD"
about: Describe this issue template's purpose here.
title: '[ldd-request] Create new LDD "<proposed namespace ID>"'
labels: enhancement, ldd-request, p.must-have
assignees: c-suh

---

* **Local Data Dictionary Name:**
<!-- Long name of the proposed LDD. For example, Imaging, Spectral, Survey, Geometry, Mars 2020-->

* **Namespace ID Requested:**
<!-- examples: img, geom, spectral, mars2020, ladee, etc. -->

* **Discipline or Mission LDD?** 
<!-- Is the planned LDD a mission-specific dictionary, or a multi-mission, discipline dictionary? -->

* **Steward Organization Name:** 
<!-- examples: PDS PPI Node, PDS EN Node, PDS RMS Node, PSA, JAXA -->

* **LDD Steward Name:** 
<!-- Name of lead point of contact from steward organization -->

* **LDD Steward Email:** 
<!-- email address of LDD Steward -->

* **LDD Stewardship Team Members:** 
<!-- Github usernames for all members of the LDD Stewardship Team. For more information on the responsibilities of the LDD Stewardship Team, see https://pds-data-dictionaries.github.io/development/ldd-create.html#who-is-the-ldd-stewardship-team -->

* **LDD Description:**
<!--  Brief description of the LDD. This description will be used on the PDS Data Dictionaries website here: https://pds.nasa.gov/datastandards/dictionaries/ -->

* **Rationale for creation of new LDD:**
<!-- Describe why this LDD is needed -->

---
<!-- For internal use by PDS EN Operations Team-->
**Engineering Details**
- [ ] Complete [Initializing New LDD procedure](https://pds-data-dictionaries.github.io/development/ldd-create.html#initializing-new-ldd)
- [ ] If discipline LDD
  - [ ] update [LDD script config](https://github.com/NASA-PDS/pdsen-operations/blob/master/conf/ldds/config.yml)
  - [ ] create directory and index files for Git
  - [ ] create symlink on all machines
