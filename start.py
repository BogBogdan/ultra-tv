import threading
import time
import os
import re
import json
import obsws_python as obs
from youtube_downloader import download_youtube_video
from gdrive_downloader import download_gdrive_video

# Konfiguracija OBS-a
OBS_HOST = "127.0.0.1"
OBS_PORT = 4455
OBS_PASSWORD = "[PASSWORD]"  # Ažurirano prema tvom OBS-u
OBS_SOURCE_NAME = "TV_Video_Source"  # Ime Media Source-a u OBS-u
SCHEDULE_FILE = "schedule.txt"

class TVProgram:
    def __init__(self):
        self.is_running = True
        self.obs_client = None

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
            # Provera da li izvor postoji
            inputs = self.obs_client.get_input_list().inputs
            source_exists = any(i['inputName'] == OBS_SOURCE_NAME for i in inputs)

            if not source_exists:
                # Uzmi trenutnu scenu ako ne znamo gde da napravimo
                curr_scene = self.obs_client.get_current_program_scene().current_program_scene_name
                print(f"Izvor '{OBS_SOURCE_NAME}' ne postoji. Kreiram ga u sceni '{curr_scene}'...")
                self.obs_client.create_input(
                    sceneName=curr_scene,
                    inputName=OBS_SOURCE_NAME,
                    inputKind="ffmpeg_source",
                    inputSettings={'local_file': abs_path},
                    sceneItemEnabled=True
                )
            else:
                # Podešavanje izvora na novi fajl (OBS v5 syntax)
                self.obs_client.set_input_settings(OBS_SOURCE_NAME, {'local_file': abs_path}, True)
            
            # Podešavanje zvuka
            try:
                self.obs_client.set_input_volume(OBS_SOURCE_NAME, 1.0)
                self.obs_client.set_input_audio_monitor_type(OBS_SOURCE_NAME, 'OBS_MONITOR_TYPE_MONITOR_AND_OUTPUT')
            except:
                pass

            # Automatsko skaliranje na ceo ekran
            try:
                curr_scene = self.obs_client.get_current_program_scene().current_program_scene_name
                item_id = self.obs_client.get_scene_item_id(curr_scene, OBS_SOURCE_NAME).scene_item_id
                video_settings = self.obs_client.get_video_settings()
                
                self.obs_client.set_scene_item_transform(curr_scene, item_id, {
                    'boundsType': 'OBS_BOUNDS_SCALE_INNER',
                    'boundsWidth': video_settings.base_width,
                    'boundsHeight': video_settings.base_height,
                    'positionX': 0,
                    'positionY': 0,
                    'alignment': 5
                })
            except:
                pass

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
                if response.media_state == "OBS_MEDIA_STATE_ENDED":
                    print("Video završen.")
                    break
                time.sleep(1)
            except Exception as e:
                print(f"Greška pri proveri statusa: {e}")
                break

    def parse_schedule(self):
        """Čita schedule.txt i vraća listu stavki sa date i startTime."""
        items = []
        if not os.path.exists(SCHEDULE_FILE):
            return items
        
        # Regex za format "date","startTime","name","link","duration"
        pattern = re.compile(r'"([^"]*)","([^"]*)","([^"]*)","([^"]*)","([^"]*)"')
        
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    items.append({
                        "date": match.group(1),
                        "startTime": match.group(2),
                        "name": match.group(3),
                        "link": match.group(4),
                        "duration": match.group(5)
                    })
        return items

    def save_schedule(self, schedule):
        """Čuva listu nazad u fajl sa date i startTime."""
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            for item in schedule:
                f.write(f'"{item.get("date", "2026-02-23")}","{item.get("startTime", "00:00")}","{item["name"]}","{item["link"]}","{item["duration"]}"\n')

    def playback_thread(self):
        print("Playback nit pokrenuta (Multi-Day Scheduled Mode).")
        while self.is_running:
            schedule = self.parse_schedule()
            
            if not schedule:
                time.sleep(5)
                continue

            # Uzimamo prvu stavku (pretpostavljamo da su sortirane po vremenu)
            item = schedule[0]
            date_str = item.get('date', '2026-02-23')
            start_time_str = item.get('startTime', '00:00')
            name = item['name']
            
            # Provera trenutnog datuma i vremena
            now_date = time.strftime("%Y-%m-%d")
            now_time = time.strftime("%H:%M")
            
            # Ako je datum u budućnosti
            if now_date < date_str:
                if int(time.time()) % 60 == 0:
                    print(f"Čekam na '{name}' zakazan za {date_str} {start_time_str} (Danas je: {now_date})")
                time.sleep(1)
                continue
            
            # Ako je datum današnji, ali vreme je u budućnosti
            if now_date == date_str and now_time < start_time_str:
                if int(time.time()) % 30 == 0:
                    print(f"Čekam na '{name}' (Danas {start_time_str}, Trenutno: {now_time})")
                time.sleep(1)
                continue
            
            # Vreme je (ili je prošlo)
            link = item['link']
            duration = item['duration']
            
            print(f"\n[PROGRAM] Vreme je za: {name} (Zakazano: {date_str} {start_time_str})")
            
            # Provera za promenu scene
            if link.upper().startswith("SCENE:"):
                scene_name = link[6:].strip()
                if not self.obs_client:
                    self.connect_obs()
                if self.obs_client:
                    try:
                        self.obs_client.set_current_program_scene(scene_name)
                        print(f"Promenjena OBS scena na: {scene_name}")
                    except Exception as e:
                        print(f"Greška pri promeni scene: {e}")
                
                # Ukloni i nastavi
                self.save_schedule(schedule[1:])
                continue

            file_path = None
            if "youtube.com" in link or "youtu.be" in link:
                file_path = download_youtube_video(link)
            elif "drive.google.com" in link or "docs.google.com" in link:
                file_path = download_gdrive_video(link)
            else:
                if os.path.exists(os.path.join('videos', link)):
                    file_path = os.path.join('videos', link)
                elif os.path.exists(link):
                    file_path = link
            
            if file_path and os.path.exists(file_path):
                self.play_in_obs(file_path)
                # Ukloni iz fajla nakon puštanja
                self.save_schedule(self.parse_schedule()[1:])
            else:
                print(f"Greška: Nije moguće preuzeti ili pronaći {name}")
                self.save_schedule(schedule[1:])
            
            time.sleep(1)

    def run(self):
        t1 = threading.Thread(target=self.playback_thread, daemon=True)
        t1.start()
        
        print("TV Program radi. Koristite Web UI za upravljanje planom (schedule.txt).")
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.is_running = False
            print("Gasi se TV program...")

if __name__ == "__main__":
    if not os.path.exists('videos'):
        os.makedirs('videos')
        
    program = TVProgram()
    program.run()
