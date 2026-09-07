from datetime import datetime, timezone

from infrastructure.database.repository import ResourceRepository
from domain.entities.aws_resource import AWSResource


def test_repository_round_trip_with_sqlite(tmp_path):
    db = f"sqlite:///{tmp_path / 'inventory.db'}"
    repo = ResourceRepository(db)
    repo.create_schema()
    item = AWSResource(
        resource_id="i-1", resource_type="ec2:instance", service="ec2", account_id="123456789012",
        region="us-east-1", resource_name="web", last_seen_at=datetime.now(timezone.utc), inventory_run_id="run-1",
    )
    assert repo.save_many([item]) == 1
    out = repo.list_by_run("run-1")
    assert out[0].resource_id == "i-1" and out[0].resource_name == "web"
