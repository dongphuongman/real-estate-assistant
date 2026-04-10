"""
Document management repository classes.

Provides repositories for DocumentDB, DocumentTemplateDB,
SignatureRequestDB, and SignedDocumentDB models.
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    DocumentDB,
    DocumentTemplateDB,
    SignatureRequestDB,
    SignedDocumentDB,
)


class DocumentRepository:
    """Repository for DocumentDB model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        filename: str,
        original_filename: str,
        storage_path: str,
        file_type: str,
        file_size: int,
        property_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
    ) -> DocumentDB:
        """Create a new document record."""
        import json
        from uuid import uuid4

        document = DocumentDB(
            id=str(uuid4()),
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            storage_path=storage_path,
            file_type=file_type,
            file_size=file_size,
            property_id=property_id,
            category=category,
            tags=json.dumps(tags) if tags else None,
            description=description,
            expiry_date=expiry_date,
            ocr_status="pending",
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_by_id(self, document_id: str, user_id: str) -> Optional[DocumentDB]:
        """Get document by ID (scoped to user)."""
        result = await self.session.execute(
            select(DocumentDB).where(DocumentDB.id == document_id, DocumentDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_unscoped(self, document_id: str) -> Optional[DocumentDB]:
        """Get document by ID without user scoping (for admin/internal use)."""
        result = await self.session.execute(select(DocumentDB).where(DocumentDB.id == document_id))
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        property_id: Optional[str] = None,
        category: Optional[str] = None,
        ocr_status: Optional[str] = None,
        tags: Optional[list[str]] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[DocumentDB]:
        """Get documents for a user with optional filters."""
        query = select(DocumentDB).where(DocumentDB.user_id == user_id)

        if property_id:
            query = query.where(DocumentDB.property_id == property_id)
        if category:
            query = query.where(DocumentDB.category == category)
        if ocr_status:
            query = query.where(DocumentDB.ocr_status == ocr_status)
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                (DocumentDB.original_filename.ilike(search_pattern))
                | (DocumentDB.description.ilike(search_pattern))
            )

        # Sorting
        sort_column = getattr(DocumentDB, sort_by, DocumentDB.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: str,
        property_id: Optional[str] = None,
        category: Optional[str] = None,
        ocr_status: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> int:
        """Count documents for a user with optional filters."""
        query = select(func.count(DocumentDB.id)).where(DocumentDB.user_id == user_id)

        if property_id:
            query = query.where(DocumentDB.property_id == property_id)
        if category:
            query = query.where(DocumentDB.category == category)
        if ocr_status:
            query = query.where(DocumentDB.ocr_status == ocr_status)
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                (DocumentDB.original_filename.ilike(search_pattern))
                | (DocumentDB.description.ilike(search_pattern))
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_user_simple(self, user_id: str) -> int:
        """Simple count of all documents for a user."""
        result = await self.session.execute(
            select(func.count(DocumentDB.id)).where(DocumentDB.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_by_property(
        self, user_id: str, property_id: str, limit: int = 50
    ) -> list[DocumentDB]:
        """Get all documents for a property (scoped to user)."""
        result = await self.session.execute(
            select(DocumentDB)
            .where(
                DocumentDB.user_id == user_id,
                DocumentDB.property_id == property_id,
            )
            .order_by(DocumentDB.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_expiring_soon(
        self, user_id: str, days_ahead: int = 30, limit: int = 50
    ) -> list[DocumentDB]:
        """Get documents expiring within specified days."""
        now = datetime.now(UTC)
        expiry_threshold = now + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(DocumentDB)
            .where(
                DocumentDB.user_id == user_id,
                DocumentDB.expiry_date.is_not(None),
                DocumentDB.expiry_date >= now,
                DocumentDB.expiry_date <= expiry_threshold,
                DocumentDB.expiry_notified == False,  # noqa: E712
            )
            .order_by(DocumentDB.expiry_date.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(
        self,
        document: DocumentDB,
        property_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        ocr_status: Optional[str] = None,
        extracted_text: Optional[str] = None,
    ) -> DocumentDB:
        """Update document metadata."""
        import json

        if property_id is not None:
            document.property_id = property_id
        if category is not None:
            document.category = category
        if tags is not None:
            document.tags = json.dumps(tags)
        if description is not None:
            document.description = description
        if expiry_date is not None:
            document.expiry_date = expiry_date
        if ocr_status is not None:
            document.ocr_status = ocr_status
        if extracted_text is not None:
            document.extracted_text = extracted_text

        await self.session.flush()
        return document

    async def mark_expiry_notified(self, document: DocumentDB) -> None:
        """Mark document as expiry notification sent."""
        document.expiry_notified = True
        await self.session.flush()

    async def delete(self, document: DocumentDB) -> None:
        """Delete a document record."""
        await self.session.delete(document)
        await self.session.flush()

    async def delete_by_user(self, user_id: str) -> int:
        """Delete all documents for a user (returns count deleted)."""
        result = await self.session.execute(select(DocumentDB).where(DocumentDB.user_id == user_id))
        documents = list(result.scalars().all())
        count = len(documents)
        for doc in documents:
            await self.session.delete(doc)
        await self.session.flush()
        return count

    async def get_pending_ocr(self, limit: int = 100) -> list[DocumentDB]:
        """Get documents pending OCR processing."""
        result = await self.session.execute(
            select(DocumentDB)
            .where(DocumentDB.ocr_status == "pending")
            .order_by(DocumentDB.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def bulk_update_ocr_status(self, document_ids: list[str], status: str) -> int:
        """Bulk update OCR status for multiple documents."""
        result = await self.session.execute(
            update(DocumentDB).where(DocumentDB.id.in_(document_ids)).values(ocr_status=status)
        )
        await self.session.flush()
        return result.rowcount


class DocumentTemplateRepository:
    """Repository for DocumentTemplateDB operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        name: str,
        template_type: str,
        content: str,
        description: Optional[str] = None,
        variables: Optional[dict] = None,
        is_default: bool = False,
    ) -> DocumentTemplateDB:
        """Create a new document template."""
        from uuid import uuid4

        template = DocumentTemplateDB(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            template_type=template_type,
            content=content,
            description=description,
            variables=variables,
            is_default=is_default,
        )
        self.session.add(template)
        await self.session.flush()
        return template

    async def get_by_id(
        self, template_id: str, user_id: Optional[str] = None
    ) -> Optional[DocumentTemplateDB]:
        """Get template by ID, optionally scoped to user."""
        query = select(DocumentTemplateDB).where(DocumentTemplateDB.id == template_id)
        if user_id:
            query = query.where(DocumentTemplateDB.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        template_type: Optional[str] = None,
        include_defaults: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> list[DocumentTemplateDB]:
        """Get templates for a user with optional filtering."""
        query = select(DocumentTemplateDB).where(DocumentTemplateDB.user_id == user_id)
        if template_type:
            query = query.where(DocumentTemplateDB.template_type == template_type)
        query = query.order_by(DocumentTemplateDB.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: str,
        template_type: Optional[str] = None,
    ) -> int:
        """Count templates for a user."""
        query = (
            select(func.count())
            .select_from(DocumentTemplateDB)
            .where(DocumentTemplateDB.user_id == user_id)
        )
        if template_type:
            query = query.where(DocumentTemplateDB.template_type == template_type)
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def get_default_template(
        self, template_type: str, user_id: Optional[str] = None
    ) -> Optional[DocumentTemplateDB]:
        """Get the default template for a type."""
        query = select(DocumentTemplateDB).where(
            DocumentTemplateDB.template_type == template_type,
            DocumentTemplateDB.is_default.is_(True),
        )
        if user_id:
            query = query.where(DocumentTemplateDB.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(
        self,
        template: DocumentTemplateDB,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        variables: Optional[dict] = None,
        is_default: Optional[bool] = None,
    ) -> DocumentTemplateDB:
        """Update template fields."""
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if content is not None:
            template.content = content
        if variables is not None:
            template.variables = variables
        if is_default is not None:
            template.is_default = is_default
        await self.session.flush()
        return template

    async def delete(self, template: DocumentTemplateDB) -> None:
        """Delete a template."""
        await self.session.delete(template)
        await self.session.flush()


class SignatureRequestRepository:
    """Repository for SignatureRequestDB operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        title: str,
        provider: str,
        signers: list[dict],
        document_id: Optional[str] = None,
        template_id: Optional[str] = None,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        property_id: Optional[str] = None,
        variables: Optional[dict] = None,
        document_content_hash: Optional[str] = None,
        provider_envelope_id: Optional[str] = None,
        status: str = "draft",
        expires_at: Optional[datetime] = None,
    ) -> SignatureRequestDB:
        """Create a new signature request."""
        from uuid import uuid4

        request = SignatureRequestDB(
            id=str(uuid4()),
            user_id=user_id,
            title=title,
            subject=subject,
            message=message,
            provider=provider,
            provider_envelope_id=provider_envelope_id,
            document_id=document_id,
            template_id=template_id,
            property_id=property_id,
            document_content_hash=document_content_hash,
            signers=signers,
            variables=variables,
            status=status,
            expires_at=expires_at,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_by_id(
        self, request_id: str, user_id: Optional[str] = None
    ) -> Optional[SignatureRequestDB]:
        """Get signature request by ID, optionally scoped to user."""
        query = select(SignatureRequestDB).where(SignatureRequestDB.id == request_id)
        if user_id:
            query = query.where(SignatureRequestDB.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_provider_envelope_id(
        self, provider: str, envelope_id: str
    ) -> Optional[SignatureRequestDB]:
        """Get signature request by provider envelope ID."""
        result = await self.session.execute(
            select(SignatureRequestDB).where(
                SignatureRequestDB.provider == provider,
                SignatureRequestDB.provider_envelope_id == envelope_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        property_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[SignatureRequestDB]:
        """Get signature requests for a user with filtering."""
        query = select(SignatureRequestDB).where(SignatureRequestDB.user_id == user_id)
        if status:
            query = query.where(SignatureRequestDB.status == status)
        if property_id:
            query = query.where(SignatureRequestDB.property_id == property_id)
        query = query.order_by(SignatureRequestDB.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> int:
        """Count signature requests for a user."""
        query = (
            select(func.count())
            .select_from(SignatureRequestDB)
            .where(SignatureRequestDB.user_id == user_id)
        )
        if status:
            query = query.where(SignatureRequestDB.status == status)
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def update_status(
        self,
        request: SignatureRequestDB,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        viewed_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> SignatureRequestDB:
        """Update signature request status."""
        request.status = status
        if error_message is not None:
            request.error_message = error_message
        if sent_at is not None:
            request.sent_at = sent_at
        if viewed_at is not None:
            request.viewed_at = viewed_at
        if completed_at is not None:
            request.completed_at = completed_at
        if cancelled_at is not None:
            request.cancelled_at = cancelled_at
        await self.session.flush()
        return request

    async def update_signers(
        self, request: SignatureRequestDB, signers: list[dict]
    ) -> SignatureRequestDB:
        """Update signer information (e.g., status changes from webhook)."""
        request.signers = signers
        await self.session.flush()
        return request

    async def update_provider_envelope_id(
        self, request: SignatureRequestDB, envelope_id: str
    ) -> SignatureRequestDB:
        """Update provider envelope ID after sending."""
        request.provider_envelope_id = envelope_id
        await self.session.flush()
        return request

    async def mark_reminder_sent(self, request: SignatureRequestDB) -> SignatureRequestDB:
        """Mark that a reminder was sent."""
        request.reminder_sent_at = datetime.now(UTC)
        request.reminder_count += 1
        await self.session.flush()
        return request

    async def get_expiring_requests(self, within_hours: int = 24) -> list[SignatureRequestDB]:
        """Get requests expiring within specified hours that haven't been notified."""
        threshold = datetime.now(UTC) + timedelta(hours=within_hours)
        result = await self.session.execute(
            select(SignatureRequestDB).where(
                SignatureRequestDB.status.in_(["sent", "viewed", "partially_signed"]),
                SignatureRequestDB.expires_at <= threshold,
                SignatureRequestDB.expires_at > datetime.now(UTC),
            )
        )
        return list(result.scalars().all())

    async def cancel(self, request: SignatureRequestDB) -> SignatureRequestDB:
        """Cancel a signature request."""
        request.status = "cancelled"
        request.cancelled_at = datetime.now(UTC)
        await self.session.flush()
        return request

    async def delete(self, request: SignatureRequestDB) -> None:
        """Delete a signature request."""
        await self.session.delete(request)
        await self.session.flush()


class SignedDocumentRepository:
    """Repository for SignedDocumentDB operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        signature_request_id: str,
        storage_path: str,
        file_size: int,
        document_id: Optional[str] = None,
        provider_document_id: Optional[str] = None,
        certificate_url: Optional[str] = None,
        signature_hash: Optional[str] = None,
    ) -> SignedDocumentDB:
        """Create a signed document record."""
        from uuid import uuid4

        signed_doc = SignedDocumentDB(
            id=str(uuid4()),
            signature_request_id=signature_request_id,
            document_id=document_id,
            storage_path=storage_path,
            file_size=file_size,
            provider_document_id=provider_document_id,
            certificate_url=certificate_url,
            signature_hash=signature_hash,
        )
        self.session.add(signed_doc)
        await self.session.flush()
        return signed_doc

    async def get_by_id(self, signed_doc_id: str) -> Optional[SignedDocumentDB]:
        """Get signed document by ID."""
        result = await self.session.execute(
            select(SignedDocumentDB).where(SignedDocumentDB.id == signed_doc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_signature_request(
        self, signature_request_id: str
    ) -> Optional[SignedDocumentDB]:
        """Get signed document by signature request ID."""
        result = await self.session.execute(
            select(SignedDocumentDB).where(
                SignedDocumentDB.signature_request_id == signature_request_id
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, signed_doc: SignedDocumentDB) -> None:
        """Delete a signed document record."""
        await self.session.delete(signed_doc)
        await self.session.flush()
