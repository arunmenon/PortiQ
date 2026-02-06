# ADR-NF-017: Data Encryption

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Security

---

## Context

The platform handles sensitive financial and business data that requires encryption at rest and in transit to meet compliance and security requirements.

### Business Context
Sensitive data types:
- Financial data (invoices, payments, credit information)
- Business documents (contracts, RFQs, purchase orders)
- User credentials and personal information
- API keys and integration secrets
- Supplier pricing and commercial terms
- Banking and payment details

### Technical Context
- AWS infrastructure (ADR-NF-011)
- PostgreSQL database (ADR-NF-001)
- S3 for document storage (ADR-NF-013)
- Redis for caching (ADR-NF-005)
- RBI compliance for financial data
- Multi-tenant architecture

### Assumptions
- AWS KMS for key management
- TLS 1.3 for all communications
- Field-level encryption for highly sensitive data
- Encryption at rest for all storage
- Key rotation without downtime

---

## Decision Drivers

- Regulatory compliance (RBI, PCI-DSS considerations)
- Data breach protection
- Performance impact minimization
- Key management complexity
- Audit requirements
- Multi-tenant isolation

---

## Considered Options

### Option 1: AWS KMS with SDK Integration
**Description:** Use AWS KMS for key management with direct SDK calls.

**Pros:**
- Managed service
- Hardware-backed security
- Audit logging via CloudTrail
- Automatic key rotation
- AWS service integration

**Cons:**
- AWS lock-in
- Latency for encryption calls
- Cost per API call

### Option 2: HashiCorp Vault
**Description:** Self-managed secrets and encryption platform.

**Pros:**
- Multi-cloud support
- Rich features
- Dynamic secrets
- No cloud lock-in

**Cons:**
- Operational complexity
- Additional infrastructure
- Expertise required

### Option 3: Application-Level Encryption Only
**Description:** Custom encryption in application code.

**Pros:**
- Full control
- No external dependencies
- Cloud agnostic

**Cons:**
- Key management burden
- Security responsibility
- No HSM backing
- Audit complexity

---

## Decision

**Chosen Option:** AWS KMS with Envelope Encryption

We will use AWS KMS for key management with envelope encryption pattern. Data encryption keys (DEKs) are generated locally and encrypted with KMS master keys. Field-level encryption for PII and financial data.

### Rationale
AWS KMS provides HSM-backed security with managed key rotation and full audit trails via CloudTrail. Envelope encryption minimizes KMS API calls while maintaining security. Integration with AWS services (RDS, S3, ElastiCache) is native.

---

## Consequences

### Positive
- HSM-backed key security
- Automatic key rotation
- Full audit trail
- Native AWS service integration
- Compliance-friendly

### Negative
- AWS dependency for encryption
- **Mitigation:** Abstract encryption layer for portability
- KMS API costs
- **Mitigation:** Envelope encryption reduces calls

### Risks
- Key deletion: Key deletion protection, backup procedures
- Performance: Local DEK caching, async encryption where possible
- Compliance gaps: Regular security audits, penetration testing

---

## Implementation Notes

### Encryption Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Encryption Architecture                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                        AWS KMS                               │    │
│  │                                                              │    │
│  │   CMK (ship-chandlery-master)                               │    │
│  │         │                                                    │    │
│  │         ├──▶ RDS Encryption Key                             │    │
│  │         ├──▶ S3 Encryption Key                              │    │
│  │         ├──▶ ElastiCache Encryption Key                     │    │
│  │         └──▶ Application Data Keys                          │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Envelope Encryption                       │    │
│  │                                                              │    │
│  │   1. Generate DEK locally                                    │    │
│  │   2. Encrypt data with DEK                                   │    │
│  │   3. Encrypt DEK with CMK (KMS call)                        │    │
│  │   4. Store encrypted DEK with data                          │    │
│  │                                                              │    │
│  │   Decryption:                                                │    │
│  │   1. Decrypt DEK with CMK (KMS call)                        │    │
│  │   2. Decrypt data with DEK                                   │    │
│  │   3. Cache DEK for performance                              │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    TLS 1.3 In Transit                        │    │
│  │                                                              │    │
│  │   Client ──TLS──▶ CloudFront ──TLS──▶ ALB ──TLS──▶ ECS     │    │
│  │   ECS ──TLS──▶ RDS (SSL required)                           │    │
│  │   ECS ──TLS──▶ ElastiCache (TLS enabled)                    │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### KMS Configuration

```hcl
# terraform/modules/kms/main.tf

# Master key for application encryption
resource "aws_kms_key" "main" {
  description             = "Ship Chandlery master encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow ECS Task Role"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow RDS"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "ship-chandlery-master-key"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/ship-chandlery-${var.environment}"
  target_key_id = aws_kms_key.main.key_id
}

# Separate key for secrets
resource "aws_kms_key" "secrets" {
  description             = "Ship Chandlery secrets encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "ship-chandlery-secrets-key"
    Environment = var.environment
  }
}
```

### Encryption Service

```typescript
// encryption/services/encryption.service.ts
import {
  KMSClient,
  GenerateDataKeyCommand,
  DecryptCommand,
  EncryptCommand,
} from '@aws-sdk/client-kms';
import * as crypto from 'crypto';

@Injectable()
export class EncryptionService {
  private readonly kms: KMSClient;
  private readonly keyId: string;
  private readonly dekCache: Map<string, CachedDEK> = new Map();
  private readonly DEK_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  constructor(private readonly configService: ConfigService) {
    this.kms = new KMSClient({ region: configService.get('AWS_REGION') });
    this.keyId = configService.get('KMS_KEY_ID');
  }

  /**
   * Encrypt data using envelope encryption
   */
  async encrypt(plaintext: string | Buffer, context?: Record<string, string>): Promise<EncryptedData> {
    // Generate a new data encryption key
    const { dataKey, encryptedDataKey } = await this.generateDataKey(context);

    // Encrypt the plaintext with the DEK
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-gcm', dataKey, iv);

    const plaintextBuffer = typeof plaintext === 'string'
      ? Buffer.from(plaintext, 'utf-8')
      : plaintext;

    const encrypted = Buffer.concat([
      cipher.update(plaintextBuffer),
      cipher.final(),
    ]);

    const authTag = cipher.getAuthTag();

    // Clear plaintext DEK from memory
    dataKey.fill(0);

    return {
      ciphertext: encrypted.toString('base64'),
      encryptedDataKey: encryptedDataKey.toString('base64'),
      iv: iv.toString('base64'),
      authTag: authTag.toString('base64'),
      algorithm: 'AES-256-GCM',
    };
  }

  /**
   * Decrypt data using envelope encryption
   */
  async decrypt(encryptedData: EncryptedData, context?: Record<string, string>): Promise<Buffer> {
    // Decrypt the data encryption key
    const dataKey = await this.decryptDataKey(
      Buffer.from(encryptedData.encryptedDataKey, 'base64'),
      context
    );

    // Decrypt the ciphertext with the DEK
    const decipher = crypto.createDecipheriv(
      'aes-256-gcm',
      dataKey,
      Buffer.from(encryptedData.iv, 'base64')
    );

    decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'base64'));

    const decrypted = Buffer.concat([
      decipher.update(Buffer.from(encryptedData.ciphertext, 'base64')),
      decipher.final(),
    ]);

    // Clear DEK from memory
    dataKey.fill(0);

    return decrypted;
  }

  /**
   * Generate a data encryption key using KMS
   */
  private async generateDataKey(context?: Record<string, string>): Promise<{
    dataKey: Buffer;
    encryptedDataKey: Buffer;
  }> {
    const command = new GenerateDataKeyCommand({
      KeyId: this.keyId,
      KeySpec: 'AES_256',
      EncryptionContext: context,
    });

    const response = await this.kms.send(command);

    return {
      dataKey: Buffer.from(response.Plaintext!),
      encryptedDataKey: Buffer.from(response.CiphertextBlob!),
    };
  }

  /**
   * Decrypt a data encryption key using KMS (with caching)
   */
  private async decryptDataKey(
    encryptedDataKey: Buffer,
    context?: Record<string, string>
  ): Promise<Buffer> {
    const cacheKey = encryptedDataKey.toString('base64');
    const cached = this.dekCache.get(cacheKey);

    if (cached && Date.now() < cached.expiresAt) {
      return Buffer.from(cached.dataKey);
    }

    const command = new DecryptCommand({
      CiphertextBlob: encryptedDataKey,
      KeyId: this.keyId,
      EncryptionContext: context,
    });

    const response = await this.kms.send(command);
    const dataKey = Buffer.from(response.Plaintext!);

    // Cache the DEK
    this.dekCache.set(cacheKey, {
      dataKey: dataKey.toString('base64'),
      expiresAt: Date.now() + this.DEK_CACHE_TTL,
    });

    return dataKey;
  }

  /**
   * Direct KMS encryption for small values (like API keys)
   */
  async kmsEncrypt(plaintext: string): Promise<string> {
    const command = new EncryptCommand({
      KeyId: this.keyId,
      Plaintext: Buffer.from(plaintext),
    });

    const response = await this.kms.send(command);
    return Buffer.from(response.CiphertextBlob!).toString('base64');
  }

  /**
   * Direct KMS decryption
   */
  async kmsDecrypt(ciphertext: string): Promise<string> {
    const command = new DecryptCommand({
      CiphertextBlob: Buffer.from(ciphertext, 'base64'),
      KeyId: this.keyId,
    });

    const response = await this.kms.send(command);
    return Buffer.from(response.Plaintext!).toString('utf-8');
  }
}

interface EncryptedData {
  ciphertext: string;
  encryptedDataKey: string;
  iv: string;
  authTag: string;
  algorithm: string;
}

interface CachedDEK {
  dataKey: string;
  expiresAt: number;
}
```

### Field-Level Encryption

```typescript
// encryption/decorators/encrypted-column.decorator.ts
import { Transform } from 'class-transformer';

/**
 * Decorator for encrypting sensitive entity fields
 */
export function EncryptedColumn(): PropertyDecorator {
  return function(target: any, propertyKey: string) {
    // Mark field for encryption
    Reflect.defineMetadata('encrypted', true, target, propertyKey);
  };
}

// encryption/subscribers/encryption.subscriber.ts
@EventSubscriber()
export class EncryptionSubscriber implements EntitySubscriberInterface {
  constructor(
    private readonly connection: Connection,
    private readonly encryptionService: EncryptionService,
  ) {
    connection.subscribers.push(this);
  }

  listenTo() {
    return Object;
  }

  async beforeInsert(event: InsertEvent<any>) {
    await this.encryptFields(event.entity);
  }

  async beforeUpdate(event: UpdateEvent<any>) {
    if (event.entity) {
      await this.encryptFields(event.entity);
    }
  }

  async afterLoad(entity: any) {
    await this.decryptFields(entity);
  }

  private async encryptFields(entity: any) {
    const metadata = this.connection.getMetadata(entity.constructor);

    for (const column of metadata.columns) {
      const isEncrypted = Reflect.getMetadata(
        'encrypted',
        entity.constructor.prototype,
        column.propertyName
      );

      if (isEncrypted && entity[column.propertyName]) {
        const encrypted = await this.encryptionService.encrypt(
          entity[column.propertyName],
          { table: metadata.tableName, column: column.propertyName }
        );
        entity[column.propertyName] = JSON.stringify(encrypted);
      }
    }
  }

  private async decryptFields(entity: any) {
    const metadata = this.connection.getMetadata(entity.constructor);

    for (const column of metadata.columns) {
      const isEncrypted = Reflect.getMetadata(
        'encrypted',
        entity.constructor.prototype,
        column.propertyName
      );

      if (isEncrypted && entity[column.propertyName]) {
        try {
          const encryptedData = JSON.parse(entity[column.propertyName]);
          const decrypted = await this.encryptionService.decrypt(
            encryptedData,
            { table: metadata.tableName, column: column.propertyName }
          );
          entity[column.propertyName] = decrypted.toString('utf-8');
        } catch (error) {
          // Field might not be encrypted (migration case)
        }
      }
    }
  }
}
```

### Entity with Encrypted Fields

```typescript
// organizations/entities/organization.entity.ts
@Entity('organizations')
export class Organization {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  // Encrypted banking details
  @Column({ type: 'text', nullable: true })
  @EncryptedColumn()
  bankAccountNumber: string;

  @Column({ type: 'text', nullable: true })
  @EncryptedColumn()
  bankIfscCode: string;

  @Column({ type: 'text', nullable: true })
  @EncryptedColumn()
  taxId: string;

  // Non-sensitive fields
  @Column()
  address: string;

  @CreateDateColumn()
  createdAt: Date;
}
```

### Secrets Management

```typescript
// secrets/services/secrets.service.ts
import {
  SecretsManagerClient,
  GetSecretValueCommand,
  CreateSecretCommand,
  UpdateSecretCommand,
} from '@aws-sdk/client-secrets-manager';

@Injectable()
export class SecretsService {
  private readonly client: SecretsManagerClient;
  private readonly cache: Map<string, CachedSecret> = new Map();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  constructor(private readonly configService: ConfigService) {
    this.client = new SecretsManagerClient({
      region: configService.get('AWS_REGION'),
    });
  }

  async getSecret<T = string>(secretName: string): Promise<T> {
    const cached = this.cache.get(secretName);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.value as T;
    }

    const command = new GetSecretValueCommand({
      SecretId: secretName,
    });

    const response = await this.client.send(command);
    const value = response.SecretString
      ? JSON.parse(response.SecretString)
      : response.SecretBinary;

    this.cache.set(secretName, {
      value,
      expiresAt: Date.now() + this.CACHE_TTL,
    });

    return value as T;
  }

  async createSecret(secretName: string, value: any): Promise<void> {
    const command = new CreateSecretCommand({
      Name: secretName,
      SecretString: JSON.stringify(value),
      KmsKeyId: this.configService.get('KMS_SECRETS_KEY_ID'),
    });

    await this.client.send(command);
  }

  async updateSecret(secretName: string, value: any): Promise<void> {
    const command = new UpdateSecretCommand({
      SecretId: secretName,
      SecretString: JSON.stringify(value),
    });

    await this.client.send(command);
    this.cache.delete(secretName);
  }
}
```

### Database Encryption (RDS)

```hcl
# RDS with encryption
resource "aws_db_instance" "main" {
  # ... other config

  storage_encrypted = true
  kms_key_id        = aws_kms_key.main.arn

  # Force SSL connections
  parameter_group_name = aws_db_parameter_group.ssl.name
}

resource "aws_db_parameter_group" "ssl" {
  name   = "ship-chandlery-postgres-ssl"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}
```

### S3 Encryption

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true  # Reduces KMS API calls
  }
}
```

### Redis Encryption

```hcl
resource "aws_elasticache_replication_group" "main" {
  # ... other config

  at_rest_encryption_enabled = true
  kms_key_id                = aws_kms_key.main.arn
  transit_encryption_enabled = true
}
```

### TLS Configuration

```typescript
// main.ts - TLS for external connections
const httpsOptions = {
  key: fs.readFileSync('/etc/ssl/private/key.pem'),
  cert: fs.readFileSync('/etc/ssl/certs/cert.pem'),
};

const app = await NestFactory.create(AppModule, {
  httpsOptions: process.env.NODE_ENV === 'production' ? httpsOptions : undefined,
});

// Database connection with SSL
// ormconfig.ts
export default {
  ssl: {
    rejectUnauthorized: true,
    ca: fs.readFileSync('/etc/ssl/certs/rds-ca-2019-root.pem'),
  },
};
```

### Dependencies
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-001: PostgreSQL as Unified Data Store
- ADR-NF-013: Object Storage (S3)
- ADR-NF-005: Caching Strategy (Redis)

### Migration Strategy
1. Create KMS keys and configure policies
2. Enable RDS encryption (requires snapshot/restore for existing)
3. Enable S3 default encryption
4. Enable ElastiCache encryption
5. Implement application-level encryption service
6. Add field-level encryption for PII
7. Migrate secrets to Secrets Manager
8. Enable and verify TLS everywhere
9. Audit and compliance verification

---

## Operational Considerations

### Encryption Scope

**Encryption at Rest:**

| Data Store | Encryption Method | Key Type | Key Rotation |
|------------|-------------------|----------|--------------|
| RDS PostgreSQL | AWS RDS Encryption | KMS CMK | Annual (automatic) |
| S3 Documents | SSE-KMS | KMS CMK | Annual (automatic) |
| S3 Media | SSE-S3 | AWS Managed | Automatic |
| ElastiCache Redis | At-rest encryption | KMS CMK | Annual (automatic) |
| EBS Volumes | EBS Encryption | KMS CMK | Annual (automatic) |
| Secrets Manager | Default encryption | KMS CMK | Annual (automatic) |
| CloudWatch Logs | Log encryption | KMS CMK | Annual (automatic) |

**Encryption in Transit:**

| Connection | Protocol | Minimum Version | Certificate |
|------------|----------|-----------------|-------------|
| Client -> CloudFront | TLS | 1.2 | ACM managed |
| CloudFront -> ALB | TLS | 1.2 | ACM managed |
| ALB -> ECS | TLS | 1.2 | ACM managed |
| ECS -> RDS | TLS | 1.2 | RDS CA |
| ECS -> ElastiCache | TLS | 1.2 | ElastiCache CA |
| ECS -> S3 | HTTPS | 1.2 | AWS |
| Internal services | mTLS (optional) | 1.3 | Private CA |

**Field-Level Encryption (Sensitive Data):**

| Data Type | Encrypted Fields | Encryption Method | Access Control |
|-----------|------------------|-------------------|----------------|
| Banking Info | accountNumber, ifscCode, routingNumber | AES-256-GCM (envelope) | Finance role only |
| PII | taxId, panNumber, aadharNumber | AES-256-GCM (envelope) | Compliance role only |
| Payment Data | cardLast4, cardFingerprint | AES-256-GCM (envelope) | Payment service only |
| API Keys | keyHash (stored hashed, not encrypted) | SHA-256 | N/A |
| Passwords | passwordHash (bcrypt) | bcrypt (cost=12) | N/A |

### Key Management Ownership

**KMS Key Hierarchy:**

```
AWS Account Root
└── Ship Chandlery KMS Keys
    ├── ship-chandlery-master (CMK)
    │   ├── RDS encryption
    │   ├── S3 document encryption
    │   ├── ElastiCache encryption
    │   └── Application envelope encryption
    │
    ├── ship-chandlery-secrets (CMK)
    │   └── Secrets Manager encryption
    │
    └── ship-chandlery-logs (CMK)
        └── CloudWatch Logs encryption
```

**Key Access Policies:**

| Principal | Key | Allowed Operations |
|-----------|-----|-------------------|
| ECS Task Role | Master CMK | Decrypt, GenerateDataKey |
| Lambda Execution Role | Master CMK | Decrypt, GenerateDataKey |
| RDS Service | Master CMK | Decrypt, GenerateDataKey |
| S3 Service | Master CMK | Decrypt, GenerateDataKey |
| DevOps Role | All CMKs | Full management |
| Security Admin | All CMKs | Describe, GetKeyPolicy, ListGrants |
| Application Developers | None | No direct KMS access |

**Terraform Key Policy:**

```hcl
resource "aws_kms_key" "master" {
  description             = "Ship Chandlery master encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccess"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "ECSTaskAccess"
        Effect = "Allow"
        Principal = { AWS = aws_iam_role.ecs_task.arn }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "s3.ap-south-1.amazonaws.com",
              "rds.ap-south-1.amazonaws.com",
              "elasticache.ap-south-1.amazonaws.com"
            ]
          }
        }
      },
      {
        Sid    = "AuditAccess"
        Effect = "Allow"
        Principal = { AWS = aws_iam_role.security_auditor.arn }
        Action = [
          "kms:DescribeKey",
          "kms:GetKeyPolicy",
          "kms:GetKeyRotationStatus",
          "kms:ListGrants",
          "kms:ListKeyPolicies"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### Secrets Handling

**Secret Categories and Storage:**

| Secret Type | Storage | Rotation | Access Method |
|-------------|---------|----------|---------------|
| Database credentials | Secrets Manager | 30 days | ECS task definition |
| API keys (external) | Secrets Manager | 90 days | Runtime fetch |
| JWT signing keys | Secrets Manager | 90 days | Startup load |
| Encryption DEKs | In-memory cache | Per-use | KMS GenerateDataKey |
| OAuth client secrets | Secrets Manager | 180 days | Runtime fetch |
| Webhook signing keys | Secrets Manager | 90 days | Runtime fetch |

**Secrets Manager Structure:**

```
/ship-chandlery/{environment}/
├── database/
│   ├── primary          # {"username": "...", "password": "...", "host": "..."}
│   └── readonly         # Read replica credentials
├── redis/
│   └── primary          # {"url": "redis://...", "password": "..."}
├── jwt/
│   ├── access-token     # {"privateKey": "...", "publicKey": "..."}
│   └── refresh-token    # {"privateKey": "...", "publicKey": "..."}
├── external/
│   ├── stripe           # {"secretKey": "...", "webhookSecret": "..."}
│   ├── razorpay         # {"keyId": "...", "keySecret": "..."}
│   ├── sendgrid         # {"apiKey": "..."}
│   └── aws-ses          # {"accessKey": "...", "secretKey": "..."}
└── internal/
    ├── encryption-dek    # Data encryption key for envelope encryption
    └── webhook-signing   # Internal webhook signature key
```

**Secrets Access Service:**

```typescript
@Injectable()
export class SecretsService {
  private cache = new Map<string, CachedSecret>();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  async getSecret<T>(secretName: string): Promise<T> {
    const cached = this.cache.get(secretName);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.value as T;
    }

    const command = new GetSecretValueCommand({
      SecretId: secretName,
    });

    const response = await this.secretsManager.send(command);
    const value = JSON.parse(response.SecretString);

    this.cache.set(secretName, {
      value,
      expiresAt: Date.now() + this.CACHE_TTL,
      version: response.VersionId,
    });

    return value as T;
  }

  // Subscribe to rotation events for immediate refresh
  @OnEvent('secrets.rotated')
  async handleSecretRotation(event: SecretRotationEvent): Promise<void> {
    this.cache.delete(event.secretName);
    this.logger.log(`Secret ${event.secretName} rotated, cache cleared`);
  }
}
```

### Rotation Process

**Automated Rotation Schedule:**

| Secret Type | Rotation Frequency | Rotation Method | Downtime |
|-------------|-------------------|-----------------|----------|
| Database credentials | 30 days | Secrets Manager + Lambda | Zero (dual user) |
| JWT signing keys | 90 days | Manual + deployment | Zero (overlap period) |
| API keys (internal) | 90 days | Secrets Manager + Lambda | Zero (key overlap) |
| External API keys | 180 days | Manual + Secrets Manager | Minimal (coordinated) |
| KMS CMKs | Annual | Automatic | Zero |

**Database Credential Rotation Lambda:**

```typescript
// lambda/secret-rotation/database.ts
export const handler = async (event: SecretsManagerRotationEvent) => {
  const { SecretId, ClientRequestToken, Step } = event;

  switch (Step) {
    case 'createSecret':
      // Generate new password
      const newPassword = generateSecurePassword(32);
      await secretsManager.putSecretValue({
        SecretId,
        ClientRequestToken,
        SecretString: JSON.stringify({
          ...currentSecret,
          password: newPassword,
        }),
        VersionStages: ['AWSPENDING'],
      });
      break;

    case 'setSecret':
      // Create new database user with new password
      await createDatabaseUser(pendingSecret);
      break;

    case 'testSecret':
      // Verify new credentials work
      await testDatabaseConnection(pendingSecret);
      break;

    case 'finishSecret':
      // Move AWSCURRENT label to new version
      await secretsManager.updateSecretVersionStage({
        SecretId,
        VersionStage: 'AWSCURRENT',
        MoveToVersionId: ClientRequestToken,
        RemoveFromVersionId: currentVersionId,
      });
      // Drop old database user after grace period
      setTimeout(() => dropOldUser(previousSecret), 3600000);
      break;
  }
};
```

**JWT Key Rotation Process:**

```typescript
// Manual rotation with overlap period
async rotateJwtKeys(): Promise<void> {
  // 1. Generate new key pair
  const newKeyPair = await generateKeyPair('RS256');

  // 2. Store new keys with "pending" suffix
  await this.secretsService.updateSecret(
    '/ship-chandlery/prod/jwt/access-token-pending',
    newKeyPair
  );

  // 3. Update JWKS endpoint to include both keys
  await this.updateJwksEndpoint([currentPublicKey, newKeyPair.publicKey]);

  // 4. Deploy new version using pending keys for signing
  // (old keys still valid for verification)

  // 5. After 24h, remove old key from JWKS
  // 6. Move pending to current, delete old
}
```

### Open Questions - Answered

- **Q:** What is the key rotation cadence and audit plan?
  - **A:**

    **Rotation Cadence:**

    | Key/Secret Type | Rotation Period | Method | Notification |
    |-----------------|-----------------|--------|--------------|
    | KMS CMKs | Annual | Automatic (AWS) | CloudTrail event |
    | Database credentials | 30 days | Secrets Manager Lambda | SNS notification |
    | JWT signing keys | 90 days | Manual deployment | Slack alert |
    | Internal API keys | 90 days | Secrets Manager Lambda | SNS notification |
    | External API keys | 180 days | Manual | Calendar reminder |
    | TLS certificates | 60 days before expiry | ACM auto-renewal | SNS notification |

    **Audit Plan:**

    | Audit Type | Frequency | Scope | Tool |
    |------------|-----------|-------|------|
    | KMS key usage | Real-time | All key operations | CloudTrail |
    | Secret access | Real-time | All secret reads | CloudTrail |
    | Encryption compliance | Weekly | All data stores | AWS Config |
    | Key policy review | Quarterly | All KMS keys | Manual review |
    | Rotation compliance | Monthly | All rotatable secrets | Automated report |
    | Penetration testing | Annual | Encryption implementation | Third party |

    **CloudTrail Audit Queries:**

    ```sql
    -- KMS key usage audit
    SELECT
      eventTime,
      userIdentity.arn as principal,
      eventName,
      requestParameters.keyId,
      sourceIPAddress
    FROM cloudtrail_logs
    WHERE eventSource = 'kms.amazonaws.com'
      AND eventTime > DATE_SUB(NOW(), INTERVAL 7 DAY)
    ORDER BY eventTime DESC;

    -- Secret access audit
    SELECT
      eventTime,
      userIdentity.arn as principal,
      eventName,
      requestParameters.secretId,
      sourceIPAddress
    FROM cloudtrail_logs
    WHERE eventSource = 'secretsmanager.amazonaws.com'
      AND eventName IN ('GetSecretValue', 'PutSecretValue', 'DeleteSecret')
      AND eventTime > DATE_SUB(NOW(), INTERVAL 7 DAY)
    ORDER BY eventTime DESC;
    ```

    **Compliance Alerts:**

    ```hcl
    resource "aws_cloudwatch_metric_alarm" "kms_unusual_activity" {
      alarm_name          = "kms-unusual-activity"
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      metric_name         = "CallCount"
      namespace           = "AWS/KMS"
      period              = 300
      statistic           = "Sum"
      threshold           = 1000  # Unusual high volume
      alarm_description   = "Unusual KMS API call volume detected"
      alarm_actions       = [aws_sns_topic.security_alerts.arn]
    }

    resource "aws_cloudwatch_metric_alarm" "secret_access_anomaly" {
      alarm_name          = "secret-access-anomaly"
      comparison_operator = "GreaterThanThreshold"
      evaluation_periods  = 1
      metric_name         = "CallCount"
      namespace           = "AWS/SecretsManager"
      period              = 300
      statistic           = "Sum"
      threshold           = 100  # More than expected
      alarm_actions       = [aws_sns_topic.security_alerts.arn]
    }
    ```

---

## References
- [AWS KMS Documentation](https://docs.aws.amazon.com/kms/)
- [Envelope Encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping)
- [RBI Data Security Guidelines](https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=11822)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
