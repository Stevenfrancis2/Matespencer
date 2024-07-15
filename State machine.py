import json
import RPi.GPIO as GPIO
import os
import pyaudio
import struct
import pvporcupine
from google.cloud import speech, texttospeech
import speech_recognition as sr
import requests
import pygame
import nltk
from nltk.tokenize import word_tokenize
from nltk import pos_tag
import time

# Initialize Pygame mixer for audio playback
pygame.mixer.init()

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

# Set your Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "coffee-419117-0d8ce7aeba95.json"

# Access Key for Porcupine
ACCESS_KEY = "UrYr3bejm5LN4oV48HXXmrLLvjkMfIL4NPIOKU7EOiH/4Qq0tcpICQ=="

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN)
GPIO.setup(22, GPIO.IN)
# 27 coffee
GPIO.setup(27, GPIO.OUT)
GPIO.output(27, GPIO.LOW)

# 16 sugar
GPIO.setup(16, GPIO.OUT)
GPIO.output(16, GPIO.LOW)
# 17 milk
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, GPIO.LOW)


def detect_wake_word(access_key):
    try:
        porcupine = pvporcupine.create(access_key=access_key, keywords=["porcupine"])
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True,
                               frames_per_buffer=porcupine.frame_length)
        print("Listening for wake word...")
        while True:
            pcm = audio_stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            if porcupine.process(pcm) >= 0:
                print("Wake word detected!")
                return True
    finally:
        porcupine.delete()
        audio_stream.close()
        pa.terminate()


def listen_and_record(filename="user_command.wav"):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)  # Shorter adjustment period for quicker response
        print("Please speak now...")
        try:
            audio_data = recognizer.listen(source, timeout=3, phrase_time_limit=5)
            with open(filename, "wb") as f:
                f.write(audio_data.get_wav_data())
            print(f"Recording saved as {filename}.")
            return True
        except sr.WaitTimeoutError:
            print("No speech was detected. Let's try again.")
            return False


def speech_to_text(speech_file='user_command.wav'):
    client = speech.SpeechClient()
    with open(speech_file, 'rb') as audio_file:
        content = audio_file.read()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        language_code='en-US'
    )
    response = client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript if response.results else "No speech could be recognized."


def send_text_to_model(text):
    url = "http://172.20.10.3:5555/conversation"  # Update to your API's endpoint
    data = {"prompt": text}
    response = requests.post(url, json=data)
    return response.json() if response.status_code == 200 else {"error": "Network or server error"}


def text_to_speech(text, filename="output.mp3", return_filename=False):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code='en-US', ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    path = os.path.join(os.getcwd(), filename)
    with open(path, 'wb') as audio_file:
        audio_file.write(response.audio_content)
    print(f'Audio content written to "{filename}"')
    if return_filename:
        return path


def speak(filename):
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()
    os.remove(filename)  # Clean up after playback


def interpret_yes_no_response(filename="user_response.wav"):
    text = speech_to_text(filename).lower()
    if text in ["no speech could be recognized.", "", "no speech"]:
        return "ambiguous"
    tokens = word_tokenize(text)
    tagged = pos_tag(tokens)
    positive_responses = ["yes", "sure", "okay", "alright", "yep", "definitely", "absolutely", "yup"]
    negative_responses = ["no", "not", "nope", "nah", "never"]
    positive = any(token in positive_responses for token, _ in tagged)
    negative = any(token in negative_responses for token, _ in tagged)
    if positive and not negative:
        return "yes"
    elif negative and not positive:
        return "no"
    else:
        return "ambiguous"


def ask_question_and_interpret_response(question, base_filename):
    response = "ambiguous"
    while response == "ambiguous":
        question_filename = text_to_speech(question, f"{base_filename}.mp3", return_filename=True)
        speak(question_filename)
        if not listen_and_record("user_response.wav"):
            reask_message = f"I didn't catch that. {question}"
            reask_filename = text_to_speech(reask_message, f"reask_{base_filename}.mp3", return_filename=True)
            speak(reask_filename)
            continue
        response = interpret_yes_no_response("user_response.wav")
        if response != "ambiguous":
            return response == "yes"


state = "idle"
while True:
    if state == "idle":
        text_to_speech("Listening for Wake Word", "wake.mp3")
        speak("wake.mp3")
        if detect_wake_word(ACCESS_KEY):  # Using ACCESS_KEY in detect_wake_word call
            state = "listen"
    elif state == "listen":
        text_to_speech("How can I help you?", "starting.mp3")
        speak("starting.mp3")
        listen_and_record()
        state = "speech_to_txt"
    elif state == "speech_to_txt":
        text = speech_to_text()
        with open("listening1.txt", "w") as text_file:
            text_file.write(text)
        state = "processing"
    elif state == "processing":
        json_response = send_text_to_model(text)
        is_about_coffee = json_response.get('results', {}).get('isAboutCoffee', False)
        if is_about_coffee:
            sugar_needed = json_response.get('results', {}).get('sugarPreference', 'not specified')
            milk_needed = json_response.get('results', {}).get('milkPreference', 'not specified')
            if sugar_needed == 'not specified':
                sugar_needed = ask_question_and_interpret_response("Do you need sugar?", "sugar_question.mp3")
                json_response['results']['sugarPreference'] = sugar_needed
            if milk_needed == 'not specified':
                milk_needed = ask_question_and_interpret_response("Do you want milk?", "milk_question.mp3")
                json_response['results']['milkPreference'] = milk_needed
            state = "make_cup"
        else:
            state = "continue_speaking"
    elif state == "continue_speaking":
        message_text = json_response.get('response', {}).get('content', "Sorry, I didn't catch that.")
        text_to_speech(message_text, "message.mp3")
        speak("message.mp3")
        state = "idle"
    elif state == "make_cup":
        text_to_speech("Making Your Cup of coffee", "making.mp3")
        speak("making.mp3")
        is_about_coffee = json_response.get('results', {}).get('isAboutCoffee', False)
        sugar_needed = str(json_response.get('results', {}).get('sugarPreference', 'false')).lower() == 'true'
        milk_needed = str(json_response.get('results', {}).get('milkPreference', 'false')).lower() == 'true'
        GPIO.output(27, GPIO.HIGH if is_about_coffee else GPIO.LOW)
        GPIO.output(16, GPIO.HIGH if sugar_needed else GPIO.LOW)
        GPIO.output(17, GPIO.HIGH if milk_needed else GPIO.LOW)
        print("starting the coffee-making process")
        print("Making a cup of coffee. Here's what I know:")
        print(f"Coffee: {json_response.get('results', {}).get('isAboutCoffee', False)}")
        print(f"Sugar preference: {json_response.get('results', {}).get('sugarPreference', 'not specified')}")
        print(f"Milk preference: {json_response.get('results', {}).get('milkPreference', 'not specified')}")

        while True:
            if GPIO.input(18) == GPIO.HIGH:
                print("DISPENSE WATER")
                text_to_speech("Dispense Water please", "dispense.mp3")
                speak("dispense.mp3")
                break
            time.sleep(0.5)

        while True:
            if GPIO.input(22) == GPIO.HIGH:
                print("coffe done making")
                break
            time.sleep(0.5)

        GPIO.output(16, GPIO.LOW)
        GPIO.output(17, GPIO.LOW)
        GPIO.output(27, GPIO.LOW)

        state = "welcome"
    elif state == "welcome":
        text_to_speech("Your coffee is done ", "coffee_done.mp3")
        speak("coffee_done.mp3")
        state = "idle"