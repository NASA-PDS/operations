---
name: PDS LDD Release Request
about: Request EN to release a new version of an LDD off the nominal build schedule
  or against a past PDS4 IM Version.
title: "[ldd-release] <LDD Name> LDD Version:<LDD_version> IM Version:<IM_Version>"
labels: ldd-release
assignees: c-suh, elawsgh

---

* **Is the LDD IngestLDD in Github?** _Yes or no_
* **Has the LDD Namespace been registered in the [Namespace Registry](https://pds.nasa.gov/datastandards/schema/pds-namespace-registry.pdf)?** _Yes or no_

### Ingest LDD is in Github
* **Local Data Dictionary to Release**: _Link to LDD repo here_
* **PDS4 IM version to release with**: _PDS4 IM version here_
* **Need-by date**: _Please indicate a drop-dead need-by date for this release_
* ** Need-by date rationale**: _For quick turnarounds of releases, please indicate a rationale for the condensed schedule_

### Ingest LDD is NOT in Github

* **LDD**: _Name of LDD Ready for release_
* **LDD Submission Package (.zip)**: _ zip consisting of the following files generated from LDDTool:
    * .xsd – XML Schema file
    * .sch – Schematron file
    * .xml – Label file
    * .JSON – JSON File
    * IngestLDD.xml - Ingest LDD File used as input to LDDTool

_NOTE: A code freeze is expected for this LDD repo as soon as this request is submitted in order to avoid collision with additional changes. Once this ticket has been closed, active development may resume._
