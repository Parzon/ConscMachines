import logging
from openai import OpenAI
import time
import asyncio
from utilities import write_csv
from audio import listen_to_user, analyze_voice_sentiment, transcribe_audio, generate_voice_embeddings
from video import stream_video, detect_faces, analyze_face_sentiment, generate_face_embeddings, handle_new_face, handle_new_voice
from sentiment_analysis import wants_response, generate_response, generate_speech_response
from database_operations import setup_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

if __name__ == "__main__":
    setup_database()  # Ensure the database is set up

    csv_data = []

    logger.info("Starting application")

    # Analyze video stream for face sentiment and recognition
    stream = stream_video()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(analyze_face_sentiment(stream, csv_data))

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    faces = detect_faces(frame)

    for (x, y, w, h) in faces:
        face = frame[y:y+h, x:x+w]
        face_embedding = generate_face_embeddings(face)
        name, user_id = handle_new_face(face_embedding)

        # Capture voice input and generate embeddings
        listen_to_user()
        audio_file = "audio.wav"
        voice_embedding = generate_voice_embeddings(audio_file)
        handle_new_voice(voice_embedding, user_id)

        text_result = transcribe_audio(audio_file, client)
        logger.info(f"Transcribed text: {text_result}")

        time.sleep(10)

        voice_task = asyncio.create_task(analyze_voice_sentiment(audio_file, csv_data))
        video_stream = stream_video()
        face_task = asyncio.create_task(analyze_face_sentiment(video_stream, csv_data))

        asyncio.run(asyncio.gather(voice_task, face_task))

        if wants_response(text_result, client):
            response_text = generate_response(text_result, "Sentiment analysis data", client)
            logger.info(f"Generated response: {response_text}")
            speech_file = generate_speech_response(response_text, client)
            logger.info(f"Speech response saved to {speech_file}")
        else:
            logger.info("User did not ask for a response. Continuing to listen...")
            listen_to_user()

    write_csv("sentiment_analysis.csv", csv_data)
    logger.info("Data written to CSV")
