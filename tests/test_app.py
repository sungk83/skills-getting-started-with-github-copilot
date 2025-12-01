"""
Tests for the High School Activities API

Tests cover:
- Getting activities list
- Signing up for activities
- Unregistering from activities
- Error handling and validation
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    
    # Clear and reset
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for retrieving activities"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_has_required_fields(self, client, reset_activities):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignUpForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_for_available_activity(self, client, reset_activities):
        """Test successfully signing up for an activity with available spots"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify student was added
        response = client.get("/activities")
        activities_data = response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test that signing up for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_already_registered(self, client, reset_activities):
        """Test that signing up twice returns an error"""
        # First signup
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        # Second signup with same email
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is already signed up"
    
    def test_signup_for_full_activity(self, client, reset_activities):
        """Test that signing up for a full activity returns an error"""
        # Create a minimal activity with 0 max participants
        activities["Full Activity"] = {
            "description": "Completely full",
            "schedule": "Never",
            "max_participants": 1,
            "participants": ["existing@mergington.edu"]
        }
        
        response = client.post(
            "/activities/Full Activity/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Activity is full"


class TestUnregisterFromActivity:
    """Tests for unregistering from activities"""
    
    def test_unregister_from_activity(self, client, reset_activities):
        """Test successfully unregistering from an activity"""
        # First verify participant is there
        response = client.get("/activities")
        assert "michael@mergington.edu" in response.json()["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "michael@mergington.edu" in data["message"]
        
        # Verify participant was removed
        response = client.get("/activities")
        assert "michael@mergington.edu" not in response.json()["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test that unregistering from a non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test that unregistering a student not in the activity returns an error"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"


class TestIntegration:
    """Integration tests combining signup and unregister"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test the full flow of signing up and then unregistering"""
        email = "integrationtest@mergington.edu"
        activity = "Programming Class"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant added
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify participant removed
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_signups(self, client, reset_activities):
        """Test multiple different students signing up for the same activity"""
        activity = "Gym Class"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        # Sign up multiple students
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in emails:
            assert email in participants
