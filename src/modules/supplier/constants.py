"""Supplier tier capabilities, document requirements, and valid status transitions."""

from __future__ import annotations

from src.models.enums import KycDocumentType, OnboardingStatus, SupplierTier

TIER_CAPABILITIES: dict[SupplierTier, dict] = {
    SupplierTier.PENDING: {
        "max_quotes": 0,
        "can_bid_rfq": False,
        "financing_eligible": False,
        "visibility": "HIDDEN",
        "commission_percent": 0,
        "payment_terms": None,
    },
    SupplierTier.BASIC: {
        "max_quotes": 5,
        "can_bid_rfq": True,
        "financing_eligible": False,
        "visibility": "LIMITED",
        "commission_percent": 5,
        "payment_terms": "Net 15",
    },
    SupplierTier.VERIFIED: {
        "max_quotes": 20,
        "can_bid_rfq": True,
        "financing_eligible": True,
        "visibility": "STANDARD",
        "commission_percent": 4,
        "payment_terms": "Net 30",
    },
    SupplierTier.PREFERRED: {
        "max_quotes": 50,
        "can_bid_rfq": True,
        "financing_eligible": True,
        "visibility": "ENHANCED",
        "commission_percent": 3,
        "payment_terms": "Net 45",
    },
    SupplierTier.PREMIUM: {
        "max_quotes": None,
        "can_bid_rfq": True,
        "financing_eligible": True,
        "visibility": "ENHANCED",
        "commission_percent": 2,
        "payment_terms": "Net 60",
    },
}

# Documents required per tier. Each value is a set of KycDocumentType members
# that must have at least one VERIFIED document for the supplier to qualify.
TIER_DOCUMENT_REQUIREMENTS: dict[SupplierTier, set[KycDocumentType]] = {
    SupplierTier.BASIC: {
        KycDocumentType.GST_CERTIFICATE,
        KycDocumentType.PAN_CARD,
        KycDocumentType.ADDRESS_PROOF,
    },
    SupplierTier.VERIFIED: {
        KycDocumentType.GST_CERTIFICATE,
        KycDocumentType.PAN_CARD,
        KycDocumentType.ADDRESS_PROOF,
        KycDocumentType.INCORPORATION_CERT,
        KycDocumentType.BANK_STATEMENT,
        KycDocumentType.REFERENCE_LETTER,
    },
    SupplierTier.PREFERRED: {
        KycDocumentType.GST_CERTIFICATE,
        KycDocumentType.PAN_CARD,
        KycDocumentType.ADDRESS_PROOF,
        KycDocumentType.INCORPORATION_CERT,
        KycDocumentType.BANK_STATEMENT,
        KycDocumentType.REFERENCE_LETTER,
        KycDocumentType.AUDITED_FINANCIALS,
        KycDocumentType.INSURANCE_CERTIFICATE,
        KycDocumentType.QUALITY_CERTIFICATION,
    },
    SupplierTier.PREMIUM: {
        KycDocumentType.GST_CERTIFICATE,
        KycDocumentType.PAN_CARD,
        KycDocumentType.ADDRESS_PROOF,
        KycDocumentType.INCORPORATION_CERT,
        KycDocumentType.BANK_STATEMENT,
        KycDocumentType.REFERENCE_LETTER,
        KycDocumentType.AUDITED_FINANCIALS,
        KycDocumentType.INSURANCE_CERTIFICATE,
        KycDocumentType.QUALITY_CERTIFICATION,
        KycDocumentType.DIRECTOR_ID,
    },
}

# Valid onboarding status transitions: current_status -> {allowed next statuses}
VALID_STATUS_TRANSITIONS: dict[OnboardingStatus, set[OnboardingStatus]] = {
    OnboardingStatus.STARTED: {
        OnboardingStatus.DOCUMENTS_PENDING,
    },
    OnboardingStatus.DOCUMENTS_PENDING: {
        OnboardingStatus.DOCUMENTS_SUBMITTED,
    },
    OnboardingStatus.DOCUMENTS_SUBMITTED: {
        OnboardingStatus.VERIFICATION_IN_PROGRESS,
        OnboardingStatus.MANUAL_REVIEW_PENDING,
    },
    OnboardingStatus.VERIFICATION_IN_PROGRESS: {
        OnboardingStatus.VERIFICATION_PASSED,
        OnboardingStatus.VERIFICATION_FAILED,
    },
    OnboardingStatus.VERIFICATION_PASSED: {
        OnboardingStatus.MANUAL_REVIEW_PENDING,
        OnboardingStatus.APPROVED,
    },
    OnboardingStatus.VERIFICATION_FAILED: {
        OnboardingStatus.DOCUMENTS_PENDING,
        OnboardingStatus.REJECTED,
    },
    OnboardingStatus.MANUAL_REVIEW_PENDING: {
        OnboardingStatus.MANUAL_REVIEW_IN_PROGRESS,
    },
    OnboardingStatus.MANUAL_REVIEW_IN_PROGRESS: {
        OnboardingStatus.APPROVED,
        OnboardingStatus.REJECTED,
    },
    OnboardingStatus.APPROVED: {
        OnboardingStatus.SUSPENDED,
    },
    OnboardingStatus.REJECTED: {
        OnboardingStatus.DOCUMENTS_PENDING,
    },
    OnboardingStatus.SUSPENDED: {
        OnboardingStatus.APPROVED,
    },
}
