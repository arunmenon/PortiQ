# ADR-NF-013: Object Storage (S3)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Infrastructure

---

## Context

The platform requires scalable object storage for documents, images, and other binary assets generated through procurement workflows.

### Business Context
Storage requirements:
- Procurement documents (POs, invoices, delivery notes)
- Product images and catalogs
- User-uploaded attachments
- Generated reports and exports
- Document AI processing artifacts
- Audit trail and compliance archives

### Technical Context
- AWS as cloud provider (ADR-NF-011)
- Document AI pipeline generates intermediate files
- Multi-tenant data isolation needed
- Some documents require long-term retention
- Varying access patterns (hot vs cold data)

### Assumptions
- S3 meets compliance requirements
- CloudFront can be used for static asset delivery
- Lifecycle policies handle data retention
- Server-side encryption sufficient for most cases

---

## Decision Drivers

- Scalability and durability
- Cost optimization
- Security and compliance
- Integration with AWS services
- Access patterns (hot/warm/cold)
- Developer experience

---

## Considered Options

### Option 1: Amazon S3
**Description:** AWS native object storage service.

**Pros:**
- 99.999999999% durability
- Deep AWS integration
- Multiple storage classes
- Comprehensive security
- Event triggers (Lambda, SNS)
- Versioning and lifecycle policies

**Cons:**
- AWS lock-in
- Egress costs can add up
- Complex permission model

### Option 2: MinIO (Self-Hosted)
**Description:** S3-compatible open-source storage.

**Pros:**
- S3 API compatible
- No vendor lock-in
- Full control
- No egress fees

**Cons:**
- Operational overhead
- Need to manage durability
- Scaling complexity
- Infrastructure costs

### Option 3: Google Cloud Storage
**Description:** GCP native object storage.

**Pros:**
- Similar features to S3
- Good pricing
- Strong consistency

**Cons:**
- Different cloud provider
- Additional complexity
- Less AWS integration

---

## Decision

**Chosen Option:** Amazon S3

We will use Amazon S3 for object storage, leveraging storage classes for cost optimization and lifecycle policies for compliance-driven retention.

### Rationale
S3's integration with our AWS infrastructure (ADR-NF-011) provides seamless connectivity with ECS, Lambda, and CloudFront. The 11 nines of durability ensures document safety. Storage classes (Intelligent-Tiering, Glacier) enable cost optimization for varying access patterns.

---

## Consequences

### Positive
- Extremely high durability
- Native AWS integration
- Flexible storage classes
- Built-in versioning
- Event-driven workflows

### Negative
- AWS vendor lock-in
- **Mitigation:** Use S3-compatible APIs, abstract storage layer
- Egress costs
- **Mitigation:** CloudFront for frequently accessed files

### Risks
- Cost overruns: Enable S3 analytics, set budgets
- Accidental deletion: Versioning, MFA delete for critical buckets
- Public exposure: Block public access by default, regular audits

---

## Implementation Notes

### Bucket Structure

```
ship-chandlery-{env}/
├── documents/
│   ├── procurement/     # POs, invoices, contracts
│   ├── shipping/        # Bills of lading, delivery notes
│   └── compliance/      # Certificates, audit reports
├── uploads/
│   ├── temp/           # Processing uploads (TTL: 24h)
│   └── attachments/    # User attachments
├── media/
│   ├── products/       # Product images
│   └── organizations/  # Logos, branding
├── exports/
│   └── reports/        # Generated reports (TTL: 7d)
└── ai-processing/
    ├── raw/            # Original documents
    ├── processed/      # Extracted data
    └── training/       # ML training data
```

### Terraform Configuration

```hcl
# terraform/modules/s3/main.tf

# Main documents bucket
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
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "temp-cleanup"
    status = "Enabled"

    filter {
      prefix = "uploads/temp/"
    }

    expiration {
      days = 1
    }
  }

  rule {
    id     = "exports-cleanup"
    status = "Enabled"

    filter {
      prefix = "exports/"
    }

    expiration {
      days = 7
    }
  }

  rule {
    id     = "archive-old-documents"
    status = "Enabled"

    filter {
      prefix = "documents/"
    }

    transition {
      days          = 90
      storage_class = "INTELLIGENT_TIERING"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "compliance-retention"
    status = "Enabled"

    filter {
      prefix = "documents/compliance/"
    }

    # 7-year retention for financial documents
    noncurrent_version_expiration {
      noncurrent_days = 2555
    }
  }
}

# CORS for direct uploads
resource "aws_s3_bucket_cors_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# Intelligent Tiering configuration
resource "aws_s3_bucket_intelligent_tiering_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  name   = "AutoTiering"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}
```

### Storage Service

```typescript
// storage/services/storage.service.ts
import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

@Injectable()
export class StorageService {
  private readonly s3: S3Client;
  private readonly bucket: string;

  constructor(private readonly configService: ConfigService) {
    this.s3 = new S3Client({
      region: configService.get('AWS_REGION'),
    });
    this.bucket = configService.get('S3_BUCKET');
  }

  async upload(
    key: string,
    body: Buffer | Readable,
    options: UploadOptions = {}
  ): Promise<UploadResult> {
    const command = new PutObjectCommand({
      Bucket: this.bucket,
      Key: key,
      Body: body,
      ContentType: options.contentType,
      Metadata: options.metadata,
      ServerSideEncryption: 'aws:kms',
      Tagging: this.buildTags(options.tags),
    });

    await this.s3.send(command);

    return {
      key,
      bucket: this.bucket,
      url: `s3://${this.bucket}/${key}`,
    };
  }

  async getSignedUploadUrl(
    key: string,
    contentType: string,
    expiresIn: number = 3600
  ): Promise<string> {
    const command = new PutObjectCommand({
      Bucket: this.bucket,
      Key: key,
      ContentType: contentType,
      ServerSideEncryption: 'aws:kms',
    });

    return getSignedUrl(this.s3, command, { expiresIn });
  }

  async getSignedDownloadUrl(
    key: string,
    expiresIn: number = 3600
  ): Promise<string> {
    const command = new GetObjectCommand({
      Bucket: this.bucket,
      Key: key,
    });

    return getSignedUrl(this.s3, command, { expiresIn });
  }

  async download(key: string): Promise<Readable> {
    const command = new GetObjectCommand({
      Bucket: this.bucket,
      Key: key,
    });

    const response = await this.s3.send(command);
    return response.Body as Readable;
  }

  async delete(key: string): Promise<void> {
    const command = new DeleteObjectCommand({
      Bucket: this.bucket,
      Key: key,
    });

    await this.s3.send(command);
  }

  async copy(sourceKey: string, destinationKey: string): Promise<void> {
    const command = new CopyObjectCommand({
      Bucket: this.bucket,
      CopySource: `${this.bucket}/${sourceKey}`,
      Key: destinationKey,
    });

    await this.s3.send(command);
  }

  private buildTags(tags?: Record<string, string>): string | undefined {
    if (!tags) return undefined;
    return Object.entries(tags)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&');
  }
}

interface UploadOptions {
  contentType?: string;
  metadata?: Record<string, string>;
  tags?: Record<string, string>;
}
```

### Document Storage with Multi-Tenancy

```typescript
// storage/services/document-storage.service.ts
@Injectable()
export class DocumentStorageService {
  constructor(
    private readonly storageService: StorageService,
    @InjectRepository(Document)
    private readonly documentRepository: Repository<Document>
  ) {}

  async uploadDocument(
    file: Express.Multer.File,
    organizationId: string,
    category: DocumentCategory,
    metadata: DocumentMetadata
  ): Promise<Document> {
    // Generate tenant-isolated key
    const key = this.generateKey(organizationId, category, file.originalname);

    // Upload to S3
    await this.storageService.upload(key, file.buffer, {
      contentType: file.mimetype,
      metadata: {
        organizationId,
        uploadedBy: metadata.userId,
        originalName: file.originalname,
      },
      tags: {
        organization: organizationId,
        category,
        environment: process.env.NODE_ENV,
      },
    });

    // Create database record
    const document = await this.documentRepository.save({
      organizationId,
      category,
      name: file.originalname,
      mimeType: file.mimetype,
      size: file.size,
      storageKey: key,
      uploadedBy: metadata.userId,
    });

    return document;
  }

  async getDownloadUrl(
    documentId: string,
    organizationId: string
  ): Promise<string> {
    const document = await this.documentRepository.findOne({
      where: { id: documentId, organizationId },
    });

    if (!document) {
      throw new NotFoundException('Document not found');
    }

    return this.storageService.getSignedDownloadUrl(document.storageKey);
  }

  private generateKey(
    organizationId: string,
    category: DocumentCategory,
    filename: string
  ): string {
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const uuid = crypto.randomUUID();
    const ext = path.extname(filename);

    return `documents/${category}/${organizationId}/${year}/${month}/${uuid}${ext}`;
  }
}
```

### Event-Driven Processing

```typescript
// storage/handlers/s3-event.handler.ts
import { SQSHandler } from 'aws-lambda';

export const handler: SQSHandler = async (event) => {
  for (const record of event.Records) {
    const s3Event = JSON.parse(record.body);

    for (const s3Record of s3Event.Records) {
      const bucket = s3Record.s3.bucket.name;
      const key = decodeURIComponent(s3Record.s3.object.key);

      // Trigger document processing pipeline
      if (key.startsWith('documents/procurement/')) {
        await triggerDocumentAI(bucket, key);
      }

      // Generate thumbnails for images
      if (key.startsWith('media/products/')) {
        await generateThumbnails(bucket, key);
      }
    }
  }
};
```

### Direct Upload from Frontend

```typescript
// storage/controllers/upload.controller.ts
@Controller('api/v1/uploads')
export class UploadController {
  constructor(private readonly storageService: StorageService) {}

  @Post('presigned-url')
  @UseGuards(AuthGuard)
  async getPresignedUrl(
    @Body() dto: PresignedUrlDto,
    @CurrentUser() user: User
  ): Promise<PresignedUrlResponse> {
    const key = `uploads/temp/${user.organizationId}/${crypto.randomUUID()}/${dto.filename}`;

    const uploadUrl = await this.storageService.getSignedUploadUrl(
      key,
      dto.contentType,
      300 // 5 minutes
    );

    return {
      uploadUrl,
      key,
      expiresIn: 300,
    };
  }

  @Post('complete')
  @UseGuards(AuthGuard)
  async completeUpload(
    @Body() dto: CompleteUploadDto,
    @CurrentUser() user: User
  ): Promise<Document> {
    // Move from temp to permanent location
    const permanentKey = dto.key.replace('uploads/temp/', `documents/${dto.category}/`);

    await this.storageService.copy(dto.key, permanentKey);
    await this.storageService.delete(dto.key);

    // Create document record
    return this.documentStorageService.createFromUpload(
      permanentKey,
      dto,
      user
    );
  }
}
```

### Dependencies
- ADR-NF-011: Cloud Provider - AWS Mumbai
- ADR-NF-014: CDN Strategy
- ADR-FN-006: Document AI Pipeline Architecture

### Migration Strategy
1. Create S3 buckets with Terraform
2. Configure encryption and lifecycle policies
3. Implement storage service abstraction
4. Set up event notifications
5. Migrate existing files if any
6. Configure CloudFront for static assets

---

## Operational Considerations

### Bucket Layout Strategy

**Production Environment Buckets:**

| Bucket Name | Purpose | Access Pattern | Encryption |
|-------------|---------|----------------|------------|
| `ship-chandlery-documents-prod` | Business documents | Private, signed URLs | KMS (CMK) |
| `ship-chandlery-media-prod` | Product images, logos | Public via CloudFront | SSE-S3 |
| `ship-chandlery-uploads-prod` | Temporary user uploads | Private, presigned | KMS (CMK) |
| `ship-chandlery-exports-prod` | Generated reports | Private, signed URLs | KMS (CMK) |
| `ship-chandlery-ai-prod` | Document AI processing | Private, service access | KMS (CMK) |
| `ship-chandlery-backups-prod` | Database/compliance backups | Private, restricted | KMS (CMK) |
| `ship-chandlery-logs-prod` | Access logs, audit trails | Private, log analysis | SSE-S3 |

**Detailed Prefix Structure:**

```
ship-chandlery-documents-prod/
├── procurement/
│   ├── {org_id}/
│   │   ├── purchase-orders/
│   │   │   └── {year}/{month}/{document_id}.pdf
│   │   ├── invoices/
│   │   │   └── {year}/{month}/{document_id}.pdf
│   │   └── contracts/
│   │       └── {year}/{document_id}.pdf
├── shipping/
│   ├── {org_id}/
│   │   ├── bills-of-lading/
│   │   └── delivery-notes/
└── compliance/
    ├── {org_id}/
    │   ├── certificates/
    │   ├── audit-reports/
    │   └── kyc-documents/

ship-chandlery-media-prod/
├── products/
│   ├── {product_id}/
│   │   ├── original.{ext}
│   │   ├── thumbnail_100x100.webp
│   │   ├── medium_400x400.webp
│   │   └── large_800x800.webp
├── organizations/
│   ├── {org_id}/
│   │   ├── logo.{ext}
│   │   └── banner.{ext}
└── categories/
    └── {category_id}/
        └── icon.svg
```

### Lifecycle Policies

| Prefix | Transition to IA | Transition to Glacier | Expiration | Versioning |
|--------|------------------|----------------------|------------|------------|
| `uploads/temp/` | N/A | N/A | 1 day | Disabled |
| `exports/reports/` | N/A | N/A | 7 days | Disabled |
| `documents/procurement/` | 90 days | 365 days | Never | Enabled |
| `documents/compliance/` | 90 days | 365 days | 7 years | Enabled |
| `media/products/` | N/A | N/A | Never | Enabled |
| `ai-processing/raw/` | 7 days | 30 days | 90 days | Disabled |
| `ai-processing/processed/` | 30 days | 90 days | 1 year | Disabled |
| `backups/` | 30 days | 90 days | 7 years | Enabled |

**Terraform Lifecycle Configuration:**

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  # Temporary uploads - auto-expire
  rule {
    id     = "temp-uploads-cleanup"
    status = "Enabled"
    filter { prefix = "uploads/temp/" }
    expiration { days = 1 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }

  # Export reports - short retention
  rule {
    id     = "exports-cleanup"
    status = "Enabled"
    filter { prefix = "exports/" }
    expiration { days = 7 }
  }

  # Procurement documents - tiered storage
  rule {
    id     = "procurement-tiering"
    status = "Enabled"
    filter { prefix = "documents/procurement/" }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER_IR"
    }
    noncurrent_version_expiration {
      noncurrent_days = 2555  # 7 years
    }
  }

  # Compliance documents - long retention with Object Lock
  rule {
    id     = "compliance-retention"
    status = "Enabled"
    filter { prefix = "documents/compliance/" }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }
    # No expiration - retained indefinitely with Object Lock
  }

  # AI processing artifacts
  rule {
    id     = "ai-raw-cleanup"
    status = "Enabled"
    filter { prefix = "ai-processing/raw/" }

    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }
    expiration { days = 90 }
  }
}
```

### Encryption Approach

| Data Classification | Encryption Method | Key Management | Rationale |
|--------------------|-------------------|----------------|-----------|
| Public media | SSE-S3 | AWS managed | Cost-effective, sufficient for public data |
| Business documents | SSE-KMS (CMK) | Customer managed | Audit trail, access control |
| Financial records | SSE-KMS (CMK) | Customer managed | Compliance requirement |
| PII/Sensitive | SSE-KMS (CMK) | Customer managed | Data protection laws |
| Backups | SSE-KMS (CMK) | Customer managed | Disaster recovery security |

**Bucket Key for Cost Optimization:**

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true  # Reduces KMS API calls by 99%
  }
}
```

### Large Object Upload Strategy

**Multipart Upload Thresholds:**

| File Size | Strategy | Part Size | Max Parts |
|-----------|----------|-----------|-----------|
| < 5 MB | Single PUT | N/A | N/A |
| 5 MB - 100 MB | Multipart (optional) | 5 MB | 20 |
| 100 MB - 5 GB | Multipart (required) | 10 MB | 500 |
| > 5 GB | Multipart (required) | 100 MB | 10,000 |

**Frontend Direct Upload Implementation:**

```typescript
// storage/services/multipart-upload.service.ts
@Injectable()
export class MultipartUploadService {
  private readonly PART_SIZE = 10 * 1024 * 1024; // 10MB

  async initiateUpload(
    key: string,
    contentType: string,
    totalSize: number,
  ): Promise<MultipartUploadInit> {
    const command = new CreateMultipartUploadCommand({
      Bucket: this.bucket,
      Key: key,
      ContentType: contentType,
      ServerSideEncryption: 'aws:kms',
      KMSMasterKeyId: this.kmsKeyId,
    });

    const { UploadId } = await this.s3.send(command);

    const partCount = Math.ceil(totalSize / this.PART_SIZE);
    const presignedUrls: PresignedPart[] = [];

    for (let partNumber = 1; partNumber <= partCount; partNumber++) {
      const uploadPartCommand = new UploadPartCommand({
        Bucket: this.bucket,
        Key: key,
        UploadId,
        PartNumber: partNumber,
      });

      const presignedUrl = await getSignedUrl(this.s3, uploadPartCommand, {
        expiresIn: 3600, // 1 hour per part
      });

      presignedUrls.push({ partNumber, presignedUrl });
    }

    return {
      uploadId: UploadId,
      key,
      partSize: this.PART_SIZE,
      parts: presignedUrls,
    };
  }

  async completeUpload(
    key: string,
    uploadId: string,
    parts: CompletedPart[],
  ): Promise<CompleteUploadResult> {
    const command = new CompleteMultipartUploadCommand({
      Bucket: this.bucket,
      Key: key,
      UploadId: uploadId,
      MultipartUpload: {
        Parts: parts.map(p => ({
          PartNumber: p.partNumber,
          ETag: p.etag,
        })),
      },
    });

    const result = await this.s3.send(command);

    return {
      location: result.Location,
      etag: result.ETag,
      key: result.Key,
    };
  }

  async abortUpload(key: string, uploadId: string): Promise<void> {
    await this.s3.send(new AbortMultipartUploadCommand({
      Bucket: this.bucket,
      Key: key,
      UploadId: uploadId,
    }));
  }
}
```

### Integrity Checks

**Upload Integrity:**

| Method | Implementation | Use Case |
|--------|----------------|----------|
| Content-MD5 | Required for single PUT | Small files < 5MB |
| ETag validation | Compare after upload | All uploads |
| Checksum (SHA256) | `x-amz-checksum-sha256` header | High-value documents |
| Client-side hash | Pre-upload hash, verify post-upload | Critical financial docs |

**Implementation:**

```typescript
async uploadWithIntegrity(
  key: string,
  body: Buffer,
  options: UploadOptions,
): Promise<UploadResult> {
  // Calculate checksums
  const md5 = crypto.createHash('md5').update(body).digest('base64');
  const sha256 = crypto.createHash('sha256').update(body).digest('base64');

  const command = new PutObjectCommand({
    Bucket: this.bucket,
    Key: key,
    Body: body,
    ContentMD5: md5,
    ChecksumAlgorithm: 'SHA256',
    ChecksumSHA256: sha256,
    Metadata: {
      'x-original-sha256': sha256,
      'x-upload-timestamp': new Date().toISOString(),
    },
  });

  const result = await this.s3.send(command);

  // Verify upload by reading back metadata
  const headCommand = new HeadObjectCommand({
    Bucket: this.bucket,
    Key: key,
  });
  const head = await this.s3.send(headCommand);

  if (head.ChecksumSHA256 !== sha256) {
    // Delete corrupted upload
    await this.s3.send(new DeleteObjectCommand({ Bucket: this.bucket, Key: key }));
    throw new Error('Upload integrity check failed');
  }

  return {
    key,
    etag: result.ETag,
    checksum: sha256,
    size: body.length,
  };
}
```

### Open Questions - Answered

- **Q:** How will immutable records and legal holds be handled?
  - **A:** We use S3 Object Lock for compliance and legal hold requirements:

    **Object Lock Configuration:**

    ```hcl
    # Enable Object Lock at bucket creation
    resource "aws_s3_bucket" "compliance_documents" {
      bucket              = "ship-chandlery-compliance-prod"
      object_lock_enabled = true
    }

    resource "aws_s3_bucket_object_lock_configuration" "compliance" {
      bucket = aws_s3_bucket.compliance_documents.id

      rule {
        default_retention {
          mode = "GOVERNANCE"  # GOVERNANCE allows override with special permissions
          years = 7            # 7-year retention for financial documents
        }
      }
    }
    ```

    **Retention Modes:**

    | Mode | Use Case | Override Capability |
    |------|----------|---------------------|
    | GOVERNANCE | Standard compliance | Users with `s3:BypassGovernanceRetention` |
    | COMPLIANCE | Legal/regulatory | No override possible |

    **Legal Hold Implementation:**

    ```typescript
    // Apply legal hold to documents in litigation
    async applyLegalHold(key: string, holdId: string): Promise<void> {
      await this.s3.send(new PutObjectLegalHoldCommand({
        Bucket: this.complianceBucket,
        Key: key,
        LegalHold: { Status: 'ON' },
      }));

      // Log for audit trail
      await this.auditService.log({
        action: 'LEGAL_HOLD_APPLIED',
        resourceType: 'document',
        resourceKey: key,
        holdId,
        timestamp: new Date(),
      });
    }

    // Remove legal hold (requires specific IAM permissions)
    async removeLegalHold(key: string, holdId: string, reason: string): Promise<void> {
      await this.s3.send(new PutObjectLegalHoldCommand({
        Bucket: this.complianceBucket,
        Key: key,
        LegalHold: { Status: 'OFF' },
      }));

      await this.auditService.log({
        action: 'LEGAL_HOLD_REMOVED',
        resourceType: 'document',
        resourceKey: key,
        holdId,
        reason,
        timestamp: new Date(),
      });
    }
    ```

    **Document Categories with Retention:**

    | Document Type | Retention Period | Object Lock Mode | Legal Hold Eligible |
    |---------------|------------------|------------------|---------------------|
    | Invoices | 7 years | GOVERNANCE | Yes |
    | Contracts | 10 years | GOVERNANCE | Yes |
    | Tax documents | 7 years | COMPLIANCE | Yes |
    | KYC documents | Account lifetime + 5 years | GOVERNANCE | Yes |
    | Audit reports | 7 years | GOVERNANCE | Yes |
    | Bills of lading | 3 years | GOVERNANCE | Yes |

---

## References
- [Amazon S3 Documentation](https://docs.aws.amazon.com/s3/)
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)
