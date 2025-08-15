-  speed up transcript retrieval speed
-  more functions for transcript retrieval
- ui changes (in-progress)
-  add video views/likes to db to improving trending_score 
- scrape transcripts of youtube if nothing else works for getting them
- llm can detect certain types of videos (tierlists, songs, 5 reasons why....) and give customized results for those
- add related/recommended videos, https://stackoverflow.com/questions/19725950/youtube-related-videos-using-youtube-v3-api

bugs:
llm not generating 3 faqs. generating 0 or 1 sometimes
sometimes videos will randomly fail
transcript doesn't exist and llm says that to user


another frontend todo
allow pasting of url to also search for video:
lets say you paste this "https://youtube-summarizer-lime.vercel.app/summary/GuSc2oKTeDc", it should just trim and search for video id


summarize videos after searching when inserting to db


- add more channels to file, 