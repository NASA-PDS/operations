---
name: "[ldd-request] PDS LDD Release"
about: Request EN to release a new version of an LDD off the nominal build schedule
  or against a past PDS4 IM Version.
title: "[ldd-release] <LDD Name> LDD Version:<LDD_version> IM Version:<IM_Version>"
labels: ldd-release
assignees: c-suh, viviant100

---

<!--
         The following questionnaire should be filled out by the LDD Steward and only 
         submitted for Off-Nominal Releases. See the documentation here for more details:
         https://pds-data-dictionaries.github.io/development/ldd-release.html#off-nominal-release
-->

* **Is the LDD IngestLDD in Github?** _Yes or no_

* **Has the LDD Namespace been registered in the [Namespace Registry](https://github.com/NASA-PDS/pds4-information-model/raw/main/docs/namespace-registry/pds-namespace-registry.pdf)?** _Yes or no_

<!-- Please indicate a drop-dead need-by date for this release -->
* **Need-by date**:

<!-- For quick turnarounds of releases, please indicate a rationale for the condensed schedule -->
* **Need-by date rationale**:

----

### Latest LDD is in Github

<!-- Link to LDD's tagged version under the repo's Releases.
        e.g. https://github.com/pds-data-dictionaries/ldd-geom/releases -->
* **GitHub Tagged Release of LDD**:

<!-- PDS4 IM version here -->
* **PDS4 IM version to release with**:

_NOTE: A code freeze is expected for this LDD repo as soon as this request is submitted in order to avoid collision with additional changes. Once this ticket has been closed, active development may resume. If the LDD to release is not in the repo, PDS Operations will upload those files to the repo._

### Latest LDD is NOT in Github

* **LDD**: _Name of LDD Ready for release_
* **LDD Submission Package (.zip)**: _zip consisting of the following files generated from LDDTool_
    * .xsd – XML Schema file
    * .sch – Schematron file
    * .xml – Label file
    * .JSON – JSON File
    * IngestLDD.xml - Ingest LDD File used as input to LDDTool
