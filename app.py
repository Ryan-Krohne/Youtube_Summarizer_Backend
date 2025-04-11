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
  model_name="gemini-2.0-flash-lite",
  generation_config=generation_config,
)

def gemini_summary(transcript, faqs):
    try:
        answers_dict = {}
        # Start the chat session and send the message to the model
        chat_session = model.start_chat()
        response = chat_session.send_message(f"""
        I will send you a transcript from a youtube video, aswell as questions and I need you to do 3 things for me:
        - Give me a description of the transcript
        - Give me key points from the transcript
        - Answer some questions that users want to know
                                             
        Format the response exactly as follows:

        **Description:**
        This video provides an in-depth discussion on a specific topic, explaining key ideas and insights in a structured and engaging way. This will be roughly 4 detailed sentences.

        **Key Points:**

        - First Key Point: Briefly explain this key idea in 4-5 lines, offering detailed context and examples as needed.\n
        - Another Key Point: Provide a short, 4-5 line explanation of this concept, including relevant details.\n
        - Additional Key Point: Summarize another insight from the discussion in 4-5 lines, providing clear context.\n
        - More Key Points as Needed: Continue listing key points from the transcript, keeping each explanation around 4-5 lines.\n

        **Answer Section:**
        ANSWER1: Answer for Question 1
        ANSWER2: Answer for Question 2
        ANSWER3: Answer for Question 3

        ### **Formatting Rules:**
        - The words **"Description"**, **"Key Points"** and **"Answer Section:"** must be bold and appear exactly as written. The phrase "Key Points" should not have any text before or after them.
        - **Do not introduce extra labels or sections other than what is above.
        - Each key point must follow this format:
        `- [Short, bold subheading]: [Explanation in 4-5 lines]`
        - Use a dash (`-`) to list key points. **Do not use numbers or asterisks.**
        - Ensure the structure remains consistent across responses.
        You will be given 3 questions after the transcript. Provide a concise answer to the questions given based *only* on the provided transcript. 
        Only include the answer in the response. Separated each answer by the delimiter '---ANSWER_SEPARATOR---'.**
        If you're not sure about a question, do your best to provide a response for the user.

        Here are the questions, and the transcript will be below: {', '.join(faqs.values())}
        Here is the transcript: {transcript}
        """)

        summary_with_faqs = response.text
        print(summary_with_faqs, "\n\n\n\n\n\n")

        # Extract the description and key points from the response using regular expressions
        description_match = re.search(r"\*\*Description:\*\*(.*?)\*\*Key Points:\*\*", summary_with_faqs, re.DOTALL)
        key_points_match = re.search(r"\*\*Key Points:\*\*(.*?)(?=\n\n\*\*Answer Section:\*\*|$)", summary_with_faqs, re.DOTALL)
        answer_pattern = r"ANSWER\d+:\s(.*?)(?:\s---ANSWER_SEPARATOR---|$)"

        description = description_match.group(1).strip() if description_match else ""
        key_points = key_points_match.group(1).strip() if key_points_match else ""
        matches = re.findall(answer_pattern, summary_with_faqs, re.DOTALL)

        for i, answer in enumerate(matches):
            answers_dict[faqs[f"q{i+1}"]] = answer.strip()


        # Print the extracted information
        print("\nDescription:", description)
        print("\nKey Points:", key_points)
        print("\nFAQ Answers:", answers_dict)

        return {
            "description": description,
            "key_points": key_points,
            "faqs": answers_dict
        }

    except Exception as e:
        print(f"Error occurred while fetching the summary and FAQs: {e}")
        return None
    

def generate_faqs(title):
    try:
        # Start the chat session and send the message to the model
        chat_session = model.start_chat()

        response = chat_session.send_message(f"""
        Given the YouTube video title below, identify the top 3 most likely questions a user would have about the video's content *before* watching it. Focus on questions that would help them understand the video's main topic, scope, and key takeaways.

        Return the three questions, with each question on a new line and preceded by the delimiter '---QUESTION---'. Do not include any other introductory or concluding text.

        Here is the Title: {title}
        """)

        faqs_string = response.text.strip()
        faqs_list = [q.replace('---QUESTION---', '').strip() for q in faqs_string.split('\n') if '---QUESTION---' in q]

        faq_dict = {
            "q1": faqs_list[0],
            "q2": faqs_list[1],
            "q3": faqs_list[2]
        }

        return faq_dict

    except Exception as e:
        print(f"Error occurred while fetching the faqs: {e}")
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
    max_attempts = len(transcript_functions)

    for attempt in range(max_attempts):
        current_function = transcript_functions[current_transcript_index]

        current_transcript_index = (current_transcript_index + 1) % len(transcript_functions)

        try:
            transcript = current_function(video_id)
            if transcript:
                return transcript
        except Exception as e:
            print(f"Error occurred while trying {current_function.__name__}: {e}")

    print("Failed to retrieve transcript using all available methods.")
    return None  # Or raise an exception here if you prefer




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

        #500 requests/day
        title, xml_url, duration = get_video_title_and_xmlUrl(video_id)
        print(f"Youtube Title: {title}, Video Duration: {duration}")

        faq_dict=generate_faqs(title)
        print(f"FAQS:\n{faq_dict}")

        if int(duration) > 2700:
            return jsonify({"error": "Video can't be greater than 45 minutes."}), 400
        
        transcript=""

        if xml_url:
            print(f"There is an XML URL: {xml_url}\n")
            transcript=get_transcript_from_xml_url(xml_url)
            if transcript:
                print("XML Succeeded")
            else:
                print("XML FAILED")
        else:
            print("There is NO XML URL")

        if not transcript:
            transcript = roundRobinTranscript(video_id)
            
        
        if transcript:
            print("Received Transcript")
        else:
            raise ValueError("There are no transcripts available for this video. Try another one.")

        print(transcript)

        # Get Summary
        response = gemini_summary(transcript, faq_dict)
        description = response["description"]
        key_points = response["key_points"]
        faqs = response["faqs"]

        return jsonify({
            "title": title,
            "description": description,
            "key_points": key_points,
            "faqs": faqs
        })

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/testing', methods=['POST'])
def testing():
    
    # Mock data for description and summary
    description = (
        "This video provides a clear and concise explanation of tree data structures, focusing specifically on binary search trees. It introduces the concept of trees with a root node and child nodes, emphasizing binary trees where each node has at most two children. The video then delves into the ordering properties of binary search trees, insert and find operations, and the importance of balanced trees to maintain efficiency. The video concludes by explaining tree traversal methods and the code implementation of the insert, find, and print inorder methods, along with an example walkthrough of the methods."
    )
    key_points = ("""
        -   **What are Trees?:** A tree is a data structure where a root node has child nodes that can also have child nodes, creating a hierarchical structure. Binary trees are a specific type where each node has a maximum of two children (left and right nodes). Binary search trees are a type of binary tree with an ordering property where left nodes are smaller than the root, and right nodes are larger.\n\n-   **Insertion and Finding:** Inserting a node into a binary search tree involves comparing the new value with the existing nodes, moving left or right based on the comparison, and inserting the new node in an empty spot. Finding a node is similar; it involves comparing the target value with the current node, moving left or right to narrow down the search, making it very fast.\n\n-   **Tree Balancing:** When elements are inserted into a binary search tree in a particular order, the tree can become imbalanced, resembling a long list and reducing search efficiency. Algorithms ensure trees stay balanced, maintaining roughly the same number of nodes on the left and right sides of each node.\n\n-   **Tree Traversal Methods:** There are three common ways to traverse a tree: inorder, preorder, and postorder. Inorder traversal visits the left nodes, then the current node, and finally the right nodes. Preorder visits the current node first, then the left, then the right. Postorder visits the left, then the right, then the current node. Inorder traversals are often used in binary search trees to print nodes in order.\n\n-   **Implementation of insert, find and print inorder:** The video outlines how to implement a binary search tree using node classes with pointers to left and right children, and a data field. The insert method recursively inserts a new node based on its value compared to the current node. The find method uses recursion to check if a node with a given value exists and inorder traversal prints the node left child, itself, then right.
    """
    )
    title = ("Data Structures: Trees")

    faqs = {
        "How are trees used in computer science and what are some practical examples?": "The video explains that inorder traversals are typically used in binary search trees because they allow the nodes to be printed in order. Practical examples of tree use cases are not provided, but the video notes the implementation of insert, find, and print inorder methods.",
        "What are data structures, specifically trees, and why are they important?": "Data structures, specifically trees, organize data in a hierarchical structure with a root node and child nodes. Binary search trees, which are covered in the video, are an important type of tree due to their efficiency in searching, inserting, and deleting data, as long as the tree is balanced. They allow quick retrieval of information.",
        "What types of trees are covered in this video?": "The video focuses on binary trees and binary search trees, where each node has at most two children (left and right)."
    }
    # Return as JSON
    return jsonify({
        "title": title,
        "description": description,
        "key_points": key_points,
        "faqs" : faqs
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
        print(transcript)
        summary = gemini_summary(transcript, faqs={"Q1":"What's the weather like", "Q2":"What's the weather like", "Q3":"What's the weather like" })
        return summary
    else:
        return "No transcript provided."
    
@app.route('/faq', methods=['GET'])
def faq():
    print("Running FAQS")
    title = "iOS 17 Hands-On: Top 5 Features!"
    
    if title:
        print("testing function")
        faqs = generate_faqs(title)
        return faqs
    else:
        return "No transcript provided."

@app.route('/test', methods=['GET'])
def test_endpoint():
    """A simple test endpoint that returns a JSON message."""
    return jsonify({"message": "Hello from the test API!"})

if __name__ == '__main__':
    app.run(debug=True)
