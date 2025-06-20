from flask import Flask, render_template, request, jsonify, session
import os
import random
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.secret_key = 'jlpt_quiz_secret_key_2024'

class JLPTWebApp:
    def __init__(self):
        self.credentials_file = 'credentials.json'
        self.spreadsheet_id = "1ROkMNwMWyUYoE7LdNFLqc85xUUiToWMOqnS61R095zg"
        self.sheet_name = "גיליון1"
        self.service = None
        self.data = None
        self.data_loaded = False
        
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            if not os.path.exists(self.credentials_file):
                print(f"❌ Credentials file not found: {self.credentials_file}")
                return False
            
            credentials = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Authenticated with Google Sheets API")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def load_data(self):
        """Load grammar data from Google Sheets - ONLY CALLED ONCE AT STARTUP"""
        if self.data_loaded and self.data is not None:
            print("✅ Data already loaded from cache")
            return True
            
        try:
            print("📥 Loading data from Google Sheets...")
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1:Z1000"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print("❌ No data found in Google Sheets")
                return False
            
            self.data = pd.DataFrame(values[1:], columns=values[0])
            self.data_loaded = True
            print(f"✅ Successfully loaded {len(self.data)} grammar points into DataFrame!")
            return True
            
        except HttpError as error:
            print(f"❌ Error loading data: {error}")
            return False
    
    def parse_example_sentences(self, example_text):
        """Parse example sentences and their translations"""
        if not example_text or str(example_text) == 'nan':
            return []
        
        sentences = []
        lines = str(example_text).split('\n')
        
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                japanese = lines[i].strip()
                english = lines[i + 1].strip()
                if japanese and english:
                    sentences.append({
                        'japanese': japanese,
                        'english': english
                    })
        
        return sentences
    
    def get_random_grammar_question(self):
        """Get a random grammar question from cached DataFrame"""
        if self.data is None or self.data.empty:
            print("❌ No data available for grammar questions")
            return None
        
        row = self.data.sample(n=1).iloc[0]
        
        # Try different possible column names for examples
        example = None
        possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
        
        for col_name in possible_example_columns:
            if col_name in self.data.columns:
                example = row.get(col_name, None)
                if example and str(example) != 'nan' and str(example).strip():
                    break
        
        # Extract Japanese example sentence only
        japanese_example = None
        if example:
            example_str = str(example)
            example_lines = example_str.split('\n')
            japanese_example = example_lines[0].strip()
            
            if not japanese_example or japanese_example.isspace():
                japanese_example = example_str.strip()
        
        return {
            'grammar': row.get('Grammar Lesson', 'N/A'),
            'japanese': row.get('文法レッスン', 'N/A'),
            'correct': row.get('Grammar Meaning', 'N/A'),
            'example': japanese_example
        }
    
    def get_random_sentence_question(self):
        """Get a random sentence question from cached DataFrame"""
        if self.data is None or self.data.empty:
            print("❌ No data available for sentence questions")
            return None
        
        # Try different possible column names for examples
        example_column = None
        possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
        
        for col_name in possible_example_columns:
            if col_name in self.data.columns:
                example_column = col_name
                break
        
        if not example_column:
            print("❌ No example column found")
            return None
        
        # Get all sentences from all rows
        all_sentences = []
        
        for i, row in self.data.iterrows():
            example_text = row.get(example_column, '')
            if example_text and str(example_text) != 'nan':
                sentences = self.parse_example_sentences(example_text)
                all_sentences.extend(sentences)
        
        if not all_sentences:
            print("❌ No sentences found in data")
            return None
        
        return random.choice(all_sentences)
    
    def generate_options(self, correct_answer, is_sentence=False):
        """Generate 4 multiple choice options from cached DataFrame"""
        if is_sentence:
            # For sentence questions, get other English translations
            wrong_answers = []
            example_column = None
            possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
            
            for col_name in possible_example_columns:
                if col_name in self.data.columns:
                    example_column = col_name
                    break
            
            if example_column:
                for _, row in self.data.iterrows():
                    example_text = row.get(example_column, '')
                    sentences = self.parse_example_sentences(example_text)
                    for sentence in sentences:
                        english = sentence['english']
                        if english and english != correct_answer and len(wrong_answers) < 5:
                            wrong_answers.append(english)
            
            generic_answers = ["I don't know", "It's difficult", "Please help me", "I understand"]
            while len(wrong_answers) < 3:
                generic = random.choice(generic_answers)
                if generic not in wrong_answers and generic != correct_answer:
                    wrong_answers.append(generic)
        else:
            # For grammar questions, get wrong answers from other grammar points
            wrong_answers = []
            sample = self.data.sample(n=min(10, len(self.data)))
            
            for _, row in sample.iterrows():
                meaning = row.get('Grammar Meaning', '')
                if meaning and meaning != correct_answer and len(wrong_answers) < 3:
                    wrong_answers.append(meaning)
            
            generic = ["to do something", "because of", "in order to", "while doing"]
            while len(wrong_answers) < 3:
                wrong_answers.append(generic[len(wrong_answers)])
        
        # Create and shuffle options
        options = [correct_answer] + wrong_answers[:3]
        random.shuffle(options)
        return options

# Initialize the JLPT app
jlpt_app = JLPTWebApp()

@app.route('/')
def index():
    """Main page with quiz mode selection"""
    return render_template('index.html')

@app.route('/grammar-quiz')
def grammar_quiz():
    """Grammar quiz page"""
    return render_template('grammar_quiz.html')

@app.route('/sentence-quiz')
def sentence_quiz():
    """Sentence quiz page"""
    return render_template('sentence_quiz.html')

@app.route('/api/grammar-question')
def get_grammar_question():
    """API endpoint to get a grammar question - uses cached data only"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    question = jlpt_app.get_random_grammar_question()
    if not question:
        return jsonify({'error': 'No questions available'}), 404
    
    options = jlpt_app.generate_options(question['correct'])
    
    return jsonify({
        'grammar': question['grammar'],
        'japanese': question['japanese'],
        'example': question['example'],
        'options': options,
        'correct': question['correct']
    })

@app.route('/api/sentence-question')
def get_sentence_question():
    """API endpoint to get a sentence question - uses cached data only"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    question = jlpt_app.get_random_sentence_question()
    if not question:
        return jsonify({'error': 'No sentences available'}), 404
    
    options = jlpt_app.generate_options(question['english'], is_sentence=True)
    
    return jsonify({
        'japanese': question['japanese'],
        'options': options,
        'correct': question['english']
    })

@app.route('/stats')
def stats():
    """Statistics page"""
    return render_template('stats.html')

if __name__ == '__main__':
    # Load data ONCE when starting the app
    print("🚀 Starting JLPT Web App...")
    print("📋 Initializing data loading...")
    
    if jlpt_app.authenticate():
        if jlpt_app.load_data():
            print("✅ App ready! Data loaded successfully.")
            print(f"📊 DataFrame shape: {jlpt_app.data.shape}")
            print("🌐 Starting web server...")
        else:
            print("❌ Failed to load data! Check your Google Sheets connection.")
            exit(1)
    else:
        print("❌ Failed to authenticate! Check your credentials.json file.")
        exit(1)
    
    app.run(debug=True, host='0.0.0.0', port=5000) 