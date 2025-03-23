# FinTrack - Financial Portfolio Tracker

FinTrack is a web application that helps users track their stocks, mutual funds, and insurance policies in one place.

## Features

- User authentication
- Stock portfolio tracking (using Yahoo Finance API)
- Mutual fund tracking (using MFAPI.in)
- Insurance policy management
- Data storage with Firebase Firestore

## Tech Stack

- Flask (Python web framework)
- Bootstrap (UI)
- Firebase Firestore (Database)
- Yahoo Finance API (Stock data)
- MFAPI.in (Mutual fund data)

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fintrack
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up Firebase:
   - Create a Firebase project at https://console.firebase.google.com/
   - Enable Firestore Database
   - Generate a service account key:
     - Go to Project Settings > Service Accounts
     - Click "Generate New Private Key"
     - Save the file as `service-account-key.json` in the project root

4. Create `.env` file:
   ```
   FLASK_SECRET_KEY=your_secure_random_key
   FIREBASE_API_KEY=your_firebase_api_key
   FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com
   FIREBASE_DATABASE_URL=https://your_project_id.firebaseio.com
   FIREBASE_PROJECT_ID=your_project_id
   FIREBASE_STORAGE_BUCKET=your_project_id.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
   FIREBASE_APP_ID=your_app_id
   ```

5. Run the application:
   ```
   python main.py
   ```

6. Open http://localhost:5000 in your browser

## Default Login

- Email: demo@example.com
- Password: demo123

## License

MIT 