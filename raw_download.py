import pytube
import datetime

url = ""
yt = pytube.YouTube(url)

start_tiem = datetime.datetime.now()

stream = yt.streams.filter(progressive=True).order_by("resolution").desc().first()
stream.download(output_path="downloads", filename="video.mp4")
end_time = datetime.datetime.now()
print(f"Time taken: {end_time - start_tiem}")
