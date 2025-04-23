# ASHA Bot - Career Guidance Assistant for Women Professionals

ASHA (Advancement Support & Help Assistant) is a specialized AI assistant focused on providing tailored career guidance for women professionals. This project builds and trains a specialized conversational AI model using Ollama and provides a user-friendly web interface.

## Features

- **Specialized Career Guidance**: Provides advice tailored for women professionals
- **Session Recommendations**: Recommends relevant professional development sessions
- **Interactive Interface**: User-friendly web interface built with Streamlit
- **Data-Driven Responses**: Trained on actual session data for relevant recommendations
- **Context-Aware Suggestions**: Offers relevant follow-up questions based on conversation context

## Requirements

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running
- Streamlit and other required Python packages

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/asha-bot.git
   cd asha-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Make scripts executable and set up directory structure:
   ```bash
   ./setup.sh
   ```

## Data Preparation

You have two options for providing session data:

### Option 1: Using data/raw/herkey.sessions.json directly
1. Place your Herkey sessions data in `data/raw/herkey.sessions.json` directly
2. Process the raw data into structured format:
   ```bash
   ./prepare_herkey_data.py
   ```

### Option 2: Using paste.txt
1. Place your Herkey sessions data in `paste.txt` in the root directory.
2. Process the raw data into structured format:
   ```bash
   ./prepare_herkey_data.py
   ```

Either option will generate:
- `data/sessions.json` - Streamlined data for the application

## Training the Model

1. Ensure Ollama is running:
   ```bash
   ollama serve
   ```

2. Run the training script:
   ```bash
   ./train.sh
   ```

This script will:
- Process session data from `data/raw/herkey.sessions.json`
- Generate training examples
- Create and train the ASHA bot model in Ollama

## Using the Web Interface

1. Start the enhanced web interface:
   ```bash
   ./streamlit_app/start_enhanced.sh
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8501
   ```

## Using the API

You can also interact with ASHA directly via the Python API:

```python
from asha_api import ask_asha

response = ask_asha("How can I improve my leadership skills?")
print(response)
```

Or via command line:
```bash
./asha_api.py "How can I improve my leadership skills?"
```

## Project Structure

- `prepare_herkey_data.py` - Processes raw Herkey session data
- `generate_examples.py` - Generates training examples from processed data
- `train.sh` - Trains the model using Ollama
- `test_asha.py` - Tests the trained model with sample queries
- `asha_api.py` - Simple API for interacting with ASHA
- `model/Modelfile` - Defines the model parameters for Ollama
- `streamlit_app/` - Contains the web interface
  - `asha_streamlit_enhanced.py` - Enhanced Streamlit interface
  - `start_enhanced.sh` - Script to start the enhanced interface
- `data/` - Contains data files
  - `raw/` - Raw data files
  - `processed/` - Processed data
  - `training/` - Training examples

## Customization

### Modifying the Model

To change the model parameters, edit `model/Modelfile` and retrain:

```bash
./train.sh
```

### Customizing the Interface

To modify the web interface, edit `streamlit_app/asha_streamlit_enhanced.py`.

### Adding New Sessions

1. Add new session data to `paste.txt`
2. Re-run data preparation: `./prepare_herkey_data.py`
3. Re-run training: `./train.sh`

## Troubleshooting

- **Ollama Not Responding**: Ensure Ollama is running with `ollama serve`
- **Model Training Issues**: Check that your session data is in the correct format
- **Streamlit Interface Not Starting**: Check for Python errors or missing dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.