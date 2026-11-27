# Research scripts

These scripts support the [documented studies](../docs/README.md). They are experiment code, not a single automated benchmark suite. Each study note identifies its runtime, inputs, controls, and valid outputs. Most model and runtime binaries are external to this repository; the [provenance record](../data/qwen3-same-source-artifact-provenance-2026-11-21.json) pins the later Qwen3 artifacts.

## Local resource experiments

- [run_inference_resource_study.py](run_inference_resource_study.py) and [run_lossless_compression_study.py](run_lossless_compression_study.py): early CPU inference and byte-exact archival checks.
- [run_same_base_quantization_pilot.py](run_same_base_quantization_pilot.py) and [audit_same_base_gguf.py](audit_same_base_gguf.py): same-base quantization and tensor identity checks.
- [run_cold_cgroup_gguf_pilot.py](run_cold_cgroup_gguf_pilot.py): cold-cache memory accounting.
- [run_frontier_cpu_minimal_bundle_pilot.py](run_frontier_cpu_minimal_bundle_pilot.py), [run_frontier_cpu_served_task_pilot.py](run_frontier_cpu_served_task_pilot.py), and [audit_gguf_tensor_topology.py](audit_gguf_tensor_topology.py): deployed-file census, complete served tasks, and tensor layout.

## Benign quality and audit tools

- [run_generated_multistep_quality.py](run_generated_multistep_quality.py), [run_gsm8k_pair_diagnostic.py](run_gsm8k_pair_diagnostic.py), and [plan_paired_quality_sample.py](plan_paired_quality_sample.py): public calibration, diagnostic scoring, and sample planning.
- `calibrate_reference_structural_quality*.py` and `audit_reference_*.py`: versioned public structural-task calibration and independent audits. The version suffixes preserve earlier protocols and are not interchangeable.
- [run_same_source_chain_assay.py](run_same_source_chain_assay.py), [run_qwen3_structural_assay.py](run_qwen3_structural_assay.py), and [audit_qwen3_structural_manifest.py](audit_qwen3_structural_manifest.py): the November 21 same-source study and its frozen manifest check. That held-out evaluation was interrupted before candidate testing.

Run commands, hardware assumptions, and result admission criteria are in the study notes. No script should be treated as evidence of a successful four-measure result without its paired records and review.
