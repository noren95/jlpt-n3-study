import os
import random
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class JLPTApp:
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
                'name': "Kanji",  # Change this to your actual kanji sheet name
                'data': None,
                'loaded': False
            }
        }
        self.service = None
        self.data = None  # Keep for backward compatibility
        self.score = 0
        self.total_questions = 0
        
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
            print("✅ Connected to Google Sheets!")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def load_data(self):
        """Load all sheet data from Google Sheets"""
        try:
            # Load grammar data
            print("📥 Loading grammar data...")
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheets_config['grammar']['name']}!A1:Z1000"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print("❌ No grammar data found!")
                return False
            
            # Convert to DataFrame
            self.sheets_config['grammar']['data'] = pd.DataFrame(values[1:], columns=values[0])
            self.sheets_config['grammar']['loaded'] = True
            print(f"✅ Loaded {len(self.sheets_config['grammar']['data'])} grammar points!")
            
            # For backward compatibility, set the main data to grammar data
            self.data = self.sheets_config['grammar']['data']
            
            # Debug: Show available columns
            print("📋 Available grammar columns:")
            for i, col in enumerate(self.data.columns):
                print(f"  {i}: {col}")
            
            # Try to load kanji data
            try:
                print("📥 Loading kanji data...")
                kanji_result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheets_config['kanji']['name']}!A1:Z1000"
                ).execute()
                
                kanji_values = kanji_result.get('values', [])
                if kanji_values:
                    self.sheets_config['kanji']['data'] = pd.DataFrame(kanji_values[1:], columns=kanji_values[0])
                    self.sheets_config['kanji']['loaded'] = True
                    print(f"✅ Loaded {len(self.sheets_config['kanji']['data'])} kanji items!")
                    
                    print("📋 Available kanji columns:")
                    for i, col in enumerate(self.sheets_config['kanji']['data'].columns):
                        print(f"  {i}: {col}")
                else:
                    print("⚠️ No kanji data found")
            except Exception as e:
                print(f"⚠️ Could not load kanji sheet: {e}")
            
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
    
    def get_random_sentence_question(self):
        """Get a random sentence question from example sentences"""
        if self.sheets_config['grammar']['data'] is None or self.sheets_config['grammar']['data'].empty:
            return None
        
        # Try different possible column names for examples
        example_column = None
        possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
        
        for col_name in possible_example_columns:
            if col_name in self.sheets_config['grammar']['data'].columns:
                example_column = col_name
                break
        
        if not example_column:
            return None
        
        # Get all sentences from all rows
        all_sentences = []
        
        for i, row in self.sheets_config['grammar']['data'].iterrows():
            example_text = row.get(example_column, '')
            if example_text and str(example_text) != 'nan':
                sentences = self.parse_example_sentences(example_text)
                all_sentences.extend(sentences)
        
        if not all_sentences:
            return None
        
        # Pick a random sentence
        return random.choice(all_sentences)
    
    def generate_sentence_options(self, correct_english):
        """Generate wrong options for sentence questions"""
        # Get other English translations from the data
        wrong_answers = []
        example_column = None
        possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
        
        for col_name in possible_example_columns:
            if col_name in self.sheets_config['grammar']['data'].columns:
                example_column = col_name
                break
        
        if example_column:
            for _, row in self.sheets_config['grammar']['data'].iterrows():
                example_text = row.get(example_column, '')
                sentences = self.parse_example_sentences(example_text)
                for sentence in sentences:
                    english = sentence['english']
                    if english and english != correct_english and len(wrong_answers) < 5:
                        wrong_answers.append(english)
        
        # Add generic wrong answers if needed
        generic_answers = [
            "I don't know",
            "It's difficult",
            "Please help me",
            "I understand",
            "That's correct"
        ]
        
        while len(wrong_answers) < 3:
            generic = random.choice(generic_answers)
            if generic not in wrong_answers and generic != correct_english:
                wrong_answers.append(generic)
        
        return wrong_answers[:3]
    
    def get_random_question(self):
        """Get a random grammar question"""
        if self.sheets_config['grammar']['data'] is None or self.sheets_config['grammar']['data'].empty:
            return None
        
        row = self.sheets_config['grammar']['data'].sample(n=1).iloc[0]
        
        # Try different possible column names for examples
        example = None
        possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
        
        for col_name in possible_example_columns:
            if col_name in self.sheets_config['grammar']['data'].columns:
                example = row.get(col_name, None)
                if example and str(example) != 'nan' and str(example).strip():
                    break
        
        # Extract Japanese example sentence only
        japanese_example = None
        if example:
            example_str = str(example)
            # Split by newline and take the first line (Japanese part)
            example_lines = example_str.split('\n')
            japanese_example = example_lines[0].strip()
            
            # If it's still empty or just whitespace, try the whole string
            if not japanese_example or japanese_example.isspace():
                japanese_example = example_str.strip()
        
        return {
            'grammar': row.get('Grammar Lesson', 'N/A'),
            'japanese': row.get('文法レッスン', 'N/A'),
            'correct': row.get('Grammar Meaning', 'N/A'),
            'example': japanese_example
        }
    
    def generate_options(self, correct_answer):
        """Generate 4 multiple choice options"""
        # Get wrong answers from other grammar points
        wrong_answers = []
        sample = self.sheets_config['grammar']['data'].sample(n=min(10, len(self.sheets_config['grammar']['data'])))
        
        for _, row in sample.iterrows():
            meaning = row.get('Grammar Meaning', '')
            if meaning and meaning != correct_answer and len(wrong_answers) < 3:
                wrong_answers.append(meaning)
        
        # Add generic answers if needed
        generic = ["to do something", "because of", "in order to", "while doing"]
        while len(wrong_answers) < 3:
            wrong_answers.append(generic[len(wrong_answers)])
        
        # Create and shuffle options
        options = [correct_answer] + wrong_answers[:3]
        random.shuffle(options)
        return options
    
    def play_sentence_quiz(self):
        """Play quiz using example sentences"""
        print("\n🇯🇵 JLPT N3 Sentence Translation Quiz 🇯🇵")
        print("=" * 60)
        print("How to play:")
        print("• You'll see a Japanese sentence")
        print("• Choose the correct English translation (A, B, C, D)")
        print("• Type 'quit' to exit")
        print("• Type 'stats' to see your score")
        print("• Type 'grammar' to switch to grammar quiz")
        print("=" * 60)
        
        while True:
            question = self.get_random_sentence_question()
            if not question:
                print("❌ No sentence questions available!")
                break
            
            print(f"\n📝 Japanese Sentence:")
            print(f"「{question['japanese']}」")
            print(f"\nWhat does this mean?")
            
            # Generate options
            correct_english = question['english']
            wrong_answers = self.generate_sentence_options(correct_english)
            options = [correct_english] + wrong_answers
            random.shuffle(options)
            
            # Show options
            for i, option in enumerate(options):
                print(f"{chr(65+i)}. {option}")
            
            # Get user answer
            while True:
                answer = input("\nYour answer (A/B/C/D, 'quit', 'stats', or 'grammar'): ").strip().upper()
                
                if answer == 'QUIT':
                    self.show_final_stats()
                    return
                elif answer == 'STATS':
                    self.show_stats()
                    break
                elif answer == 'GRAMMAR':
                    self.play_quiz()
                    return
                elif answer in ['A', 'B', 'C', 'D']:
                    # Check answer
                    user_choice = options[ord(answer) - 65]
                    self.total_questions += 1
                    
                    if user_choice == correct_english:
                        print("✅ Correct!")
                        self.score += 1
                    else:
                        print(f"❌ Wrong! The answer is: {correct_english}")
                    
                    print(f"Score: {self.score}/{self.total_questions}")
                    break
                else:
                    print("Please enter A, B, C, D, quit, stats, or grammar")
    
    def play_quiz(self):
        """Main grammar quiz game"""
        print("\n🎌 JLPT N3 Grammar Quiz 🎌")
        print("=" * 50)
        print("How to play:")
        print("• Choose A, B, C, or D for the meaning")
        print("• Type 'quit' to exit")
        print("• Type 'stats' to see your score")
        print("• Type 'sentence' to switch to sentence quiz")
        print("=" * 50)
        
        while True:
            question = self.get_random_question()
            if not question:
                print("❌ No questions available!")
                break
            
            print(f"\n📝 Grammar: {question['grammar']}")
            print(f"🇯🇵 Japanese: {question['japanese']}")
            
            if question['example'] and str(question['example']) != 'nan':
                print(f"📖 Example: {question['example']}")
            
            print(f"\nWhat does this mean?")
            
            # Show options
            options = self.generate_options(question['correct'])
            for i, option in enumerate(options):
                print(f"{chr(65+i)}. {option}")
            
            # Get user answer
            while True:
                answer = input("\nYour answer (A/B/C/D, 'quit', 'stats', or 'sentence'): ").strip().upper()
                
                if answer == 'QUIT':
                    self.show_final_stats()
                    return
                elif answer == 'STATS':
                    self.show_stats()
                    break
                elif answer == 'SENTENCE':
                    self.play_sentence_quiz()
                    return
                elif answer in ['A', 'B', 'C', 'D']:
                    # Check answer
                    user_choice = options[ord(answer) - 65]
                    self.total_questions += 1
                    
                    if user_choice == question['correct']:
                        print("✅ Correct!")
                        self.score += 1
                    else:
                        print(f"❌ Wrong! The answer is: {question['correct']}")
                    
                    print(f"Score: {self.score}/{self.total_questions}")
                    break
                else:
                    print("Please enter A, B, C, D, quit, stats, or sentence")
    
    def show_stats(self):
        """Show current statistics"""
        print(f"\n📊 Current Stats:")
        print(f"   Score: {self.score}/{self.total_questions}")
        if self.total_questions > 0:
            percentage = (self.score / self.total_questions) * 100
            print(f"   Accuracy: {percentage:.1f}%")
        else:
            print("   Accuracy: 0%")
    
    def show_final_stats(self):
        """Show final statistics"""
        print("\n" + "=" * 50)
        print("🏁 Quiz Complete!")
        self.show_stats()
        print("=" * 50)
    
    def play_kanji_quiz(self):
        """Play kanji quiz"""
        print("\n" + "=" * 50)
        print("🈶 KANJI QUIZ")
        print("=" * 50)
        print("How to play:")
        print("• Choose A, B, C, or D for kanji meaning questions")
        print("• Type your answer for sentence translation questions")
        print("• Type 'quit' to exit")
        print("• Type 'stats' to see your score")
        print("• Type 'grammar' to switch to grammar quiz")
        print("=" * 50)
        
        if not self.sheets_config['kanji']['loaded']:
            print("❌ Kanji data not available. Please check your kanji sheet.")
            return
        
        while True:
            # Randomly choose between classic kanji and sentence questions
            question_type = random.choice(['classic', 'sentence'])
            
            if question_type == 'sentence':
                # Sentence translation question
                question = self.get_random_kanji_sentence_question()
                if not question:
                    # Fallback to classic kanji question if no sentences available
                    question = self.get_random_kanji_question()
                    if not question:
                        print("❌ No kanji questions available")
                        return
                    question_type = 'classic'
                else:
                    # Display sentence question
                    print(f"\n🇯🇵 SENTENCE TRANSLATION")
                    print(f"📝 {question['japanese']}")
                    print(f"\nTranslate this sentence to English:")
                    
                    # Get user answer
                    while True:
                        answer = input("\nYour answer (or 'quit', 'stats', 'grammar'): ").strip()
                        
                        if answer.lower() == 'quit':
                            self.show_final_stats()
                            return
                        elif answer.lower() == 'stats':
                            self.show_stats()
                            break
                        elif answer.lower() == 'grammar':
                            self.play_quiz()
                            return
                        elif answer:
                            # Check answer similarity
                            self.total_questions += 1
                            is_correct = self.check_answer_similarity(answer, question['english'])
                            
                            if is_correct:
                                print("✅ Correct!")
                                self.score += 1
                            else:
                                print(f"❌ Close, but not quite right.")
                                print(f"📖 The answer was: {question['english']}")
                            
                            print(f"Score: {self.score}/{self.total_questions}")
                            break
                        else:
                            print("Please enter your answer or 'quit', 'stats', 'grammar'")
                    
                    continue  # Skip to next question
            
            # Classic kanji meaning question
            question = self.get_random_kanji_question()
            if not question:
                print("❌ No kanji questions available")
                return
            
            correct_answer = question['meaning']
            question_text = f"What does the kanji {question['kanji']} mean?"
            options = self.generate_kanji_options(correct_answer, 'meaning')
            
            # Display classic kanji question with readings
            print(f"\n🈶 CLASSIC KANJI QUESTION")
            print(f"🈶 {question['kanji']}")
            
            # Show readings if available
            readings_display = []
            if question['onyomi'] and str(question['onyomi']) != 'nan':
                readings_display.append(f"音読み: {question['onyomi']}")
            if question['kunyomi'] and str(question['kunyomi']) != 'nan':
                readings_display.append(f"訓読み: {question['kunyomi']}")
            
            if readings_display:
                print(f"📖 Readings: {' | '.join(readings_display)}")
            
            print(f"📝 Question: {question_text}")
            
            # Show options
            all_options = [correct_answer] + options
            random.shuffle(all_options)
            for i, option in enumerate(all_options):
                print(f"{chr(65+i)}. {option}")
            
            # Get user answer
            while True:
                answer = input("\nYour answer (A/B/C/D, 'quit', 'stats', or 'grammar'): ").strip().upper()
                
                if answer == 'QUIT':
                    self.show_final_stats()
                    return
                elif answer == 'STATS':
                    self.show_stats()
                    break
                elif answer == 'GRAMMAR':
                    self.play_quiz()
                    return
                elif answer in ['A', 'B', 'C', 'D']:
                    # Check answer
                    user_choice = all_options[ord(answer) - 65]
                    self.total_questions += 1
                    
                    if user_choice == correct_answer:
                        print("✅ Correct!")
                        self.score += 1
                    else:
                        print(f"❌ Wrong! The answer is: {correct_answer}")
                    
                    print(f"Score: {self.score}/{self.total_questions}")
                    break
                else:
                    print("Please enter A, B, C, D, quit, stats, or grammar")

    def choose_quiz_mode(self):
        """Let user choose quiz mode"""
        print("\n🎯 Choose Quiz Mode:")
        print("1. Grammar Quiz - Learn grammar meanings")
        print("2. Sentence Quiz - Translate Japanese sentences")
        print("3. Kanji Quiz - Test kanji meanings and readings")
        print("4. Exit")
        
        while True:
            choice = input("\nEnter 1, 2, 3, or 4: ").strip()
            if choice == '1':
                self.play_quiz()
                break
            elif choice == '2':
                self.play_sentence_quiz()
                break
            elif choice == '3':
                self.play_kanji_quiz()
                break
            elif choice == '4':
                print("👋 Goodbye!")
                break
            else:
                print("Please enter 1, 2, 3, or 4")
    
    def run(self):
        """Main application runner"""
        print("🚀 Starting JLPT Grammar Quiz...")
        
        if not self.authenticate():
            return
        
        if not self.load_data():
            return
        
        self.choose_quiz_mode()

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
        # This is the core of the fix to prevent 'N/A' questions.
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
            # This is the core of the fix to prevent 'N/A' as a choice.
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

def main():
    app = JLPTApp()
    app.run()

if __name__ == "__main__":
    main() 