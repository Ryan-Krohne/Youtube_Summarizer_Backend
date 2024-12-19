from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
CORS(app)

client = OpenAI()

@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "YouTube URL is required"}), 400

        video_id = url.replace('https://www.youtube.com/watch?v=', '')

        transcript = YouTubeTranscriptApi.get_transcript(video_id)
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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)