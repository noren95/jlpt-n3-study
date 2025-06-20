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
        self.sheet_name = "גיליון1"
        self.service = None
        self.data = None
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
        """Load grammar data from Google Sheets"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1:Z1000"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print("❌ No data found!")
                return False
            
            # Convert to DataFrame
            self.data = pd.DataFrame(values[1:], columns=values[0])
            print(f"✅ Loaded {len(self.data)} grammar points!")
            
            # Debug: Show available columns
            print("📋 Available columns:")
            for i, col in enumerate(self.data.columns):
                print(f"  {i}: {col}")
            
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
        if self.data is None or self.data.empty:
            return None
        
        # Try different possible column names for examples
        example_column = None
        possible_example_columns = ['Example Senstence', 'Example Sentence', 'Example', 'Examples', 'Sentence', 'Sentences']
        
        for col_name in possible_example_columns:
            if col_name in self.data.columns:
                example_column = col_name
                break
        
        if not example_column:
            return None
        
        # Get all sentences from all rows
        all_sentences = []
        
        for i, row in self.data.iterrows():
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
            if col_name in self.data.columns:
                example_column = col_name
                break
        
        if example_column:
            for _, row in self.data.iterrows():
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
        if self.data is None or self.data.empty:
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
        sample = self.data.sample(n=min(10, len(self.data)))
        
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
    
    def choose_quiz_mode(self):
        """Let user choose quiz mode"""
        print("\n🎯 Choose Quiz Mode:")
        print("1. Grammar Quiz - Learn grammar meanings")
        print("2. Sentence Quiz - Translate Japanese sentences")
        print("3. Exit")
        
        while True:
            choice = input("\nEnter 1, 2, or 3: ").strip()
            if choice == '1':
                self.play_quiz()
                break
            elif choice == '2':
                self.play_sentence_quiz()
                break
            elif choice == '3':
                print("👋 Goodbye!")
                break
            else:
                print("Please enter 1, 2, or 3")
    
    def run(self):
        """Main application runner"""
        print("🚀 Starting JLPT Grammar Quiz...")
        
        if not self.authenticate():
            return
        
        if not self.load_data():
            return
        
        self.choose_quiz_mode()

def main():
    app = JLPTApp()
    app.run()

if __name__ == "__main__":
    main() 