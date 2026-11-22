import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.infrastructure.trusted_files import (
    TrustedFileError,
    read_bounded_bytes,
    read_verified_bytes,
    write_exclusive_bytes,
)
from vehicle_platform.mlops.monitoring import MonitoringProtocol, monitor_receipts
from vehicle_platform.mlops.policy import require_controlled_environment


def test_independent_acceptance_oracle_uses_hand_computed_small_fixture():
    import sys
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    checker_path = Path(__file__).resolve().parents[4] / "scripts" / "check_mlops.py"
    spec = spec_from_file_location("phase10_acceptance_checker", checker_path)
    assert spec is not None and spec.loader is not None
    checker = module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)

    result = checker._verify_bounded_oracle_fixture()
    assert result["status"] == "PASS"
    assert result["baseline_receipts"] == 4
    assert result["baseline_scored"] == 3
    assert result["baseline_abstained"] == 1
    assert result["comparison_scored_coverage"] == 1.0
    assert result["comparison_delta"] == 0.25
    assert result["psi"] == pytest.approx(0.25 * math.log(3))


def test_trusted_artifact_files_are_bounded_private_and_checksum_bound(tmp_path):
    import hashlib

    root = tmp_path / "artifacts"
    path = root / "runs" / "artifact.bin"
    payload = b"immutable artifact bytes"
    write_exclusive_bytes(root, path.relative_to(root), payload)
    checksum = hashlib.sha256(payload).hexdigest()

    assert (
        read_bounded_bytes(root, path, maximum_bytes=64, expected_owner=path.stat().st_uid)
        == payload
    )
    assert (
        read_verified_bytes(
            root,
            path,
            checksum,
            maximum_bytes=64,
            expected_size=len(payload),
            expected_owner=path.stat().st_uid,
            require_private=True,
        )
        == payload
    )

    with pytest.raises(FileExistsError):
        write_exclusive_bytes(root, path.relative_to(root), b"replacement")
    with pytest.raises(TrustedFileError, match="byte limit"):
        read_bounded_bytes(root, path, maximum_bytes=2)
    with pytest.raises(TrustedFileError, match="size or checksum"):
        read_verified_bytes(root, path, checksum, maximum_bytes=64, expected_size=len(payload) + 1)
    with pytest.raises(TrustedFileError, match="checksum mismatch"):
        read_verified_bytes(root, path, "0" * 64, maximum_bytes=64)
    with pytest.raises(TrustedFileError, match="owner"):
        read_bounded_bytes(root, path, maximum_bytes=64, expected_owner=-1)
    with pytest.raises(TrustedFileError, match="invalid"):
        read_bounded_bytes(root, path, maximum_bytes=0)
    with pytest.raises(TrustedFileError, match="escapes"):
        read_bounded_bytes(root, tmp_path / "outside.bin", maximum_bytes=64)


def test_trusted_artifact_reader_rejects_symlinks_and_non_regular_files(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    target = root / "target.bin"
    target.write_bytes(b"data")
    link = root / "link.bin"
    link.symlink_to(target)

    with pytest.raises(TrustedFileError, match="symlink"):
        read_bounded_bytes(root, link, maximum_bytes=64)
    directory = root / "directory"
    directory.mkdir()
    with pytest.raises(TrustedFileError, match="regular file"):
        read_bounded_bytes(root, directory, maximum_bytes=64)

    symlink_parent = tmp_path / "linked-root"
    symlink_parent.symlink_to(root, target_is_directory=True)
    with pytest.raises(TrustedFileError, match="unsafe directory"):
        read_bounded_bytes(symlink_parent, symlink_parent / "target.bin", maximum_bytes=64)


def test_trusted_artifact_reader_enforces_private_files_and_write_error_cleanup(
    monkeypatch, tmp_path
):
    import os
    import stat

    root = tmp_path / "private"
    path = root / "item.bin"
    write_exclusive_bytes(root, Path("item.bin"), b"private")
    path.chmod(0o644)
    with pytest.raises(TrustedFileError, match="permissions"):
        read_bounded_bytes(root, path, maximum_bytes=64, require_private=True)

    with pytest.raises(TrustedFileError, match="invalid"):
        write_exclusive_bytes(root, Path("."), b"invalid path")
    with pytest.raises(TrustedFileError, match="invalid"):
        write_exclusive_bytes(root, Path("/absolute.bin"), b"invalid path")

    blocked_root = tmp_path / "blocked"

    def fail_link(*_args, **_kwargs):
        raise PermissionError

    real_link = os.link
    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(TrustedFileError, match="published safely"):
        write_exclusive_bytes(blocked_root, Path("nested/item.bin"), b"blocked")
    monkeypatch.setattr(os, "link", real_link)

    import vehicle_platform.infrastructure.trusted_files as trusted_files

    monkeypatch.setattr(
        os,
        "fstat",
        lambda _descriptor: SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600, st_size=1, st_uid=os.getuid()
        ),
    )
    with pytest.raises(TrustedFileError, match="byte limit"):
        trusted_files.read_bounded_bytes(root, path, maximum_bytes=4)


def test_trusted_artifact_access_fails_closed_without_nofollow_support(monkeypatch, tmp_path):
    import os

    root = tmp_path / "artifacts"
    root.mkdir()
    path = root / "item.bin"
    path.write_bytes(b"data")
    monkeypatch.delattr(os, "O_NOFOLLOW")
    with pytest.raises(TrustedFileError, match="unavailable"):
        read_bounded_bytes(root, path, maximum_bytes=64)
    with pytest.raises(TrustedFileError, match="unavailable"):
        write_exclusive_bytes(root, Path("new.bin"), b"data")


def test_phase10_contracts_reject_naive_non_utc_and_inconsistent_source_counts():
    from datetime import timedelta, timezone

    from vehicle_platform.mlops.contracts import DatasetBinding

    base = {
        "source_role": SourceRole.SYNTHETIC,
        "source_fingerprint": "a" * 64,
        "row_fingerprint": "b" * 64,
        "feature_set_version": "phase9a-pull-v2",
        "feature_checksum": "c" * 64,
        "label_checksum": "d" * 64,
        "row_count": 2,
        "session_count": 2,
        "cutoff": datetime(2026, 1, 1, tzinfo=UTC),
    }
    assert DatasetBinding(**base).row_count == 2
    with pytest.raises(ValidationError, match="UTC offset"):
        DatasetBinding(**{**base, "cutoff": datetime(2026, 1, 1)})
    with pytest.raises(ValidationError, match="expressed in UTC"):
        DatasetBinding(
            **{**base, "cutoff": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1)))}
        )
    with pytest.raises(ValidationError, match="session count"):
        DatasetBinding(**{**base, "row_count": 1})


def test_phase10_reproduction_contract_is_read_only_and_serving_separated():
    from vehicle_platform.mlops.contracts import ReproductionReceipt

    receipt = {
        "original_run_id": uuid4(),
        "candidate_version_id": uuid4(),
        "definition_fingerprint": "a" * 64,
        "expected_source_fingerprint": "b" * 64,
        "reproduced_source_fingerprint": "b" * 64,
        "expected_training_dataset_checksum": "c" * 64,
        "reproduced_training_dataset_checksum": "c" * 64,
        "expected_artifact_checksum": "d" * 64,
        "reproduced_artifact_checksum": "d" * 64,
        "expected_evaluation_checksum": "e" * 64,
        "reproduced_evaluation_checksum": "e" * 64,
        "evaluation_rows_fingerprint": "f" * 64,
        "expected_metrics_checksum": "1" * 64,
        "reproduced_metrics_checksum": "1" * 64,
        "holdout_usage": "READ_ONLY_REPRODUCTION_AUDIT_NO_SELECTION_OR_TUNING",
        "scientific_limitations": (
            "Synthetic validation is not real-world validity.",
            "Scores are not mechanical failure probabilities.",
            "Unlabeled real telemetry cannot establish accuracy.",
            "No component diagnosis is established.",
        ),
        "status": "REPRODUCED",
    }
    assert ReproductionReceipt(**receipt).serving_action == "NONE"
    with pytest.raises(ValidationError):
        ReproductionReceipt(**{**receipt, "holdout_usage": "THRESHOLD_TUNING"})
    with pytest.raises(ValidationError):
        ReproductionReceipt(**{**receipt, "serving_action": "ACTIVATE"})


@pytest.mark.asyncio
async def test_mlops_reproduction_budget_deadline_is_bounded():
    import asyncio
    from time import perf_counter

    from vehicle_platform.mlops.reproduction import ReproductionError, _within_budget

    async def quick_operation():
        return "reproduced"

    async def slow_operation():
        await asyncio.sleep(0.05)

    assert await _within_budget(quick_operation, perf_counter() + 1) == "reproduced"
    with pytest.raises(ReproductionError, match="REPRODUCTION_TIMEOUT"):
        await _within_budget(quick_operation, 0)
    with pytest.raises(ReproductionError, match="REPRODUCTION_TIMEOUT"):
        await _within_budget(slow_operation, perf_counter() + 0.001)


@pytest.mark.asyncio
async def test_mlops_reproduction_rejects_ineligible_run_before_training(monkeypatch):
    from vehicle_platform.features.service import default_feature_version
    from vehicle_platform.mlops import reproduction
    from vehicle_platform.mlops.contracts import ResourceBudget

    monkeypatch.setattr(reproduction, "require_controlled_environment", lambda: "test")
    monkeypatch.setattr(reproduction, "checkout_is_dirty", AsyncMock(return_value=False))

    class FakeResult:
        def __init__(self, row):
            self.row = row

        def mappings(self):
            return self

        def one_or_none(self):
            return self.row

    class FakeSession:
        def __init__(self, rows):
            self.rows = iter(rows)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def begin(self):
            return self

        async def execute(self, *_args, **_kwargs):
            return FakeResult(next(self.rows))

    class FakeDatabase:
        def __init__(self, rows):
            self.rows = iter(rows)

        def session(self):
            return FakeSession(self.rows)

    def make_definition(**updates):
        updates["expected_feature_checksum"] = default_feature_version().checksum
        return _supervised_definition("reproduction-unit-v1").model_copy(update=updates)

    def make_record(definition, **updates):
        candidate_id = uuid4()
        comparison = {
            "status": "COMPARABLE_OFFLINE",
            "serving_action": "NONE",
            "task": definition.task.value,
            "source_role": definition.source_role.value,
            "evaluation_dataset_checksum": definition.expected_evaluation_checksum,
            "challenger_version_id": str(candidate_id),
            "challenger": {},
        }
        record = {
            "state": "COMPLETED",
            "definition_fingerprint": definition.fingerprint,
            "body": definition.model_dump(mode="json"),
            "comparison": comparison,
            "model_version_id": str(candidate_id),
        }
        record.update(updates)
        return record

    async def run(record):
        database = FakeDatabase([None, record])
        return await reproduction.reproduce_supervised_run(database, uuid4())

    with pytest.raises(reproduction.ReproductionError, match="REQUIRES_COMPLETED"):
        await run(None)
    with pytest.raises(reproduction.ReproductionError, match="REQUIRES_COMPLETED"):
        await run({"state": "FAILED"})
    with pytest.raises(reproduction.ReproductionError, match="LINEAGE_MISSING"):
        await run(make_record(make_definition(), body=None))
    with pytest.raises(reproduction.ReproductionError, match="LINEAGE_MISSING"):
        await run(make_record(make_definition(), comparison=[]))

    imported = make_definition(source_role=SourceRole.IMPORTED_FIXTURE)
    with pytest.raises(reproduction.ReproductionError, match="DEFINITION_INELIGIBLE"):
        await run(make_record(imported))

    resource_limited = make_definition(budget=ResourceBudget(max_features=1))
    with pytest.raises(reproduction.ReproductionError, match="RESOURCE_LIMIT"):
        await run(make_record(resource_limited))

    incompatible = make_record(make_definition())
    incompatible["comparison"]["status"] = "NOT_COMPARABLE"
    with pytest.raises(reproduction.ReproductionError, match="COMPARISON_INELIGIBLE"):
        await run(incompatible)

    monkeypatch.setattr(reproduction, "checkout_is_dirty", AsyncMock(return_value=True))
    with pytest.raises(reproduction.ReproductionError, match="SOURCE_COMMIT_MISMATCH"):
        await run(make_record(make_definition()))


@pytest.mark.asyncio
async def test_mlops_reproduction_checks_training_lineage_before_split(monkeypatch):
    from vehicle_platform.features.service import default_feature_version
    from vehicle_platform.mlops import reproduction
    from vehicle_platform.mlops.contracts import ResourceBudget

    monkeypatch.setattr(reproduction, "require_controlled_environment", lambda: "test")
    monkeypatch.setattr(reproduction, "checkout_is_dirty", AsyncMock(return_value=False))

    class FakeResult:
        def __init__(self, row):
            self.row = row

        def mappings(self):
            return self

        def one_or_none(self):
            return self.row

    class FakeSession:
        def __init__(self, rows):
            self.rows = iter(rows)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def begin(self):
            return self

        async def execute(self, *_args, **_kwargs):
            return FakeResult(next(self.rows))

    class FakeDatabase:
        def __init__(self, rows):
            self.rows = iter(rows)

        def session(self):
            return FakeSession(self.rows)

    definition = _supervised_definition("reproduction-lineage-v1").model_copy(
        update={"expected_feature_checksum": default_feature_version().checksum}
    )
    candidate_id = uuid4()
    record = {
        "state": "COMPLETED",
        "definition_fingerprint": definition.fingerprint,
        "body": definition.model_dump(mode="json"),
        "model_version_id": str(candidate_id),
        "comparison": {
            "status": "COMPARABLE_OFFLINE",
            "serving_action": "NONE",
            "task": definition.task.value,
            "source_role": "synthetic",
            "evaluation_dataset_checksum": definition.expected_evaluation_checksum,
            "challenger_version_id": str(candidate_id),
            "challenger": {},
        },
    }

    async def build_bad_dataset(*_args, **_kwargs):
        return SimpleNamespace(checksum="0" * 64, source_fingerprint="1" * 64, rows=()), None, None

    monkeypatch.setattr(reproduction, "build_task_dataset", build_bad_dataset)
    with pytest.raises(reproduction.ReproductionError, match="TRAINING_LINEAGE_MISMATCH"):
        await reproduction.reproduce_supervised_run(FakeDatabase([None, record]), uuid4())

    async def build_matching_dataset(*_args, **_kwargs):
        return (
            SimpleNamespace(
                checksum=definition.expected_dataset_checksum,
                source_fingerprint=definition.expected_source_fingerprint,
                rows=(),
            ),
            None,
            None,
        )

    def stop_after_lineage(_dataset):
        raise RuntimeError("training split reached after verified lineage")

    monkeypatch.setattr(reproduction, "build_task_dataset", build_matching_dataset)
    monkeypatch.setattr(reproduction, "chronological_group_split", stop_after_lineage)
    with pytest.raises(RuntimeError, match="verified lineage"):
        await reproduction.reproduce_supervised_run(FakeDatabase([None, record]), uuid4())

    class FakeArtifactStore:
        async def load_registered(self, _database, _candidate_id):
            return SimpleNamespace(
                model_version=SimpleNamespace(
                    supervised_dataset_id=uuid4(),
                    label_definition_id=uuid4(),
                    feature_set_version_id=uuid4(),
                )
            )

    def train_stub(*_args, **_kwargs):
        return SimpleNamespace(input_schema={})

    monkeypatch.setattr(reproduction, "build_task_dataset", build_matching_dataset)
    monkeypatch.setattr(
        reproduction,
        "chronological_group_split",
        lambda _dataset: SimpleNamespace(test=()),
    )
    monkeypatch.setattr(reproduction, "train_and_evaluate", train_stub)
    monkeypatch.setattr(reproduction, "ArtifactStore", FakeArtifactStore)
    with pytest.raises(reproduction.ReproductionError, match="REGISTERED_CANDIDATE_MISMATCH"):
        await reproduction.reproduce_supervised_run(
            FakeDatabase([None, record, None, None]), uuid4()
        )

    from vehicle_platform.ml.domain import ModelState

    candidate_checksum = "a" * 64
    record["comparison"]["challenger_artifact_checksum"] = candidate_checksum
    model_spec = reproduction.get_model_spec(definition.task)
    candidate = SimpleNamespace(
        model_version=SimpleNamespace(
            supervised_dataset_id=uuid4(),
            label_definition_id=uuid4(),
            feature_set_version_id=uuid4(),
            task=definition.task,
            state=ModelState.CANDIDATE,
            dataset_checksum=definition.expected_dataset_checksum,
            repository_sha=definition.git_sha,
            artifact_checksum=candidate_checksum,
        ),
        input_schema={},
        model_spec_checksum=model_spec.checksum,
    )
    registered_dataset = {
        "source_role": "synthetic",
        "source_fingerprint": definition.expected_source_fingerprint,
        "checksum": definition.expected_dataset_checksum,
        "label_checksum": model_spec.label_definition.checksum,
        "feature_checksum": definition.expected_feature_checksum,
    }

    class OversizedArtifactStore:
        def __init__(self, *_args):
            pass

        async def load_registered(self, _database, _candidate_id):
            return candidate

        def write(self, *_args, **_kwargs):
            return SimpleNamespace(size_bytes=2)

    training = SimpleNamespace(
        input_schema={},
        selected_model=object(),
        selected_threshold=0.5,
        selected_family=SimpleNamespace(value="logistic_regression"),
    )
    monkeypatch.setattr(reproduction, "train_and_evaluate", lambda *_args, **_kwargs: training)
    monkeypatch.setattr(reproduction, "ArtifactStore", OversizedArtifactStore)
    monkeypatch.setattr(
        reproduction,
        "chronological_group_split",
        lambda _dataset: SimpleNamespace(test=()),
    )
    bounded_definition = definition.model_copy(
        update={"budget": ResourceBudget(max_artifact_bytes=1)}
    )
    bounded_record = {
        **record,
        "definition_fingerprint": bounded_definition.fingerprint,
        "body": bounded_definition.model_dump(mode="json"),
        "comparison": {**record["comparison"]},
    }
    with pytest.raises(reproduction.ReproductionError, match="ARTIFACT_EXCEEDS_BUDGET"):
        await reproduction.reproduce_supervised_run(
            FakeDatabase([None, bounded_record, None, registered_dataset]), uuid4()
        )


@pytest.mark.asyncio
async def test_phase10_acceptance_reads_next_pull_binding_with_literal_kind(monkeypatch):
    import sys
    from importlib.util import module_from_spec, spec_from_file_location

    from vehicle_platform.ml.domain import MLTask

    def load_evaluator():
        evaluator_path = Path(__file__).resolve().parents[4] / "scripts" / "evaluate_mlops.py"
        monkeypatch.syspath_prepend(str(evaluator_path.parent))
        spec = spec_from_file_location("phase10_acceptance_runtime", evaluator_path)
        assert spec is not None and spec.loader is not None
        evaluator = module_from_spec(spec)
        sys.modules[spec.name] = evaluator
        spec.loader.exec_module(evaluator)
        return evaluator

    evaluator = load_evaluator()

    calls = []
    expected_binding = uuid4()

    class FakeRepository:
        async def bindings_for_slot(self, *args):
            calls.append(args)
            return [SimpleNamespace(is_active=True, id=expected_binding)]

    class FakeService:
        def __init__(self, *_args):
            self.repository = FakeRepository()

        async def close(self):
            return None

    monkeypatch.setattr(evaluator, "PredictionService", FakeService)
    binding = await evaluator._active_binding_id(object(), object(), MLTask.THERMAL_DEGRADATION)

    assert binding == expected_binding
    assert calls == [("next_pull", MLTask.THERMAL_DEGRADATION.value, SourceRole.SYNTHETIC, "test")]


def test_phase10_pipeline_contracts_enforce_task_oracle_and_gate_invariants():
    from datetime import timedelta, timezone

    from vehicle_platform.anomalies.domain import AnomalyFamily, DetectorMethod
    from vehicle_platform.ml.domain import MLTask
    from vehicle_platform.mlops.contracts import (
        EvaluationGate,
        GateState,
        PipelineDefinition,
        PipelineKind,
    )

    base = {
        "definition_version": "contract-validation-v1",
        "kind": PipelineKind.SUPERVISED,
        "task": MLTask.THERMAL_DEGRADATION,
        "source_role": SourceRole.SYNTHETIC,
        "cutoff": datetime(2026, 1, 1, tzinfo=UTC),
        "git_sha": "a" * 40,
        "expected_source_fingerprint": "b" * 64,
        "expected_dataset_checksum": "c" * 64,
        "expected_feature_checksum": "d" * 64,
        "evaluation_cutoff": datetime(2026, 1, 2, tzinfo=UTC),
        "training_pull_ids": (uuid4(),),
        "evaluation_pull_ids": (uuid4(),),
        "expected_evaluation_checksum": "e" * 64,
        "expected_evaluation_source_fingerprint": "f" * 64,
    }
    assert PipelineDefinition(**base).fingerprint
    with pytest.raises(ValidationError, match="bounded, disjoint training"):
        PipelineDefinition(**{**base, "training_pull_ids": ()})
    with pytest.raises(ValidationError, match="bounded, disjoint training"):
        PipelineDefinition(**{**base, "training_pull_ids": base["evaluation_pull_ids"]})
    with pytest.raises(ValidationError, match="bounded, disjoint training"):
        PipelineDefinition(
            **{
                **base,
                "training_pull_ids": tuple(sorted((uuid4(), uuid4()), key=str)),
                "budget": {"max_rows": 1},
            }
        )
    with pytest.raises(ValidationError, match="task only"):
        PipelineDefinition(**{**base, "family": AnomalyFamily.THERMAL})
    with pytest.raises(ValidationError, match="bounded, disjoint training"):
        PipelineDefinition(**{**base, "evaluation_cutoff": None})
    with pytest.raises(ValidationError, match="UTC"):
        PipelineDefinition(
            **{**base, "cutoff": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1)))}
        )

    anomaly = {
        **base,
        "kind": PipelineKind.ANOMALY,
        "task": None,
        "family": AnomalyFamily.THERMAL,
        "method": DetectorMethod.ROBUST_MAD,
        "anchor_pull_id": uuid4(),
        "training_pull_ids": (),
        "evaluation_cutoff": None,
        "evaluation_pull_ids": (),
        "expected_evaluation_checksum": None,
        "expected_evaluation_source_fingerprint": None,
    }
    assert PipelineDefinition(**anomaly).kind.value == "anomaly"
    with pytest.raises(ValidationError, match="family, method and anchor"):
        PipelineDefinition(**{**anomaly, "anchor_pull_id": None})
    with pytest.raises(ValidationError, match="cohort and oracle"):
        PipelineDefinition(**{**anomaly, "evaluation_pull_ids": (uuid4(),)})

    gate = {
        "name": "SCIENTIFIC_ELIGIBILITY",
        "status": GateState.PASS,
        "numerator": 1,
        "denominator": 1,
        "reason": "fixture support",
        "policy_version": "v1",
        "evidence_checksum": "a" * 64,
    }
    assert EvaluationGate(**gate).numerator == 1
    with pytest.raises(ValidationError, match="numerator exceeds"):
        EvaluationGate(**{**gate, "numerator": 2})


def test_mlops_cli_parser_and_manifest_reader_are_bounded(tmp_path):
    from vehicle_platform.mlops.cli import MAX_MANIFEST_BYTES, _read_manifest, parser

    manifest = tmp_path / "definition.json"
    manifest.write_bytes(b"{}")
    assert _read_manifest(manifest) == b"{}"
    assert parser().parse_args(["plan", "--manifest", str(manifest)]).command == "plan"
    assert parser().parse_args(["monitor", "--manifest", str(manifest)]).command == "monitor"
    assert parser().parse_args(["inspect", "--run-id", str(uuid4())]).command == "inspect"
    assert parser().parse_args(["reproduce", "--run-id", str(uuid4())]).command == "reproduce"
    assert parser().parse_args(["proposal", "--proposal-id", str(uuid4())]).command == "proposal"
    assert (
        parser()
        .parse_args(
            [
                "review",
                "--proposal-id",
                str(uuid4()),
                "--proposal-checksum",
                "a" * 64,
                "--decision",
                "accept",
                "--reason",
                "reviewed",
            ]
        )
        .command
        == "review"
    )
    assert (
        parser()
        .parse_args(
            ["rollback-plan", "--proposal-id", str(uuid4()), "--target-binding-id", str(uuid4())]
        )
        .command
        == "rollback-plan"
    )
    assert parser().parse_args(["rollback-inspect", "--plan-id", str(uuid4())]).command == (
        "rollback-inspect"
    )
    assert parser().parse_args(["run", "--manifest", str(manifest)]).command == "run"
    assert (
        parser()
        .parse_args(["resume", "--run-id", str(uuid4()), "--manifest", str(manifest)])
        .command
        == "resume"
    )

    manifest.write_bytes(b"x" * (MAX_MANIFEST_BYTES + 1))
    with pytest.raises(ValueError, match="bounded regular file"):
        _read_manifest(manifest)
    with pytest.raises(OSError):
        _read_manifest(tmp_path / "absent.json")
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(ValueError, match="bounded regular file"):
        _read_manifest(directory)
    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(directory)
    with pytest.raises(OSError):
        _read_manifest(symlink)


def test_mlops_report_store_is_exclusive_bounded_and_checksum_verified(monkeypatch, tmp_path):
    import hashlib

    from vehicle_platform.mlops import report_store

    monkeypatch.chdir(tmp_path)
    run_id = uuid4()
    checksum, size = report_store.write_report(run_id, {"status": "RECORDED"})
    assert size > 0
    assert report_store.read_report(run_id, expected_checksum=checksum) == {"status": "RECORDED"}
    with pytest.raises(FileExistsError):
        report_store.write_report(run_id, {"status": "REPLACEMENT"})
    with pytest.raises(ValueError, match="invalid report checksum"):
        report_store.read_report(run_id, expected_checksum="bad")
    with pytest.raises(ValueError, match="checksum mismatch"):
        report_store.read_report(run_id, expected_checksum="0" * 64)
    with pytest.raises(ValueError, match="JSON compliant"):
        report_store.write_report(uuid4(), {"unsafe": float("nan")})

    raw_id = uuid4()
    report_dir = Path("apps/api/.artifacts/phase10/reports")
    raw_payload = b"[]"
    raw_path = report_dir / f"{raw_id}.json"
    raw_path.write_bytes(raw_payload)
    raw_path.chmod(0o600)
    with pytest.raises(ValueError, match="root must be an object"):
        report_store.read_report(raw_id, expected_checksum=hashlib.sha256(raw_payload).hexdigest())

    failed_id = uuid4()
    original_fsync = report_store.os.fsync

    def fail_fsync(_descriptor):
        raise OSError("simulated fsync failure")

    monkeypatch.setattr(report_store.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="simulated fsync failure"):
        report_store.write_report(failed_id, {"status": "not-published"})
    assert not (report_dir / f"{failed_id}.json").exists()
    monkeypatch.setattr(report_store.os, "fsync", original_fsync)
    monkeypatch.setattr(report_store, "MAX_REPORT_BYTES", 2)
    with pytest.raises(ValueError, match="fixed size budget"):
        report_store.write_report(uuid4(), {"payload": "large"})


@pytest.mark.asyncio
async def test_mlops_cli_dispatches_plan_run_resume_and_monitor(monkeypatch, tmp_path):
    from vehicle_platform.mlops import cli

    monkeypatch.setattr(cli, "require_controlled_environment", lambda: "test")
    monkeypatch.setattr(cli, "Settings", lambda: object())

    class FakeDatabase:
        def __init__(self, *_args, **_kwargs):
            self.closed = False

        async def close(self):
            self.closed = True

    class FakeTelemetry:
        def __init__(self, *_args, **_kwargs):
            self.shutdown_called = False
            self.mlops_review_events = SimpleNamespace(add=lambda *_: None)
            self.mlops_rollback_plans = SimpleNamespace(add=lambda *_: None)

        def render_metrics(self):
            return b"# metrics\n"

        def shutdown(self):
            self.shutdown_called = True

    monkeypatch.setattr(cli, "Database", FakeDatabase)
    monkeypatch.setattr(cli, "Telemetry", FakeTelemetry)
    manifest = tmp_path / "definition.json"
    manifest.write_text(_supervised_definition().model_dump_json())
    protocol_file = tmp_path / "monitor.json"
    protocol_file.write_text(protocol().model_dump_json())
    calls = []

    async def plan(_database, definition):
        calls.append(("plan", definition.kind))
        return {"status": "BLOCKED"}

    async def run(_database, definition, **kwargs):
        calls.append(("run", kwargs["execute"]))
        return {"status": "COMPLETED", "execution": "STARTED"}

    async def resume(_database, definition, run_id, **kwargs):
        calls.append(("resume", run_id, kwargs["execute"]))
        return {"status": "IDEMPOTENT_REPLAY"}

    async def monitor(_database, definition, **kwargs):
        calls.append(("monitor", definition.binding_id))
        return {"status": "MONITORED"}

    monkeypatch.setattr(cli, "plan_supervised", plan)
    monkeypatch.setattr(cli, "plan_anomaly", plan)
    monkeypatch.setattr(cli, "run_pipeline", run)
    monkeypatch.setattr(cli, "resume_pipeline", resume)
    monkeypatch.setattr(cli, "monitor_receipts", monitor)
    base = {"metrics_file": None}

    planned, code = await cli._run(SimpleNamespace(**base, command="plan", manifest=manifest))
    assert planned["status"] == "BLOCKED" and code == 2
    run_result, code = await cli._run(
        SimpleNamespace(
            **base,
            command="run",
            manifest=manifest,
            execute=True,
            confirm_environment="test",
            fingerprint="f" * 64,
            champion_binding_id=None,
        )
    )
    assert run_result["status"] == "COMPLETED" and code == 0
    run_id = uuid4()
    resumed, code = await cli._run(
        SimpleNamespace(
            **base,
            command="resume",
            manifest=manifest,
            run_id=run_id,
            execute=False,
            confirm_environment=None,
            fingerprint=None,
            champion_binding_id=None,
        )
    )
    assert resumed["status"] == "IDEMPOTENT_REPLAY" and code == 0
    monitored, code = await cli._run(
        SimpleNamespace(**base, command="monitor", manifest=protocol_file)
    )
    assert monitored["status"] == "MONITORED" and code == 0
    assert [call[0] for call in calls] == ["plan", "run", "resume", "monitor"]


@pytest.mark.asyncio
async def test_mlops_cli_reviews_and_inspects_without_serving_actions(monkeypatch):
    from vehicle_platform.mlops import cli

    monkeypatch.setattr(cli, "require_controlled_environment", lambda: "test")
    monkeypatch.setattr(cli, "Settings", lambda: object())
    monkeypatch.setattr(
        cli, "Database", lambda *_args, **_kwargs: SimpleNamespace(close=AsyncMock())
    )

    class Counter:
        def add(self, *_args):
            pass

    class FakeTelemetry:
        def __init__(self, *_args, **_kwargs):
            self.mlops_review_events = Counter()
            self.mlops_rollback_plans = Counter()

        def shutdown(self):
            pass

        def render_metrics(self):
            return b"# metrics\n"

    monkeypatch.setattr(cli, "Telemetry", FakeTelemetry)
    calls = []

    class FakeRepository:
        def __init__(self, _database):
            pass

        async def inspect_run(self, run_id):
            calls.append(("inspect", run_id))
            return {"status": "INSPECTED"}

        async def inspect_proposal(self, proposal_id):
            calls.append(("proposal", proposal_id))
            return {"status": "PROPOSAL"}

        async def review_proposal(self, proposal_id, **kwargs):
            calls.append(("review", proposal_id, kwargs))
            return "ACCEPTED_FOR_REVIEW"

    monkeypatch.setattr(cli, "ControlPlaneRepository", FakeRepository)
    run_id, proposal_id = uuid4(), uuid4()
    inspect, code = await cli._run(
        SimpleNamespace(command="inspect", run_id=run_id, metrics_file=None)
    )
    assert inspect["status"] == "INSPECTED" and code == 0
    proposal, code = await cli._run(
        SimpleNamespace(command="proposal", proposal_id=proposal_id, metrics_file=None)
    )
    assert proposal["status"] == "PROPOSAL" and code == 0
    dry_review, code = await cli._run(
        SimpleNamespace(
            command="review",
            proposal_id=proposal_id,
            proposal_checksum="a" * 64,
            decision="accept",
            reason="reviewed",
            execute=False,
            metrics_file=None,
        )
    )
    assert dry_review["serving_action"] == "NONE" and code == 0
    assert dry_review["execution"] == "NOT_STARTED"
    monkeypatch.setattr(cli, "authenticated_reviewer", lambda: ("reviewer-1", "mlops_reviewer"))
    review, code = await cli._run(
        SimpleNamespace(
            command="review",
            proposal_id=proposal_id,
            proposal_checksum="a" * 64,
            decision="accept",
            reason="reviewed",
            execute=True,
            confirm_environment="test",
            confirm_proposal_checksum="a" * 64,
            metrics_file=None,
        )
    )
    assert review["status"] == "ACCEPTED_FOR_REVIEW" and code == 0
    assert review["serving_action"] == "NONE"
    with pytest.raises(ValueError, match="REVIEW_CONFIRMATION_MISMATCH"):
        await cli._run(
            SimpleNamespace(
                command="review",
                proposal_id=proposal_id,
                proposal_checksum="a" * 64,
                decision="accept",
                reason="reviewed",
                execute=True,
                confirm_environment="test",
                confirm_proposal_checksum="b" * 64,
                metrics_file=None,
            )
        )


@pytest.mark.asyncio
async def test_mlops_cli_rollback_paths_write_metrics_and_always_close(monkeypatch, tmp_path):
    from vehicle_platform.mlops import cli

    monkeypatch.setattr(cli, "require_controlled_environment", lambda: "test")
    monkeypatch.setattr(cli, "Settings", lambda: object())
    closed = []

    class FakeDatabase:
        def __init__(self, *_args, **_kwargs):
            pass

        async def close(self):
            closed.append(True)

    class Counter:
        def add(self, *_args):
            pass

    class FakeTelemetry:
        def __init__(self, *_args, **_kwargs):
            self.mlops_rollback_plans = Counter()
            self.mlops_review_events = Counter()

        def render_metrics(self):
            return b"# mlops metrics\n"

        def shutdown(self):
            pass

    monkeypatch.setattr(cli, "Database", FakeDatabase)
    monkeypatch.setattr(cli, "Telemetry", FakeTelemetry)
    monkeypatch.setattr(cli, "plan_rollback", AsyncMock(return_value={"status": "BLOCKED"}))
    monkeypatch.setattr(cli, "inspect_rollback_plan", AsyncMock(return_value={"status": "STALE"}))
    metrics = tmp_path / "metrics.prom"
    plan, code = await cli._run(
        SimpleNamespace(
            command="rollback-plan",
            proposal_id=uuid4(),
            target_binding_id=uuid4(),
            execute=False,
            confirm_environment=None,
            confirm_proposal_checksum=None,
            metrics_file=metrics,
        )
    )
    assert plan["status"] == "BLOCKED" and code == 0
    assert metrics.read_bytes() == b"# mlops metrics\n"
    inspected, code = await cli._run(
        SimpleNamespace(command="rollback-inspect", plan_id=uuid4(), metrics_file=None)
    )
    assert inspected["status"] == "STALE" and code == 2
    assert len(closed) == 2


def test_operator_auth_reads_private_owner_bound_config_and_authenticates_token(
    monkeypatch, tmp_path
):
    import hashlib
    import json

    from vehicle_platform.mlops.operator_auth import authenticated_reviewer

    token = "reviewer-secret-" + "x" * 32
    config = tmp_path / "reviewers.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": "phase10-review-auth-v1",
                "operators": [
                    {
                        "id": "operator-1",
                        "role": "mlops_reviewer",
                        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                    }
                ],
            }
        )
    )
    config.chmod(0o600)
    monkeypatch.setenv("MLOPS_REVIEWER_CONFIG", str(config))
    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", token)
    assert authenticated_reviewer() == ("operator-1", "mlops_reviewer")

    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", "wrong-token-that-is-long-enough-0000")
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()
    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", token)
    config.chmod(0o644)
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()


@pytest.mark.parametrize(
    "raw_config",
    (
        '{"schema_version":"wrong","operators":[]}',
        '{"schema_version":"phase10-review-auth-v1","operators":[]}',
        '{"schema_version":"phase10-review-auth-v1","operators":[null]}',
        '{"schema_version":"phase10-review-auth-v1","operators":[{"id":"r","role":"mlops_reviewer","token_sha256":"bad"}]}',
        '{"schema_version":"phase10-review-auth-v1","operators":[{"id":"reviewer-1","role":"observer","token_sha256":"'
        + "a" * 64
        + '"}]}',
        '{"schema_version":"phase10-review-auth-v1","operators":[{"id":"reviewer-1","role":"mlops_reviewer","token_sha256":"'
        + "a" * 64
        + '"},{"id":"reviewer-2","role":"mlops_reviewer","token_sha256":"'
        + "a" * 64
        + '"}]}',
    ),
)
def test_operator_auth_rejects_malformed_or_ambiguous_reviewer_config(
    monkeypatch, tmp_path, raw_config
):
    from vehicle_platform.mlops.operator_auth import authenticated_reviewer

    config = tmp_path / "reviewers.json"
    config.write_text(raw_config)
    config.chmod(0o600)
    monkeypatch.setenv("MLOPS_REVIEWER_CONFIG", str(config))
    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", "reviewer-secret-" + "x" * 32)
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()


def test_operator_auth_rejects_missing_or_unsafe_environment_and_duplicate_json_keys(
    monkeypatch, tmp_path
):
    from vehicle_platform.mlops.operator_auth import authenticated_reviewer

    monkeypatch.delenv("MLOPS_REVIEWER_CONFIG", raising=False)
    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", "reviewer-secret-" + "x" * 32)
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()
    monkeypatch.setenv("MLOPS_REVIEWER_CONFIG", str(tmp_path / "missing.json"))
    monkeypatch.delenv("MLOPS_OPERATOR_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()
    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", "short")
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()
    monkeypatch.setenv("MLOPS_OPERATOR_TOKEN", "reviewer-secret-" + "x" * 32)
    monkeypatch.setenv("MLOPS_REVIEWER_CONFIG", "relative.json")
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"phase10-review-auth-v1","schema_version":"phase10-review-auth-v1",'
        '"operators":[]}'
    )
    duplicate.chmod(0o600)
    monkeypatch.setenv("MLOPS_REVIEWER_CONFIG", str(duplicate))
    with pytest.raises(RuntimeError, match="authentication is unavailable"):
        authenticated_reviewer()


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def one_or_none(self):
        return self.rows

    def all(self):
        return self.rows


class Session:
    def __init__(self, binding, baseline, comparison):
        self.results = [Result(None), Result(binding), Result(baseline), Result(comparison)]
        self.parameters = []
        self.statements = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def begin(self):
        return self

    async def execute(self, statement, parameters=None):
        self.statements.append(str(statement))
        self.parameters.append(parameters)
        return self.results.pop(0)


def protocol():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return MonitoringProtocol(
        binding_id=uuid4(),
        vehicle_id=uuid4(),
        configuration_id=uuid4(),
        source_role=SourceRole.SYNTHETIC,
        baseline_start=start,
        baseline_end=start + timedelta(days=1),
        comparison_start=start + timedelta(days=1),
        comparison_end=start + timedelta(days=2),
        minimum_rows=2,
        minimum_sessions=2,
        max_rows_per_window=4,
        psi_bins=2,
        feature_keys=("thermal.iat_delta_k",),
    )


def receipt(score, session):
    return {
        "id": uuid4(),
        "session_id": session,
        "status": "READY_SCORE" if score is not None else "ABSTAINED_LOW_QUALITY",
        "engineering_validation_score": score,
        "anomaly_score": None,
        "coverage": 0.5 if score is None else 1.0,
        "effective_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "observed_end": datetime(2026, 1, 1, tzinfo=UTC),
        "source_role": "synthetic",
        "source_type": "synthetic",
        "feature_set_version": "v1",
        "receipt_feature_source_checksum": "e" * 64,
        "feature_source_checksum": "e" * 64,
        "stored_feature_set_version": "v1",
        "feature_version_checksum": "f" * 64,
        "quality_summary": {"missing_reason_counts": {}},
        "feature_quality_metadata": {"signal_coverage": {"engine.intake_air_temperature": 1.0}},
        "selected_features": {
            "thermal.iat_delta_k": {
                "value": score * 10 if score is not None else None,
                "unit": "K",
                "quality": "valid" if score is not None else "unavailable",
                "missing_reason": None if score is not None else "unavailable_signal",
            }
        },
    }


@pytest.mark.asyncio
async def test_monitor_counts_actual_receipts_and_preserves_missing_label_uncertainty(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    policy = protocol()
    one, two = uuid4(), uuid4()
    binding = {
        "source_role": "synthetic",
        "result_kind": "next_pull",
        "subject_key": "task",
        "feature_set_version": "v1",
        "feature_set_checksum": "f" * 64,
        "environment": "test",
    }
    session = Session(
        binding,
        [receipt(0.1, one), receipt(0.2, two), receipt(None, two)],
        [receipt(0.8, one), receipt(0.9, two), receipt(None, one)],
    )
    result = await monitor_receipts(SimpleNamespace(session=lambda: session), policy)
    assert result["windows"]["baseline"]["receipts"] == 3
    assert result["windows"]["baseline"]["scored"] == 2
    assert result["windows"]["baseline"]["abstained"] == 1
    assert result["windows"]["comparison"]["sessions"] == 2
    assert result["score_distribution_shift"]["status"] == "WARNING"
    assert result["performance_drift"]["status"] == "UNKNOWN"
    assert result["performance_drift"]["value"] is None
    assert (
        result["feature_distribution_shift"]["features"]["thermal.iat_delta_k"]["status"]
        == "WARNING"
    )
    assert result["real_world_predictive_validity"] == "NOT_ESTABLISHED"
    assert result["serving_action"] == "NONE"
    assert session.parameters[2]["vehicle"] == policy.vehicle_id
    assert session.parameters[2]["configuration"] == policy.configuration_id
    assert "s.source_type" in session.statements[2]
    assert "p.source_type" not in session.statements[2]


@pytest.mark.asyncio
async def test_monitor_empty_window_does_not_report_healthy_or_zero_accuracy(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    binding = {
        "source_role": "synthetic",
        "result_kind": "next_pull",
        "subject_key": "task",
        "feature_set_version": "v1",
        "feature_set_checksum": "f" * 64,
        "environment": "test",
    }
    session = Session(binding, [], [])
    result = await monitor_receipts(SimpleNamespace(session=lambda: session), protocol())
    assert result["windows"]["baseline"]["status"] == "NO_OBSERVATIONS"
    assert result["windows"]["baseline"]["mean_feature_coverage"] is None
    assert result["score_distribution_shift"]["psi"] is None
    assert result["performance_drift"]["value"] is None


@pytest.mark.asyncio
async def test_monitor_requires_independent_scored_sessions_for_drift(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    binding = {
        "source_role": "synthetic",
        "result_kind": "next_pull",
        "subject_key": "task",
        "feature_set_version": "v1",
        "feature_set_checksum": "f" * 64,
        "environment": "test",
    }
    one, two = uuid4(), uuid4()
    window = [receipt(0.1, one), receipt(0.2, one), receipt(None, two)]
    session = Session(binding, window, window)
    result = await monitor_receipts(SimpleNamespace(session=lambda: session), protocol())
    assert result["windows"]["baseline"]["status"] == "OBSERVED"
    assert result["windows"]["baseline"]["scored_sessions"] == 1
    assert result["score_distribution_shift"]["status"] == "INSUFFICIENT_SUPPORT"
    assert result["score_distribution_shift"]["psi"] is None


@pytest.mark.asyncio
async def test_monitor_rejects_binding_from_another_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    binding = {"source_role": "synthetic", "environment": "production"}
    session = Session(binding, [], [])
    with pytest.raises(ValueError, match="environment mismatch"):
        await monitor_receipts(SimpleNamespace(session=lambda: session), protocol())


@pytest.mark.asyncio
async def test_monitor_all_abstentions_are_not_scored_observations(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    binding = {
        "source_role": "synthetic",
        "environment": "test",
        "result_kind": "next_pull",
        "subject_key": "task",
        "feature_set_version": "v1",
        "feature_set_checksum": "f" * 64,
    }
    rows = [receipt(None, uuid4()), receipt(None, uuid4())]
    session = Session(binding, rows, rows)
    result = await monitor_receipts(SimpleNamespace(session=lambda: session), protocol())
    assert result["windows"]["baseline"]["status"] == "NO_OBSERVATIONS"
    assert result["windows"]["baseline"]["abstained"] == 2
    assert result["score_distribution_shift"]["psi"] is None


def test_monitor_protocol_rejects_future_overlap_and_environment_fails_closed(monkeypatch):
    policy = protocol()
    with pytest.raises(ValidationError):
        MonitoringProtocol(**{**policy.model_dump(), "comparison_start": policy.baseline_start})
    for value in ("production", "", "unknown"):
        monkeypatch.setenv("ENVIRONMENT", value)
        with pytest.raises(RuntimeError):
            require_controlled_environment()
    monkeypatch.delenv("ENVIRONMENT")
    with pytest.raises(RuntimeError):
        require_controlled_environment()


def test_monitoring_protocol_rejects_non_utc_long_or_inconsistent_contracts(monkeypatch):
    from datetime import timezone

    from vehicle_platform.features.domain import FeatureDType
    from vehicle_platform.mlops import monitoring

    base = protocol().model_dump()
    with pytest.raises(ValidationError, match="UTC"):
        MonitoringProtocol(
            **{
                **base,
                "baseline_start": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1))),
            }
        )
    with pytest.raises(ValidationError, match="one year"):
        MonitoringProtocol(
            **{
                **base,
                "comparison_start": datetime(2026, 1, 2, tzinfo=UTC),
                "comparison_end": datetime(2027, 1, 3, tzinfo=UTC),
            }
        )
    with pytest.raises(ValidationError, match="support exceeds"):
        MonitoringProtocol(**{**base, "minimum_rows": 3, "max_rows_per_window": 2})
    with pytest.raises(ValidationError, match="unique and sorted"):
        MonitoringProtocol(
            **{**base, "feature_keys": ("thermal.iat_delta_k", "thermal.iat_delta_k")}
        )
    monkeypatch.setattr(
        monitoring,
        "DEFAULT_REGISTRY",
        SimpleNamespace(resolve=lambda _key: SimpleNamespace(dtype=FeatureDType.BOOLEAN)),
    )
    with pytest.raises(ValidationError, match="must be numeric"):
        MonitoringProtocol(**{**base, "feature_keys": ("fixture.boolean",)})


@pytest.mark.asyncio
async def test_monitoring_enforces_row_cutoff_score_and_scope_guards(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    policy = protocol()
    binding = {
        "source_role": "synthetic",
        "result_kind": "next_pull",
        "subject_key": "task",
        "feature_set_version": "v1",
        "feature_set_checksum": "f" * 64,
        "environment": "test",
    }

    with pytest.raises(ValueError, match="row budget"):
        await monitor_receipts(
            SimpleNamespace(session=lambda: Session(binding, [receipt(0.1, uuid4())] * 5, [])),
            policy,
        )
    late = receipt(0.1, uuid4())
    late["effective_cutoff"] = late["created_at"] + timedelta(seconds=1)
    with pytest.raises(ValueError, match="CUTOFF_LEAKAGE"):
        await monitor_receipts(
            SimpleNamespace(session=lambda: Session(binding, [late], [])), policy
        )
    missing_score = receipt(None, uuid4())
    missing_score["status"] = "READY_SCORE"
    with pytest.raises(ValueError, match="missing its score"):
        await monitor_receipts(
            SimpleNamespace(session=lambda: Session(binding, [missing_score], [])), policy
        )
    non_finite = receipt(float("nan"), uuid4())
    with pytest.raises(ValueError, match="finite"):
        await monitor_receipts(
            SimpleNamespace(session=lambda: Session(binding, [non_finite], [])), policy
        )
    wrong_role = {**binding, "source_role": "imported"}
    with pytest.raises(ValueError, match="source role/environment mismatch"):
        await monitor_receipts(SimpleNamespace(session=lambda: Session(wrong_role, [], [])), policy)


@pytest.mark.asyncio
async def test_monitoring_reports_feature_source_missingness_and_role_drift(monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setenv("ENVIRONMENT", "test")
    policy = MonitoringProtocol(
        **{**protocol().model_dump(), "minimum_rows": 2, "minimum_sessions": 2}
    )
    binding = {
        "source_role": "synthetic",
        "result_kind": "next_pull",
        "subject_key": "task",
        "feature_set_version": "v1",
        "feature_set_checksum": "f" * 64,
        "environment": "test",
    }
    base = [receipt(0.1, uuid4()), receipt(0.2, uuid4())]
    comparison = [receipt(0.8, uuid4()), receipt(0.9, uuid4())]
    for row in base:
        row["feature_set_version"] = "legacy"
        row["stored_feature_set_version"] = "legacy"
        row["feature_version_checksum"] = "a" * 64
        row["feature_source_checksum"] = "b" * 64
        row["receipt_feature_source_checksum"] = "c" * 64
        item = row["selected_features"]["thermal.iat_delta_k"]
        item["unit"] = "invalid-unit"
        item["value"] = True
        row["quality_summary"] = {"missing_reason_counts": {"sensor_absent": -1}}
        row["feature_quality_metadata"] = {
            "signal_coverage": {"engine.intake_air_temperature": True}
        }
    for row in comparison:
        row["source_role"] = "imported"
        row["source_type"] = "imported"

    class Span:
        def set_attribute(self, *_args):
            pass

    findings = []

    class Counter:
        def add(self, value, attributes):
            findings.append((value, attributes))

    class Duration:
        def record(self, _value):
            pass

    telemetry = SimpleNamespace(
        tracer=SimpleNamespace(start_as_current_span=lambda _name: nullcontext(Span())),
        mlops_monitor_findings=Counter(),
        mlops_monitor_duration=Duration(),
    )
    result = await monitor_receipts(
        SimpleNamespace(session=lambda: Session(binding, base, comparison)),
        policy,
        telemetry=telemetry,
    )
    assert result["feature_source_drift"]["status"] == "WARNING"
    assert result["feature_source_drift"]["feature_version_mismatches"]["baseline"] == 2
    assert result["feature_source_drift"]["feature_checksum_mismatches"]["baseline"] == 2
    assert result["source_role_drift"]["mismatched_receipts"] == 2
    assert (
        result["windows"]["baseline"]["feature_missingness"]["thermal.iat_delta_k"]["missing"] == 2
    )
    assert len(findings) >= 1


def test_report_store_detects_tampering_and_rejects_overwrite_and_symlink(tmp_path, monkeypatch):
    from vehicle_platform.mlops.report_store import read_report, write_report

    monkeypatch.chdir(tmp_path)
    report_id = uuid4()
    checksum, length = write_report(report_id, {"score": 0.5, "status": "SYNTHETIC_ONLY"})
    assert length > 0
    assert read_report(report_id, expected_checksum=checksum)["score"] == 0.5
    with pytest.raises(FileExistsError):
        write_report(report_id, {"score": 0.6})
    path = tmp_path / "apps" / "api" / ".artifacts" / "phase10" / "reports" / f"{report_id}.json"
    path.write_text('{"score":0.6}')
    with pytest.raises(ValueError, match="checksum"):
        read_report(report_id, expected_checksum=checksum)
    target = tmp_path / "outside"
    target.mkdir()
    path.unlink()
    path.symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        read_report(report_id, expected_checksum=checksum)


def test_report_store_rejects_symlinked_ancestor(tmp_path, monkeypatch):
    from vehicle_platform.mlops.report_store import write_report

    monkeypatch.chdir(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "apps").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        write_report(uuid4(), {"value": 1})
    assert list(outside.iterdir()) == []


@pytest.mark.asyncio
async def test_prior_holdout_overlap_and_missing_history_fail_closed(monkeypatch):
    from vehicle_platform.features.domain import stable_hash
    from vehicle_platform.mlops.holdout import prior_holdout_conflict

    class HoldoutSession:
        def __init__(self, responses):
            self.responses = iter(responses)
            self.parameters = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def begin(self):
            return self

        async def execute(self, _statement, _parameters=None):
            return None

        async def scalar(self, _statement, parameters):
            self.parameters.append(parameters)
            return next(self.responses)

    monkeypatch.setenv("ENVIRONMENT", "test")
    row = SimpleNamespace(
        row_id="a" * 64,
        session_id="session",
        vehicle_id="vehicle",
        configuration_id="configuration",
        input_pull_id="input",
        target_pull_id="target",
    )
    # Row IDs do not overlap, but a shared physical session does.
    session = HoldoutSession([False, False, False, True])
    reason = await prior_holdout_conflict(SimpleNamespace(session=lambda: session), [row])
    assert reason == "PRIOR_RESERVED_HOLDOUT_OVERLAP"
    assert session.parameters[-1]["values"] == [stable_hash("session")]
    session = HoldoutSession([True])
    reason = await prior_holdout_conflict(SimpleNamespace(session=lambda: session), [row])
    assert reason == "HOLDOUT_HISTORY_UNVERIFIABLE"


@pytest.mark.asyncio
async def test_comparison_denies_missing_or_wrong_scope_champion(monkeypatch):
    from vehicle_platform.ml.domain import MLTask
    from vehicle_platform.mlops import comparison
    from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(comparison, "checkout_is_dirty", AsyncMock(return_value=False))
    definition = PipelineDefinition(
        definition_version="comparison-test-v1",
        kind=PipelineKind.SUPERVISED,
        task=MLTask.THERMAL_DEGRADATION,
        source_role=SourceRole.SYNTHETIC,
        cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="a" * 40,
        expected_source_fingerprint="b" * 64,
        expected_dataset_checksum="c" * 64,
        expected_feature_checksum="d" * 64,
        evaluation_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
        training_pull_ids=(uuid4(),),
        evaluation_pull_ids=(uuid4(),),
        expected_evaluation_checksum="e" * 64,
        expected_evaluation_source_fingerprint="f" * 64,
    )
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(
        comparison, "PredictionRepository", lambda _: SimpleNamespace(binding=lookup)
    )
    args = {"champion_binding_id": uuid4(), "challenger_version_id": uuid4()}
    result = await comparison.compare_supervised(object(), definition, **args)
    assert result["reason"] == "NO_ACTIVE_CHAMPION"
    assert result["serving_action"] == "NONE"
    lookup.return_value = SimpleNamespace(
        is_active=True,
        model_version_id=uuid4(),
        environment="production",
        scope="controlled",
        result_kind="next_pull",
        source_role=SourceRole.SYNTHETIC,
        subject_key=definition.task.value,
    )
    result = await comparison.compare_supervised(object(), definition, **args)
    assert result["reason"] == "CHAMPION_SCOPE_MISMATCH"
    assert result["real_world_predictive_validity"] == "NOT_ESTABLISHED"


@pytest.mark.asyncio
async def test_inspect_returns_bounded_receipts_without_lease_secret(monkeypatch):
    from vehicle_platform.mlops.repository import ControlPlaneConflict, ControlPlaneRepository

    monkeypatch.setenv("ENVIRONMENT", "test")
    run = {"id": uuid4(), "state": "FAILED", "fencing_token": 2}
    session = Session(run, [{"to_state": "FAILED"}], [{"state": "SUCCEEDED"}])
    report = await ControlPlaneRepository(SimpleNamespace(session=lambda: session)).inspect_run(
        run["id"]
    )
    assert report["run"]["state"] == "FAILED"
    assert "lease_token" not in report["run"]
    assert report["serving_action"] == "NONE"
    session = Session(run, [{}] * 1001, [])
    with pytest.raises(ControlPlaneConflict, match="bound"):
        await ControlPlaneRepository(SimpleNamespace(session=lambda: session)).inspect_run(
            run["id"]
        )


@pytest.mark.asyncio
async def test_supervised_training_enforces_budget_before_registry_writes(monkeypatch):
    from vehicle_platform.ml import pipeline
    from vehicle_platform.ml.domain import MLTask

    dataset = SimpleNamespace(
        checksum="a" * 64,
        source_fingerprint="b" * 64,
        rows=(SimpleNamespace(session_id="one"), SimpleNamespace(session_id="two")),
    )
    materialize = AsyncMock(return_value=(dataset, object(), object()))
    registry = SimpleNamespace(ensure_definitions=AsyncMock())
    monkeypatch.setattr(pipeline, "build_task_dataset", materialize)
    monkeypatch.setattr(pipeline, "MLRegistry", lambda _: registry)
    options = {
        "source": "synthetic",
        "git_sha": "c" * 40,
        "candidate_pull_ids": (uuid4(),),
        "expected_dataset_checksum": dataset.checksum,
        "expected_source_fingerprint": dataset.source_fingerprint,
    }
    with pytest.raises(ValueError, match="specification exceeds"):
        await pipeline.train_task(
            None,
            MLTask.THERMAL_DEGRADATION,
            datetime(2026, 1, 1, tzinfo=UTC),
            **options,
            max_features=1,
        )
    materialize.assert_not_awaited()
    with pytest.raises(ValueError, match="sessions exceed"):
        await pipeline.train_task(
            None,
            MLTask.THERMAL_DEGRADATION,
            datetime(2026, 1, 1, tzinfo=UTC),
            **options,
            max_sessions=1,
        )
    assert materialize.await_args is not None
    assert materialize.await_args.kwargs["candidate_pull_ids"] == options["candidate_pull_ids"]
    registry.ensure_definitions.assert_not_awaited()


@pytest.mark.asyncio
async def test_supervised_worker_records_rejection_and_fit_failure(monkeypatch):
    from vehicle_platform.ml.domain import MLTask, ModelState
    from vehicle_platform.mlops import executor
    from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind

    monkeypatch.setenv("ENVIRONMENT", "test")
    definition = PipelineDefinition(
        definition_version="supervised-worker-v1",
        kind=PipelineKind.SUPERVISED,
        task=MLTask.THERMAL_DEGRADATION,
        source_role=SourceRole.SYNTHETIC,
        cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="a" * 40,
        expected_source_fingerprint="b" * 64,
        expected_dataset_checksum="c" * 64,
        expected_feature_checksum="d" * 64,
        evaluation_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
        training_pull_ids=(uuid4(),),
        evaluation_pull_ids=(uuid4(),),
        expected_evaluation_checksum="e" * 64,
        expected_evaluation_source_fingerprint="f" * 64,
    )
    record = AsyncMock()
    train = AsyncMock(
        return_value=SimpleNamespace(
            training=SimpleNamespace(
                state=ModelState.REJECTED,
                acceptance={"criteria": {"support": False, "integrity": True}},
            )
        )
    )
    monkeypatch.setattr(executor, "checkout_is_dirty", AsyncMock(return_value=False))
    monkeypatch.setattr(executor, "train_task", train)
    monkeypatch.setattr(
        executor, "ControlPlaneRepository", lambda _: SimpleNamespace(record_step=record)
    )
    options = {"run_id": uuid4(), "token": uuid4(), "fence": 1}
    with pytest.raises(ValueError, match="CANDIDATE_REJECTED"):
        await executor.execute_supervised_job(None, definition, **options)
    assert [call.kwargs["state"] for call in record.await_args_list] == ["RUNNING", "FAILED"]
    assert record.await_args_list[-1].kwargs["output"]["reason"] == "CANDIDATE_REJECTED"
    assert record.await_args_list[-1].kwargs["output"]["failed_criteria"] == ["support"]
    assert train.await_args.kwargs["max_artifact_bytes"] == definition.budget.max_artifact_bytes
    assert train.await_args.kwargs["candidate_pull_ids"] == definition.training_pull_ids
    record.reset_mock()
    train.side_effect = RuntimeError("private source details")
    with pytest.raises(RuntimeError, match="private source details"):
        await executor.execute_supervised_job(None, definition, **options)
    assert record.await_args_list[-1].kwargs["output"] == {"reason": "FIT_FAILED"}


def _supervised_definition(version: str = "runner-test-v1"):
    from vehicle_platform.ml.domain import MLTask
    from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind

    return PipelineDefinition(
        definition_version=version,
        kind=PipelineKind.SUPERVISED,
        task=MLTask.THERMAL_DEGRADATION,
        source_role=SourceRole.SYNTHETIC,
        cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="a" * 40,
        expected_source_fingerprint="b" * 64,
        expected_dataset_checksum="c" * 64,
        expected_feature_checksum="d" * 64,
        evaluation_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
        training_pull_ids=(uuid4(),),
        evaluation_pull_ids=(uuid4(),),
        expected_evaluation_checksum="e" * 64,
        expected_evaluation_source_fingerprint="f" * 64,
    )


@pytest.mark.asyncio
async def test_supervised_materialization_uses_only_versioned_training_or_evaluation_ids(
    monkeypatch,
):
    from vehicle_platform.mlops import planner

    monkeypatch.setenv("ENVIRONMENT", "test")
    calls = []

    class Builder:
        async def build(self, definition, *, candidate_pull_ids, persist, max_rows):
            calls.append((tuple(candidate_pull_ids), persist, max_rows))
            return SimpleNamespace(
                candidates=tuple(SimpleNamespace(pull_id=pull_id) for pull_id in candidate_pull_ids)
            )

    monkeypatch.setattr(planner, "DatasetBuilder", lambda *_: Builder())
    monkeypatch.setattr(planner, "build_supervised_dataset", lambda *_args, **_kwargs: "dataset")
    definition = _supervised_definition()

    assert (
        await planner.materialize_supervised_readonly(object(), definition, evaluation=False)
        == "dataset"
    )
    assert len(calls) == 2
    assert all(call[0] == definition.training_pull_ids for call in calls)
    assert all(call[1] is False for call in calls)

    calls.clear()
    assert (
        await planner.materialize_supervised_readonly(object(), definition, evaluation=True)
        == "dataset"
    )
    assert len(calls) == 2
    assert all(call[0] == definition.evaluation_pull_ids for call in calls)

    class IncompleteBuilder(Builder):
        async def build(self, dataset_definition, *, candidate_pull_ids, persist, max_rows):
            calls.append((tuple(candidate_pull_ids), persist, max_rows))
            return SimpleNamespace(candidates=())

    monkeypatch.setattr(planner, "DatasetBuilder", lambda *_: IncompleteBuilder())
    with pytest.raises(ValueError, match="TRAINING_COHORT_MISMATCH"):
        await planner.materialize_supervised_readonly(object(), definition, evaluation=False)


@pytest.mark.asyncio
async def test_runner_is_dry_by_default_and_checks_exact_confirmation(monkeypatch):
    from vehicle_platform.mlops import runner

    monkeypatch.setenv("ENVIRONMENT", "test")
    definition = _supervised_definition()
    plan = AsyncMock(return_value={"status": "READY_TO_REVIEW"})
    repository = AsyncMock()
    monkeypatch.setattr(runner, "plan_supervised", plan)
    monkeypatch.setattr(runner, "ControlPlaneRepository", lambda _: repository)
    output = await runner.run_pipeline(object(), definition)
    assert output["execution"] == "NOT_STARTED"
    repository.create_run.assert_not_awaited()
    with pytest.raises(ValueError, match="EXECUTION_CONFIRMATION_MISMATCH"):
        await runner.run_pipeline(
            object(),
            definition,
            execute=True,
            confirmed_environment="development",
            confirmed_fingerprint=definition.fingerprint,
        )
    repository.create_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_exact_completed_run_replays_before_replanning(monkeypatch):
    from vehicle_platform.mlops import runner

    monkeypatch.setenv("ENVIRONMENT", "test")
    definition = _supervised_definition("runner-replay-v1")
    run_id = uuid4()
    repository = AsyncMock()
    repository.find_exact_run.return_value = {
        "run_id": run_id,
        "state": "COMPLETED",
        "has_steps": True,
    }
    planner = AsyncMock(side_effect=AssertionError("completed replay must not replan"))
    monkeypatch.setattr(runner, "ControlPlaneRepository", lambda _: repository)
    monkeypatch.setattr(runner, "plan_supervised", planner)

    result = await runner.run_pipeline(
        object(),
        definition,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
    )

    assert result == {
        "schema_version": "phase10-run-v1",
        "status": "EXISTING_RUN",
        "run_id": str(run_id),
        "state": "COMPLETED",
        "idempotent_replay": True,
        "serving_action": "NONE",
        "real_world_predictive_validity": "NOT_ESTABLISHED",
    }
    repository.find_exact_run.assert_awaited_once_with(definition)
    planner.assert_not_awaited()


@pytest.mark.asyncio
async def test_runner_completes_only_with_artifact_evaluation_and_review_receipts(
    monkeypatch, tmp_path
):
    from vehicle_platform.mlops import runner

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.chdir(tmp_path)
    definition = _supervised_definition("runner-execute-v1")
    run_id, token, version_id = uuid4(), uuid4(), uuid4()
    plan = {
        "status": "READY_TO_REVIEW",
        "reason": "PRECONDITIONS_MET",
        "dataset_checksum": "1" * 64,
        "evaluation_dataset_checksum": "2" * 64,
        "labeled_rows": 80,
        "evaluation_rows": 60,
        "feature_checksum": "3" * 64,
        "feature_set_version": "phase9a-pull-v2",
        "label_checksum": "4" * 64,
        "source_fingerprint": "5" * 64,
        "evaluation_source_fingerprint": "6" * 64,
    }

    class Repository:
        def __init__(self, _database):
            self.steps = []
            self.proposal_body = None

        async def find_exact_run(self, _definition):
            return None

        async def create_run(self, _definition):
            return run_id, True

        async def claim(self, _run_id):
            return token, 1

        async def transition(self, *_args, **_kwargs):
            return None

        async def record_step(self, **kwargs):
            self.steps.append(kwargs)

        async def create_proposal(self, *_args, **kwargs):
            self.proposal_body = kwargs["body"]
            return uuid4(), "c" * 64, True

        async def complete_run(self, *_args, **_kwargs):
            return None

    repository = Repository(None)
    result = {
        "model_version_id": str(version_id),
        "artifact_checksum": "7" * 64,
        "report_file_checksum": "8" * 64,
        "evaluation_report_checksum": "9" * 64,
        "scientific_readiness": {"synthetic_calibration": "SYNTHETIC_ONLY"},
    }
    monkeypatch.setattr(runner, "plan_supervised", AsyncMock(return_value=plan))
    monkeypatch.setattr(runner, "ControlPlaneRepository", lambda _: repository)
    monkeypatch.setattr(runner, "execute_supervised_job", AsyncMock(return_value=result))
    monkeypatch.setattr(
        runner,
        "compare_supervised",
        AsyncMock(return_value={"status": "NOT_COMPARABLE", "reason": "NO_CHAMPION"}),
    )
    output = await runner.run_pipeline(
        object(),
        definition,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
    )
    assert output["status"] == "COMPLETED"
    assert output["serving_action"] == "NONE"
    assert output["real_world_predictive_validity"] == "NOT_ESTABLISHED"
    assert [row["name"] for row in repository.steps if row["state"] == "RUNNING"] == [
        "select",
        "validate",
        "compare",
        "report",
    ]
    assert repository.steps[-1]["output"]["serving_permission"] is False


@pytest.mark.asyncio
async def test_anomaly_runner_fits_evaluates_and_reports_without_serving(monkeypatch, tmp_path):
    import json

    from vehicle_platform.features.domain import stable_hash
    from vehicle_platform.mlops import runner
    from vehicle_platform.mlops.contracts import (
        AnomalyOracleLabel,
        PipelineDefinition,
        PipelineKind,
    )

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.chdir(tmp_path)
    pull_ids = tuple(sorted((uuid4(), uuid4(), uuid4(), uuid4()), key=str))
    labels = tuple(
        AnomalyOracleLabel(pull_id=pull_id, scenario="clean" if index < 2 else "thermal")
        for index, pull_id in enumerate(pull_ids)
    )
    definition = PipelineDefinition(
        definition_version="anomaly-runner-v1",
        kind=PipelineKind.ANOMALY,
        family="thermal",
        method="robust_mad",
        anchor_pull_id=uuid4(),
        source_role=SourceRole.SYNTHETIC,
        cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="a" * 40,
        expected_source_fingerprint="b" * 64,
        expected_dataset_checksum="c" * 64,
        expected_feature_checksum="d" * 64,
        evaluation_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
        evaluation_pull_ids=pull_ids,
        expected_evaluation_checksum="e" * 64,
        expected_evaluation_source_fingerprint="f" * 64,
        evaluation_oracle=labels,
        expected_oracle_checksum=stable_hash([item.model_dump(mode="json") for item in labels]),
    )
    run_id, token, detector_id = uuid4(), uuid4(), uuid4()
    plan = {
        "status": "READY_TO_REVIEW",
        "reason": "REFERENCE_PRECONDITIONS_MET",
        "reference_checksum": "1" * 64,
        "evaluation_dataset_checksum": "e" * 64,
        "reference_rows": 80,
        "reference_sessions": 12,
        "evaluation_rows": 4,
        "feature_checksum": "d" * 64,
        "feature_set_version": "phase9a-pull-v2",
        "label_checksum": definition.expected_oracle_checksum,
        "source_fingerprint": "b" * 64,
        "evaluation_source_fingerprint": "f" * 64,
    }

    class Repository:
        def __init__(self, _database):
            self.steps = []
            self.final_state = None
            self.proposal_body = None

        async def find_exact_run(self, _definition):
            return None

        async def create_run(self, _definition):
            return run_id, True

        async def claim(self, _run_id):
            return token, 1

        async def transition(self, _run_id, **kwargs):
            self.final_state = kwargs.get("target")

        async def record_step(self, **kwargs):
            self.steps.append(kwargs)

        async def create_proposal(self, *_args, **kwargs):
            self.proposal_body = kwargs["body"]
            return uuid4(), "c" * 64, True

        async def complete_run(self, *_args, **_kwargs):
            self.final_state = "COMPLETED"

    repository = Repository(None)
    monkeypatch.setattr(runner, "plan_anomaly", AsyncMock(return_value=plan))
    monkeypatch.setattr(runner, "ControlPlaneRepository", lambda _: repository)
    monkeypatch.setattr(
        runner,
        "execute_anomaly_fit_job",
        AsyncMock(
            return_value={
                "detector_version_id": str(detector_id),
                "artifact_checksum": "9" * 64,
                "serving_action": "NONE",
            }
        ),
    )
    monkeypatch.setattr(
        runner,
        "evaluate_anomaly_job",
        AsyncMock(
            return_value={
                "evaluation_status": "SYNTHETIC_EVALUATED",
                "scientific_readiness": "SYNTHETIC_ONLY",
                "report_content_checksum": "a" * 64,
                "report_file_checksum": "b" * 64,
                "report_bytes": 2048,
                "evaluation_dataset_checksum": "e" * 64,
                "evaluation_source_fingerprint": "f" * 64,
                "evaluation_summary": {
                    "target_metrics": {"precision": 0.8, "recall": 0.7},
                    "support": {"rows": 4, "scored": 4, "abstained": 0},
                    "cross_family_alerts": {
                        "boost_air": {"support": 2, "alarms": 0},
                        "fuel": {"support": 2, "alarms": 0},
                        "performance": {"support": 2, "alarms": 0},
                    },
                },
            }
        ),
    )
    monkeypatch.setattr(
        runner,
        "compare_anomaly",
        AsyncMock(return_value={"status": "NOT_COMPARABLE", "reason": "NO_CHAMPION"}),
    )
    result = await runner.run_pipeline(
        object(),
        definition,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
    )
    assert result["status"] == "COMPLETED"
    assert result["review_proposal_status"] == "REVIEW_REQUIRED"
    assert result["serving_action"] == "NONE"
    assert result["real_world_predictive_validity"] == "NOT_ESTABLISHED"
    assert repository.proposal_body["candidate_dossier"]["task_or_family"] == "thermal"
    assert repository.proposal_body["candidate_dossier"]["cross_family_specificity"] == {
        "boost_air": {"support": 2, "alarms": 0},
        "fuel": {"support": 2, "alarms": 0},
        "performance": {"support": 2, "alarms": 0},
    }
    assert repository.proposal_body["candidate_dossier_checksum"] == (
        runner.stable_hash(repository.proposal_body["candidate_dossier"])
    )
    from vehicle_platform.mlops.contracts import ReviewProposal

    ReviewProposal.model_validate_json(json.dumps(repository.proposal_body))
    assert repository.final_state == "COMPLETED"
    assert [row["name"] for row in repository.steps if row["state"] == "RUNNING"] == [
        "select",
        "validate",
        "evaluate",
        "compare",
        "report",
    ]


@pytest.mark.asyncio
async def test_resume_requires_exact_definition_and_retries_verified_pre_fit_checkpoints(
    monkeypatch,
):
    from vehicle_platform.mlops import runner

    monkeypatch.setenv("ENVIRONMENT", "test")
    definition = _supervised_definition("resume-safety-v1")
    run_id = uuid4()
    retry_id = uuid4()

    class Repository:
        def __init__(self, _database):
            self.state = "RUNNING"
            self.expiry = datetime.now(UTC) + timedelta(minutes=1)
            self.failed = False

        async def inspect_run(self, _run_id):
            return {
                "run": {
                    "definition_fingerprint": definition.fingerprint,
                    "state": self.state,
                    "lease_expires_at": self.expiry,
                },
                "steps": [],
            }

        async def fail_expired_run(self, _run_id):
            self.failed = True
            self.state = "FAILED"

        async def create_checkpoint_retry(self, _run_id):
            assert self.failed
            return retry_id, True

    repository = Repository(None)
    monkeypatch.setattr(runner, "ControlPlaneRepository", lambda _: repository)
    pipeline = AsyncMock(return_value={"status": "COMPLETED"})
    monkeypatch.setattr(runner, "run_pipeline", pipeline)
    active = await runner.resume_pipeline(
        object(),
        definition,
        run_id,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
    )
    assert active["status"] == "RUN_STILL_OWNED"
    assert not repository.failed
    assert not pipeline.await_count

    repository.expiry = datetime.now(UTC) - timedelta(seconds=1)
    recovered = await runner.resume_pipeline(
        object(),
        definition,
        run_id,
        execute=True,
        confirmed_environment="test",
        confirmed_fingerprint=definition.fingerprint,
    )
    assert recovered["status"] == "COMPLETED"
    assert recovered["resume_action"] == "VERIFIED_CHECKPOINT_RETRY"
    assert recovered["resumed_from_run_id"] == str(run_id)
    assert repository.failed
    assert pipeline.await_count == 1
    assert pipeline.await_args.kwargs["checkpoint_retry_id"] == retry_id
    with pytest.raises(ValueError, match="EXECUTION_CONFIRMATION_MISMATCH"):
        await runner.resume_pipeline(
            object(), definition, run_id, execute=True, confirmed_environment="test"
        )


def test_resume_checkpoint_hash_and_lineage_are_verified():
    from vehicle_platform.features.domain import stable_hash
    from vehicle_platform.mlops.repository import ControlPlaneConflict
    from vehicle_platform.mlops.runner import _reuse_checkpoint

    source_run_id = uuid4()
    output = {"plan_status": "READY_TO_REVIEW", "rows": 8}
    checkpoint = {
        "checkpoint_source_run_id": source_run_id,
        "step_name": "validate",
        "state": "SUCCEEDED",
        "input_checksum": "a" * 64,
        "output_checksum": stable_hash(output),
        "output_body": output,
    }
    assert _reuse_checkpoint(
        checkpoint,
        parent_run_id=source_run_id,
        name="validate",
        input_checksum="a" * 64,
        expected_output=output,
    )
    with pytest.raises(ControlPlaneConflict, match="RESUME_CHECKPOINT_MISMATCH"):
        _reuse_checkpoint(
            checkpoint,
            parent_run_id=uuid4(),
            name="validate",
            input_checksum="a" * 64,
            expected_output=output,
        )
    assert not _reuse_checkpoint(
        None,
        parent_run_id=None,
        name="select",
        input_checksum="b" * 64,
        expected_output={"source_role": "synthetic"},
    )


@pytest.mark.asyncio
async def test_rollback_plan_is_read_only_until_exact_proposal_confirmation(monkeypatch):
    from uuid import UUID

    from vehicle_platform.anomalies.domain import SourceRole as ServingSourceRole
    from vehicle_platform.features.domain import stable_hash
    from vehicle_platform.mlops import rollback
    from vehicle_platform.predictions.domain import ServingEventType

    monkeypatch.setenv("ENVIRONMENT", "test")
    proposal_id, target_id, target_event = uuid4(), uuid4(), uuid4()
    active_id, active_event, target_version, active_version = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    proposal_row = {
        "run_state": "COMPLETED",
        "source_role": "synthetic",
        "candidate_kind": "supervised",
        "content_checksum": "a" * 64,
    }
    target = SimpleNamespace(
        id=target_id,
        result_kind="next_pull",
        subject_key="thermal_degradation",
        source_role=ServingSourceRole.SYNTHETIC,
        environment="test",
        scope="controlled-engineering-dataset",
        model_version_id=target_version,
        detector_version_id=None,
        artifact_checksum="b" * 64,
        feature_set_version="features-v1",
        feature_set_checksum="c" * 64,
        schema_checksum="d" * 64,
        latest_event_id=target_event,
        latest_event_type=ServingEventType.SUPERSEDED,
        is_active=False,
    )
    active = SimpleNamespace(
        id=active_id,
        is_active=True,
        latest_event_id=active_event,
        model_version_id=active_version,
        detector_version_id=None,
    )
    candidate = SimpleNamespace(
        artifact_checksum="b" * 64,
        feature_set_version="features-v1",
        feature_set_checksum="c" * 64,
        schema_checksum="d" * 64,
        source_role=ServingSourceRole.SYNTHETIC,
        validation_status="PASS",
    )

    class Repository:
        def __init__(self, _database):
            self.persisted = []

        async def inspect_proposal(self, _proposal_id):
            return {"state": "APPROVED_FOR_CONTROLLED_REVIEW", "proposal": proposal_row}

        async def create_rollback_plan(self, *args, **kwargs):
            self.persisted.append((args, kwargs))
            return uuid4(), stable_hash(kwargs["body"])

        async def inspect_rollback_plan(self, _plan_id):
            _args, kwargs = self.persisted[-1]
            return {
                "plan": {
                    "id": _plan_id,
                    "proposal_id": proposal_id,
                    "target_binding_id": target_id,
                    "content_checksum": stable_hash(kwargs["body"]),
                    "body": kwargs["body"],
                }
            }

    class Prediction:
        def __init__(self, *_args):
            self.repository = self
            self.closed = False

        async def binding(self, _binding_id):
            return target

        async def inspect_candidate(self, *_args):
            return candidate

        async def bindings_for_slot(self, *_args):
            return [active, target]

        async def close(self):
            self.closed = True

    repository = Repository(None)
    monkeypatch.setattr(rollback, "ControlPlaneRepository", lambda _: repository)
    monkeypatch.setattr(rollback, "PredictionService", Prediction)
    monkeypatch.setattr(rollback, "Settings", lambda: object())
    dry_run = await rollback.plan_rollback(None, proposal_id, target_id)
    assert dry_run["execution"] == "NOT_STARTED"
    assert dry_run["serving_action"] == "NONE"
    assert dry_run["plan"]["expected_active_binding_id"] == str(active_id)
    assert repository.persisted == []

    with pytest.raises(ValueError, match="ROLLBACK_PLAN_CONFIRMATION_MISMATCH"):
        await rollback.plan_rollback(
            None,
            proposal_id,
            target_id,
            execute=True,
            confirmed_environment="test",
            confirmed_proposal_checksum="f" * 64,
        )
    assert repository.persisted == []

    persisted = await rollback.plan_rollback(
        None,
        proposal_id,
        target_id,
        execute=True,
        confirmed_environment="test",
        confirmed_proposal_checksum="a" * 64,
    )
    assert persisted["execution"] == "PERSISTED"
    assert persisted["serving_action"] == "NONE"
    assert len(repository.persisted) == 1
    inspected = await rollback.inspect_rollback_plan(None, UUID(persisted["plan_id"]))
    assert inspected["status"] == "READY_FOR_SEPARATE_9D_REVIEW"
    active.latest_event_id = uuid4()
    stale = await rollback.inspect_rollback_plan(None, UUID(persisted["plan_id"]))
    assert stale["status"] == "STALE"
    assert stale["serving_action"] == "NONE"
