from gtts import gTTS
from playsound import playsound
import speech_recognition as sr

def convert_text_to_speech(text, filename):
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    #playsound(filename)

# Example usage
# text = "Hello, how are you?"
# filename = "outpuut.mp3"
# convert_text_to_speech(text, filename)



def convert_speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)  # Read the entire audio file

    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        print("Speech recognition could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))

# Example usage
# audio_file = "audio.wav"
# result = convert_speech_to_text(audio_file)
# print("Text: ", result)
