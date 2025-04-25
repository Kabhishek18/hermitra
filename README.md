# ASHA Chatbot

ASHA is a specialized AI chatbot designed to provide tailored career guidance for women professionals.

## Features

- Tailored career guidance for women
- Contextual and continuous conversations
- Integration with women's professional communities
- Ethical AI with gender bias mitigation
- Robust security and privacy measures

## Prerequisites

- Python 3.8+
- MongoDB
- Ollama with the following models installed:
  - mistral:latest
  - deepseek-r1:1.5b
  - llama3.3:latest
- AWS Bedrock access

## Installation

1. Clone the repository:
git clone https://github.com/your-organization/asha-bot.git
cd asha-bot

2. Create a virtual environment and install dependencies:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

3. Configure environment variables by editing the `.env` file.

4. Initialize the database:
python main.py --init-db

5. Load existing data (optional):
python main.py --load-data

## Running the Application

Start the Streamlit application:
python main.py

Or directly with Streamlit:
streamlit run src/app.py

The application will be available at http://localhost:8501

## Project Structure

- `data/raw/`: Contains raw data files
- `src/`: Source code
  - `services/`: Core service modules
  - `utils/`: Utility functions
  - `app.py`: Streamlit application
- `scripts/`: Utility scripts
  - `init_db.py`: Database initialization
  - `load_data.py`: Data loading

## Usage

1. Open the application in your web browser
2. Set your career preferences in the sidebar
3. Ask career-related questions in the chat input
4. Receive tailored guidance from ASHA