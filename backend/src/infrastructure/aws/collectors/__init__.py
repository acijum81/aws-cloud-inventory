from .ec2_collector import EC2Collector
from .ebs_collector import EBSCollector
from .ecs_collector import ECSCollector
from .eks_collector import EKSCollector
from .elb_collector import ELBCollector
from .iam_collector import IAMCollector
from .lambda_collector import LambdaCollector
from .rds_collector import RDSCollector
from .s3_collector import S3Collector
from .vpc_collector import VPCCollector

MVP_COLLECTORS = (
    EC2Collector,
    EBSCollector,
    VPCCollector,
    S3Collector,
    RDSCollector,
    LambdaCollector,
    IAMCollector,
    ELBCollector,
    ECSCollector,
    EKSCollector,
)

__all__ = [
    "EC2Collector", "EBSCollector", "VPCCollector", "S3Collector", "RDSCollector",
    "LambdaCollector", "IAMCollector", "ELBCollector", "ECSCollector", "EKSCollector", "MVP_COLLECTORS",
]
