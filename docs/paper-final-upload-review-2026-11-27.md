# Project Drexel preprint: final upload review

Advent Cybersecurity, 27 November 2026. This is a final publication check of version 0.4, following the detailed [version 0.2-to-0.3 QA record](paper-quality-assurance-2026-11-27.md). The review covered the manuscript's argument, all 31 bibliography entries at their original publication or pinned source where accessible, the selected numerical claims, the PDF, and the deposit archive. It did not run a model, agent, malware sample, or payload.

## Corrections made in this pass

- The manuscript now describes the 31-case selection as proximity cases **or explicit boundary comparators**. The [case ledger](../data/closest-case-claim-ledger-2026-11-26.json) has one comparator outside all four strict links. The RQ1 question asks whether observed environmental information changes model-conditioned behavior while function is retained; comparative performance against fixed-rule and unchanged controls is reported separately. The claim-link table uses the ledger's narrower “two active revisions” label.
- Publication-facing research notes were editorially reframed to use Project Drexel terminology. These wording changes do not alter case statuses, experimental results, source IDs, or raw data.
- [Zenodo's publication-date guidance](https://help.zenodo.org/docs/deposit/describe-records/publication-date/) calls for the first-public date when work was already available elsewhere. The deposit guide therefore specifies **27 November 2026**, when this version became public in the repository, rather than automatically using a later deposit date. [Zenodo's resource-type guide](https://help.zenodo.org/docs/deposit/describe-records/resource-type/) permits choosing the primary publication type for a mixed archive; its [license guide](https://help.zenodo.org/docs/deposit/describe-records/licenses/) permits multiple licenses when appropriate.

## Publication boundary

The manuscript is a preliminary narrative preprint and prospective research program. It is not a completed dissertation, a systematic review, or an empirical demonstration. The reviewed sources do not establish universal environmental adaptation or invisibility to defenders. The source registry is a heterogeneous bibliography, and the selected-case ledger is not a trial denominator. The PDF is not tagged for accessibility. The depositor must choose a license for the Zenodo record; no license or DOI is asserted in the manuscript.

## Final artifact checks

The LaTeX build produces a 14-page PDF with Jashid Sany and Advent Cybersecurity in the author metadata. All 31 cited bibliography keys resolve, the PDF carries 32 unique clickable URLs, and the build log has no unresolved citation, reference, fatal, or overfull-box warning. Rendered pages were inspected for table overflow, clipping, and readable references. The package has 240 payload files plus a SHA-256 manifest; all file hashes and ZIP CRCs match, all 730 local Markdown links resolve within the archive, and the standalone PDF and TeX match their archived copies. The source registry retains 512 unique IDs and URLs, and all 31 selected cases reference registered source IDs. Neither the manuscript nor publication archive names the earlier narrative source. These checks support deposit readiness for the stated preliminary preprint; they are not model or malware tests.
