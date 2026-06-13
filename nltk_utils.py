import nltk
import numpy as np
import os
import csv
import re
from nltk.stem.porter import PorterStemmer
from spellchecker import SpellChecker

nltk.download('punkt')
nltk.download('punkt_tab')

stemmer = PorterStemmer()
spell = SpellChecker()

# Load custom vocabulary to protect specialized train terms
def _load_custom_vocab():
    custom_words = set()
    data_path = os.path.join(os.path.dirname(__file__), 'data.csv')
    if os.path.exists(data_path):
        try:
            with open(data_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Collect stations, train names, and types
                    for key in ['From', 'To', 'Train_Name', 'Train_Type']:
                        val = row.get(key, '')
                        # Split by space and hyphen to get individual words
                        words = re.split(r'[\s\-]+', val)
                        for w in words:
                            if w: custom_words.add(w.lower())
        except Exception as e:
            print(f"Warning: Could not load custom vocab for spellchecker: {e}")
    
    # Add common intent words that might be rare in basic English dicts
    custom_words.update(['talgo', 'sleeper', 'ac', 'trip', 'fare', 'schedule'])
    return list(custom_words)

# Add custom words to the spellchecker dictionary
spell.word_frequency.load_words(_load_custom_vocab())

def tokenize(sentence):
    return nltk.word_tokenize(sentence)

def correct_spelling(tokens):
    corrected_tokens = []
    for token in tokens:
        # Only correct alphabetic tokens longer than 2 chars to avoid messing with IDs/Times
        if token.isalpha() and len(token) > 2:
            corrected = spell.correction(token)
            corrected_tokens.append(corrected if corrected else token)
        else:
            corrected_tokens.append(token)
    return corrected_tokens

def stem(word):
    return stemmer.stem(word.lower())

def bag_of_words(tokenized_sentence, all_words):
    tokenized_sentence = [stem(w) for w in tokenized_sentence]
    bag = np.zeros(len(all_words), dtype=np.float32)
    for idx, w in enumerate(all_words):
        if w in tokenized_sentence:
            bag[idx] = 1.0
    return bag
