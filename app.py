from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import sys
import flask
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
import pkg_resources
import requests
import os

app = Flask(__name__)
CORS(app)

client = OpenAI()

PROXY = os.getenv("HTTP_PROXY", "http://123.45.67.89:8080")

session = requests.Session()
session.proxies = {
    "http": PROXY,
    "https": PROXY,
}

# Log the proxy being used
print(f"Using proxy: {session.proxies}")

def fetch_transcript_with_proxy(video_id):
    # Set up the proxy for the YouTubeTranscriptApi
    YouTubeTranscriptApi._http = session  # Patching the internal request session of YouTubeTranscriptApi
    return YouTubeTranscriptApi.get_transcript(video_id)

@app.route('/summarize', methods=['POST'])
def summarize():
    print("1: Received request")
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "YouTube URL is required"}), 400
        print(f"URL:", url)

        video_id = url.replace('https://www.youtube.com/watch?v=', '')

        # Log to see if the video_id is correct
        print(f"Video ID: {video_id}")
        print("2: Extracted video ID")
        try:
            # Use the patched method to fetch the transcript through the proxy
            transcript = fetch_transcript_with_proxy(video_id)
        except Exception as e:
            print(f"Error fetching transcript: {str(e)}")  # Log the error
            return jsonify({"error": f"Could not retrieve a transcript for the video. Error: {str(e)}"}), 400

        ans = ""
        for x in transcript:
            ans += x['text']

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""
            You are a helpful assistant. Summarize the following video transcript in two parts:
            1. At the top, write a summary that identifies the main takeaways of the video.
            2. Provide a chronological summary of the video, highlighting key points as they happen.

            Here is the transcript: {ans}"""}
            ]
        )
        summary = completion.choices[0].message.content

        return jsonify({"summary": summary})

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Log the error
        return jsonify({"error": str(e)}), 500


@app.route('/version', methods=['GET'])
def version():
    return jsonify({
        "python_version": sys.version,
        "flask_version": flask.__version__,
        "openai_version": openai.__version__,
        "youtube_transcript_api_version": pkg_resources.get_distribution("youtube-transcript-api").version
    })


@app.route('/test-youtube', methods=['GET'])
def test_youtube():
    response = requests.get('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    return jsonify({"status": response.status_code, "content": response.text[:200]})


@app.route('/greet', methods=['POST'])
def greet():
    print("1: Received request")
    
    completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": """Hi, how are you doing?

            """}
            ]
        )
    summary = completion.choices[0].message.content

    return jsonify({"summary": summary})


@app.route('/get_transcript', methods=['GET'])
def get_transcript():
    print("1: Received GET request for transcript")
    try:
        # Select a random video URL
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"Selected video URL: {url}")

        # Extract video ID
        video_id = url.split("v=")[-1]
        print(f"Extracted video ID: {video_id}")

        # Fetch the transcript
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            print(f"Error fetching transcript: {str(e)}")  # Log the error
            return jsonify({"error": f"Could not retrieve a transcript for the video. Error: {str(e)}"}), 400

        # Combine transcript into a single string
        transcript_text = " ".join([x['text'] for x in transcript])
        print("2: Successfully fetched transcript")

        return jsonify({
            "video_url": url,
            "transcript": transcript_text
        })

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Log the error
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)