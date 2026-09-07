from botocore.exceptions import ClientError

from infrastructure.aws.inventory_runner import InventoryRunner
from infrastructure.aws.session_factory import AwsSessionFactory


class GoodCollector:
    service_name = "good"
    is_global = False

    def __init__(self, session) -> None:
        self.session = session

    def collect(self, account_id: str, region: str):
        return []


class FailingCollector:
    service_name = "failing"
    is_global = False

    def __init__(self, session) -> None:
        self.session = session

    def collect(self, account_id: str, region: str):
        raise ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
            "DescribeSomething",
        )


def test_inventory_runner_isolates_collector_failure() -> None:
    factory = AwsSessionFactory()
    result = InventoryRunner(factory, [FailingCollector, GoodCollector]).collect_account_region(
        "123456789012", "us-east-1"
    )

    assert result.resources == []
    assert len(result.errors) == 1
    assert result.errors[0].service == "failing"
    assert result.errors[0].category.value == "AccessDenied"
    assert result.errors[0].message == "denied"
