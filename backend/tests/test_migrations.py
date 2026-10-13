from app.models import Account, Benchmark, ImportRow, ImportRun, Instrument, Observation, Operation, OperationRevision, User


def test_core_models_expose_tablenames() -> None:
    assert {
        User.__tablename__,
        Account.__tablename__,
        Instrument.__tablename__,
        Operation.__tablename__,
        OperationRevision.__tablename__,
        Observation.__tablename__,
        Benchmark.__tablename__,
        ImportRun.__tablename__,
        ImportRow.__tablename__,
    } == {
        "users",
        "accounts",
        "instruments",
        "operations",
        "operation_revisions",
        "observations",
        "benchmarks",
        "import_runs",
        "import_rows",
    }
