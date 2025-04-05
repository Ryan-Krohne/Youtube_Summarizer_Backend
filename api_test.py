import google.generativeai as genai
import os

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

#trying to get json response instead of normal so we can avoid regex
def gemini_summary(transcript, faqs):
    try:
        # Start the chat session and send the message to the model
        chat_session = model.start_chat()
        response = chat_session.send_message(f"""
        I will send you a transcript from a youtube video, and some questions about the video. I need you to do 3 things for me.
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

    except Exception as e:
        print(f"Error occurred while fetching the summary and FAQs: {e}")
        return None
   



txt="Hi, I&#39;m Gayle Laakmann McDowell, author of Cracking the Coding Interview. In this video I&#39;m going to cover trees. A tree is best\nthought of in this sort of picture. You have a root node at the very top and it\nhas child notes and each of those child nodes, they have child nodes themselves,\nand so on and so on. Very often when we&#39;re talking about trees we talk about binary trees. A binary tree means that each node has no more than\ntwo child nodes. That is that each node has a left node and a right node. Of\ncourse one or both of those could also be null. Very often when we&#39;re talking\nabout binary trees we actually want to talk about binary search trees. A binary\nsearch tree is a binary tree which fulfills a specific ordering property. So\non any subtree the left nodes are less than the root node which is less than\nall of the right nodes. This ordering property makes finding a node very very\nfast because we have a pretty good idea of where it would be. So suppose we&#39;re\nlooking for 17 in this tree We can say okay, is 17 bigger or smaller than the\nroot node? Well it&#39;s bigger than the root node so let&#39;s go to\nthe right. Now is it bigger or smaller than that next node there? Well it&#39;s smaller than that node so it must\nbe on the left of it. And so very very quickly we can start to zoom in on where\nthat node will be because at each operation we&#39;ve chopped off hopefully\nabout half of the nodes and we do that over and over again and very very\nquickly we find the node we&#39;re looking for. So it makes finds very very fast. But how do\nthose elements get in there in the first place? Well let&#39;s talk about how inserts work.\nInserts work much like finding an element works. We start with some element we want to insert like say, 19, and we say is it bigger or smaller than the route? Well its bigger so let&#39;s go to the right. Now is it bigger or smaller than that that next\nnode? It&#39;s smaller so let&#39;s go to the left. I would do this over and over again until we\nget to an empty spot or a null node and then we say ok that&#39;s where we should insert\nour new element. Now the one problem here is that if we get elements in a particular order, we could get really\nimbalanced. Suppose we have a new binary search tree and we just follow the\nproperties of insertion. So we insert one and then 2 to it&#39;s right and then 3 to it&#39;s\nright and 4 to it&#39;s right, we&#39;re going to get this data structure that looks\nless like a tree and more like a long list. And then inserts and fines will no\nlonger be so fast. There are some algorithms that can ensure that our tree\nstays balanced, that is that roughly the same number of nodes will be on the left\nside the subtree and on the right. These algorithms get pretty complicated so we&#39;re not gonna go into the details here, but it&#39;s worth knowing that they&#39;re\nbuilt into a lot of programming languages and in a lot of cases and\ninterview questions you&#39;ll just assume that you have a balanced tree. The last\noperation to talk about is traversing or walking through a tree. So there&#39;s three\ncommon ways we walk through a tree we can do an inorder traversal, a preorder traversal, or a postorder traversal. A preorder traversal means that you visit\nthe root first and then you visit its left nodes and it&#39;s right nodes. In an inorder traversal you visit the left nodes first then the current node and then you\ngo to the right nodes. In a postorder traversal, the root node comes up last so\nyou visit the left nodes and then the right nodes, then the current root node.\nTypically in binary search trees we want to do inorder traversals because\nthat actually allows the nodes to be printed in order. So for example on this\ntree here with just a 1, a 2, and a 3, the nodes in an in order traversal\nwill actually be printed out in the order one then two then three. So typically we&#39;ll see inorder traversals.\nNow that we&#39;ve covered the basic operations let&#39;s take a look at the code for binary\nsearch tree. To implement a binary search tree we&#39;ll need a class node that has\npointers to the left node and the right node and then some sort of data\npresumably, and I&#39;m going to give ourselves a constructor just to make our\nlives a little bit easier. Ok so the first method I&#39;m going to add\nis an insert method. And this is going to take in, I&#39;m gonna call ot value here. This\nis going to take in a node, take in a node value and look to the left and the\nright to see where we want to insert it. So first if value is less than or equal to\nthe actual data of our node then we should insert it on the left side. If\nthere is no left node yet then this becomes my new node. Otherwise then I\nasked my left to insert it and I push that down the recursion stack. And then\notherwise if value is bigger than data than myself then it should be inserted\non the right side and so if there is no right node put this as my right\nnode, otherwise ask my right to insert it. That&#39;s the basics of insert. Ok so\nlet&#39;s walk through this code on an example. So we have the simple tree and\nwe want to insert the value eight, so we call 10 dot insert of 8 and 8 is\nsmaller than 10, so we go to the left and we call it left dot insert of 8, so 5 dot insert\nof 8, 8 is bigger than 5 so we go and we don&#39;t have a right child and so we\nset 5&#39;s right child equal to 8. The next method I&#39;ll do is find. So find is\ngoing to operate recursively just like insert, in fact will be somewhat similar\nin a lot of ways. And it&#39;s going to want to return a boolean. And actually I&#39;m gonna call\nthis contains because we&#39;re not really finding the nodes as much as checking if\nthe tree contains it. Ok, so first of all, if I&#39;m there, return true, otherwise if\nvalue is smaller than data that it should be on the left side, if there is\nno left node then I know the answer is false. Otherwise if there is a left node\ngo ask my left node what the answer is. Ok now I do the same thing on the right.\nIf, actually I can just do an else,  if right is null or if there is no right node the\nanswer is false, otherwise go ask my right child and return its answer. Alright so that&#39;s the recursive\nimplementation of contains. So let&#39;s walk through this function and imagine we&#39;re\ntrying to find the value 8 that we just inserted. So we call 10 dot contains\nof 8, 8  is smaller than 10, so go to the left, and then we do 5 dot contains of\n8, 5 is smaller than 8, and so we go to the right, and then of course we see that\n8 in fact equals 8 and so we return true all the way up the stack. The final method that we&#39;ll implement is an inorder traversal. Specifically I&#39;m going to print all of the nodes in the tree. So\nI just call this print in order and this is actually very simple. First if my, if I have a\nleft child then I do my in order printing first of my left child. Then I\nprint my own data and then same thing on the right. If right is not null, then I do right dot\nprint in order. So remember that inorder traversals do the left child, myself, and\nthen my right child. That&#39;s exactly what the code here does. So that&#39;s how you do an inorder printing. So let&#39;s walk through what this code does. So we&#39;re going to first\ncall 10 dot print inorder. Ten&#39;s gonna say left dot print in order\nfirst, that&#39;s the very first thing that&#39;s gonna\nhappen. Then we&#39;re going to print the root and then it&#39;s going to say right dot\nprint in order so we&#39;re going to recurse down. And 5, so we get 5 dot print in\norder. Five is going to say, ok print, but we got nothing on the left to print, so print me\nnext and then call right dot print in order where 8 will get printed. And\nthen we&#39;re going to go back up to 10 and 10 is going to get printed, and then\nwe&#39;re going to go and go down to the right in that third step and print 15. So\nthat&#39;s how an in order traversal works. If we want to do a pre or post order\ntraversal we do a very very similar things just in a slightly different order, a\npre-order traversal means that the root gets printed first. So we&#39;d print the route,\nthen print the left subtree, then print the right. In a postorder traversal the\nroot gets printed last, so we&#39;d print the left, then print the right, and then we\nprint the root node. So it&#39;s a pretty natural translation of the algorithmic\nconcepts. A lot of times in interviews people get kind of intimidated by the\nidea of implementing a binary search tree. They just assume it&#39;s something really challenging. But if you understand the\nconcept pretty well you can just take that and just translate it fairly\ndirectly into the code, just be really careful about the null pointer checks.\nSo now that we&#39;ve gone through the basic operations why don&#39;t you try out these\nconcepts on a new problem. Good luck."


if __name__=="__main__":
    print("hi")












