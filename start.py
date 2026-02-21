import threading
import queue
import time
import os
import json
import obsws_python as obs
from youtube_downloader import download_youtube_video
from gdrive_downloader import download_gdrive_video

# Konfiguracija OBS-a
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "tvoja_lozinka"  # Promeni ovo ili ostavi prazno ako nema lozinke
OBS_SOURCE_NAME = "TV_Video_Source"  # Ime Media Source-a u OBS-u
PLAYLIST_FILE = "playlist.json"

class TVProgram:
    def __init__(self):
        self.queue = queue.Queue()
        self.is_running = True
        self.obs_client = None
        self.load_playlist()

    def load_playlist(self):
        if os.path.exists(PLAYLIST_FILE):
            try:
                with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self.queue.put(item)
                print(f"Učitan plan programa iz {PLAYLIST_FILE} ({len(data)} videa).")
            except Exception as e:
                print(f"Greška pri učitavanju plana: {e}")

    def save_item_to_file(self, item):
        # Jednostavno dodavanje u JSON fajl
        items = []
        if os.path.exists(PLAYLIST_FILE):
            try:
                with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    items = json.load(f)
            except:
                pass
        
        items.append(item)
        with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=4, ensure_ascii=False)

    def connect_obs(self):
        try:
            self.obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
            print("Povezan sa OBS-om (v5)!")
            return True
        except Exception as e:
            print(f"Greška pri povezivanju sa OBS-om: {e}")
            return False

    def play_in_obs(self, file_path):
        if not self.obs_client:
            if not self.connect_obs():
                return

        abs_path = os.path.abspath(file_path)
        
        try:
            # Podešavanje izvora na novi fajl (OBS v5 syntax)
            self.obs_client.set_input_settings(OBS_SOURCE_NAME, {'local_file': abs_path}, True)
            print(f"Pustam u OBS-u: {os.path.basename(abs_path)}")
            
            # Sačekaj malo da se učita pa proveri status
            time.sleep(2)
            self.wait_for_video_finish()
            
        except Exception as e:
            print(f"Greška prilikom kontrole OBS-a: {e}")

    def wait_for_video_finish(self):
        while self.is_running:
            try:
                # Provera statusa medija
                response = self.obs_client.get_media_input_status(OBS_SOURCE_NAME)
                # U OBS v5, ovo vraća objekat sa media_state
                # stanjima: OBS_MEDIA_STATE_PLAYING, OBS_MEDIA_STATE_ENDED, itd.
                if response.media_state == "OBS_MEDIA_STATE_ENDED":
                    print("Video završen.")
                    break
                time.sleep(1)
            except Exception as e:
                print(f"Greška pri proveri statusa: {e}")
                break

    def playback_thread(self):
        print("Playback nit pokrenuta.")
        while self.is_running:
            try:
                video_data = self.queue.get(timeout=1)
                name = video_data['name']
                link = video_data['link']
                
                print(f"\n[PROGRAM] Sledeći na redu: {name}")
                
                file_path = None
                if "youtube.com" in link or "youtu.be" in link:
                    file_path = download_youtube_video(link)
                elif "drive.google.com" in link or "docs.google.com" in link:
                    file_path = download_gdrive_video(link)
                else:
                    if os.path.exists(link):
                        file_path = link
                
                if file_path and os.path.exists(file_path):
                    self.play_in_obs(file_path)
                else:
                    print(f"Greška: Nije moguće preuzeti {name}")
                
                self.queue.task_done()
            except queue.Empty:
                continue

    def input_thread(self):
        print("Input nit pokrenuta. Kucajte 'exit' za kraj.")
        while self.is_running:
            try:
                print("\nDodaj novi video u plan:")
                name = input("Ime: ").strip()
                if not name: continue
                if name.lower() == 'exit':
                    self.is_running = False
                    break
                
                link = input("Link: ").strip()
                if not link: continue
                
                item = {'name': name, 'link': link}
                self.queue.put(item)
                self.save_item_to_file(item)
                print(f"Video '{name}' dodat u plan i zapisan u {PLAYLIST_FILE}.")
            except EOFError:
                break

    def run(self):
        t1 = threading.Thread(target=self.playback_thread, daemon=True)
        t2 = threading.Thread(target=self.input_thread)
        
        t1.start()
        t2.start()
        
        # Čekamo samo input nit (t2) jer je t1 daemon
        t2.join()
        print("Gasi se TV program...")

if __name__ == "__main__":
    if not os.path.exists('videos'):
        os.makedirs('videos')
        
    program = TVProgram()
    program.run()
