# asha/add_sample_sessions.py
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient
import config
from datetime import datetime, timedelta
import uuid

def create_sample_sessions():
    """Create and add sample sessions to the database for testing"""
    print("Creating sample sessions for testing...")
    
    # Connect to MongoDB
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    sessions_collection = db[config.MONGO_SESSIONS_COLLECTION]
    
    # Sample hosts
    hosts = [
        {"user_id": 12345, "username": "Marissa Johnson", "role": "host", "profile_url": "marissaj"},
        {"user_id": 23456, "username": "John Smith", "role": "host", "profile_url": "johns"},
        {"user_id": 34567, "username": "Sarah Williams", "role": "host", "profile_url": "sarahw"},
        {"user_id": 45678, "username": "David Chen", "role": "host", "profile_url": "davidc"},
        {"user_id": 56789, "username": "Jennifer Lopez", "role": "host", "profile_url": "jenniferl"}
    ]
    
    # Sample sessions
    sample_sessions = [
        {
            "session_title": "Leadership Development for Women in Tech",
            "description": "This session focuses on leadership strategies specifically designed for women in technology fields. We'll discuss overcoming challenges, building influence, and creating a leadership path.",
            "host_user": [hosts[0]],  # Marissa
            "duration": "1hr 30min",
            "external_url": "https://meet.google.com/sample-link-1",
            "schedule": {
                "start_time": (datetime.now() - timedelta(days=15)).isoformat() + "Z",
                "end_time": (datetime.now() - timedelta(days=15) + timedelta(hours=1, minutes=30)).isoformat() + "Z",
                "duration_minutes": 90
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                "updated_at": (datetime.now() - timedelta(days=25)).isoformat() + "Z",
                "session_type": "online",
                "status": "completed"
            }
        },
        {
            "session_title": "Effective Salary Negotiation Tactics",
            "description": "Learn proven strategies for negotiating your salary confidently. This workshop covers research techniques, response tactics, and practice scenarios for your next negotiation.",
            "host_user": [hosts[1]],  # John
            "duration": "1hr",
            "external_url": "https://meet.google.com/sample-link-2",
            "schedule": {
                "start_time": (datetime.now() - timedelta(days=7)).isoformat() + "Z",
                "end_time": (datetime.now() - timedelta(days=7) + timedelta(hours=1)).isoformat() + "Z",
                "duration_minutes": 60
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": (datetime.now() - timedelta(days=20)).isoformat() + "Z",
                "updated_at": (datetime.now() - timedelta(days=18)).isoformat() + "Z",
                "session_type": "online",
                "status": "completed"
            }
        },
        {
            "session_title": "Career Transition: Moving into Product Management",
            "description": "A practical guide for professionals looking to transition into product management roles. We'll cover required skills, portfolio building, and interview preparation.",
            "host_user": [hosts[2]],  # Sarah
            "duration": "2hrs",
            "external_url": "https://meet.google.com/sample-link-3",
            "schedule": {
                "start_time": (datetime.now() - timedelta(days=2)).isoformat() + "Z",
                "end_time": (datetime.now() - timedelta(days=2) + timedelta(hours=2)).isoformat() + "Z",
                "duration_minutes": 120
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": (datetime.now() - timedelta(days=15)).isoformat() + "Z",
                "updated_at": (datetime.now() - timedelta(days=14)).isoformat() + "Z",
                "session_type": "online",
                "status": "completed"
            }
        },
        {
            "session_title": "Interview Preparation Masterclass",
            "description": "Comprehensive interview preparation covering behavioral questions, technical assessments, and creating a lasting impression. Includes mock interview practice.",
            "host_user": [hosts[0]],  # Marissa
            "duration": "2hrs 30min",
            "external_url": "https://meet.google.com/sample-link-4",
            "schedule": {
                "start_time": (datetime.now() + timedelta(days=5)).isoformat() + "Z",
                "end_time": (datetime.now() + timedelta(days=5) + timedelta(hours=2, minutes=30)).isoformat() + "Z",
                "duration_minutes": 150
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": (datetime.now() - timedelta(days=10)).isoformat() + "Z",
                "updated_at": (datetime.now() - timedelta(days=8)).isoformat() + "Z",
                "session_type": "online",
                "status": "upcoming"
            }
        },
        {
            "session_title": "Building Your Personal Brand Online",
            "description": "Strategies for creating a compelling personal brand across digital platforms. We'll cover LinkedIn optimization, content creation, and networking techniques.",
            "host_user": [hosts[3]],  # David
            "duration": "1hr 15min",
            "external_url": "https://meet.google.com/sample-link-5",
            "schedule": {
                "start_time": (datetime.now() + timedelta(days=10)).isoformat() + "Z",
                "end_time": (datetime.now() + timedelta(days=10) + timedelta(hours=1, minutes=15)).isoformat() + "Z",
                "duration_minutes": 75
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": (datetime.now() - timedelta(days=5)).isoformat() + "Z",
                "updated_at": (datetime.now() - timedelta(days=3)).isoformat() + "Z",
                "session_type": "online",
                "status": "upcoming"
            }
        },
        {
            "session_title": "Leadership Styles and Effective Team Management",
            "description": "Explore different leadership styles and learn when to apply each for optimal team performance. Includes conflict resolution and delegation techniques.",
            "host_user": [hosts[4]],  # Jennifer
            "duration": "1hr 45min",
            "external_url": "https://meet.google.com/sample-link-6",
            "schedule": {
                "start_time": datetime(2023, 1, 15, 10, 0, 0).isoformat() + "Z",
                "end_time": datetime(2023, 1, 15, 11, 45, 0).isoformat() + "Z",
                "duration_minutes": 105
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": datetime(2023, 1, 5).isoformat() + "Z",
                "updated_at": datetime(2023, 1, 6).isoformat() + "Z",
                "session_type": "online",
                "status": "completed"
            }
        },
        {
            "session_title": "Advanced Career Planning Workshop",
            "description": "Strategic career planning for mid to senior-level professionals. Learn to map your career trajectory, identify growth opportunities, and develop an action plan.",
            "host_user": [hosts[0]],  # Marissa
            "duration": "2hrs",
            "external_url": "https://meet.google.com/sample-link-7",
            "schedule": {
                "start_time": datetime(2023, 1, 25, 14, 0, 0).isoformat() + "Z",
                "end_time": datetime(2023, 1, 25, 16, 0, 0).isoformat() + "Z",
                "duration_minutes": 120
            },
            "session_id": str(uuid.uuid4().int)[:16],
            "meta_data": {
                "created_at": datetime(2023, 1, 10).isoformat() + "Z",
                "updated_at": datetime(2023, 1, 12).isoformat() + "Z",
                "session_type": "online",
                "status": "completed"
            }
        }
    ]
    
    # Insert sample sessions
    try:
        # Add sessions
        result = sessions_collection.insert_many(sample_sessions)
        print(f"Successfully added {len(result.inserted_ids)} sample sessions")
        
        # Print session titles
        print("\nAdded sessions:")
        for session in sample_sessions:
            host = session['host_user'][0]['username'] if session['host_user'] else "Unknown"
            print(f"- {session['session_title']} (Host: {host})")
        
        print("\nSample data now available for testing!")
        print("You can now search for sessions by host (e.g., 'Marissa Johnson'), by topic (e.g., 'leadership development'),")
        print("or by date (e.g., 'January 2023').")
        
    except Exception as e:
        print(f"Error adding sample sessions: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_sample_sessions()