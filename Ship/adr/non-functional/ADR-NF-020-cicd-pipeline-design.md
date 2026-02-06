# ADR-NF-020: CI/CD Pipeline Design

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform requires automated CI/CD pipelines for consistent, reliable deployments across environments.

### Business Context
Deployment requirements:
- Rapid iteration capability
- Consistent deployments
- Minimal downtime
- Rollback capability
- Environment promotion (dev → staging → prod)
- Compliance audit trail

### Technical Context
- GitHub for source control
- AWS infrastructure (ADR-NF-011)
- ECS Fargate containers (ADR-NF-012)
- Multiple services (API, workers, frontend)
- Terraform for infrastructure
- Database migrations with Prisma/TypeORM

### Assumptions
- GitHub Actions as primary CI/CD
- AWS deployment targets
- Container-based deployments
- Infrastructure as Code with Terraform
- Feature branch workflow

---

## Decision Drivers

- Automation and consistency
- Developer experience
- Deployment speed
- Rollback capability
- Security (secrets management)
- Cost efficiency

---

## Considered Options

### Option 1: GitHub Actions
**Description:** GitHub-native CI/CD solution.

**Pros:**
- Native GitHub integration
- Generous free tier
- Large action marketplace
- Simple YAML configuration
- Good secrets management

**Cons:**
- GitHub dependency
- Runner limitations
- Complex matrix builds

### Option 2: AWS CodePipeline + CodeBuild
**Description:** AWS-native CI/CD.

**Pros:**
- Deep AWS integration
- IAM-based security
- CodeDeploy for ECS
- AWS ecosystem

**Cons:**
- AWS lock-in
- Less flexible than GitHub Actions
- More complex setup

### Option 3: GitLab CI/CD
**Description:** GitLab integrated CI/CD.

**Pros:**
- Powerful pipeline features
- Built-in registry
- Good visualization

**Cons:**
- Requires GitLab migration
- Different from GitHub workflow

### Option 4: Jenkins
**Description:** Self-hosted CI/CD server.

**Pros:**
- Highly customizable
- Large plugin ecosystem
- Full control

**Cons:**
- Operational overhead
- Maintenance burden
- Security responsibility

---

## Decision

**Chosen Option:** GitHub Actions with AWS Integration

We will use GitHub Actions for CI/CD, with direct AWS deployment using OIDC authentication and environment-based promotion workflows.

### Rationale
GitHub Actions provides native integration with our GitHub repositories, a rich marketplace of actions, and good secrets management. OIDC authentication with AWS eliminates long-lived credentials. Environment protection rules enable safe production deployments.

---

## Consequences

### Positive
- Native GitHub integration
- No CI/CD infrastructure to manage
- Rich action ecosystem
- Environment-based workflows
- OIDC security (no long-lived credentials)

### Negative
- GitHub dependency
- **Mitigation:** Standard Docker/Terraform patterns portable
- Runner minute limits
- **Mitigation:** Optimize workflows, use caching

### Risks
- GitHub outages: Manual deployment procedures documented
- Secrets exposure: OIDC, minimal permissions, rotation
- Long build times: Caching, parallel jobs

---

## Implementation Notes

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CI/CD Pipeline Flow                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│  │  Push   │───▶│  Build  │───▶│  Test   │───▶│ Analyze │          │
│  │         │    │         │    │         │    │         │          │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│                                                     │                │
│                                     ┌───────────────┘                │
│                                     │                                │
│                                     ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Deploy Pipeline                          │    │
│  │                                                              │    │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                  │    │
│  │  │   Dev   │───▶│ Staging │───▶│  Prod   │                  │    │
│  │  │  (auto) │    │ (auto)  │    │(manual) │                  │    │
│  │  └─────────┘    └─────────┘    └─────────┘                  │    │
│  │       │              │              │                        │    │
│  │       ▼              ▼              ▼                        │    │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                  │    │
│  │  │ Smoke   │    │  E2E    │    │ Canary  │                  │    │
│  │  │ Tests   │    │ Tests   │    │ Deploy  │                  │    │
│  │  └─────────┘    └─────────┘    └─────────┘                  │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### GitHub Actions - Main CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  NODE_VERSION: '20'
  PNPM_VERSION: '8'

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: ${{ env.PNPM_VERSION }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Run ESLint
        run: pnpm lint

      - name: Run Prettier
        run: pnpm format:check

  test:
    name: Test
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: ${{ env.PNPM_VERSION }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Run database migrations
        run: pnpm db:migrate
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/test

      - name: Run unit tests
        run: pnpm test:cov
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: true

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: ${{ env.PNPM_VERSION }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'pnpm'

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm build

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
          retention-days: 1

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: [lint]
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Run npm audit
        run: npm audit --audit-level=high
        continue-on-error: true

  docker:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [build]
    if: github.event_name == 'push'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - name: Download build artifact
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-south-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Docker meta
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/ship-chandlery-api
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Deployment Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        type: choice
        options:
          - development
          - staging
          - production
      version:
        description: 'Version/tag to deploy'
        required: false
        type: string

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false

jobs:
  deploy-dev:
    name: Deploy to Development
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch'
    environment:
      name: development
      url: https://dev.shipchandlery.com

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_DEV }}
          aws-region: ap-south-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Get image tag
        id: image
        run: |
          if [ -n "${{ inputs.version }}" ]; then
            echo "tag=${{ inputs.version }}" >> $GITHUB_OUTPUT
          else
            echo "tag=${{ github.sha }}" >> $GITHUB_OUTPUT
          fi

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: .aws/task-definitions/api-dev.json
          service: api
          cluster: ship-chandlery-dev
          wait-for-service-stability: true
          force-new-deployment: true

      - name: Run smoke tests
        run: |
          sleep 30
          curl -f https://dev-api.shipchandlery.com/health || exit 1

      - name: Notify on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "❌ Development deployment failed",
              "attachments": [{
                "color": "danger",
                "fields": [
                  {"title": "Repository", "value": "${{ github.repository }}", "short": true},
                  {"title": "Commit", "value": "${{ github.sha }}", "short": true}
                ]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [deploy-dev]
    environment:
      name: staging
      url: https://staging.shipchandlery.com

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_STAGING }}
          aws-region: ap-south-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run database migrations
        run: |
          aws ecs run-task \
            --cluster ship-chandlery-staging \
            --task-definition ship-chandlery-migration \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[${{ secrets.SUBNET_IDS }}],securityGroups=[${{ secrets.SG_ID }}]}" \
            --started-by "github-actions"

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: .aws/task-definitions/api-staging.json
          service: api
          cluster: ship-chandlery-staging
          wait-for-service-stability: true
          force-new-deployment: true

      - name: Run E2E tests
        run: |
          pnpm install --frozen-lockfile
          pnpm test:e2e
        env:
          BASE_URL: https://staging-api.shipchandlery.com

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    environment:
      name: production
      url: https://shipchandlery.com

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_PROD }}
          aws-region: ap-south-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run database migrations
        run: |
          aws ecs run-task \
            --cluster ship-chandlery-prod \
            --task-definition ship-chandlery-migration \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[${{ secrets.SUBNET_IDS }}],securityGroups=[${{ secrets.SG_ID }}]}" \
            --started-by "github-actions"

      - name: Deploy API (Blue/Green)
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: .aws/task-definitions/api-prod.json
          service: api
          cluster: ship-chandlery-prod
          wait-for-service-stability: true
          codedeploy-appspec: .aws/appspec.yml
          codedeploy-application: ship-chandlery-api
          codedeploy-deployment-group: production

      - name: Deploy Workers
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: .aws/task-definitions/worker-prod.json
          service: worker
          cluster: ship-chandlery-prod
          wait-for-service-stability: true

      - name: Create release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ github.run_number }}
          release_name: Release ${{ github.run_number }}
          body: |
            Deployed commit: ${{ github.sha }}
            Deployed by: ${{ github.actor }}

      - name: Notify on success
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Production deployment successful",
              "attachments": [{
                "color": "good",
                "fields": [
                  {"title": "Version", "value": "v${{ github.run_number }}", "short": true},
                  {"title": "Deployed by", "value": "${{ github.actor }}", "short": true}
                ]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Infrastructure Workflow

```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        type: choice
        options:
          - development
          - staging
          - production
      action:
        description: 'Terraform action'
        required: true
        type: choice
        options:
          - plan
          - apply

jobs:
  terraform:
    name: Terraform
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment || 'development' }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-south-1

      - name: Terraform Init
        working-directory: terraform/environments/${{ inputs.environment || 'development' }}
        run: terraform init

      - name: Terraform Plan
        working-directory: terraform/environments/${{ inputs.environment || 'development' }}
        run: terraform plan -out=tfplan
        env:
          TF_VAR_environment: ${{ inputs.environment || 'development' }}

      - name: Upload Plan
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: terraform/environments/${{ inputs.environment || 'development' }}/tfplan

      - name: Terraform Apply
        if: inputs.action == 'apply' && github.ref == 'refs/heads/main'
        working-directory: terraform/environments/${{ inputs.environment || 'development' }}
        run: terraform apply -auto-approve tfplan
```

### Database Migration Task

```yaml
# .aws/task-definitions/migration.json
{
  "family": "ship-chandlery-migration",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${execution_role_arn}",
  "taskRoleArn": "${task_role_arn}",
  "containerDefinitions": [
    {
      "name": "migration",
      "image": "${ecr_repository}:${image_tag}",
      "command": ["npm", "run", "db:migrate:deploy"],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ship-chandlery/migration",
          "awslogs-region": "ap-south-1",
          "awslogs-stream-prefix": "migration"
        }
      },
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "${database_url_secret_arn}"
        }
      ]
    }
  ]
}
```

### Rollback Workflow

```yaml
# .github/workflows/rollback.yml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to rollback'
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        description: 'Version to rollback to (image tag)'
        required: true
        type: string

jobs:
  rollback:
    name: Rollback Deployment
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-south-1

      - name: Update task definition with rollback version
        run: |
          # Get current task definition
          TASK_DEF=$(aws ecs describe-task-definition --task-definition ship-chandlery-api-${{ inputs.environment }})

          # Update with rollback image
          NEW_TASK_DEF=$(echo $TASK_DEF | jq --arg IMAGE "${ECR_REGISTRY}/ship-chandlery-api:${{ inputs.version }}" \
            '.taskDefinition | .containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

          # Register new task definition
          aws ecs register-task-definition --cli-input-json "$NEW_TASK_DEF"

      - name: Deploy rollback version
        run: |
          aws ecs update-service \
            --cluster ship-chandlery-${{ inputs.environment }} \
            --service api \
            --force-new-deployment

      - name: Wait for stability
        run: |
          aws ecs wait services-stable \
            --cluster ship-chandlery-${{ inputs.environment }} \
            --services api

      - name: Notify
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "⚠️ Rollback completed",
              "attachments": [{
                "color": "warning",
                "fields": [
                  {"title": "Environment", "value": "${{ inputs.environment }}", "short": true},
                  {"title": "Version", "value": "${{ inputs.version }}", "short": true},
                  {"title": "Triggered by", "value": "${{ github.actor }}", "short": true}
                ]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### OIDC Configuration for AWS

```hcl
# terraform/modules/github-oidc/main.tf

# GitHub OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# Role for GitHub Actions
resource "aws_iam_role" "github_actions" {
  name = "github-actions-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:your-org/ship-chandlery:*"
          }
        }
      }
    ]
  })
}

# Attach necessary policies
resource "aws_iam_role_policy_attachment" "ecr" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.ecr_push.arn
}

resource "aws_iam_role_policy_attachment" "ecs_deploy" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.ecs_deploy.arn
}
```

### Dependencies
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-012: Container Orchestration
- ADR-NF-001: PostgreSQL as Unified Data Store

### Migration Strategy
1. Set up GitHub repository with branch protection
2. Configure AWS OIDC provider
3. Create IAM roles for each environment
4. Set up GitHub environments with protection rules
5. Create initial workflow files
6. Configure secrets in GitHub
7. Set up Slack/notification integration
8. Document deployment procedures

---

## Operational Considerations

### Pipeline Stages

**Complete CI/CD Pipeline:**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CI PIPELINE (on every PR)                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐           │
│  │  Lint   │──▶│  Test   │──▶│  Build  │──▶│ Security│──▶│ Analyze │           │
│  │         │   │         │   │         │   │  Scan   │   │         │           │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘           │
│    ESLint       Unit Tests    TypeScript    Trivy         SonarQube            │
│    Prettier     Integration   Next.js       npm audit     Code coverage        │
│                 E2E (subset)                Snyk                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ merge to main
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CD PIPELINE (on merge to main)                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐           │
│  │  Build  │──▶│  Push   │──▶│ Deploy  │──▶│ Smoke   │──▶│ Deploy  │           │
│  │ Docker  │   │  ECR    │   │   Dev   │   │ Tests   │   │ Staging │           │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘           │
│                                                               │                 │
│                                                               ▼                 │
│                                                          ┌─────────┐           │
│                                                          │   E2E   │           │
│                                                          │  Tests  │           │
│                                                          └─────────┘           │
│                                                               │                 │
│                                                     approval  │                 │
│                                                               ▼                 │
│                                                          ┌─────────┐           │
│                                                          │ Deploy  │           │
│                                                          │  Prod   │           │
│                                                          └─────────┘           │
│                                                               │                 │
│                                                               ▼                 │
│                                                          ┌─────────┐           │
│                                                          │ Verify  │           │
│                                                          │ + Tag   │           │
│                                                          └─────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Stage Details:**

| Stage | Duration | Failure Action | Artifacts |
|-------|----------|----------------|-----------|
| Lint | 1-2 min | Block PR | None |
| Test | 3-5 min | Block PR | Coverage report |
| Build | 2-3 min | Block PR | Build artifacts |
| Security Scan | 2-3 min | Block on Critical/High | SARIF report |
| Analyze | 2-3 min | Block on quality gate fail | SonarQube report |
| Build Docker | 3-5 min | Block deployment | Docker image |
| Push ECR | 1-2 min | Block deployment | Image tag |
| Deploy Dev | 3-5 min | Alert, investigate | Deployment manifest |
| Smoke Tests | 2-3 min | Block staging deploy | Test results |
| Deploy Staging | 3-5 min | Alert, rollback | Deployment manifest |
| E2E Tests | 10-15 min | Block prod deploy | Test results |
| Deploy Prod | 5-10 min | Alert, auto-rollback | Deployment manifest |
| Verify | 2-3 min | Alert, manual check | Health report |

### Security Scanning

**Security Gates:**

| Scan Type | Tool | Stage | Threshold |
|-----------|------|-------|-----------|
| SAST (Static Analysis) | SonarQube | CI | No new critical issues |
| Dependency Scan | npm audit, Snyk | CI | No critical, max 5 high |
| Container Scan | Trivy | Pre-Deploy | No critical, max 3 high |
| Secret Detection | Gitleaks | CI | Zero secrets |
| License Compliance | FOSSA | CI | No GPL/AGPL |
| IaC Scan | Checkov | Infra PR | No critical misconfigs |

**Security Scan Implementation:**

```yaml
security-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for secret scanning

    # Dependency vulnerabilities
    - name: Run npm audit
      run: npm audit --audit-level=high
      continue-on-error: true

    - name: Run Snyk
      uses: snyk/actions/node@master
      with:
        args: --severity-threshold=high
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

    # Secret detection
    - name: Run Gitleaks
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    # Container scanning
    - name: Build image for scanning
      run: docker build -t scan-target:${{ github.sha }} .

    - name: Run Trivy
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: scan-target:${{ github.sha }}
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'
        exit-code: '1'

    # Upload results
    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

    # SAST with SonarQube
    - name: SonarQube Scan
      uses: SonarSource/sonarqube-scan-action@master
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

    - name: SonarQube Quality Gate
      uses: SonarSource/sonarqube-quality-gate-action@master
      timeout-minutes: 5
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Environment Promotion Rules

**Environment Configuration:**

| Environment | Branch | Auto Deploy | Approval Required | Protection |
|-------------|--------|-------------|-------------------|------------|
| Development | main | Yes | No | None |
| Staging | main | Yes (after dev) | No | Smoke tests pass |
| Production | main | No | Yes (2 reviewers) | E2E tests + approval |

**GitHub Environment Protection:**

```yaml
# Production environment requires:
# - 2 approvals from @org/platform-team
# - All required status checks pass
# - Wait timer: 5 minutes (for review)
# - Restrict to protected branches only

environments:
  production:
    name: production
    url: https://shipchandlery.com
    rules:
      - type: required_reviewers
        reviewers:
          - teams: ["platform-team"]
        required_approvals: 2
      - type: wait_timer
        wait_timer: 5
      - type: branch_policy
        branches: ["main"]
```

**Deployment Checklist (Enforced by Workflow):**

- [ ] All CI checks passed
- [ ] Security scan passed (no critical/high)
- [ ] Coverage >= 80%
- [ ] No new technical debt (SonarQube)
- [ ] Staging E2E tests passed
- [ ] Database migrations tested
- [ ] Feature flags configured
- [ ] Runbook updated (if needed)

### Rollback Strategy

**Automatic Rollback Triggers:**

| Condition | Detection Time | Rollback Method |
|-----------|----------------|-----------------|
| Deployment failure | Immediate | ECS circuit breaker |
| Health check failure | 2 min | CodeDeploy auto-rollback |
| Error rate > 5% | 5 min | CloudWatch alarm + CodeDeploy |
| Latency p99 > 5s | 5 min | CloudWatch alarm + CodeDeploy |

**Rollback Implementation:**

```hcl
# ECS Deployment Circuit Breaker
resource "aws_ecs_service" "api" {
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
}

# CodeDeploy Auto-Rollback
resource "aws_codedeploy_deployment_group" "api" {
  auto_rollback_configuration {
    enabled = true
    events = [
      "DEPLOYMENT_FAILURE",
      "DEPLOYMENT_STOP_ON_ALARM",
      "DEPLOYMENT_STOP_ON_REQUEST"
    ]
  }

  alarm_configuration {
    enabled = true
    alarms = [
      aws_cloudwatch_metric_alarm.api_error_rate.name,
      aws_cloudwatch_metric_alarm.api_latency.name,
    ]
  }
}
```

**Manual Rollback Workflow:**

```yaml
# .github/workflows/rollback.yml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        type: choice
        options: [staging, production]
      version:
        description: 'Version to rollback to (image tag)'
        required: true
      reason:
        description: 'Reason for rollback'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Create rollback record
        run: |
          echo "Rollback initiated by ${{ github.actor }}"
          echo "Environment: ${{ inputs.environment }}"
          echo "Target version: ${{ inputs.version }}"
          echo "Reason: ${{ inputs.reason }}"

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-south-1

      - name: Update ECS service to previous version
        run: |
          # Get current task definition
          TASK_DEF=$(aws ecs describe-services \
            --cluster ship-chandlery-${{ inputs.environment }} \
            --services api \
            --query 'services[0].taskDefinition' \
            --output text)

          # Create new task definition with rollback image
          NEW_TASK_DEF=$(aws ecs describe-task-definition \
            --task-definition $TASK_DEF \
            --query 'taskDefinition' | \
            jq --arg IMAGE "${{ env.ECR_REGISTRY }}/api:${{ inputs.version }}" \
            '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

          NEW_TASK_ARN=$(aws ecs register-task-definition \
            --cli-input-json "$NEW_TASK_DEF" \
            --query 'taskDefinition.taskDefinitionArn' \
            --output text)

          aws ecs update-service \
            --cluster ship-chandlery-${{ inputs.environment }} \
            --service api \
            --task-definition $NEW_TASK_ARN \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster ship-chandlery-${{ inputs.environment }} \
            --services api

      - name: Verify rollback
        run: |
          # Check health endpoint
          curl -f https://${{ inputs.environment == 'production' && 'api' || 'staging-api' }}.shipchandlery.com/health

      - name: Notify team
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": ":rewind: Rollback completed",
              "attachments": [{
                "color": "warning",
                "fields": [
                  {"title": "Environment", "value": "${{ inputs.environment }}", "short": true},
                  {"title": "Version", "value": "${{ inputs.version }}", "short": true},
                  {"title": "Initiated by", "value": "${{ github.actor }}", "short": true},
                  {"title": "Reason", "value": "${{ inputs.reason }}", "short": false}
                ]
              }]
            }
```

### Artifact Versioning

**Version Strategy:**

| Artifact | Version Format | Example |
|----------|----------------|---------|
| Docker Images | `{git-sha}` (commit) | `a1b2c3d4e5f6` |
| Docker Images | `{semver}` (release) | `v1.2.3` |
| Docker Images | `{branch}-{sha}` (branch) | `main-a1b2c3d4` |
| NPM Packages | `{semver}` | `1.2.3` |
| Terraform State | `{timestamp}-{sha}` | `20250120-a1b2c3d4` |
| Database Migrations | `{timestamp}_{name}` | `20250120120000_add_orders_table` |

**Image Tagging Strategy:**

```yaml
- name: Docker meta
  id: meta
  uses: docker/metadata-action@v5
  with:
    images: ${{ env.ECR_REGISTRY }}/ship-chandlery-api
    tags: |
      # Git SHA (always)
      type=sha,prefix=

      # Branch name (for non-main branches)
      type=ref,event=branch

      # Semver tags (for releases)
      type=semver,pattern={{version}}
      type=semver,pattern={{major}}.{{minor}}

      # Latest tag for main branch
      type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
```

**Artifact Retention:**

| Artifact Type | Retention | Storage |
|---------------|-----------|---------|
| Docker images (all) | 90 days | ECR |
| Docker images (released) | Forever | ECR |
| Build artifacts | 7 days | S3 |
| Test reports | 30 days | S3 |
| Terraform plans | 7 days | S3 |
| Security scan reports | 1 year | S3 |

### Open Questions - Answered

- **Q:** How will secrets and approvals be managed in the pipeline?
  - **A:**

    **Secrets Management:**

    | Secret Type | Storage | Access Method | Rotation |
    |-------------|---------|---------------|----------|
    | AWS credentials | GitHub OIDC | Role assumption | N/A (short-lived) |
    | NPM token | GitHub Secrets | Environment variable | 90 days |
    | SonarQube token | GitHub Secrets | Environment variable | 180 days |
    | Slack webhook | GitHub Secrets | Environment variable | Never |
    | Snyk token | GitHub Secrets | Environment variable | 180 days |

    **OIDC for AWS (No Long-Lived Credentials):**

    ```yaml
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789:role/github-actions-${{ inputs.environment }}
        aws-region: ap-south-1
        # OIDC token automatically used - no access keys needed
    ```

    **Approval Workflow:**

    | Environment | Approvers | Required Approvals | Auto-Approve Conditions |
    |-------------|-----------|-------------------|------------------------|
    | Development | None | 0 | Always |
    | Staging | None | 0 | CI passes |
    | Production | @platform-team | 2 | Never |

    **Approval Process:**

    1. Developer merges PR to main
    2. CI runs, builds Docker image
    3. Auto-deploy to Development
    4. Smoke tests pass
    5. Auto-deploy to Staging
    6. E2E tests pass
    7. **Manual approval required** (Slack notification sent)
    8. Two team members review and approve in GitHub
    9. Production deployment begins (blue/green)
    10. Health checks validate deployment
    11. If issues, auto-rollback triggers

    **Emergency Deployment (Hotfix):**

    - Single approver sufficient with `hotfix/` branch prefix
    - Must include rollback plan in PR description
    - Auto-notify on-call engineer
    - Post-deployment review required within 24 hours

---

## References
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS ECS Deployment](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-types.html)
- [GitHub OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
