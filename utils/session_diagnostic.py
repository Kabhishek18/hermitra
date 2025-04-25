# asha/utils/session_diagnostic.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_all_sessions
from datetime import datetime
import json
import re

def analyze_sessions():
    """Analyze the session database and print statistics"""
    print("\n===== ASHA Session Database Diagnostic =====\n")
    
    # Get all sessions
    sessions = get_all_sessions()
    
    if not sessions:
        print("ERROR: No sessions found in the database!")
        print("Please make sure the database is properly initialized.")
        return
    
    print(f"Total sessions in database: {len(sessions)}")
    
    # Analyze hosts
    hosts = {}
    for session in sessions:
        host_users = session.get('host_user', [])
        if host_users and len(host_users) > 0:
            for host in host_users:
                username = host.get('username', '').lower()
                if username:
                    if username in hosts:
                        hosts[username] += 1
                    else:
                        hosts[username] = 1
    
    print(f"\nTotal unique hosts: {len(hosts)}")
    print("\nTop 10 hosts:")
    top_hosts = sorted(hosts.items(), key=lambda x: x[1], reverse=True)[:10]
    for host, count in top_hosts:
        print(f"  - {host}: {count} sessions")
    
    # Check if any hosts match "marissa"
    marissa_hosts = [host for host in hosts.keys() if "marissa" in host.lower()]
    if marissa_hosts:
        print("\nHosts matching 'marissa':")
        for host in marissa_hosts:
            print(f"  - {host}: {hosts[host]} sessions")
    else:
        print("\nNo hosts found matching 'marissa'")
    
    # Analyze titles
    print("\nAnalyzing session titles:")
    leadership_titles = 0
    development_titles = 0
    career_titles = 0
    
    for session in sessions:
        title = session.get('session_title', '').lower()
        if 'leadership' in title:
            leadership_titles += 1
        if 'development' in title:
            development_titles += 1
        if 'career' in title:
            career_titles += 1
    
    print(f"  - Sessions with 'leadership' in title: {leadership_titles}")
    print(f"  - Sessions with 'development' in title: {development_titles}")
    print(f"  - Sessions with 'career' in title: {career_titles}")
    
    # Analyze dates
    print("\nAnalyzing session dates:")
    sessions_with_dates = 0
    sessions_in_2023 = 0
    
    for session in sessions:
        schedule = session.get('schedule', {})
        if schedule and 'start_time' in schedule:
            start_time = schedule['start_time']
            sessions_with_dates += 1
            
            # Try to parse the date
            session_date = None
            if isinstance(start_time, str):
                # Try different date formats
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
                    try:
                        session_date = datetime.strptime(start_time, fmt)
                        break
                    except:
                        continue
            
            if session_date and session_date.year == 2023:
                sessions_in_2023 += 1
    
    print(f"  - Sessions with dates: {sessions_with_dates} out of {len(sessions)}")
    print(f"  - Sessions in 2023: {sessions_in_2023}")
    
    # Print sample session data
    if sessions:
        print("\nSample session data (first session):")
        sample = sessions[0]
        print(json.dumps(sample, indent=2, default=str)[:1000] + "...")
    
    print("\n===== End of Diagnostic =====\n")
    print("Recommendations:")
    if not hosts:
        print("  - Add host information to your sessions")
    if leadership_titles == 0 and development_titles == 0 and career_titles == 0:
        print("  - Add more relevant session titles related to career development")
    if sessions_with_dates == 0:
        print("  - Add date information to your sessions")
    print("  - Run the fix_sessions.py script to ensure data is properly imported")
    print("  - Check for any data format issues in your sessions.json file")

if __name__ == "__main__":
    analyze_sessions()