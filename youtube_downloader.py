import yt_dlp
import os

def download_youtube_video(url, output_dir='videos'):
    """
    Downloads a video from YouTube using yt-dlp.
    
    Args:
        url (str): The YouTube video URL.
        output_dir (str): The local directory to save the video.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Preuzimanje YouTube videa: {url}")
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            print("Preuzimanje završeno!")
            return file_path
    except Exception as e:
        print(f"Greška prilikom preuzimanja sa YouTube-a: {e}")
        return None

if __name__ == "__main__":
    # Primer korišćenja
    video_url = input("Unesite YouTube URL: ")
    if video_url:
        download_youtube_video(video_url)
