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
        # Configuration for multiple sheets
        self.sheets_config = {
            'grammar': {
                'name': "Grammar",
                'data': None,
                'loaded': False
            },
            'kanji': {
                'name': "Kanji",  # Change this to your actual kanji sheet name (e.g., "Sheet2", "Kanji", "漢字", etc.)
                'data': None,
                'loaded': False
            }
        }
        self.service = None
        self.data = None  # Keep for backward compatibility
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
    
    def load_sheet_data(self, sheet_type):
        """Load data from a specific sheet type"""
        if sheet_type not in self.sheets_config:
            print(f"❌ Unknown sheet type: {sheet_type}")
            return False
            
        config = self.sheets_config[sheet_type]
        
        # Check if already loaded
        if config['loaded'] and config['data'] is not None:
            print(f"✅ {sheet_type} data already loaded from cache")
            return True
            
        try:
            print(f"📥 Loading {sheet_type} data from Google Sheets...")
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{config['name']}!A1:Z1000"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print(f"❌ No data found in {sheet_type} sheet")
                return False
            
            config['data'] = pd.DataFrame(values[1:], columns=values[0])
            config['loaded'] = True
            print(f"✅ Successfully loaded {len(config['data'])} {sheet_type} items!")
            return True
            
        except HttpError as error:
            print(f"❌ Error loading {sheet_type} data: {error}")
            return False
    
    def load_data(self):
        """Load all sheet data - ONLY CALLED ONCE AT STARTUP"""
        if self.data_loaded:
            print("✅ All data already loaded from cache")
            return True
            
        # Load grammar data (existing functionality)
        if self.load_sheet_data('grammar'):
            # For backward compatibility, set the main data to grammar data
            self.data = self.sheets_config['grammar']['data']
            self.data_loaded = True
            
            # Try to load kanji data if available
            try:
                self.load_sheet_data('kanji')
            except Exception as e:
                print(f"⚠️ Could not load kanji sheet: {e}")
            
            return True
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

    def get_random_kanji_question(self):
        """Get a random kanji question from kanji sheet, ensuring it has a valid meaning."""
        if 'kanji' not in self.sheets_config or not self.sheets_config['kanji']['loaded']:
            print("❌ Kanji data not available")
            return None
        
        data = self.sheets_config['kanji']['data']
        if data is None or data.empty:
            print("❌ No kanji data available")
            return None

        # Find the meaning column to filter by
        meaning_column = None
        possible_meaning_columns = ['Meaning', 'English', 'Translation', '意味', 'Definition', 'Kanji Meaning']
        for col_name in possible_meaning_columns:
            if col_name in data.columns:
                meaning_column = col_name
                break
        
        if not meaning_column:
            print("❌ No meaning column found in kanji sheet")
            return None

        # Filter out rows that have invalid meanings (NaN, 'N/A', or empty)
        valid_rows = data[data[meaning_column].notna()]
        valid_rows = valid_rows[~valid_rows[meaning_column].astype(str).str.strip().str.lower().isin(['', 'nan', 'n/a'])]

        if valid_rows.empty:
            print("❌ No valid kanji questions with meanings found after cleaning.")
            return None

        # Now, safely sample a random row from the cleaned data
        row = valid_rows.sample(n=1).iloc[0]
        
        # Find other columns (kanji, onyomi, kunyomi)
        kanji_column = next((col for col in ['Kanji', '漢字', 'Character', '字'] if col in data.columns), None)
        onyomi_column = next((col for col in ['Onyomi', '音読み', 'On Reading', 'On'] if col in data.columns), None)
        kunyomi_column = next((col for col in ['Kunyomi', '訓読み', 'Kun Reading', 'Kun'] if col in data.columns), None)
        
        return {
            'kanji': row.get(kanji_column, 'N/A'),
            'meaning': row.get(meaning_column),  # No default needed, as we've already filtered
            'onyomi': row.get(onyomi_column, '') if onyomi_column else '',
            'kunyomi': row.get(kunyomi_column, '') if kunyomi_column else ''
        }
    
    def generate_kanji_options(self, correct_answer, question_type='meaning'):
        """Generate wrong options for kanji questions from a clean data pool."""
        if 'kanji' not in self.sheets_config or not self.sheets_config['kanji']['loaded']:
            return []
        
        data = self.sheets_config['kanji']['data']
        wrong_answers = []
        
        # Find the correct meaning column
        meaning_column = None
        possible_meaning_columns = ['Meaning', 'English', 'Translation', '意味', 'Definition', 'Kanji Meaning']
        for col_name in possible_meaning_columns:
            if col_name in data.columns:
                meaning_column = col_name
                break
        
        if meaning_column:
            # Filter the entire dataset to get a pool of valid wrong answers, excluding the correct answer
            valid_options = data[data[meaning_column].notna()]
            valid_options = valid_options[~valid_options[meaning_column].astype(str).str.strip().str.lower().isin(['', 'nan', 'n/a', correct_answer.lower()])]
            
            # If there are enough valid options, sample from them
            if len(valid_options) >= 3:
                wrong_answers = valid_options.sample(n=3)[meaning_column].tolist()

        # Fallback to generic answers only if we couldn't get enough real ones
        generic_answers = [
            "I don't know",
            "It's difficult",
            "Please help me",
            "That's correct"
        ]
        
        while len(wrong_answers) < 3:
            generic = random.choice(generic_answers)
            # Ensure no duplicates between generic answers and real answers
            if generic not in wrong_answers and generic != correct_answer:
                wrong_answers.append(generic)
        
        return wrong_answers[:3]

    def get_random_kanji_sentence_question(self):
        """Get a random kanji sentence question from example sentences"""
        if 'kanji' not in self.sheets_config or not self.sheets_config['kanji']['loaded']:
            print("❌ Kanji data not available")
            return None
        
        data = self.sheets_config['kanji']['data']
        if data is None or data.empty:
            print("❌ No kanji data available")
            return None
        
        # Try different possible column names for example sentences
        example_column = None
        possible_example_columns = ['Example Sentence', 'Example', 'Sentence', 'Sentences', '例文', 'Example Sentences']
        
        for col_name in possible_example_columns:
            if col_name in data.columns:
                example_column = col_name
                break
        
        if not example_column:
            print("❌ No example sentence column found")
            return None
        
        # Get all sentences from all rows
        all_sentences = []
        
        for i, row in data.iterrows():
            example_text = row.get(example_column, '')
            if example_text and str(example_text) != 'nan':
                sentences = self.parse_kanji_example_sentences(example_text)
                all_sentences.extend(sentences)
        
        if not all_sentences:
            print("❌ No sentences found in kanji data")
            return None
        
        return random.choice(all_sentences)
    
    def parse_kanji_example_sentences(self, example_text):
        """Parse kanji example sentences and their translations"""
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
    
    def check_answer_similarity(self, user_answer, correct_answer):
        """Check if user answer is similar enough to correct answer"""
        if not user_answer or not correct_answer:
            return False
        
        # Convert to lowercase for comparison
        user_lower = user_answer.lower().strip()
        correct_lower = correct_answer.lower().strip()
        
        # Exact match
        if user_lower == correct_lower:
            return True
        
        # Check if user answer contains key words from correct answer
        correct_words = set(correct_lower.split())
        user_words = set(user_lower.split())
        
        # Remove common words that don't add meaning
        common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'and', 'or', 'but', 'so', 'because', 'if', 'then', 'else', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose'}
        
        correct_key_words = correct_words - common_words
        user_key_words = user_words - common_words
        
        # If user has at least 50% of the key words, consider it correct
        if len(correct_key_words) > 0:
            matching_words = correct_key_words.intersection(user_key_words)
            similarity_ratio = len(matching_words) / len(correct_key_words)
            return similarity_ratio >= 0.5
        
        # Fallback: check if user answer is a substring of correct answer or vice versa
        return user_lower in correct_lower or correct_lower in user_lower

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

@app.route('/kanji-quiz')
def kanji_quiz():
    """Kanji quiz page"""
    return render_template('kanji_quiz.html')

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

@app.route('/api/kanji-question')
def get_kanji_question():
    """API endpoint to get a kanji question - uses cached data only"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    # Randomly choose between classic kanji and sentence questions
    question_type = random.choice(['classic', 'sentence'])
    
    if question_type == 'sentence':
        # Sentence translation question
        question = jlpt_app.get_random_kanji_sentence_question()
        if not question:
            # Fallback to classic kanji question if no sentences available
            question = jlpt_app.get_random_kanji_question()
            if not question:
                return jsonify({'error': 'No kanji available'}), 404
            question_type = 'classic'
        else:
            return jsonify({
                'type': 'sentence',
                'japanese': question['japanese'],
                'correct': question['english']
            })
    
    # Classic kanji meaning question
    question = jlpt_app.get_random_kanji_question()
    if not question:
        return jsonify({'error': 'No kanji available'}), 404
    
    correct_answer = question['meaning']
    question_text = f"What does the kanji {question['kanji']} mean?"
    options = jlpt_app.generate_kanji_options(correct_answer, 'meaning')
    
    # Create and shuffle options
    all_options = [correct_answer] + options
    random.shuffle(all_options)
    
    return jsonify({
        'type': 'classic',
        'kanji': question['kanji'],
        'onyomi': question['onyomi'],
        'kunyomi': question['kunyomi'],
        'question': question_text,
        'options': all_options,
        'correct': correct_answer
    })

@app.route('/api/check-kanji-answer', methods=['POST'])
def check_kanji_answer():
    """API endpoint to check kanji sentence answer similarity"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    data = request.get_json()
    user_answer = data.get('answer', '').strip()
    correct_answer = data.get('correct', '').strip()
    
    if not user_answer or not correct_answer:
        return jsonify({'error': 'Missing answer or correct answer'}), 400
    
    is_correct = jlpt_app.check_answer_similarity(user_answer, correct_answer)
    
    return jsonify({
        'correct': is_correct,
        'user_answer': user_answer,
        'correct_answer': correct_answer
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