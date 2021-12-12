
# Url Shortner Generator Using Flask & Mysql

In this solution I have consider the basic application only. 
Solution mainly focus on system desing logic using cache.

functionalities considered as of now : 

1. Generate Short Url
2. Get long url from short url
3. get analytics for short url
4. search all longs urls based on query term
5. Cron job to manage the api hit count i.e. to dump counts from cache to database

Documentation can be found here : https://documenter.getpostman.com/view/13754685/UVR5poCe

To Run The App

```shell
pip install -r requirements.txt
python main.py
```

Visit [http://localhost:5000](http://localhost:5000)

Also update the database credentials in main.py file