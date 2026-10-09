## 2026-10-09T18:10:01.701028+00:00

Initial generation: Controller plus a single Counter node. The counter logic lives in counter_core.py (no udi_interface dependency, unit tested) and counter_node.py is a thin wrapper. Persists count and step to persist_dir.

