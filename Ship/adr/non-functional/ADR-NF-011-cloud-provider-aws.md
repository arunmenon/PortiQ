# ADR-NF-011: Cloud Provider - AWS Mumbai

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform requires a cloud provider for hosting, with specific considerations for data residency and regulatory compliance.

### Business Context
Key considerations for cloud selection:
- **RBI data localization**: Financial data must reside in India
- **Target market**: Primary operations in India initially
- **Latency**: Indian users need low-latency access
- **Compliance**: SEBI, RBI guidelines for fintech operations
- **Scale**: Start small, grow efficiently

### Technical Context
- NestJS backend requiring container hosting
- PostgreSQL for primary database
- Redis for caching and queues
- S3-compatible object storage needed
- CDN for static assets

### Assumptions
- AWS Mumbai (ap-south-1) meets compliance requirements
- Managed services preferred for reduced operations
- Multi-AZ for high availability
- Cost optimization is important

---

## Decision Drivers

- Regulatory compliance (RBI data localization)
- Service availability in India
- Managed service offerings
- Team expertise and hiring pool
- Cost efficiency
- Scalability path

---

## Considered Options

### Option 1: AWS (Mumbai Region)
**Description:** Amazon Web Services ap-south-1 region.

**Pros:**
- Most mature managed services
- Largest talent pool in India
- Comprehensive compliance certifications
- Best-in-class security
- Strong partner ecosystem

**Cons:**
- Premium pricing
- Complexity can lead to cost overruns
- Vendor lock-in concerns

### Option 2: Google Cloud (Mumbai)
**Description:** Google Cloud Platform Mumbai region.

**Pros:**
- Strong data/ML capabilities
- Competitive pricing
- Good Kubernetes support
- BigQuery for analytics

**Cons:**
- Smaller service portfolio
- Less mature in India
- Smaller talent pool

### Option 3: Azure (India Regions)
**Description:** Microsoft Azure Central/South India.

**Pros:**
- Enterprise relationships
- Good hybrid cloud
- Strong compliance

**Cons:**
- Highest complexity
- Less developer-friendly
- Higher learning curve

### Option 4: Indian Providers (DigitalOcean, Yotta)
**Description:** Indian-focused cloud providers.

**Pros:**
- Local support
- Potentially lower costs
- Clear data residency

**Cons:**
- Limited managed services
- Less mature infrastructure
- Scaling challenges

---

## Decision

**Chosen Option:** AWS Mumbai (ap-south-1)

We will deploy on AWS in the Mumbai (ap-south-1) region, leveraging managed services for core infrastructure while maintaining cost consciousness.

### Rationale
AWS offers the most comprehensive managed services, reducing operational burden. The Mumbai region meets RBI data localization requirements and provides low latency for Indian users. AWS's mature security and compliance certifications satisfy fintech requirements. The large AWS talent pool in India supports hiring and training.

---

## Consequences

### Positive
- Comprehensive managed services
- Strong compliance posture
- Low latency for Indian users
- Large talent pool
- Clear scaling path

### Negative
- Premium pricing
- **Mitigation:** Cost optimization practices, reserved instances
- Vendor lock-in
- **Mitigation:** Use standard interfaces where possible (PostgreSQL, S3-compatible)

### Risks
- Cost overruns: Budgets, alerts, regular reviews
- Complexity: Start simple, add services as needed
- Single region dependency: Multi-AZ initially, DR plan for critical data

---

## Implementation Notes

### Core Services Selection

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS Architecture (ap-south-1)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                        VPC                                   │    │
│  │                                                              │    │
│  │   Public Subnets                Private Subnets              │    │
│  │  ┌──────────────┐            ┌──────────────────────┐       │    │
│  │  │     ALB      │            │    ECS Fargate       │       │    │
│  │  │              │───────────▶│    (API Services)    │       │    │
│  │  └──────────────┘            └──────────┬───────────┘       │    │
│  │                                         │                    │    │
│  │  ┌──────────────┐            ┌──────────▼───────────┐       │    │
│  │  │   CloudFront │            │    RDS PostgreSQL    │       │    │
│  │  │     (CDN)    │            │    (Multi-AZ)        │       │    │
│  │  └──────────────┘            └──────────────────────┘       │    │
│  │                                                              │    │
│  │  ┌──────────────┐            ┌──────────────────────┐       │    │
│  │  │     NAT      │            │   ElastiCache Redis  │       │    │
│  │  │   Gateway    │            │                      │       │    │
│  │  └──────────────┘            └──────────────────────┘       │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Supporting Services                       │   │
│  │                                                               │   │
│  │  S3 (Documents)  │  SES (Email)  │  CloudWatch (Monitoring)  │   │
│  │  Secrets Manager │  KMS          │  WAF                      │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Service Selection

| Need | AWS Service | Rationale |
|------|-------------|-----------|
| Compute | ECS Fargate | Serverless containers, no cluster management |
| Database | RDS PostgreSQL | Managed, Multi-AZ, automated backups |
| Cache | ElastiCache Redis | Managed Redis for caching and BullMQ |
| Object Storage | S3 | Documents, attachments, exports |
| CDN | CloudFront | Static assets, global edge locations |
| Load Balancer | ALB | Layer 7, WebSocket support |
| DNS | Route 53 | Managed DNS, health checks |
| Email | SES | Transactional email |
| Secrets | Secrets Manager | Secure credential storage |
| Monitoring | CloudWatch | Logs, metrics, alarms |
| Security | WAF, Shield | DDoS protection, web firewall |

### Terraform Infrastructure

```hcl
# terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "ship-chandlery-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project     = "ship-chandlery"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "ship-chandlery-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = var.environment != "prod"
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
}

# RDS PostgreSQL
module "rds" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "ship-chandlery-${var.environment}"

  engine               = "postgres"
  engine_version       = "16.1"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.environment == "prod" ? "db.r6g.xlarge" : "db.t4g.micro"

  allocated_storage     = 100
  max_allocated_storage = 1000

  db_name  = "ship_chandlery"
  username = "admin"
  port     = 5432

  multi_az               = var.environment == "prod"
  db_subnet_group_name   = module.vpc.database_subnet_group
  vpc_security_group_ids = [module.security_groups.rds_sg_id]

  maintenance_window      = "Mon:00:00-Mon:03:00"
  backup_window           = "03:00-06:00"
  backup_retention_period = var.environment == "prod" ? 30 : 7

  performance_insights_enabled = true
  deletion_protection          = var.environment == "prod"

  parameters = [
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements,pgvector"
    }
  ]
}

# ElastiCache Redis
module "elasticache" {
  source = "terraform-aws-modules/elasticache/aws"

  cluster_id           = "ship-chandlery-${var.environment}"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.environment == "prod" ? "cache.r6g.large" : "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name   = module.vpc.elasticache_subnet_group_name
  security_group_ids  = [module.security_groups.redis_sg_id]

  snapshot_retention_limit = 7
  snapshot_window          = "05:00-09:00"
}

# S3 Buckets
resource "aws_s3_bucket" "documents" {
  bucket = "ship-chandlery-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
  }
}
```

### Cost Optimization Strategies

```markdown
## Cost Optimization Plan

### Compute (ECS Fargate)
- Use Fargate Spot for non-critical workloads (up to 70% savings)
- Right-size tasks based on actual usage
- Use ARM64 (Graviton) instances (20% savings)

### Database (RDS)
- Reserved Instances for production (up to 60% savings)
- Use appropriate instance size
- Consider Aurora Serverless v2 for variable workloads

### Caching (ElastiCache)
- Reserved Nodes for production
- Use appropriate node type

### Storage (S3)
- Intelligent Tiering for documents
- Lifecycle policies for old data
- Glacier for long-term retention

### Data Transfer
- Use VPC endpoints for AWS services
- CloudFront for content delivery
- Minimize cross-AZ traffic

### Monitoring
- Set up billing alerts
- Use Cost Explorer
- Regular cost reviews
```

### Security Configuration

```hcl
# Security Groups
module "security_groups" {
  source = "./modules/security-groups"

  vpc_id = module.vpc.vpc_id

  # ALB Security Group
  alb_ingress_rules = [
    {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  ]

  # ECS Security Group
  ecs_ingress_rules = [
    {
      from_port       = 3000
      to_port         = 3000
      protocol        = "tcp"
      security_groups = [alb_sg_id]
    }
  ]

  # RDS Security Group
  rds_ingress_rules = [
    {
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [ecs_sg_id]
    }
  ]
}

# WAF
resource "aws_wafv2_web_acl" "main" {
  name        = "ship-chandlery-waf"
  description = "WAF rules for Ship Chandlery"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # AWS Managed Rules
  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "ship-chandlery-waf"
    sampled_requests_enabled   = true
  }
}
```

### Dependencies
- ADR-NF-012: Container Orchestration
- ADR-NF-013: Object Storage (S3)
- ADR-NF-001: PostgreSQL as Unified Data Store

### Migration Strategy
1. Set up AWS account and organization
2. Create Terraform infrastructure code
3. Deploy VPC and networking
4. Provision RDS and ElastiCache
5. Set up S3 buckets
6. Configure ECS cluster
7. Deploy application
8. Set up monitoring and alerts

---

## Data Residency and Compliance

### Data Residency Requirements

| Data Type | Residency Requirement | Storage Location |
|-----------|----------------------|------------------|
| Customer PII | India only | ap-south-1 (Mumbai) |
| Financial/Payment data | India only (RBI mandate) | ap-south-1 |
| Business transactions | India preferred | ap-south-1 |
| Logs and analytics | No restriction | ap-south-1 (co-located) |
| Static assets/CDN | Global distribution OK | CloudFront global |

### Compliance Framework

| Regulation | Requirement | Implementation |
|------------|-------------|----------------|
| **RBI Data Localization** | Payment data in India | All payment DB in Mumbai |
| **IT Act 2000** | Data protection | Encryption at rest/transit |
| **GDPR** (if EU customers) | Data portability, deletion | Export/delete APIs |
| **SOC 2 Type II** (future) | Security controls | AWS compliance inheritance |

### Compliance Verification

```yaml
# AWS Config rules for compliance
compliance_rules:
  - rule: s3-bucket-server-side-encryption-enabled
    description: All S3 buckets encrypted
  - rule: rds-storage-encrypted
    description: RDS encryption at rest
  - rule: vpc-flow-logs-enabled
    description: Network logging enabled
  - rule: cloudtrail-enabled
    description: API audit logging
```

## Disaster Recovery Strategy

### RTO/RPO Targets

| Tier | Services | RTO | RPO | Strategy |
|------|----------|-----|-----|----------|
| **Tier 1 (Critical)** | API, Database, Auth | 1 hour | 5 min | Multi-AZ active |
| **Tier 2 (Important)** | Search, Cache | 4 hours | 1 hour | Restore from backup |
| **Tier 3 (Standard)** | Analytics, Reports | 24 hours | 24 hours | Rebuild/restore |

### Backup Strategy

| Resource | Backup Method | Frequency | Retention | Verification |
|----------|---------------|-----------|-----------|--------------|
| RDS PostgreSQL | Automated snapshot | Continuous (5 min) | 30 days | Weekly restore test |
| S3 Documents | Cross-region replication | Real-time | Indefinite | Quarterly audit |
| Redis | RDB snapshot | Hourly | 7 days | Monthly test |
| ECS Config | Terraform state | On change | 90 days | Every deploy |
| Secrets | AWS Backup | Daily | 30 days | Quarterly rotation |

### Backup Verification Process

```bash
# Monthly DR drill checklist
1. Restore RDS snapshot to test instance
2. Verify data integrity with checksums
3. Run application health checks against restored DB
4. Document restoration time (must be < RTO)
5. Delete test resources
6. Update runbook if issues found
```

## Multi-Region Failover Plan

### Current Architecture (Single Region)

```
ap-south-1 (Mumbai) - PRIMARY
├── VPC (Multi-AZ)
│   ├── AZ-a: ECS, RDS Primary, Redis Primary
│   └── AZ-b: ECS, RDS Standby, Redis Replica
├── S3 (Regional)
└── CloudFront (Global Edge)
```

### Future Multi-Region (If Required)

**Trigger for Multi-Region:**
- Regulatory requirement for geo-redundancy
- Customer SLA requiring 99.99% availability
- Regional AWS outage lasting >4 hours

**Expansion Plan:**
```
ap-south-1 (Mumbai) - PRIMARY
├── Active workloads
└── Primary database

ap-southeast-1 (Singapore) - DR
├── Warm standby (scaled down)
├── Read replica (async)
└── Failover target

Route 53
├── Health checks
├── Failover routing
└── <60 second DNS failover
```

### Failover Procedure

| Step | Action | Automation | Time |
|------|--------|------------|------|
| 1 | Detect primary failure | Route 53 health check | Auto (30s) |
| 2 | DNS failover to DR | Route 53 automatic | Auto (60s) |
| 3 | Promote read replica | Manual trigger | 5-10 min |
| 4 | Scale up DR resources | Auto Scaling | 5 min |
| 5 | Verify application health | Synthetic monitoring | 5 min |
| **Total RTO** | | | ~20 min |

### Cost Consideration

| Configuration | Monthly Cost | Availability |
|---------------|--------------|--------------|
| Single AZ | $X | 99.5% |
| Multi-AZ (current) | ~1.5X | 99.95% |
| Multi-Region warm | ~2.2X | 99.99% |
| Multi-Region active-active | ~2.5X | 99.995% |

**Recommendation**: Start with Multi-AZ, plan for Multi-Region warm standby when business justifies the cost.

---

## References
- [AWS Mumbai Region](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/)
- [RBI Data Localization Guidelines](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11244)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Pricing Calculator](https://calculator.aws/)
