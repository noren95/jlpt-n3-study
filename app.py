from flask import Flask, render_template, request, jsonify, session
import os
import random
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

app = Flask(__name__)
app.secret_key = 'jlpt_quiz_secret_key_2024'

class JLPTWebApp:
    def __init__(self):
        self.credentials_file = 'credentials.json'
        self.spreadsheet_id = "1ROkMNwMWyUYoE7LdNFLqc85xUUiToWMOqnS61R095zg"
        
        # Knowledge tracking files and data
        self.kanji_knowledge_file = 'kanji_knowledge.json'
        self.vocabulary_knowledge_file = 'vocabulary_knowledge.json'
        self.grammar_knowledge_file = 'grammar_knowledge.json'
        
        self.kanji_knowledge = {}
        self.vocabulary_knowledge = {}
        self.grammar_knowledge = {}

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
            },
            'vocabulary': {
                'name': "Vocabulary",
                'data': None,
                'loaded': False
            }
        }
        self.service = None
        self.data = None  # Keep for backward compatibility
        self.data_loaded = False
        
        # Load all knowledge data on startup
        self.load_kanji_knowledge()
        self.load_vocabulary_knowledge()
        self.load_grammar_knowledge()

    def load_kanji_knowledge(self):
        """Loads the kanji knowledge data from a JSON file."""
        self.kanji_knowledge = self._load_knowledge_data(self.kanji_knowledge_file)

    def save_kanji_knowledge(self):
        """Saves the kanji knowledge data to a JSON file."""
        self._save_knowledge_data(self.kanji_knowledge, self.kanji_knowledge_file)

    def load_vocabulary_knowledge(self):
        """Loads the vocabulary knowledge data from a JSON file."""
        self.vocabulary_knowledge = self._load_knowledge_data(self.vocabulary_knowledge_file)

    def save_vocabulary_knowledge(self):
        """Saves the vocabulary knowledge data to a JSON file."""
        self._save_knowledge_data(self.vocabulary_knowledge, self.vocabulary_knowledge_file)

    def load_grammar_knowledge(self):
        """Loads the grammar knowledge data from a JSON file."""
        self.grammar_knowledge = self._load_knowledge_data(self.grammar_knowledge_file)

    def save_grammar_knowledge(self):
        """Saves the grammar knowledge data to a JSON file."""
        self._save_knowledge_data(self.grammar_knowledge, self.grammar_knowledge_file)

    def _load_knowledge_data(self, file_path):
        """Generic function to load knowledge data from a JSON file."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    knowledge_data = json.load(f)
                print(f"✅ Loaded {len(knowledge_data)} entries from {file_path}.")
                return knowledge_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Could not load {file_path}, starting fresh. Error: {e}")
                return {}
        else:
            print(f"ℹ️ No {file_path} found. A new one will be created.")
            return {}

    def _save_knowledge_data(self, data, file_path):
        """Generic function to save knowledge data to a JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"❌ Could not save {file_path}. Error: {e}")

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
                range=f"{config['name']}!A:Z"
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
            
            # Try to load other sheets if available
            try:
                self.load_sheet_data('kanji')
            except Exception as e:
                print(f"⚠️ Could not load kanji sheet: {e}")

            try:
                if self.load_sheet_data('vocabulary'):
                    # --- DIAGNOSTIC CODE ---
                    vocab_df = self.sheets_config['vocabulary']['data']
                    if vocab_df is not None:
                        print("📖 DEBUG: Found the following columns in your 'Vocabulary' sheet:")
                        for i, col in enumerate(vocab_df.columns):
                            print(f"  -> Column index {i}: '{col}'")
                    # --- END OF DIAGNOSTIC CODE ---
            except Exception as e:
                print(f"⚠️ Could not load vocabulary sheet: {e}")
            
            return True
        return False
    
    def create_grammar_quiz_set(self, num_questions=20):
        """Create a set of grammar questions without repeating grammar points"""
        if self.data is None or self.data.empty:
            print("❌ No data available for grammar questions")
            return None
        
        # Get all available grammar points
        available_grammars = self.data.copy()
        grammar_col = 'Grammar Lesson' # Assuming this is the unique identifier

        # Filter out 'good' grammar points
        good_grammar = [k for k, v in self.grammar_knowledge.items() if v == 'good']
        if good_grammar:
            original_count = len(available_grammars)
            available_grammars = available_grammars[~available_grammars[grammar_col].isin(good_grammar)]
            print(f"ℹ️ Filtered out {original_count - len(available_grammars)} 'good' grammar points.")

        # If we have fewer grammar points than requested, use all available
        if len(available_grammars) < num_questions:
            print(f"⚠️ Only {len(available_grammars)} grammar points available, using all of them")
            num_questions = len(available_grammars)
        
        # Randomly sample grammar points without replacement
        selected_grammars = available_grammars.sample(n=num_questions)
        
        quiz_set = []
        for _, row in selected_grammars.iterrows():
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
            
            grammar_lesson = row.get(grammar_col, 'N/A')
            
            question = {
                'grammar': grammar_lesson,
                'japanese': row.get('文法レッスン', 'N/A'),
                'correct': row.get('Grammar Meaning', 'N/A'),
                'example': japanese_example,
                'level': self.grammar_knowledge.get(grammar_lesson, 'none')
            }
            
            # Generate options for this question
            options = self.generate_options(question['correct'])
            question['options'] = options
            
            quiz_set.append(question)
        
        return quiz_set
    
    def create_vocabulary_quiz_set(self, num_questions=20):
        """Create a set of vocabulary questions without repeating words."""
        if 'vocabulary' not in self.sheets_config or not self.sheets_config['vocabulary']['loaded']:
            print("❌ Vocabulary data not available")
            return None
        
        vocab_data = self.sheets_config['vocabulary']['data']
        if vocab_data is None or vocab_data.empty:
            print("❌ No data available for vocabulary questions")
            return None

        # Identify columns, now case-insensitive
        word_col = next((col for col in vocab_data.columns if col.strip().lower() in ['word', '単語', 'vocabulary']), None)
        meaning_col = next((col for col in vocab_data.columns if col.strip().lower() in ['meaning', '意味', 'english']), None)

        if not word_col or not meaning_col:
            print("❌ Could not find 'Word' or 'Meaning' columns in Vocabulary sheet.")
            return None
            
        # Filter out rows with invalid meanings
        valid_vocab = vocab_data[vocab_data[meaning_col].notna()]
        valid_vocab = valid_vocab[~valid_vocab[meaning_col].astype(str).str.strip().str.lower().isin(['', 'nan', 'n/a'])]

        # Filter out 'good' vocabulary
        good_vocab = [k for k, v in self.vocabulary_knowledge.items() if v == 'good']
        if good_vocab:
            original_count = len(valid_vocab)
            valid_vocab = valid_vocab[~valid_vocab[word_col].isin(good_vocab)]
            print(f"ℹ️ Filtered out {original_count - len(valid_vocab)} 'good' vocabulary words.")

        if len(valid_vocab) < num_questions:
            print(f"⚠️ Only {len(valid_vocab)} vocabulary words available, using all of them")
            num_questions = len(valid_vocab)
        
        if num_questions == 0:
            print("❌ No valid vocabulary words found.")
            return None

        selected_vocab = valid_vocab.sample(n=num_questions)
        
        quiz_set = []
        for _, row in selected_vocab.iterrows():
            correct_meaning = row[meaning_col]
            word = row.get(word_col, 'N/A')
            
            question = {
                'word': word,
                'correct': correct_meaning,
                'level': self.vocabulary_knowledge.get(word, 'none')
            }
            
            quiz_set.append(question)
        
        return quiz_set

    def generate_vocabulary_options(self, correct_answer):
        """Generate 3 wrong multiple choice options for a vocabulary question."""
        if 'vocabulary' not in self.sheets_config or not self.sheets_config['vocabulary']['loaded']:
            return []
            
        vocab_data = self.sheets_config['vocabulary']['data']
        meaning_col = next((col for col in vocab_data.columns if col.strip().lower() in ['meaning', '意味', 'english']), None)
        
        if not meaning_col:
            return []

        # Get a pool of valid wrong answers
        valid_options = vocab_data[vocab_data[meaning_col].notna()]
        valid_options = valid_options[~valid_options[meaning_col].astype(str).str.strip().str.lower().isin(['', 'nan', 'n/a', correct_answer.lower()])]

        wrong_answers = []
        if len(valid_options) >= 3:
            wrong_answers = valid_options.sample(n=3)[meaning_col].tolist()

        # Fallback to generic answers if needed
        generic_answers = ["I don't know", "A type of food", "An action", "A place"]
        while len(wrong_answers) < 3:
            generic = random.choice(generic_answers)
            if generic not in wrong_answers and generic != correct_answer:
                wrong_answers.append(generic)
        
        # Create and shuffle options
        all_options = [correct_answer] + wrong_answers[:3]
        random.shuffle(all_options)
        return all_options

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

        # --- Knowledge-based filtering ---
        good_kanji = [k for k, v in self.kanji_knowledge.items() if v == 'good']
        if good_kanji:
            # Filter out the kanji marked as 'good'
            original_count = len(valid_rows)
            valid_rows = valid_rows[~valid_rows[meaning_column].isin(good_kanji)]
            print(f"ℹ️ Filtered out {original_count - len(valid_rows)} 'good' kanji from quiz pool.")

        if valid_rows.empty:
            print("❌ No valid kanji questions with meanings found after cleaning and filtering.")
            # Optional: a message to the user that they've learned everything
            # or reset the 'good' list if they want to practice again.
            return None

        # Now, safely sample a random row from the cleaned data
        row = valid_rows.sample(n=1).iloc[0]
        
        kanji_column = next((col for col in ['Kanji', '漢字', 'Character', '字'] if col in data.columns), None)
        onyomi_column = next((col for col in ['Onyomi', '音読み', 'On Reading', 'On'] if col in data.columns), None)
        kunyomi_column = next((col for col in ['Kunyomi', '訓読み', 'Kun Reading', 'Kun'] if col in data.columns), None)
        
        kanji_char = row.get(kanji_column, 'N/A')
        current_level = self.kanji_knowledge.get(kanji_char, 'none')
        
        return {
            'kanji': kanji_char,
            'meaning': row.get(meaning_column),  # No default needed, as we've already filtered
            'onyomi': row.get(onyomi_column, '') if onyomi_column else '',
            'kunyomi': row.get(kunyomi_column, '') if kunyomi_column else '',
            'level': current_level
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

@app.route('/vocabulary-quiz')
def vocabulary_quiz():
    """Vocabulary quiz page"""
    return render_template('vocabulary_quiz.html')

@app.route('/grammar-knowledge')
def grammar_knowledge():
    """Page to display categorized grammar knowledge."""
    knowledge = jlpt_app.grammar_knowledge
    categorized = {
        'good': [k for k, v in knowledge.items() if v == 'good'],
        'medium': [k for k, v in knowledge.items() if v == 'medium'],
        'dont_know': [k for k, v in knowledge.items() if v == 'dont_know']
    }
    return render_template('grammar_knowledge.html', categorized=categorized)

@app.route('/vocabulary-knowledge')
def vocabulary_knowledge():
    """Page to display categorized vocabulary knowledge."""
    knowledge = jlpt_app.vocabulary_knowledge
    categorized = {
        'good': [k for k, v in knowledge.items() if v == 'good'],
        'medium': [k for k, v in knowledge.items() if v == 'medium'],
        'dont_know': [k for k, v in knowledge.items() if v == 'dont_know']
    }
    return render_template('vocabulary_knowledge.html', categorized=categorized)

@app.route('/kanji-knowledge')
def kanji_knowledge():
    """Page to display categorized kanji knowledge."""
    knowledge = jlpt_app.kanji_knowledge
    
    categorized = {
        'good': [k for k, v in knowledge.items() if v == 'good'],
        'medium': [k for k, v in knowledge.items() if v == 'medium'],
        'dont_know': [k for k, v in knowledge.items() if v == 'dont_know']
    }
    
    return render_template('kanji_knowledge.html', categorized=categorized)

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

@app.route('/api/start-grammar-quiz')
def start_grammar_quiz():
    """API endpoint to start a new grammar quiz set"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    # Create a new quiz set of 20 questions
    quiz_set = jlpt_app.create_grammar_quiz_set(20)
    if not quiz_set:
        return jsonify({'error': 'No questions available'}), 404
    
    # Store quiz set in session
    session['grammar_quiz_set'] = quiz_set
    session['current_question_index'] = 0
    session['grammar_quiz_score'] = 0
    
    return jsonify({
        'message': 'Quiz started',
        'total_questions': len(quiz_set),
        'current_question': 1
    })

@app.route('/api/grammar-quiz-question/<int:question_index>')
def get_grammar_quiz_question(question_index):
    """API endpoint to get a specific question from the current quiz set"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    # Check if quiz set exists in session
    quiz_set = session.get('grammar_quiz_set')
    if not quiz_set:
        return jsonify({'error': 'No active quiz. Please start a new quiz.'}), 400
    
    # Check if question index is valid
    if question_index < 0 or question_index >= len(quiz_set):
        return jsonify({'error': 'Invalid question index'}), 400
    
    question = quiz_set[question_index]
    options = jlpt_app.generate_options(question['correct'])
    
    return jsonify({
        'question_index': question_index,
        'total_questions': len(quiz_set),
        'grammar': question['grammar'],
        'japanese': question['japanese'],
        'example': question['example'],
        'options': question['options'],
        'correct': question['correct']
    })

@app.route('/api/submit-grammar-answer', methods=['POST'])
def submit_grammar_answer():
    """API endpoint to submit an answer and get the next question"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    data = request.get_json()
    user_answer = data.get('answer', '').strip()
    question_index = data.get('question_index', 0)
    
    # Check if quiz set exists in session
    quiz_set = session.get('grammar_quiz_set')
    if not quiz_set:
        return jsonify({'error': 'No active quiz. Please start a new quiz.'}), 400
    
    # Check if question index is valid
    if question_index < 0 or question_index >= len(quiz_set):
        return jsonify({'error': 'Invalid question index'}), 400
    
    question = quiz_set[question_index]
    is_correct = user_answer == question['correct']
    
    # Update score
    if is_correct:
        session['grammar_quiz_score'] = session.get('grammar_quiz_score', 0) + 1
    
    # Check if this is the last question
    is_last_question = question_index == len(quiz_set) - 1
    
    response = {
        'correct': is_correct,
        'correct_answer': question['correct'],
        'score': session['grammar_quiz_score'],
        'total_questions': len(quiz_set),
        'is_last_question': is_last_question
    }
    
    # If not the last question, include next question info
    if not is_last_question:
        response['next_question_index'] = question_index + 1
    
    return jsonify(response)

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

@app.route('/api/update-kanji-knowledge', methods=['POST'])
def update_kanji_knowledge():
    """API endpoint to update the knowledge level of a kanji."""
    data = request.get_json()
    kanji = data.get('kanji')
    level = data.get('level')
    
    if not kanji or not level:
        return jsonify({'error': 'Missing kanji or level'}), 400
        
    jlpt_app.kanji_knowledge[kanji] = level
    jlpt_app.save_kanji_knowledge()
    
    return jsonify({'success': True, 'kanji': kanji, 'level': level})

@app.route('/api/update-grammar-knowledge', methods=['POST'])
def update_grammar_knowledge():
    """API endpoint to update the knowledge level of a grammar point."""
    data = request.get_json()
    grammar = data.get('grammar')
    level = data.get('level')
    if not grammar or not level:
        return jsonify({'error': 'Missing grammar or level'}), 400
    jlpt_app.grammar_knowledge[grammar] = level
    jlpt_app.save_grammar_knowledge()
    return jsonify({'success': True, 'grammar': grammar, 'level': level})

@app.route('/api/update-vocabulary-knowledge', methods=['POST'])
def update_vocabulary_knowledge():
    """API endpoint to update the knowledge level of a vocabulary word."""
    data = request.get_json()
    word = data.get('word')
    level = data.get('level')
    if not word or not level:
        return jsonify({'error': 'Missing word or level'}), 400
    jlpt_app.vocabulary_knowledge[word] = level
    jlpt_app.save_vocabulary_knowledge()
    return jsonify({'success': True, 'word': word, 'level': level})

@app.route('/api/start-vocabulary-quiz')
def start_vocabulary_quiz():
    """API endpoint to start a new vocabulary quiz set"""
    if not jlpt_app.data_loaded:
        return jsonify({'error': 'Data not loaded. Please restart the app.'}), 500
    
    quiz_set = jlpt_app.create_vocabulary_quiz_set(20)
    if not quiz_set:
        return jsonify({'error': 'No vocabulary questions available'}), 404
    
    session['vocabulary_quiz_set'] = quiz_set
    session['vocabulary_quiz_score'] = 0
    
    return jsonify({
        'message': 'Quiz started',
        'total_questions': len(quiz_set)
    })

@app.route('/api/vocabulary-quiz-question/<int:question_index>')
def get_vocabulary_quiz_question(question_index):
    """API endpoint to get a specific question from the current vocabulary quiz set"""
    quiz_set = session.get('vocabulary_quiz_set')
    if not quiz_set or question_index < 0 or question_index >= len(quiz_set):
        return jsonify({'error': 'Invalid quiz or question index'}), 400
    
    question = quiz_set[question_index]
    
    # Generate options on the fly
    options = jlpt_app.generate_vocabulary_options(question['correct'])
    
    return jsonify({
        'question_index': question_index,
        'total_questions': len(quiz_set),
        'word': question['word'],
        'options': options,
        'correct': question['correct']
    })

@app.route('/api/submit-vocabulary-answer', methods=['POST'])
def submit_vocabulary_answer():
    """API endpoint to submit a vocabulary answer"""
    data = request.get_json()
    user_answer = data.get('answer', '').strip()
    question_index = data.get('question_index', 0)
    
    quiz_set = session.get('vocabulary_quiz_set')
    if not quiz_set or question_index < 0 or question_index >= len(quiz_set):
        return jsonify({'error': 'Invalid quiz or question index'}), 400
    
    question = quiz_set[question_index]
    is_correct = user_answer == question['correct']
    
    if is_correct:
        session['vocabulary_quiz_score'] = session.get('vocabulary_quiz_score', 0) + 1
    
    return jsonify({
        'correct': is_correct,
        'correct_answer': question['correct'],
        'score': session.get('vocabulary_quiz_score', 0),
        'total_questions': len(quiz_set),
        'is_last_question': question_index == len(quiz_set) - 1
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