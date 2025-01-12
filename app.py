from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import sys
import pkg_resources
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import time
import os
import re

app = Flask(__name__)
CORS(app)
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
client = OpenAI()

# List of functions for getting transcripts
transcript_functions = []



#Functions
def extract_video_id(url):
    patterns = [
        r'https://youtu.be/([a-zA-Z0-9_-]+)',  # For mobile format (youtu.be)
        r'https://youtube.com/shorts/([a-zA-Z0-9_-]+)',  # For mobile shorts format
        r'https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]+)',  # For web format (watch?v=)
        r'https://www.youtube.com/shorts/([a-zA-Z0-9_-]+)',  # For web shorts format
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_video_title(video_id):
    url = "https://yt-api.p.rapidapi.com/video/info"
    querystring = {"id": video_id}

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "yt-api.p.rapidapi.com"
    }

    try:
        # Make the request to the API
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx, 5xx)
        
        # Parse the JSON response
        data = response.json()

        # Extract the title
        title = data.get("title")
        
        if title is None:
            raise ValueError("Title not found in the response data.")
        
        return title

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None  # Or return an appropriate error message or value

    except ValueError as e:
        print(f"Error extracting title: {e}")
        return None  # Or return an appropriate error message or value



#https://rapidapi.com/8v2FWW4H6AmKw89/api/youtube-transcripts
def Youtube_Transcripts(video_id):
    rapid_api_url = "https://youtube-transcripts.p.rapidapi.com/youtube/transcript"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "youtube-transcripts.p.rapidapi.com"
    }
    params = {"videoId": video_id, "chunkSize": "500"}
    print("0")
    try:
        # Make the request to the API
        response = requests.get(rapid_api_url, headers=headers, params=params)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx, 5xx)

        if response.status_code == 200:
            transcript = [item["text"] for item in response.json().get("content", [])]
            ans = " ".join(transcript)
            print("Received Transcript")
            return ans
        else:
            print("Error: Could not fetch transcript")
            return None  # Or raise an exception if you want to handle it differently

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None  # Or return an appropriate error message or value

#https://rapidapi.com/solid-api-solid-api-default/api/youtube-transcript3
def Youtube_Transcript(video_id):
    print("1")
    try:
        # RapidAPI request setup
        url = "https://youtube-transcript3.p.rapidapi.com/api/transcript"

        querystring = {"videoId": video_id}

        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "youtube-transcript3.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
    
        transcript = response.json().get("transcript", [])
        
        # Extracting just the text from the transcript
        text = [entry["text"] for entry in transcript]
        
        return text


    except Exception as e:
        return jsonify({"error": "An error occurred.", "details": str(e)}), 500

#https://rapidapi.com/timetravellershq/api/youtube-transcripts-api
def Youtube_Transcripts_API(video_id):
    url = "https://youtube-transcripts-api.p.rapidapi.com/api/transcript/"
    print("2")
    querystring = {"video_id": video_id, "language": 'en'}

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "youtube-transcripts-api.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        transcript = [item['text'] for item in response.json().get('content', [])]

        # Remove the first element, and the last two elements
        if len(transcript) > 2:
            transcript = transcript[1:-2]
        
        # Modify the last element to remove its first and last characters
        if len(transcript) > 0:
            transcript[-1] = transcript[-1][1:-1]

        # Join the lines into a single string
        return " ".join(transcript)
    else:
        return {"error": "Failed to fetch transcript", "status_code": response.status_code}


current_function_index = 0
#transcript_functions.append(Youtube_Transcripts)
transcript_functions.append(Youtube_Transcript)
transcript_functions.append(Youtube_Transcripts_API)


def roundRobinTranscript(video_id):
    global current_function_index

    # Get the function to call based on the current index
    current_function = transcript_functions[current_function_index]

    # Call the selected function
    result = current_function(video_id)
    print(result)


    # Update the index for the next round-robin call
    current_function_index = (current_function_index + 1) % len(transcript_functions)

    return result



def get_video_summary(title, transcript):
    try:
        # Make the request to GPT-4 model for summarization
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""
                You are a helpful assistant. Summarize the following video transcript in two parts:
                1. A short descrption of the video
                2. Key points of the video in chronoligcal order

                Here is the transcript: {transcript}"""}
            ]
        )

        # Extract the summary from the response
        summary = completion.choices[0].message.content
        return summary

    except Exception as e:
        print(f"Error occurred while fetching the summary: {e}")
        return None  # Or return an appropriate error message or value


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
scheduler.add_job(func=ping_self, trigger="interval", minutes=14)
scheduler.start()

#Flask Api's
@app.route('/summarize', methods=['POST'])
def summarize():
    
    try:
        #Get URL
        data = request.get_json()
        url = data.get('url')
        print(f"\n\nReceived request for summarize:", url)

        #Get Video ID
        video_id = extract_video_id(url)


        #Get Title
        title = get_video_title(video_id)
        print(f"Title:", title)


        # Get Transcript
        transcript = roundRobinTranscript(video_id)
        if transcript:
            print("Receieved Transcript")
        else:
            raise ValueError("Transcript retrieval failed.")


        # Get Summary
        summary = get_video_summary(title, transcript)
        print("Returning Summary...")

        return jsonify({"title": title, "summary": summary})

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/testing', methods=['POST'])
def testing():
    time.sleep(5)
    return jsonify({"title": "how to run fast", "summary": "###The **video** discusses #the extensive history of Lockheed Martin, focusing on two major narratives: the Skunk Works and its innovative achievements, particularly in aerospace, and the influence of the military-industrial complex on American society and defense policies. It highlights how Lockheed Martin became a pivotal player in U.S. defense through pioneering aircraft like the SR-71 Blackbird and its contributions to technological advancements. The conversation emphasizes the dynamic between government contracts, the shifting perceptions of military spending, and the long-term implications of these developments on America's technological leadership and national security. The discussion addresses the challenges of adapting to new market needs and realities in a post-Cold War world while also critiquing the relationship between government interests and private contractors."})

@app.route('/version', methods=['GET'])
def version():
    return jsonify({
        "python_version": sys.version,
        "flask_version": pkg_resources.get_distribution("flask").version,  # Corrected to get flask version
        "openai_version": pkg_resources.get_distribution("openai").version,
        "beautifulsoup_version": pkg_resources.get_distribution("beautifulsoup4").version 
    })

# Flask route to handle the ping
@app.route("/ping")
def ping():
    print("Pong! Server is alive!")
    return "Pong! Server is alive!", 200

# Flask home route
@app.route("/")
def home():
    return "Flask app is running!"


if __name__ == '__main__':
    app.run(debug=True)
