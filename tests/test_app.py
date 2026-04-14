"""
Tests for the Mergington High School Activities API

This module contains unit tests for all endpoints of the FastAPI application.
Each test uses isolated, mocked activity data to ensure test independence.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """
    Fixture that provides a TestClient with fresh mocked activity data.
    
    Each test gets a clean copy of activities to prevent cross-test contamination.
    """
    # Store original activities
    original_activities = activities.copy()
    
    # Create a fresh copy with nested dictionaries for this test
    test_activities = {
        activity_name: {
            **activity_data,
            "participants": activity_data["participants"].copy()
        }
        for activity_name, activity_data in original_activities.items()
    }
    
    # Replace app's activities with test data
    activities.clear()
    activities.update(test_activities)
    
    yield TestClient(app)
    
    # Restore original activities after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Should return all activities with correct structure"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a dictionary of activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Each activity should have required fields
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Should contain all expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class"
        ]
        
        for activity_name in expected_activities:
            assert activity_name in data


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Should successfully sign up a new student"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Should return 404 if activity doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_already_registered(self, client):
        """Should return 400 if student is already registered"""
        # michael@mergington.edu is already in Chess Club
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"].lower()
    
    def test_signup_multiple_students_same_activity(self, client):
        """Should allow multiple different students to sign up for same activity"""
        # First student
        response1 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "student1@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Second student
        response2 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "student2@mergington.edu"}
        )
        assert response2.status_code == 200
        
        # Verify both were added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert "student1@mergington.edu" in participants
        assert "student2@mergington.edu" in participants
    
    def test_signup_same_student_different_activities(self, client):
        """Should allow same student to sign up for different activities"""
        email = "versatile@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify student is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Should successfully unregister an existing student"""
        # michael@mergington.edu is already in Chess Club
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "michael@mergington.edu" in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert "michael@mergington.edu" not in participants
    
    def test_unregister_activity_not_found(self, client):
        """Should return 404 if activity doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_student_not_registered(self, client):
        """Should return 400 if student is not registered for activity"""
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_decreases_participant_count(self, client):
        """Should decrease participant count after unregistering"""
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Chess Club"]["participants"])
        
        # Unregister a student
        client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        
        # Get updated count
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Chess Club"]["participants"])
        
        assert final_count == initial_count - 1
    
    def test_unregister_then_signup_same_student(self, client):
        """Should allow re-signup after unregistering"""
        email = "michael@mergington.edu"
        
        # Unregister
        response1 = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Re-signup
        response2 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify student is back
        activities_response = client.get("/activities")
        assert email in activities_response.json()["Chess Club"]["participants"]
