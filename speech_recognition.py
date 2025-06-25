<<<<<<< HEAD
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/speech_recognition.py b/speech_recognition.py
index d407e37d842c5fa249bff9d04d2f133dfb7e3dad..f783aefb5e83202240e3d757bd4a6c20b8d86ad2 100644
--- a/speech_recognition.py
+++ b/speech_recognition.py
@@ -1,27 +1,28 @@
 import os
 import azure.cognitiveservices.speech as speechsdk
 
 def recognize_from_microphone():
      # This example requires environment variables named "SPEECH_KEY" and "ENDPOINT"
      # Replace with your own subscription key and endpoint, the endpoint is like : "https://YourServiceRegion.api.cognitive.microsoft.com"
     speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), endpoint=os.environ.get('ENDPOINT'))
-    speech_config.speech_recognition_language="en-US"
+    # Set the recognition language to Japanese
+    speech_config.speech_recognition_language="ja-JP"
 
     audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
     speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
 
     print("Speak into your microphone.")
     speech_recognition_result = speech_recognizer.recognize_once_async().get()
 
     if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
         print("Recognized: {}".format(speech_recognition_result.text))
     elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
         print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
     elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
         cancellation_details = speech_recognition_result.cancellation_details
         print("Speech Recognition canceled: {}".format(cancellation_details.reason))
         if cancellation_details.reason == speechsdk.CancellationReason.Error:
             print("Error details: {}".format(cancellation_details.error_details))
             print("Did you set the speech resource key and endpoint values?")
 
-recognize_from_microphone()
+recognize_from_microphone()
 
EOF
)
=======
import os
import azure.cognitiveservices.speech as speechsdk

def recognize_from_microphone():
     # This example requires environment variables named "SPEECH_KEY" and "ENDPOINT"
     # Replace with your own subscription key and endpoint, the endpoint is like : "https://YourServiceRegion.api.cognitive.microsoft.com"
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), endpoint=os.environ.get('ENDPOINT'))
    # Set the recognition language to Japanese
    speech_config.speech_recognition_language="ja-JP"

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("Speak into your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and endpoint values?")

recognize_from_microphone()
>>>>>>> 8fad3789fc3ef9ed6bc503335fc09ac1b27a06d7
