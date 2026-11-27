# Project Drexel paper, version 0.4

This directory contains Jashid Sany's publication-reviewed Project Drexel working preprint for Advent Cybersecurity, prepared 27 November 2026. Version 0.4 supersedes version 0.3, which remains in the repository and Git history. The revision develops a doctoral-style preliminary research framework around local model capability, polymorphism, environment coverage, serial code revision, and defender observability. It does not report a completed dissertation, a Drexel experiment, or a measured universal adaptation or detection-evasion rate.

Version 0.4 was published as a [Zenodo preprint](https://doi.org/10.5281/zenodo.24591891) on 27 November 2026 (DOI: `10.5281/zenodo.24591891`). The record contains `drexel-feasibility-v0.4.pdf` and `zenodo-upload-v0.4.zip`, credits Jashid Sany with Advent Cybersecurity affiliation, and uses Creative Commons Attribution 4.0 International (CC BY 4.0). The ZIP preserves the deposit-time snapshot; this repository note was added after publication.

## Files for a Zenodo deposit

- `drexel-feasibility-v0.4.pdf`: reader-facing preprint.
- `zenodo-upload-v0.4.zip`: LaTeX source, PDF, all current research notes, data records, and benign evaluation scripts in the `docs`, `data`, and `scripts` directories, plus this guide and a file-hash manifest. The archive preserves the evidence snapshot independently of later changes to the [public research repository](https://github.com/Advent-Cybersecurity/advent-drexel). Its external source URLs still require network access. The current research notes were editorially reframed for publication; their earlier wording remains in Git history.
- `drexel-feasibility-v0.4.tex`: editable single-file LaTeX source.

Upload the PDF and ZIP together as one versioned Zenodo record. The ZIP already contains the PDF, so the separate PDF is for direct viewing. Set the publication date to **27 November 2026**, when this version first became public in the repository, even if the Zenodo deposit occurs later. Set version to `0.4` and choose a publication/preprint resource type if offered; the paper is the primary contribution in this mixed paper/data/script archive. Suggested keywords: `Project Drexel`, `polymorphic malware`, `local language models`, `environmental adaptation`, `defender observability`. Enter **Jashid Sany** as creator with **Advent Cybersecurity** as affiliation. Zenodo requires a license; inspect the rights for the paper, data, and scripts and select one or more appropriate licenses at deposit time. No DOI or license has been presumed in the manuscript.

The public abstract can be copied from the PDF. The paper's evidence cutoff is 27 November 2026. Later research and testing should receive a new version rather than an unmarked overwrite.

The commit-pinned GitHub link for the benign inference pilot printed in the deposited version 0.3 and 0.4 PDFs predates a repository privacy cleanup and may no longer resolve. The [pilot record](../docs/inference-resource-study-2026-11-11.md) remains in this repository and in the deposited version 0.4 ZIP. The repository's editable TeX links were repaired after deposit; the published PDF and ZIP are unchanged and preserve the deposit-time source.

## Rebuild

From this directory, run:

```powershell
tectonic drexel-feasibility-v0.4.tex
```

The TeX file uses a self-contained `thebibliography` block and standard packages. No BibTeX step is needed. The PDF displays complete, clickable source URLs that remain traceable in print.

The packaged evidence files include descriptive research records and benign evaluation scripts, not malware samples or operational payloads. The 512-entry source registry is a heterogeneous bibliography. The 31-case ledger is relevance selected for the serial-revision subclaim and does not provide a trial denominator for the wider Project Drexel questions. The archived ledger has four link statuses and explanatory notes, not uniform structured per-case extraction of every attribute considered in the narrative review.

Run `python make_zenodo_bundle.py` after the last PDF or text change. It writes the ZIP and `SHA256SUMS-v0.4.txt` for the archived files. Zenodo's [publication-date guidance](https://help.zenodo.org/docs/deposit/describe-records/publication-date/) says to use the first-public date for work already available elsewhere; its [resource-type guidance](https://help.zenodo.org/docs/deposit/describe-records/resource-type/) supports a primary type for mixed uploads. Its [versioning guidance](https://help.zenodo.org/docs/deposit/manage-versions/) treats later changed files as a new record version, and its [license guidance](https://help.zenodo.org/docs/deposit/describe-records/licenses/) permits multiple licenses when needed.
