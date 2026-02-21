import gdown
import os
import re

def download_gdrive_video(url, output_dir='videos'):
    """
    Downloads a video from Google Drive using gdown.
    
    Args:
        url (str): The Google Drive file URL.
        output_dir (str): The local directory to save the video.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Pokušaj ekstrakcije ID-ja fajla iz URL-a
    file_id = None
    resource_key = None
    
    # Ekstrakcija ID-ja
    id_match = re.search(r'(?:id=|/d/|/file/d/|/open\?id=)([a-zA-Z0-9_-]+)', url)
    if id_match:
        file_id = id_match.group(1)
    
    # Ekstrakcija resourcekey-a
    rk_match = re.search(r'resourcekey=([a-zA-Z0-9_-]+)', url)
    if rk_match:
        resource_key = rk_match.group(1)

    if not file_id:
        print("Greška: Nije moguće pronaći ID fajla u URL-u.")
        return

    # Konstruisanje direktnog download URL-a
    download_url = f'https://drive.google.com/uc?id={file_id}&export=download'
    if resource_key:
        download_url += f'&resourcekey={resource_key}'

    output_path = os.path.join(output_dir, f'gdrive_video_{file_id}.mp4')
    
    try:
        print(f"Preuzimanje Google Drive videa (ID: {file_id})...")
        # gdown.download najbolje radi sa direktnim uc?id linkom
        saved_path = gdown.download(download_url, output_path, quiet=False)
        print(f"Preuzimanje završeno! Fajl je sačuvan kao: {saved_path}")
        return saved_path
    except Exception as e:
        print(f"Greška prilikom preuzimanja sa Drive-a: {e}")
        return None

if __name__ == "__main__":
    # Primer korišćenja sa linkom korisnika
    example_url = "https://docs.google.com/file/d/0B2BJTpRXmbpra0JWUXlqbXpOUmc/preview?resourcekey=0-8VBUR4Q_wjD4xxJxBzE-Ug"
    
    print(f"Podrazumevani primer URL-a: {example_url}")
    video_url = input("Unesite Google Drive URL (ostavite prazno za primer): ")
    
    if not video_url:
        video_url = example_url
        
    download_gdrive_video(video_url)
