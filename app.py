from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import sys
import pkg_resources
import requests
import yt_dlp
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)

client = OpenAI()

def ping_self():
    try:
        response = requests.get(
            "https://renderbackend-8hhs.onrender.com/ping",  # Use the deployed URL
            headers={"User-Agent": "Flask-Ping-Bot"}  # Add a User-Agent header
        )
        if response.status_code == 200:
            print("Successfully pinged the server.")
        else:
            print(f"Ping failed with status code: {response.status_code}")
    except Exception as e:
        print(f"Error while pinging the server: {e}")


scheduler = BackgroundScheduler()
scheduler.add_job(func=ping_self, trigger="interval", seconds=14 * 60)
scheduler.start()

@app.route('/get_title', methods=['GET'])
def get_title():
    # Extract video URL from the query parameters
    video_url = request.args.get("url")

    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400

    # Parse the video ID using replace
    if video_url.startswith('https://www.youtube.com/watch?v='):
        video_id = video_url.replace('https://www.youtube.com/watch?v=', '')
    else:
        return jsonify({"error": "Invalid YouTube URL format"}), 400

    # RapidAPI endpoint and headers
    url = "https://yt-api.p.rapidapi.com/video/info"
    querystring = {"id": video_id}

    headers = {
        "x-rapidapi-key": "817820eb8cmsha7b606618240564p19021djsn6d68dd3cbd32",
        "x-rapidapi-host": "yt-api.p.rapidapi.com"
    }

    try:
        # Make the request to the API
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()

        # Extract and return the title
        if "title" in data:
            return jsonify({"title": data["title"]})
        else:
            return jsonify({"error": "Title not found in the response"}), 404
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/summarize', methods=['POST'])
def summarize():
    print("1: Received request")
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "YouTube URL is required"}), 400
        print(f"URL: {url}")

        video_id = url.replace('https://www.youtube.com/watch?v=', '')
        print(f"Video ID: {video_id}")
        print("2: Extracted video ID")


        #Get Title
        url = "https://yt-api.p.rapidapi.com/video/info"
        querystring = {"id": video_id}

        headers = {
        "x-rapidapi-key": "817820eb8cmsha7b606618240564p19021djsn6d68dd3cbd32",
        "x-rapidapi-host": "yt-api.p.rapidapi.com"
        }

        # Make the request to the API
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()

        title=data.get("title")


        # Fetch transcript
        rapid_api_url = "https://youtube-transcripts.p.rapidapi.com/youtube/transcript"
        headers = {
            "x-rapidapi-key": "817820eb8cmsha7b606618240564p19021djsn6d68dd3cbd32",
            "x-rapidapi-host": "youtube-transcripts.p.rapidapi.com"
        }
        params = {"videoId": video_id, "chunkSize": "500"}

        response = requests.get(rapid_api_url, headers=headers, params=params)
        if response.status_code == 200:
            transcript = [item["text"] for item in response.json().get("content", [])]
        else:
            return jsonify({"error": "Could not fetch transcript"}), 400

        print("\n\n\n GOT TRANSCRIPT")
        ans = " ".join(transcript)

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
        print("\n\n\n",summary)

        print("success")
        return jsonify({"title": title, "summary": summary})

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/version', methods=['GET'])
def version():
    return jsonify({
        "python_version": sys.version,
        "flask_version": pkg_resources.get_distribution("flask").version,  # Corrected to get flask version
        "openai_version": pkg_resources.get_distribution("openai").version,
        "youtube_transcript_api_version": pkg_resources.get_distribution("youtube-transcript-api").version,
        "beautifulsoup_version": pkg_resources.get_distribution("beautifulsoup4").version  # Commented out
    })


@app.route('/test-youtube', methods=['GET'])
def test_youtube():
    response = requests.get('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    return jsonify({"status": response.status_code, "content": response.text[:200]})


@app.route('/greet', methods=['GET'])
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

# Flask route to handle the ping
@app.route("/ping")
def ping():
    print("Pong! Server is alive!")
    return "Pong! Server is alive!", 200

# Flask home route
@app.route("/")
def home():
    return "Flask app is running and pinging itself every 5 second!"

if __name__ == '__main__':
    app.run(debug=True)
