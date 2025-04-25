import os
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASHA Chatbot")
    parser.add_argument("--init-db", action="store_true", help="Initialize the database")
    parser.add_argument("--load-data", action="store_true", help="Load data from JSON files")
    
    args = parser.parse_args()
    
    if args.init_db:
        # Simply run the init_db.py script
        os.system("python scripts/init_db.py")
    elif args.load_data:
        # Simply run the load_data.py script
        os.system("python scripts/load_data.py")
    else:
        # Run the Streamlit app
        os.system("streamlit run src/app.py")