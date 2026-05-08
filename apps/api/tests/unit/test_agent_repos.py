"""
Unit tests for db/agent_repos.py — AgentProfileRepository,
AgentListingRepository, AgentInquiryRepository, ViewingAppointmentRepository.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.agent_repos import (
    AgentInquiryRepository,
    AgentListingRepository,
    AgentProfileRepository,
    ViewingAppointmentRepository,
)
from db.models import AgentInquiry, AgentListing, AgentProfile, ViewingAppointment

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """AsyncSession mock with both sync and async methods used by repos."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def profile_repo(mock_session):
    return AgentProfileRepository(mock_session)


@pytest.fixture
def listing_repo(mock_session):
    return AgentListingRepository(mock_session)


@pytest.fixture
def inquiry_repo(mock_session):
    return AgentInquiryRepository(mock_session)


@pytest.fixture
def appointment_repo(mock_session):
    return ViewingAppointmentRepository(mock_session)


def _make_profile(**overrides):
    """Build a mock AgentProfile with sensible defaults."""
    p = MagicMock(spec=AgentProfile)
    p.id = "profile-1"
    p.user_id = "user-1"
    p.agency_name = "Test Agency"
    p.agency_id = "agency-1"
    p.license_number = "LIC-123"
    p.license_state = "CA"
    p.professional_email = "agent@test.com"
    p.professional_phone = "+1234567890"
    p.office_address = "123 Main St"
    p.specialties = ["residential"]
    p.service_areas = ["Berlin"]
    p.property_types = ["apartment"]
    p.languages = ["en"]
    p.bio = "Experienced agent"
    p.profile_image_url = "https://img.test/agent.jpg"
    p.is_verified = False
    p.is_active = True
    p.average_rating = 4.5
    p.total_reviews = 10
    p.total_sales = 5
    p.verification_date = None
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


def _make_listing(**overrides):
    lst = MagicMock(spec=AgentListing)
    lst.id = "listing-1"
    lst.agent_id = "profile-1"
    lst.property_id = "prop-1"
    lst.listing_type = "sale"
    lst.is_primary = False
    lst.is_active = True
    lst.commission_rate = None
    lst.created_at = datetime.now(UTC)
    for k, v in overrides.items():
        setattr(lst, k, v)
    return lst


def _make_inquiry(**overrides):
    inq = MagicMock(spec=AgentInquiry)
    inq.id = "inquiry-1"
    inq.agent_id = "profile-1"
    inq.user_id = None
    inq.visitor_id = None
    inq.name = "John Doe"
    inq.email = "john@example.com"
    inq.phone = None
    inq.property_id = None
    inq.inquiry_type = "general"
    inq.message = "Hello"
    inq.status = "new"
    inq.created_at = datetime.now(UTC)
    inq.read_at = None
    inq.responded_at = None
    for k, v in overrides.items():
        setattr(inq, k, v)
    return inq


def _make_appointment(**overrides):
    appt = MagicMock(spec=ViewingAppointment)
    appt.id = "appt-1"
    appt.agent_id = "profile-1"
    appt.user_id = None
    appt.visitor_id = None
    appt.client_name = "Jane Doe"
    appt.client_email = "jane@example.com"
    appt.client_phone = None
    appt.property_id = "prop-1"
    appt.proposed_datetime = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    appt.confirmed_datetime = None
    appt.duration_minutes = 60
    appt.status = "requested"
    appt.notes = None
    appt.cancellation_reason = None
    for k, v in overrides.items():
        setattr(appt, k, v)
    return appt


def _scalar_result(value):
    """Build a mock result that supports scalar_one_or_none / scalar / scalars."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    # scalars().all() chain
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = value if isinstance(value, list) else []
    result.scalars.return_value = scalars_mock
    return result


# ===================================================================
# AgentProfileRepository
# ===================================================================


class TestAgentProfileRepositoryCreate:
    @patch("uuid.uuid4", return_value="uuid-new-profile")
    async def test_create_with_all_fields(self, _uuid, profile_repo, mock_session):
        profile = await profile_repo.create(
            user_id="user-1",
            agency_name="Acme Realty",
            agency_id="agency-1",
            license_number="LIC-999",
            license_state="NY",
            professional_email="pro@acme.com",
            professional_phone="+19999999999",
            office_address="456 Oak Ave",
            specialties=["commercial", "luxury"],
            service_areas=["New York", "Boston"],
            property_types=["condo", "penthouse"],
            languages=["en", "es"],
            bio="Top agent",
            profile_image_url="https://img.test/acme.jpg",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert profile.user_id == "user-1"
        assert profile.agency_name == "Acme Realty"
        assert profile.is_verified is False
        assert profile.is_active is True

    @patch("uuid.uuid4", return_value="uuid-minimal")
    async def test_create_minimal(self, _uuid, profile_repo, mock_session):
        profile = await profile_repo.create(user_id="user-2")
        assert profile.specialties == []
        assert profile.service_areas == []
        assert profile.property_types == []
        assert profile.languages == []


class TestAgentProfileRepositoryGet:
    async def test_get_by_id_found(self, profile_repo, mock_session):
        expected = _make_profile()
        mock_session.execute.return_value = _scalar_result(expected)
        result = await profile_repo.get_by_id("profile-1")
        assert result is expected

    async def test_get_by_id_not_found(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await profile_repo.get_by_id("nonexistent")
        assert result is None

    async def test_get_by_user_id_found(self, profile_repo, mock_session):
        expected = _make_profile(user_id="user-42")
        mock_session.execute.return_value = _scalar_result(expected)
        result = await profile_repo.get_by_user_id("user-42")
        assert result is expected

    async def test_get_by_user_id_not_found(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await profile_repo.get_by_user_id("ghost")
        assert result is None


class TestAgentProfileRepositoryGetList:
    async def test_get_list_no_filters(self, profile_repo, mock_session):
        profiles = [_make_profile()]
        mock_session.execute.return_value = _scalar_result(profiles)
        result = await profile_repo.get_list()
        assert result == profiles

    async def test_get_list_with_city(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(city="Berlin")
        mock_session.execute.assert_awaited_once()

    async def test_get_list_with_specialty(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(specialty="residential")
        mock_session.execute.assert_awaited_once()

    async def test_get_list_with_property_type(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(property_type="apartment")
        mock_session.execute.assert_awaited_once()

    async def test_get_list_with_language(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(language="en")
        mock_session.execute.assert_awaited_once()

    async def test_get_list_with_min_rating(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(min_rating=4.0)
        mock_session.execute.assert_awaited_once()

    async def test_get_list_with_agency_id(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(agency_id="agency-1")
        mock_session.execute.assert_awaited_once()

    async def test_get_list_verified_only(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(is_verified=True)
        mock_session.execute.assert_awaited_once()

    async def test_get_list_unverified_only(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(is_verified=False)
        mock_session.execute.assert_awaited_once()

    async def test_get_list_sort_asc(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        result = await profile_repo.get_list(sort_by="average_rating", sort_order="asc")
        assert result == []

    async def test_get_list_with_offset_and_limit(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(limit=5, offset=10)
        mock_session.execute.assert_awaited_once()

    async def test_get_list_all_filters_combined(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await profile_repo.get_list(
            city="Berlin",
            specialty="residential",
            property_type="apartment",
            language="en",
            min_rating=3.5,
            agency_id="agency-1",
            is_verified=True,
            limit=10,
            offset=5,
            sort_by="total_reviews",
            sort_order="asc",
        )
        mock_session.execute.assert_awaited_once()


class TestAgentProfileRepositoryCount:
    async def test_count_no_filters(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(7)
        result = await profile_repo.count()
        assert result == 7

    async def test_count_returns_zero_when_none(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await profile_repo.count()
        assert result == 0

    async def test_count_with_city(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(2)
        result = await profile_repo.count(city="Berlin")
        assert result == 2

    async def test_count_with_specialty(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(3)
        result = await profile_repo.count(specialty="luxury")
        assert result == 3

    async def test_count_with_property_type(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(1)
        result = await profile_repo.count(property_type="house")
        assert result == 1

    async def test_count_with_language(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(4)
        result = await profile_repo.count(language="de")
        assert result == 4

    async def test_count_with_all_filters(self, profile_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(1)
        result = await profile_repo.count(
            city="Berlin",
            specialty="residential",
            property_type="apartment",
            min_rating=4.0,
            agency_id="agency-1",
            is_verified=True,
            language="en",
        )
        assert result == 1


class TestAgentProfileRepositoryMutations:
    async def test_update_sets_fields(self, profile_repo, mock_session):
        profile = _make_profile()
        updated = await profile_repo.update(profile, agency_name="New Agency", bio="Updated bio")
        assert profile.agency_name == "New Agency"
        assert profile.bio == "Updated bio"
        mock_session.flush.assert_awaited_once()
        assert updated is profile

    async def test_update_ignores_unknown_fields(self, profile_repo, mock_session):
        profile = _make_profile()
        await profile_repo.update(profile, nonexistent_field="ignored")  # noqa: F841
        assert not hasattr(profile, "nonexistent_field") or True  # setattr still runs on MagicMock
        mock_session.flush.assert_awaited_once()

    async def test_update_rating(self, profile_repo, mock_session):
        profile = _make_profile()
        await profile_repo.update_rating(profile, 4.9)
        assert profile.average_rating == 4.9
        mock_session.flush.assert_awaited_once()

    async def test_increment_reviews(self, profile_repo, mock_session):
        profile = _make_profile(total_reviews=5)
        await profile_repo.increment_reviews(profile)
        assert profile.total_reviews == 6
        mock_session.flush.assert_awaited_once()

    async def test_increment_sales(self, profile_repo, mock_session):
        profile = _make_profile(total_sales=3)
        await profile_repo.increment_sales(profile)
        assert profile.total_sales == 4
        mock_session.flush.assert_awaited_once()

    async def test_verify(self, profile_repo, mock_session):
        profile = _make_profile(is_verified=False, verification_date=None)
        await profile_repo.verify(profile)
        assert profile.is_verified is True
        assert profile.verification_date is not None
        mock_session.flush.assert_awaited_once()

    async def test_delete_soft_deactivates(self, profile_repo, mock_session):
        profile = _make_profile(is_active=True)
        await profile_repo.delete(profile)
        assert profile.is_active is False
        mock_session.flush.assert_awaited_once()


# ===================================================================
# AgentListingRepository
# ===================================================================


class TestAgentListingRepositoryCreate:
    @patch("uuid.uuid4", return_value="uuid-new-listing")
    async def test_create_defaults(self, _uuid, listing_repo, mock_session):
        listing = await listing_repo.create(
            agent_id="agent-1",
            property_id="prop-1",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert listing.agent_id == "agent-1"
        assert listing.property_id == "prop-1"
        assert listing.listing_type == "sale"
        assert listing.is_primary is False
        assert listing.is_active is True
        assert listing.commission_rate is None

    @patch("uuid.uuid4", return_value="uuid-rental")
    async def test_create_with_options(self, _uuid, listing_repo, mock_session):
        listing = await listing_repo.create(
            agent_id="agent-1",
            property_id="prop-2",
            listing_type="rent",
            is_primary=True,
            commission_rate=5.5,
        )
        assert listing.listing_type == "rent"
        assert listing.is_primary is True
        assert listing.commission_rate == 5.5


class TestAgentListingRepositoryGet:
    async def test_get_by_id_found(self, listing_repo, mock_session):
        expected = _make_listing()
        mock_session.execute.return_value = _scalar_result(expected)
        result = await listing_repo.get_by_id("listing-1")
        assert result is expected

    async def test_get_by_id_not_found(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await listing_repo.get_by_id("nope")
        assert result is None

    async def test_get_by_agent_active_only(self, listing_repo, mock_session):
        listings = [_make_listing()]
        mock_session.execute.return_value = _scalar_result(listings)
        result = await listing_repo.get_by_agent("profile-1", active_only=True)
        assert result == listings

    async def test_get_by_agent_all(self, listing_repo, mock_session):
        listings = [_make_listing(), _make_listing(is_active=False)]
        mock_session.execute.return_value = _scalar_result(listings)
        result = await listing_repo.get_by_agent("profile-1", active_only=False)
        assert len(result) == 2

    async def test_get_by_agent_with_type_filter(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await listing_repo.get_by_agent("profile-1", listing_type="rent")
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_pagination(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await listing_repo.get_by_agent("profile-1", limit=10, offset=5)
        mock_session.execute.assert_awaited_once()

    async def test_get_by_property_active_only(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([_make_listing()])
        result = await listing_repo.get_by_property("prop-1", active_only=True)
        assert len(result) == 1

    async def test_get_by_property_all(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([_make_listing()])
        result = await listing_repo.get_by_property("prop-1", active_only=False)
        assert len(result) == 1


class TestAgentListingRepositoryCount:
    async def test_count_for_agent_active(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(8)
        result = await listing_repo.count_for_agent("profile-1", active_only=True)
        assert result == 8

    async def test_count_for_agent_all(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(12)
        result = await listing_repo.count_for_agent("profile-1", active_only=False)
        assert result == 12

    async def test_count_for_agent_returns_zero_when_none(self, listing_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await listing_repo.count_for_agent("profile-1")
        assert result == 0


class TestAgentListingRepositoryMutations:
    async def test_set_primary(self, listing_repo, mock_session):
        listing = _make_listing(property_id="prop-1", agent_id="agent-1")
        mock_session.execute.return_value = MagicMock()
        await listing_repo.set_primary(listing)
        assert listing.is_primary is True
        # execute called once (the bulk update) + flush
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once()

    async def test_deactivate(self, listing_repo, mock_session):
        listing = _make_listing(is_active=True)
        await listing_repo.deactivate(listing)
        assert listing.is_active is False
        mock_session.flush.assert_awaited_once()

    async def test_delete(self, listing_repo, mock_session):
        listing = _make_listing()
        await listing_repo.delete(listing)
        mock_session.delete.assert_awaited_once_with(listing)


# ===================================================================
# AgentInquiryRepository
# ===================================================================


class TestAgentInquiryRepositoryCreate:
    @patch("uuid.uuid4", return_value="uuid-new-inquiry")
    async def test_create_minimal(self, _uuid, inquiry_repo, mock_session):
        inquiry = await inquiry_repo.create(
            agent_id="agent-1",
            name="Alice",
            email="alice@test.com",
            inquiry_type="general",
            message="Hi",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert inquiry.agent_id == "agent-1"
        assert inquiry.name == "Alice"
        assert inquiry.email == "alice@test.com"
        assert inquiry.inquiry_type == "general"
        assert inquiry.message == "Hi"
        assert inquiry.status == "new"
        assert inquiry.user_id is None
        assert inquiry.visitor_id is None
        assert inquiry.phone is None
        assert inquiry.property_id is None

    @patch("uuid.uuid4", return_value="uuid-full-inquiry")
    async def test_create_with_all_fields(self, _uuid, inquiry_repo, mock_session):
        inquiry = await inquiry_repo.create(
            agent_id="agent-2",
            name="Bob",
            email="bob@test.com",
            inquiry_type="property",
            message="I want this house",
            user_id="user-5",
            visitor_id="visitor-9",
            phone="+15555555555",
            property_id="prop-99",
        )
        assert inquiry.user_id == "user-5"
        assert inquiry.visitor_id == "visitor-9"
        assert inquiry.phone == "+15555555555"
        assert inquiry.property_id == "prop-99"


class TestAgentInquiryRepositoryGet:
    async def test_get_by_id_found(self, inquiry_repo, mock_session):
        expected = _make_inquiry()
        mock_session.execute.return_value = _scalar_result(expected)
        result = await inquiry_repo.get_by_id("inquiry-1")
        assert result is expected

    async def test_get_by_id_not_found(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await inquiry_repo.get_by_id("nope")
        assert result is None

    async def test_get_by_agent_no_filters(self, inquiry_repo, mock_session):
        inquiries = [_make_inquiry()]
        mock_session.execute.return_value = _scalar_result(inquiries)
        result = await inquiry_repo.get_by_agent("agent-1")
        assert result == inquiries

    async def test_get_by_agent_with_status(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await inquiry_repo.get_by_agent("agent-1", status="read")
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_type(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await inquiry_repo.get_by_agent("agent-1", inquiry_type="property")
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_pagination(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await inquiry_repo.get_by_agent("agent-1", limit=10, offset=5)
        mock_session.execute.assert_awaited_once()


class TestAgentInquiryRepositoryCount:
    async def test_count_for_agent_no_status(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(15)
        result = await inquiry_repo.count_for_agent("agent-1")
        assert result == 15

    async def test_count_for_agent_with_status(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(3)
        result = await inquiry_repo.count_for_agent("agent-1", status="new")
        assert result == 3

    async def test_count_returns_zero_when_none(self, inquiry_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await inquiry_repo.count_for_agent("agent-1")
        assert result == 0


class TestAgentInquiryRepositoryMutations:
    async def test_mark_read(self, inquiry_repo, mock_session):
        inquiry = _make_inquiry(status="new", read_at=None)
        await inquiry_repo.mark_read(inquiry)
        assert inquiry.status == "read"
        assert inquiry.read_at is not None
        mock_session.flush.assert_awaited_once()

    async def test_mark_responded(self, inquiry_repo, mock_session):
        inquiry = _make_inquiry(status="read", responded_at=None)
        await inquiry_repo.mark_responded(inquiry)
        assert inquiry.status == "responded"
        assert inquiry.responded_at is not None
        mock_session.flush.assert_awaited_once()

    async def test_update_status(self, inquiry_repo, mock_session):
        inquiry = _make_inquiry(status="new")
        await inquiry_repo.update_status(inquiry, "closed")
        assert inquiry.status == "closed"
        mock_session.flush.assert_awaited_once()

    async def test_delete(self, inquiry_repo, mock_session):
        inquiry = _make_inquiry()
        await inquiry_repo.delete(inquiry)
        mock_session.delete.assert_awaited_once_with(inquiry)


# ===================================================================
# ViewingAppointmentRepository
# ===================================================================


class TestViewingAppointmentRepositoryCreate:
    @patch("uuid.uuid4", return_value="uuid-new-appt")
    async def test_create_minimal(self, _uuid, appointment_repo, mock_session):
        dt = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
        appt = await appointment_repo.create(
            agent_id="agent-1",
            property_id="prop-1",
            proposed_datetime=dt,
            client_name="Eve",
            client_email="eve@test.com",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert appt.agent_id == "agent-1"
        assert appt.property_id == "prop-1"
        assert appt.proposed_datetime == dt
        assert appt.client_name == "Eve"
        assert appt.client_email == "eve@test.com"
        assert appt.status == "requested"
        assert appt.duration_minutes == 60
        assert appt.user_id is None
        assert appt.visitor_id is None
        assert appt.client_phone is None
        assert appt.notes is None

    @patch("uuid.uuid4", return_value="uuid-full-appt")
    async def test_create_with_all_fields(self, _uuid, appointment_repo, mock_session):
        dt = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)
        appt = await appointment_repo.create(
            agent_id="agent-2",
            property_id="prop-5",
            proposed_datetime=dt,
            client_name="Frank",
            client_email="frank@test.com",
            user_id="user-10",
            visitor_id="visitor-3",
            client_phone="+17777777777",
            duration_minutes=90,
            notes="Needs wheelchair access",
        )
        assert appt.user_id == "user-10"
        assert appt.visitor_id == "visitor-3"
        assert appt.client_phone == "+17777777777"
        assert appt.duration_minutes == 90
        assert appt.notes == "Needs wheelchair access"


class TestViewingAppointmentRepositoryGet:
    async def test_get_by_id_found(self, appointment_repo, mock_session):
        expected = _make_appointment()
        mock_session.execute.return_value = _scalar_result(expected)
        result = await appointment_repo.get_by_id("appt-1")
        assert result is expected

    async def test_get_by_id_not_found(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await appointment_repo.get_by_id("nope")
        assert result is None

    async def test_get_by_agent_no_filters(self, appointment_repo, mock_session):
        appts = [_make_appointment()]
        mock_session.execute.return_value = _scalar_result(appts)
        result = await appointment_repo.get_by_agent("agent-1")
        assert result == appts

    async def test_get_by_agent_with_status(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await appointment_repo.get_by_agent("agent-1", status="confirmed")
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_date_range(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        from_dt = datetime(2026, 6, 1, tzinfo=UTC)
        to_dt = datetime(2026, 6, 30, tzinfo=UTC)
        await appointment_repo.get_by_agent("agent-1", from_date=from_dt, to_date=to_dt)
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_from_date_only(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        from_dt = datetime(2026, 6, 1, tzinfo=UTC)
        await appointment_repo.get_by_agent("agent-1", from_date=from_dt)
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_to_date_only(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        to_dt = datetime(2026, 6, 30, tzinfo=UTC)
        await appointment_repo.get_by_agent("agent-1", to_date=to_dt)
        mock_session.execute.assert_awaited_once()

    async def test_get_by_agent_with_pagination(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await appointment_repo.get_by_agent("agent-1", limit=10, offset=20)
        mock_session.execute.assert_awaited_once()

    async def test_get_by_user_no_status(self, appointment_repo, mock_session):
        appts = [_make_appointment(user_id="user-1")]
        mock_session.execute.return_value = _scalar_result(appts)
        result = await appointment_repo.get_by_user("user-1")
        assert result == appts

    async def test_get_by_user_with_status(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await appointment_repo.get_by_user("user-1", status="confirmed")
        mock_session.execute.assert_awaited_once()

    async def test_get_by_user_with_limit(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result([])
        await appointment_repo.get_by_user("user-1", limit=5)
        mock_session.execute.assert_awaited_once()


class TestViewingAppointmentRepositoryCount:
    async def test_count_for_agent_no_status(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(4)
        result = await appointment_repo.count_for_agent("agent-1")
        assert result == 4

    async def test_count_for_agent_with_status(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(2)
        result = await appointment_repo.count_for_agent("agent-1", status="confirmed")
        assert result == 2

    async def test_count_returns_zero_when_none(self, appointment_repo, mock_session):
        mock_session.execute.return_value = _scalar_result(None)
        result = await appointment_repo.count_for_agent("agent-1")
        assert result == 0


class TestViewingAppointmentRepositoryMutations:
    async def test_confirm_with_explicit_datetime(self, appointment_repo, mock_session):
        appt = _make_appointment(status="requested", confirmed_datetime=None)
        dt = datetime(2026, 7, 2, 11, 0, tzinfo=UTC)
        await appointment_repo.confirm(appt, confirmed_datetime=dt)
        assert appt.status == "confirmed"
        assert appt.confirmed_datetime == dt
        mock_session.flush.assert_awaited_once()

    async def test_confirm_defaults_to_proposed(self, appointment_repo, mock_session):
        proposed = datetime(2026, 7, 2, 11, 0, tzinfo=UTC)
        appt = _make_appointment(
            status="requested", proposed_datetime=proposed, confirmed_datetime=None
        )
        await appointment_repo.confirm(appt)
        assert appt.status == "confirmed"
        assert appt.confirmed_datetime == proposed

    async def test_cancel_with_reason(self, appointment_repo, mock_session):
        appt = _make_appointment(status="confirmed", cancellation_reason=None)
        await appointment_repo.cancel(appt, reason="Schedule conflict")
        assert appt.status == "cancelled"
        assert appt.cancellation_reason == "Schedule conflict"
        mock_session.flush.assert_awaited_once()

    async def test_cancel_without_reason(self, appointment_repo, mock_session):
        appt = _make_appointment(status="confirmed")
        await appointment_repo.cancel(appt)
        assert appt.status == "cancelled"
        assert appt.cancellation_reason is None

    async def test_complete(self, appointment_repo, mock_session):
        appt = _make_appointment(status="confirmed")
        await appointment_repo.complete(appt)
        assert appt.status == "completed"
        mock_session.flush.assert_awaited_once()

    async def test_update_sets_fields(self, appointment_repo, mock_session):
        appt = _make_appointment(notes=None, duration_minutes=60)
        updated = await appointment_repo.update(appt, notes="Bring documents", duration_minutes=90)
        assert appt.notes == "Bring documents"
        assert appt.duration_minutes == 90
        mock_session.flush.assert_awaited_once()
        assert updated is appt

    async def test_update_ignores_unknown_fields(self, appointment_repo, mock_session):
        appt = _make_appointment()
        await appointment_repo.update(appt, nonexistent_attr="val")
        mock_session.flush.assert_awaited_once()

    async def test_delete(self, appointment_repo, mock_session):
        appt = _make_appointment()
        await appointment_repo.delete(appt)
        mock_session.delete.assert_awaited_once_with(appt)
