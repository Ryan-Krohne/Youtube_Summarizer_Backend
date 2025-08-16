-  speed up transcript retrieval speed
-  more functions for transcript retrieval
- ui changes (in-progress)
- scrape transcripts of youtube if nothing else works for getting them
- llm can detect certain types of videos (tierlists, songs, 5 reasons why....) and give customized results for those
- add related/recommended videos, https://stackoverflow.com/questions/19725950/youtube-related-videos-using-youtube-v3-api

bugs:
llm not generating 3 faqs. generating 0 or 1 sometimes
sometimes videos will randomly fail
transcript doesn't exist and llm says that to user


- summarize videos after searching when inserting to db
- endpoint to force search and insert to database
- add more channels to file

- add audio for summaries, computer read it out loud
- translation for videos that aren't in english. users can switch between english and native language for summary