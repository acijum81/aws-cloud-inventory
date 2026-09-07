from domain.entities.aws_resource import AWSResource


def test_resource_defaults_are_safe() -> None:
    resource = AWSResource(
        resource_id="i-123",
        resource_type="AWS::EC2::Instance",
        service="ec2",
        account_id="123456789012",
    )
    assert resource.tags == {}
    assert resource.raw_data == {}
