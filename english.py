import nltk
nltk.download('words')

def is_english_word(word):
    english_words = set(nltk.corpus.words.words())
    return word.lower() in english_words

# Example usage
word = "helloz"
is_english = is_english_word(word)
print("Is English:", is_english)
