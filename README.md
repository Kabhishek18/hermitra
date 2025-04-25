# ASHA Chatbot

ASHA is a specialized AI chatbot designed to provide tailored career guidance for women professionals.

## Features

- Tailored career guidance for women
- Contextual and continuous conversations
- Integration with women's professional communities
- Ethical AI with gender bias mitigation
- Robust security and privacy measures

## Prerequisites

- Python
- MongoDB
- Ollama with the following models installed:
  - mistral:latest  Create Model Called ASHA 
- FAISS
- Streamlit 


## Guardrails & Limitations {#guardrails-limitations}
### System Guardrails
ASHA implements the following guardrails to ensure appropriate and helpful interactions:

1. Content Guardrails
- Focus on Career Guidance: Responses are limited to career-related topics
- No Personal Opinions: The system avoids offering personal opinions or predictions
- No Stereotyping: Responses are designed to avoid reinforcing gender stereotypes
- Ethical Guidance: Career advice follows ethical principles and practices
2. Interaction Guardrails
- Stay On Topic: The system redirects off-topic conversations back to career guidance
- No Sensitive Data Retention: Personal identifiable information is minimized
- Error Handling: Graceful fallbacks for unanswerable questions
- Clear Limitations: Transparent communication about system capabilities and limitations
- Known Limitations

Domain Specialization: ASHA is specialized for career guidance and not designed as a general-purpose assistant

Model Limitations:
- Context window constraints of underlying LLMs
- Performance dependent on quality of training data
Technical Limitations:
- Local processing constraints based on hardware
- Vector search performance trade-offs
Knowledge Boundaries:
- Limited to information available in its knowledge base
- Not connected to real-time job market data unless integrated



[Session Json](data/raw/herkey.sessions.json)
sample
```python 
{
  "_id": {
    "$oid": "6539d08eac5d837a984cbcb3"
  },
  "session_resources": {
    "discussion_image_url": "https://herkey-images.s3.ap-south-1.amazonaws.com/discussion/Discussion+Images/Image+9.svg",
    "watch_url": ""
  },
  "session_id": "1698287758043969496",
  "session_title": "Online vs in-person group discussion",
  "description": "{\n    \"root\": {\n        \"children\": [\n            {\n                \"children\": [\n                    {\n                        \"detail\": 0,\n                        \"format\": 0,\n                        \"mode\": \"normal\",\n                        \"style\": \"\",\n                        \"text\": \"Pros and cons of online and in-person group discussions \",\n                        \"type\": \"text\",\n                        \"version\": 1\n                    }\n                ],\n                \"direction\": \"ltr\",\n                \"format\": \"\",\n                \"indent\": 0,\n                \"type\": \"paragraph\",\n                \"version\": 1\n            }\n        ],\n        \"direction\": \"ltr\",\n        \"format\": \"\",\n        \"indent\": 0,\n        \"type\": \"root\",\n        \"version\": 1\n    }\n}",
  "host_user": [
    {
      "user_id": 3969496,
      "username": "Udhaya C",
      "role": "host",
      "blocked": false,
      "profile_picture_url": "",
      "stage_type": "riser",
      "headlines": {
        "headline1": "A Passionate Engineer",
        "headline2": "",
        "is_custom": true,
        "editable": true
      },
      "connections": [
        {
          "interaction_id": 19,
          "interaction_count": 151
        },
        {
          "interaction_id": 20,
          "interaction_count": 107
        },
        {
          "interaction_id": 21,
          "interaction_count": 69
        }
      ],
      "badge": {
        "id": "",
        "badge": false,
        "content": "",
        "url": "",
        "editable": false
      },
      "profile_url": "udhayac",
      "onboarding_status": "complete",
      "resume_parser": "",
      "roles": [
        {
          "id": 1,
          "name": "Her"
        },
        {
          "id": 2,
          "name": "For Her"
        }
      ],
      "identity": {
        "id": 1,
        "name": "Woman"
      },
      "primary_email_type": "corporate"
    }
  ],
  "discussion_url": "",
  "external_url": "https://meet.google.com/pxn-peha-teu",
  "schedule": {
    "start_time": {
      "$date": "2023-10-28T03:30:00.000Z"
    },
    "end_time": {
      "$date": "2023-10-28T04:30:00.000Z"
    },
    "duration_minutes": 60,
    "timezone": "UTC"
  },
  "categories": [],
  "tags": [],
  "engagement": {
    "participants_count": 0,
    "max_participants": 0
  },
  "user_engagement": {},
  "companies": [],
  "advance_option": {
    "feature": {
      "is_featured": false
    },
    "paid": false
  },
  "permissions": {
    "allow_edit": true,
    "allow_sharing": true,
    "allow_downloads": false
  },
  "share_with": {
    "share_id": 2,
    "share_group_ids": [],
    "is_shared_with_groups": false
  },
  "meta_data": {
    "invite_only": false,
    "recurring": false,
    "recurring_type": "",
    "blocked": true,
    "blocked_reason": "user_block",
    "is_deleted": true,
    "text_profanity": false,
    "report": false,
    "report_reason": "",
    "session_type": "online",
    "location": "",
    "transaction_id": "",
    "created_at": {
      "$date": "2023-10-26T02:35:58.653Z"
    },
    "updated_at": {
      "$date": "2024-08-16T14:17:39.175Z"
    },
    "created_by": {
      "user_id": 3969496
    },
    "status": "published"
  },
  "duration": "1hr"
},
```

