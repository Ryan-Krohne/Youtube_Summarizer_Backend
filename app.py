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
import xml.etree.ElementTree as ET
import os
import google.generativeai as genai

app = Flask(__name__)
CORS(app)
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
client = OpenAI()

# List of functions for getting transcripts
transcript_functions = []

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8000,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash-8b",
  generation_config=generation_config,
)

def gemini_summary(transcript):
    print("\n\nTALKING TO GEMINI RIGHT NOW!!!!!!\n\n")
    try:
        # Start the chat session and send the message to the model
        chat_session = model.start_chat()
        
        response = chat_session.send_message(f"""
        Provide a detailed summary of the video transcript below.
        Format the response exactly as follows:

        **Description:**  
        This video provides an in-depth discussion on a specific topic, explaining key ideas and insights in a structured and engaging way. This will be roughly 4 detailed sentences.  

        **Key Points:**  

        - First Key Point: Briefly explain this key idea in 4-5 lines, offering detailed context and examples as needed.\n
        - Another Key Point: Provide a short, 4-5 line explanation of this concept, including relevant details.\n
        - Additional Key Point: Summarize another insight from the discussion in 4-5 lines, providing clear context.\n
        - More Key Points as Needed: Continue listing key points from the transcript, keeping each explanation around 4-5 lines.\n

        ### **Formatting Rules:**  
        - The words **"Description"** and **"Key Points"** must be bold and appear exactly as written.  
        - **Do not introduce extra labels or sections.** Only one "Key Points" section should exist.  
        - Each key point must follow this format:  
        `- [Short, bold subheading]: [Explanation in 4-5 lines]`  
        - Use a dash (`-`) to list key points. **Do not use numbers or asterisks.**  
        - Ensure the structure remains consistent across responses.  

        Here is the transcript: {transcript}
        """)

        summary = response.text

        # Extract the description and key points from the response using regular expressions
        description_match = re.search(r"\*\*Description:\*\*(.*?)\*\*Key Points:\*\*", summary, re.DOTALL)
        key_points_match = re.search(r"\*\*Key Points:\*\*(.*)", summary, re.DOTALL)

        description = description_match.group(1).strip() if description_match else ""
        key_points = key_points_match.group(1).strip() if key_points_match else ""

        # Print the extracted description and key points
        print("\nDescription:", description)
        print("\nKey Points:", key_points)

        return {
            "description": description,
            "key_points": key_points
        }

    except Exception as e:
        print(f"Error occurred while fetching the summary: {e}")
        return None



#Functions
def extract_video_id(url):
    patterns = [
        r'youtu\.be/([a-zA-Z0-9_-]+)',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]+)',
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'm\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

#https://rapidapi.com/ytjar/api/yt-api
def get_video_title(video_id):
    url = "https://yt-api.p.rapidapi.com/video/info"
    querystring = {"id": video_id}

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "yt-api.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        data = response.json()

        title = data.get("title")
        
        if title is None:
            raise ValueError("Title not found in the response data.")
        
        return title

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

    except ValueError as e:
        print(f"Error extracting title: {e}")
        return None


#https://rapidapi.com/ytjar/api/yt-api
def get_video_title_and_xmlUrl(video_id):
    url = "https://yt-api.p.rapidapi.com/video/info"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "yt-api.p.rapidapi.com"
    }
    params = {"id": video_id}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        title = data["title"]
        duration= data["lengthSeconds"]

        subtitles_data = data.get('subtitles', {}).get('subtitles', [])
        for subtitle in subtitles_data:
            if subtitle.get('languageName') == 'English' or subtitle.get('languageCode') == 'en':
                subs = subtitle.get('url')
                return [title, subs, duration]

        return [title, None, duration]
    except (requests.exceptions.RequestException, KeyError):
        return None

def get_transcript_from_xml_url(xml_url):
  try:
    response = requests.get(xml_url)

    if response.status_code == 200:
      root = ET.fromstring(response.text)

      text = ' '.join([elem.text for elem in root.iter() if elem.text])

      return {"transcript": text}
    else:
      return ""
  except (requests.exceptions.RequestException, ET.ParseError) as e:
    return {"error": f"Error processing XML: {str(e)}"}


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
        response = requests.get(rapid_api_url, headers=headers, params=params)
        response.raise_for_status()

        if response.status_code == 200:
            transcript = [item["text"] for item in response.json().get("content", [])]
            ans = " ".join(transcript)
            print("Received Transcript")
            return ans
        else:
            print("Error: Could not fetch transcript")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

#https://rapidapi.com/solid-api-solid-api-default/api/youtube-transcript3
def Youtube_Transcript(video_id):
    print("1")
    try:
        url = "https://youtube-transcript3.p.rapidapi.com/api/transcript"

        querystring = {"videoId": video_id}

        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "youtube-transcript3.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
    
        transcript = response.json().get("transcript", [])
        
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

        if len(transcript) > 2:
            transcript = transcript[1:-2]
        
        if len(transcript) > 0:
            transcript[-1] = transcript[-1][1:-1]

        return " ".join(transcript)
    else:
        return {"error": "Failed to fetch transcript", "status_code": response.status_code}

#https://rapidapi.com/michelemaccini/api/youtubetextconverter
def YouTubeTextConverter(video_id):
    print("3")
    url = "https://youtubetextconverter.p.rapidapi.com/YouTubeCaptions.asp"

    querystring = {"vapi": video_id}

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "youtubetextconverter.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    return (response.text)

current_transcript_index = 0
transcript_functions.append(Youtube_Transcripts)
transcript_functions.append(Youtube_Transcript)
transcript_functions.append(Youtube_Transcripts_API)
transcript_functions.append(YouTubeTextConverter)


def roundRobinTranscript(video_id):
    global current_transcript_index

    current_function = transcript_functions[current_transcript_index]

    current_transcript_index = (current_transcript_index + 1) % len(transcript_functions)

    result = current_function(video_id)
    #print(result)

    return result



def get_video_summary(transcript):
    print("\n\nTALKING TO GPT RIGHT NOW!!!!!!\n\n")
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""
                 Provide a detailed summary of the video transcript below. 
                 Format the response as follows:\n\n

                 **Description:**\n
                 [Provide a concise and engaging description of the video's main content here.]\n\n

                 **Key Points:**\n
                 **[Subheading for the key point]**\n  
                 [Explanation of the subheading or supporting details]\n  
                 [Additional explanation if needed]\n- 
                 **[Another subheading for a key point]**\n  
                 [Explanation of this subheading]\n  
                 [Supporting details]\n\nPlease ensure:\n- 
                 
                 The words 'Description' and 'Key Points' are bold.\n- 
                 Each key point has a general subheading followed by detailed explanations.\n- 
                 Do not use numbers to order the key points; use a dash instead.\n\n
                 Here is the transcript: {transcript}"""}
            ]
        )

        summary = completion.choices[0].message.content
        print(f"Summary:", summary)

        description_match = re.search(r"\*\*Description:\*\*(.*?)\*\*Key Points:\*\*", summary, re.DOTALL)
        key_points_match = re.search(r"\*\*Key Points:\*\*(.*)", summary, re.DOTALL)

        description = description_match.group(1).strip() if description_match else ""
        key_points = key_points_match.group(1).strip() if key_points_match else ""

        print("\nDescription:", description)
        print("\nKey Points:", key_points)

        return {
            "description": description,
            "key_points": key_points
        }

    except Exception as e:
        print(f"Error occurred while fetching the summary: {e}")
        return None 


def ping_self():
    try:
        response = requests.get(
            "https://renderbackend-xfh6.onrender.com/ping",
            headers={"User-Agent": "Flask-Ping-Bot"}
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

#-------------------------------------------------- Flask Api's --------------------------------------------------
@app.route('/summarize', methods=['POST'])
def summarize():
    
    try:
        #Get URL
        data = request.get_json()
        url = data.get('url')
        print(f"\n\nReceived request for summarize:", url)

        #Get Video ID
        video_id = extract_video_id(url)
        print(f"ID: "+video_id)

        #500 requests/day
        title, xml_url, duration = get_video_title_and_xmlUrl(video_id)
        print(f"Youtube Title:",title, "\nXML URL:", xml_url,"\nVideo Duration:", duration)

        if int(duration) > 2700:
            return jsonify({"error": "Video can't be greater than 45 minutes."}), 400
        
        transcript1=""

        if xml_url:
            print("There is an xml url.")
            transcript1=get_transcript_from_xml_url(xml_url)
            #print(f"TRANSCRIPT:",transcript1)

            if transcript1:
                print("DOING XML WAY")
                
                # Get Summary
                response = gemini_summary(transcript1)
                description = response["description"]
                key_points = response["key_points"]

                return jsonify({
                    "title": title,
                    "description": description,
                    "key_points": key_points
                })

        print("XML Failed")

        # Get Transcript
        transcript = roundRobinTranscript(video_id)
        if transcript:
            print("Receieved Transcript")
        else:
            raise ValueError("There are no transcripts available for this video. Try another one.")


        # Get Summary
        response = gemini_summary(transcript)
        description = response["description"]
        key_points = response["key_points"]

        return jsonify({
            "title": title,
            "description": description,
            "key_points": key_points
        })

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/testing', methods=['POST'])
def testing():
    time.sleep(1.5)
    
    # Mock data for description and summary
    description = (
        "This video shares five fundamental rules of content creation that the speaker has implemented to grow his personal brand to over 3 million followers and achieve over 100 million views monthly. It delves into strategic advice for building a personal brand through consistent content creation, highlighting the importance of authenticity, systems, and sharing personal experiences."
    )
    key_points = (
        "1. **Introduction:** Overview of Lockheed Martin's history and significance.\n"
        "2. **Skunk Works:** Discussion on groundbreaking aerospace innovations like the SR-71 Blackbird.\n"
        "3. **Military-Industrial Complex:** Examination of the relationship between government contracts and private contractors.\n"
        "4. **Post-Cold War Challenges:** Analysis of adapting to new market needs and realities.\n"
        "5. **Conclusion:** Reflection on Lockheed Martin's role in shaping U.S. defense and technological leadership."
    )
    
    # Return as JSON
    return jsonify({
        "title": "The History of Lockheed Martin",
        "description": description,
        "key_points": key_points
    })

@app.route('/version', methods=['GET'])
def version():
    return jsonify({
        "python_version": sys.version,
        "flask_version": pkg_resources.get_distribution("flask").version,
        "openai_version": pkg_resources.get_distribution("openai").version,
    })

# Flask route to handle the ping
@app.route("/ping")
def ping():
    return "Pong! Server is alive!", 200

# Flask home route
@app.route("/")
def home():
    return "Flask app is running!"


@app.route('/get-transcript', methods=['GET'])
def get_transcript():
# URL of the YouTube timed text (XML transcript)
    url = "https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&ei=qkqaZ62WFaCK6dsPpZi9yQ4&caps=asr&opi=112496729&xoaf=5&xosf=1&hl=en&ip=0.0.0.0&ipbits=0&expire=1738190106&sparams=ip%2Cipbits%2Cexpire%2Cv%2Cei%2Ccaps%2Copi%2Cxoaf&signature=52354CB8B8F6D35C265EC8FE44CFA9F047ADAFC5.B09A7BBCEB604A4075FFB22DA13B9C8F14406FFA&key=yt8&kind=asr&lang=en&fmt=srv1"

    # Fetch the XML data from the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Print the raw XML content directly to the terminal for debugging
        print("Raw XML Response:")
        print(response.text)  # This will print the raw XML response to the console

        # Parse the XML data
        try:
            root = ET.fromstring(response.text)
            
            # Check the root and first few elements to understand the structure
            print("Root Element:", root.tag)
            for child in root:
                print("Child Element:", child.tag, "with text:", child.text)
            
            # Extract and combine the text content
            text = ' '.join([elem.text for elem in root.iter() if elem.text])  # Iterate through all elements
            
            # Return the extracted text as a JSON response
            return jsonify({"transcript": text})
        except Exception as e:
            return jsonify({"error": f"Error parsing XML: {str(e)}"}), 500
    else:
        return jsonify({"error": f"Failed to retrieve the XML data. Status code: {response.status_code}"}), 500


@app.route('/gemini_test', methods=['GET'])
def gemini_test():
    transcript = '''saying when I get older I'm just gonna hop on trt it just seems like there's like this like idea that trt is essentially like it's kind of like the Natty way it's like it's like people don't associate it with anabolics they're just like oh yeah I'm getting older I'm gonna hop on trt why do you think people see it that way um yeah it's tough because a lot of the literature that has come out is addressing true hypogonadism so if somebody has for example primary hypogonadism is literally when your testies don't respond to the signaling hormones from your brain to the testes so it's literally not responsive enough to make an adequate amount of testosterone to function properly in that case that guy needs trt essentially because what else are you going to do those studies will get conflated often with you know those outcomes were good equals I should be on trt to optimize as well but then the spectrum of risk like I said there's a a reference range on uh blood tests that you'll see that goes from as low as 270 upwards of like 1,200 depending on the lab some of it is more narrow like in Canada we have I don't know it's like 300 to 900 or something absurd and then in the US some places will go up to 1100 it kind of depends but at the end of the day there's obviously a difference between 350 and a th000 in terms of how much andro enens are floating around in your blood so to say that I'm on trt at a th000 versus I'm on trt at 600 it's like you're technically on replacement based on a therapeutic reference range at both of those amounts but how much did you actually need to replace you know the the r and trt how much did you need to replace what you naturally produced typically a lot of guys that are you know not doing the actual clinical guided way of doing trt they are kind of picking what their replacement is which is fine you can do whatever you want and that's not to say that's a bad thing again it's just a spectrum of risk because you know was you could also argue maybe the amount you produce naturally wasn't satisfactory to begin with maybe it'd be better off with a higher amount so it's all dependent on where you land and then also what you actually need to fulfill functions in the body so you'll often see 200 milligrams a week as a standard cookie cutter dose now but that's I would argue in most cases like mini baby cycle territory essentially perpetually is the yeah and this is again some people actually need more than that to achieve therapeutic replacement or symptom relief I should say more specifically but that's few and far between and just because one guy needs that it doesn't mean you need it as well so it's all like the the dose is all individual dependent based on what you need and like your original question was you know people are thinking they need it or I should just be on it not it's not the case typically that people need that high of a dose and often times it is a little bit of a cop out for wanting to optimize to a like sports trt level is what people often call it but and that's not to say that that's bad or good you just need to be cognizant of the underlying risk under that because it is not the equivalent of a study using andrel that brings guys from pipo gadle to a 550 total like you at 1,200 on injectable testosterone and anate every week is not the same as a hypogonadal guy going from 200 to 500 on Andel like conflating the two is not Apples to Apples so as long as you're on top of your health metrics though and you're Highly Educated about what you're doing at a real level because a lot of guys are very very disconnected with what they're actually doing they think they're on trt but it's like you're you're on Mini enhancement territory let's just level with what it actually is and just be aware of that and that's fine no one's going to judge you hopefully but you just need to like proactively take care of it accordingly through your uh screening and make sure ou're not putting yourself i'''
    
    if transcript:
        summary = gemini_summary(transcript)
        return summary
    else:
        return "No transcript provided."


if __name__ == '__main__':
    app.run(debug=True)
