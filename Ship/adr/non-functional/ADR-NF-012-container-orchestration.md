# ADR-NF-012: Container Orchestration

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform requires container orchestration for deploying and scaling the NestJS application and background workers.

### Business Context
Deployment requirements:
- Reliable production deployment
- Horizontal scaling capability
- Zero-downtime deployments
- Environment consistency (dev/staging/prod)
- Cost-efficient for startup scale

### Technical Context
- AWS as cloud provider (ADR-NF-011)
- NestJS containerized application
- Separate API and worker services
- Expected to scale to moderate traffic
- Team has limited DevOps experience

### Assumptions
- Kubernetes expertise is limited on the team
- Moderate scale doesn't require Kubernetes features
- Managed services preferred
- Can migrate to EKS if needed later

---

## Decision Drivers

- Operational simplicity
- Cost efficiency
- AWS integration
- Scaling capability
- Team expertise
- Future flexibility

---

## Considered Options

### Option 1: ECS Fargate
**Description:** AWS-managed serverless containers.

**Pros:**
- No cluster management
- Pay only for running tasks
- Deep AWS integration
- Simple scaling
- Lower operational overhead

**Cons:**
- Limited customization
- AWS-specific
- Some workloads costlier than EC2

### Option 2: EKS (Kubernetes)
**Description:** AWS-managed Kubernetes service.

**Pros:**
- Industry standard
- Rich ecosystem
- Portable across clouds
- Advanced scheduling features

**Cons:**
- Operational complexity
- Steeper learning curve
- Cluster management overhead
- Higher base cost

### Option 3: ECS on EC2
**Description:** ECS with self-managed EC2 instances.

**Pros:**
- Lower compute costs
- More control
- Spot instances

**Cons:**
- Instance management needed
- Capacity planning required
- More operational work

### Option 4: App Runner
**Description:** AWS-managed container deployment service.

**Pros:**
- Simplest option
- Auto-scaling built-in
- No infrastructure management

**Cons:**
- Limited flexibility
- Fewer configuration options
- Not suitable for all workloads

---

## Decision

**Chosen Option:** ECS Fargate

We will use Amazon ECS with Fargate launch type for container orchestration, providing serverless container management with minimal operational overhead.

### Rationale
ECS Fargate eliminates cluster management while providing necessary scaling and deployment capabilities. The deep AWS integration simplifies infrastructure. The team can focus on application development rather than Kubernetes operations. Migration to EKS remains possible if requirements change.

---

## Consequences

### Positive
- No cluster management
- Pay-per-use pricing
- Simple deployment model
- Deep AWS integration
- Auto-scaling out of box

### Negative
- AWS lock-in
- **Mitigation:** Standard Docker containers enable portability
- Some Fargate limitations
- **Mitigation:** Can switch to EC2 launch type for specific needs

### Risks
- Fargate costs at scale: Monitor costs, consider EC2 for stable workloads
- Feature limitations: Evaluate EKS if advanced scheduling needed
- Cold starts: Keep minimum tasks running

---

## Implementation Notes

### ECS Cluster Configuration

```hcl
# terraform/modules/ecs/main.tf

resource "aws_ecs_cluster" "main" {
  name = "ship-chandlery-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"

      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}
```

### Task Definition

```hcl
# API Service Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "ship-chandlery-api-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "NODE_ENV", value = var.environment },
        { name = "PORT", value = "3000" }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db_url.arn}"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis_url.arn}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "api"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"  # Graviton for cost savings
  }
}

# Worker Task Definition
resource "aws_ecs_task_definition" "worker" {
  family                   = "ship-chandlery-worker-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "worker"
      image = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"

      command = ["node", "dist/worker.js"]

      environment = [
        { name = "NODE_ENV", value = var.environment },
        { name = "WORKER_MODE", value = "true" }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db_url.arn}"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis_url.arn}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }
}
```

### ECS Services

```hcl
# API Service
resource "aws_ecs_service" "api" {
  name            = "api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 3000
  }

  deployment_configuration {
    deployment_maximum_percent         = 200
    deployment_minimum_healthy_percent = 100
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.api.arn
  }

  lifecycle {
    ignore_changes = [desired_count]  # Managed by auto-scaling
  }
}

# Worker Service
resource "aws_ecs_service" "worker" {
  name            = "worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 80
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 20
    base              = 1  # At least 1 regular Fargate task
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
}
```

### Auto Scaling

```hcl
# API Auto Scaling
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_count
  min_capacity       = var.api_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale based on CPU
resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Scale based on requests
resource "aws_appautoscaling_policy" "api_requests" {
  name               = "api-requests-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
    }
    target_value       = 1000  # Requests per target per minute
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Worker Auto Scaling based on queue depth
resource "aws_appautoscaling_target" "worker" {
  max_capacity       = var.worker_max_count
  min_capacity       = var.worker_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "worker_queue" {
  name               = "worker-queue-scaling"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 120
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_lower_bound = 0
      metric_interval_upper_bound = 100
      scaling_adjustment          = 1
    }

    step_adjustment {
      metric_interval_lower_bound = 100
      scaling_adjustment          = 2
    }
  }
}
```

### Dockerfile

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production image
FROM node:20-alpine AS production

# Use non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nestjs -u 1001

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

USER nestjs

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/main.js"]
```

### Deployment Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

env:
  AWS_REGION: ap-south-1
  ECR_REPOSITORY: ship-chandlery-api
  ECS_CLUSTER: ship-chandlery-prod
  ECS_SERVICE_API: api
  ECS_SERVICE_WORKER: worker

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Deploy API Service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE_API \
            --force-new-deployment

      - name: Deploy Worker Service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE_WORKER \
            --force-new-deployment

      - name: Wait for API deployment
        run: |
          aws ecs wait services-stable \
            --cluster $ECS_CLUSTER \
            --services $ECS_SERVICE_API
```

### Dependencies
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-020: CI/CD Pipeline Design

### Migration Strategy
1. Set up ECR repository
2. Create Dockerfile
3. Configure ECS cluster with Terraform
4. Create task definitions
5. Deploy services
6. Configure auto-scaling
7. Set up CI/CD pipeline

---

## Operational Considerations

### ECS vs EKS Decision Matrix

| Criteria | ECS Fargate | EKS | Winner |
|----------|-------------|-----|--------|
| **Operational Complexity** | Low (serverless) | High (cluster management) | ECS |
| **Team Expertise Required** | AWS basics | Kubernetes expertise | ECS |
| **Startup Cost** | $0 (pay per use) | ~$72/month (control plane) | ECS |
| **Scaling Speed** | 30-60 seconds | 30-60 seconds | Tie |
| **Portability** | AWS-specific | Multi-cloud | EKS |
| **Ecosystem/Tooling** | Limited | Extensive | EKS |
| **Service Mesh** | App Mesh (limited) | Istio/Linkerd | EKS |
| **Custom Scheduling** | Basic | Advanced | EKS |

**Decision: ECS Fargate** for Phase 1-3, with documented migration path to EKS if needed.

**Migration Triggers to EKS:**
- Need for advanced service mesh capabilities
- Multi-cloud deployment requirements
- Team grows with Kubernetes expertise
- Need for custom operators/CRDs

### Autoscaling Policies

**API Service Autoscaling:**

| Metric | Target | Min Capacity | Max Capacity | Scale Out Cooldown | Scale In Cooldown |
|--------|--------|--------------|--------------|-------------------|-------------------|
| CPU Utilization | 70% | 2 | 20 | 60 seconds | 300 seconds |
| Memory Utilization | 80% | 2 | 20 | 60 seconds | 300 seconds |
| Request Count per Target | 1000/min | 2 | 20 | 60 seconds | 300 seconds |

```hcl
# Predictive scaling for known traffic patterns
resource "aws_appautoscaling_policy" "api_predictive" {
  name               = "api-predictive-scaling"
  policy_type        = "PredictiveScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  predictive_scaling_policy_configuration {
    mode                         = "ForecastAndScale"
    scheduling_buffer_time       = 300
    max_capacity_breach_behavior = "IncreaseMaxCapacity"
    max_capacity_buffer          = 20

    metric_specification {
      target_value = 70
      predefined_load_metric_specification {
        predefined_metric_type = "ECSServiceAverageCPUUtilization"
        resource_label         = "${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
      }
    }
  }
}
```

**Worker Service Autoscaling (Queue-Based):**

| Queue Depth | Desired Workers | Action |
|-------------|-----------------|--------|
| 0-50 | 1 | Minimum |
| 51-200 | 2 | Scale out |
| 201-500 | 4 | Scale out |
| 501-1000 | 6 | Scale out |
| 1000+ | 10 | Maximum |

```hcl
resource "aws_appautoscaling_policy" "worker_step" {
  name               = "worker-step-scaling"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 120
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_upper_bound = 50
      scaling_adjustment          = 1
    }
    step_adjustment {
      metric_interval_lower_bound = 50
      metric_interval_upper_bound = 200
      scaling_adjustment          = 2
    }
    step_adjustment {
      metric_interval_lower_bound = 200
      metric_interval_upper_bound = 500
      scaling_adjustment          = 4
    }
    step_adjustment {
      metric_interval_lower_bound = 500
      metric_interval_upper_bound = 1000
      scaling_adjustment          = 6
    }
    step_adjustment {
      metric_interval_lower_bound = 1000
      scaling_adjustment          = 10
    }
  }
}
```

### Security Hardening

**Container Image Security:**

| Control | Implementation | Enforcement |
|---------|----------------|-------------|
| Base Image | `node:20-alpine` (minimal) | Dockerfile lint in CI |
| Non-root User | `USER nodejs:nodejs` | Container scanner |
| Read-only Filesystem | `readonlyRootFilesystem: true` | Task definition |
| No Privileged Mode | `privileged: false` | Task definition |
| Drop Capabilities | `drop: ALL` | Task definition |
| Resource Limits | CPU/Memory limits | Task definition |

**Task Definition Security Settings:**

```json
{
  "containerDefinitions": [{
    "name": "api",
    "image": "${ecr_repository}:${image_tag}",
    "user": "1001:1001",
    "readonlyRootFilesystem": true,
    "privileged": false,
    "linuxParameters": {
      "capabilities": {
        "drop": ["ALL"]
      },
      "initProcessEnabled": true
    },
    "ulimits": [
      {
        "name": "nofile",
        "softLimit": 65536,
        "hardLimit": 65536
      }
    ],
    "healthCheck": {
      "command": ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 60
    }
  }]
}
```

**Network Security:**

| Layer | Control | Configuration |
|-------|---------|---------------|
| VPC | Private subnets only | No public IPs for tasks |
| Security Groups | Minimal ingress | ALB -> Tasks only on port 3000 |
| NACLs | Default deny | Explicit allow for required traffic |
| Service Discovery | Private DNS | AWS Cloud Map |

### Image Scanning

**ECR Scan Configuration:**

```hcl
resource "aws_ecr_repository" "api" {
  name                 = "ship-chandlery-api"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.ecr.arn
  }
}

# Block deployment if critical/high vulnerabilities found
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 20 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 20
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

**CI Pipeline Security Scan:**

```yaml
- name: Scan image for vulnerabilities
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: '${{ steps.login-ecr.outputs.registry }}/ship-chandlery-api:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'

- name: Upload scan results to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

**Vulnerability Thresholds:**

| Severity | Development | Staging | Production |
|----------|-------------|---------|------------|
| Critical | Warn | Block | Block |
| High | Warn | Warn | Block |
| Medium | Info | Warn | Warn |
| Low | Info | Info | Info |

### Runtime Controls

**AWS GuardDuty for ECS:**
- Enabled for all ECS clusters
- Alerts on cryptomining, unauthorized access, malicious IPs

**CloudWatch Container Insights:**
- CPU/Memory utilization per task
- Network I/O metrics
- Storage metrics for EBS volumes

**Secrets Management:**
- All secrets from AWS Secrets Manager
- No environment variables for sensitive data
- Secrets rotated every 90 days

### Open Questions - Answered

- **Q:** How will blue/green and canary deployments be handled?
  - **A:** We implement blue/green deployments using AWS CodeDeploy integrated with ECS:

    **Blue/Green Deployment Configuration:**

    ```hcl
    resource "aws_codedeploy_app" "api" {
      name             = "ship-chandlery-api"
      compute_platform = "ECS"
    }

    resource "aws_codedeploy_deployment_group" "api_prod" {
      app_name               = aws_codedeploy_app.api.name
      deployment_group_name  = "production"
      deployment_config_name = "CodeDeployDefault.ECSLinear10PercentEvery1Minutes"
      service_role_arn       = aws_iam_role.codedeploy.arn

      ecs_service {
        cluster_name = aws_ecs_cluster.main.name
        service_name = aws_ecs_service.api.name
      }

      load_balancer_info {
        target_group_pair_info {
          prod_traffic_route {
            listener_arns = [aws_lb_listener.https.arn]
          }
          target_group {
            name = aws_lb_target_group.blue.name
          }
          target_group {
            name = aws_lb_target_group.green.name
          }
        }
      }

      blue_green_deployment_config {
        deployment_ready_option {
          action_on_timeout = "CONTINUE_DEPLOYMENT"
          wait_time_in_minutes = 5
        }
        terminate_blue_instances_on_deployment_success {
          action = "TERMINATE"
          termination_wait_time_in_minutes = 10
        }
      }

      auto_rollback_configuration {
        enabled = true
        events  = ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
      }

      alarm_configuration {
        enabled = true
        alarms  = [aws_cloudwatch_metric_alarm.api_errors.name]
      }
    }
    ```

    **Deployment Strategies:**

    | Environment | Strategy | Traffic Shift | Rollback Trigger |
    |-------------|----------|---------------|------------------|
    | Development | AllAtOnce | 100% immediate | Manual |
    | Staging | Linear10PercentEvery1Min | 10% every minute | 5XX rate > 5% |
    | Production | Linear10PercentEvery3Min | 10% every 3 minutes | 5XX rate > 1% or latency p99 > 2s |

    **Canary Testing (Pre-Production):**
    - 5% traffic routed to new version for 10 minutes
    - Automated health checks and error rate monitoring
    - Automatic rollback if error rate exceeds 0.1%
    - Manual promotion to full deployment after canary passes

---

## References
- [Amazon ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
