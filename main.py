import re
import os
from datetime import datetime
from pytube import YouTube, Stream
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="🎥",
    layout="centered",
    initial_sidebar_state="auto",
)


def download_directory() -> str:
    home = os.path.expanduser("~")
    download_path = os.path.join(home, "Downloads")
    return download_path


def add_new_row(
    percentage: float, time_passed: float, predicted_time_left: float
) -> None:
    new_row = {
        "percentage": percentage,
        "time_passed": time_passed,
        "predicted_time_left": predicted_time_left,
    }
    st.session_state["data"].loc[len(st.session_state["data"])] = new_row


def update_info(percentage: float, predicted_time_left: float) -> None:
    time_left_display.subheader(f"Time left: {predicted_time_left:.2f} seconds")
    percentage_display.subheader(f"Percentage: {percentage:.2f}%")
    progressbar.progress(int(percentage))


def update_charts() -> None:
    data = st.session_state["data"]
    percentage_time_plot.plotly_chart(
        px.line(
            data,
            x="time_passed",
            y="percentage",
            title="Percentage over time",
            labels={"percentage": "Percentage", "time_passed": "Time passed"},
        )
    )
    time_left_plot.plotly_chart(
        px.line(
            data,
            x="time_passed",
            y="predicted_time_left",
            title="Time left over time",
            labels={
                "predicted_time_left": "Time left",
                "time_passed": "Time passed",
            },
        )
    )


def progress_function(stream, chunk, bytes_remaining) -> None:
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    timestamp = datetime.now()
    time_passed = (timestamp - st.session_state["download_start"]).total_seconds()
    time_per_percent = time_passed / percentage
    predicted_time_left = (100 - percentage) * time_per_percent

    update_info(percentage, predicted_time_left)

    if st.session_state["show_plots"]:
        add_new_row(percentage, time_passed, predicted_time_left)
        update_charts()


def clean_title(yt_title: str) -> str:
    title = re.sub(r'[<>:"/\\|?* .,\(\)\[\]{}]', "_", yt_title)
    return title


def format_views(views: int) -> str:
    if views > 1_000_000:
        return f"{views/1_000_000:.2f}m"
    elif views > 1_000:
        return f"{views/1_000:.2f}k"
    else:
        return views


def download(url: str, stream: Stream) -> str:
    yt = YouTube(url)
    title = clean_title(yt.title)
    yt.register_on_progress_callback(progress_function)
    # This is where the video will be downloaded
    yt.streams.get_by_itag(stream.itag).download(
        output_path=download_directory(), filename=f"{title}.mp4"
    )
    return f"{download_directory()}/{title}.mp4"


@st.cache_resource
def get_yt_info(url: str) -> tuple[YouTube, list[Stream]] | tuple[None, None]:
    try:
        yt = YouTube(url)
        possible_streams = (
            yt.streams.filter(progressive=True).order_by("resolution").desc()
        )
    except Exception as e:
        return None, None
    return yt, possible_streams


def display_video_info(yt: YouTube) -> None:
    st.subheader("Video Information")
    with st.container(border=True):
        st.subheader(yt.title)
        st.image(yt.thumbnail_url, use_column_width=True)
        columns = st.columns(3)
        columns[0].container(border=True).metric("Author", yt.author)
        columns[1].container(border=True).metric("Views", format_views(yt.views))
        columns[2].container(border=True).metric(
            "Length", f"{round(yt.length/60,2)} min"
        )


# - - - - - UI - - - - -

# Input form
st.title("YouTube Downloader")

url = st.text_input(
    label="Enter YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
)

show_plots = st.checkbox("Show Plots", value=False, key="show_plots")

st.divider()

# If no URL is entered, stop the app
if not url:
    st.stop()

yt, possible_streams = get_yt_info(url)

# If no video is found, stop the app
if yt is None:
    st.error(f"Cannot find a video with this URL: {e}")
    st.stop()

# Show info about the video
display_video_info(yt)

# Give the user the option to select the quality
selected_stream = st.radio(
    label="Select Quality",
    options=[f"{s.resolution} {s.subtype}" for s in possible_streams],
)
# convert it back to use it in the download function
selected_stream = possible_streams.filter(
    res=selected_stream.split(" ")[0], subtype=selected_stream.split(" ")[1]
).first()

# Buttons to start and stop the download
col1, col2, col3 = st.columns([0.3, 0.3, 0.4])
if col2.button("Stop Downloading", use_container_width=True):
    st.write("Download stopped")
    st.stop()

# Start download button
if col1.button("Start Downloading", type="primary", use_container_width=True):
    # Information about the download
    progressbar = st.progress(0)
    percentage_display = st.empty()
    time_left_display = st.empty()

    # Plots
    if show_plots:
        st.session_state["data"] = pd.DataFrame(
            columns=["percentage", "time_passed", "predicted_time_left"]
        )
        percentage_time_plot = st.empty()
        time_left_plot = st.empty()

    st.session_state["download_start"] = datetime.now()

    # Download
    filename = download(url, selected_stream)

    # Calculate time passed
    time_passed = (datetime.now() - st.session_state["download_start"]).total_seconds()
    st.write(f"Download finished in {time_passed:.2f} seconds")

    # Error plot
    if show_plots:
        # Add rows to the dataframe to be able to plot the error
        data = st.session_state["data"]
        data["predicted_total_time"] = data["time_passed"] + data["predicted_time_left"]
        data["error"] = data["predicted_total_time"].apply(lambda x: x - time_passed)

        error_plot = px.line(
            data,
            x="time_passed",
            y="error",
            title="Time prediction error",
            labels={"error": "Error", "time_passed": "Time passed"},
        )
        st.plotly_chart(error_plot)

    # Download button
    if st.download_button(
        label="Download Videofile",
        data=open(filename, "rb").read(),
        file_name=filename,
    ):
        os.remove(filename)
