"""
Test suite for Mergington High School Activities API
"""

import pytest
import sys
import copy
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    global activities
    original_activities = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Test /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Soccer" in data
        assert "Basketball" in data

    def test_activity_contains_required_fields(self, client):
        """Test that each activity contains required fields"""
        response = client.get("/activities")
        data = response.json()
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_participants_are_returned_as_list(self, client):
        """Test that participants are returned as a list"""
        response = client.get("/activities")
        data = response.json()
        soccer = data["Soccer"]
        assert isinstance(soccer["participants"], list)
        assert len(soccer["participants"]) > 0


class TestSignup:
    """Test /activities/{activity_name}/signup endpoint"""

    def test_signup_for_existing_activity(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer/signup?email=newemail@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]

    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        email = "newemail@mergington.edu"
        client.post(f"/activities/Soccer/signup?email={email}")
        
        response = client.get("/activities")
        participants = response.json()["Soccer"]["participants"]
        assert email in participants

    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistent/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_duplicate_signup_returns_error(self, client, reset_activities):
        """Test that duplicate signup returns 400 error"""
        email = "alex@mergington.edu"
        response = client.post(f"/activities/Soccer/signup?email={email}")
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_multiple_signups_different_students(self, client, reset_activities):
        """Test multiple students can sign up for same activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/Soccer/signup?email={email}")
            assert response.status_code == 200

        response = client.get("/activities")
        participants = response.json()["Soccer"]["participants"]
        for email in emails:
            assert email in participants


class TestUnregister:
    """Test /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client, reset_activities):
        """Test successful unregister of a participant"""
        email = "alex@mergington.edu"
        response = client.post(f"/activities/Soccer/unregister?email={email}")
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "alex@mergington.edu"
        client.post(f"/activities/Soccer/unregister?email={email}")
        
        response = client.get("/activities")
        participants = response.json()["Soccer"]["participants"]
        assert email not in participants

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistent/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_non_participant(self, client, reset_activities):
        """Test unregister of non-registered participant returns 400"""
        response = client.post(
            "/activities/Soccer/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]

    def test_signup_then_unregister(self, client, reset_activities):
        """Test signup followed by unregister"""
        email = "test@mergington.edu"
        
        # Signup
        response = client.post(f"/activities/Basketball/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant added
        response = client.get("/activities")
        assert email in response.json()["Basketball"]["participants"]
        
        # Unregister
        response = client.post(f"/activities/Basketball/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify participant removed
        response = client.get("/activities")
        assert email not in response.json()["Basketball"]["participants"]


class TestActivityCount:
    """Test activity participant counts"""

    def test_activity_has_participants(self, client):
        """Test that activities have participants"""
        response = client.get("/activities")
        data = response.json()
        
        # Each activity should have at least one participant
        for activity_name, activity_details in data.items():
            assert len(activity_details["participants"]) > 0

    def test_participants_not_exceed_max(self, client):
        """Test that current participants don't exceed max"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            current = len(activity_details["participants"])
            max_allowed = activity_details["max_participants"]
            assert current <= max_allowed, f"{activity_name} exceeded max participants"
