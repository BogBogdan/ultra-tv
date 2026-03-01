import obsws_python as obs
import os
import time
import sys

# OBS Configuration
OBS_HOST = "127.0.0.1"
OBS_PORT = 4455
OBS_PASSWORD = "voLUQDdoL4IbMZxv"  # Updated password

# Dual Scene Configuration
SCENE_A = "Scene_A"
SCENE_B = "Scene_B"
SOURCE_A = "VideoPlayer_A"
SOURCE_B = "VideoPlayer_B"

class DualVideoSwitcher:
    def __init__(self):
        try:
            self.cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
            print("Connected to OBS!")
        except Exception as e:
            print(f"Failed to connect to OBS: {e}")
            sys.exit(1)
        
        self.videos_dir = os.path.join(os.getcwd(), 'videos')
        self.playlist = [] # Niz sourceva (video fajlova) koji se ponaša kao queue
        
        self.current_scene = SCENE_A
        self.next_scene = SCENE_B
        self.current_source = SOURCE_A
        self.next_source = SOURCE_B

    def setup_obs(self):
        """Osigurava da scene i izvori postoje u OBS-u."""
        try:
            scenes = [s['sceneName'] for s in self.cl.get_scene_list().scenes]
            
            for scene_name, source_name in [(SCENE_A, SOURCE_A), (SCENE_B, SOURCE_B)]:
                if scene_name not in scenes:
                    print(f"Kreiram scenu: {scene_name}")
                    self.cl.create_scene(scene_name)
                
                inputs = self.cl.get_input_list().inputs
                if not any(i['inputName'] == source_name for i in inputs):
                    print(f"Kreiram izvor: {source_name} u sceni {scene_name}")
                    self.cl.create_input(
                        sceneName=scene_name,
                        inputName=source_name,
                        inputKind="ffmpeg_source",
                        inputSettings={'local_file': ''},
                        sceneItemEnabled=True
                    )
                
                # Podešavanje skaliranja i zvuka
                try:
                    self.cl.set_input_volume(source_name, 1.0)
                    self.cl.set_input_audio_monitor_type(source_name, 'OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT')
                    
                    item_id = self.cl.get_scene_item_id(scene_name, source_name).scene_item_id
                    video_settings = self.cl.get_video_settings()
                    self.cl.set_scene_item_transform(scene_name, item_id, {
                        'boundsType': 'OBS_BOUNDS_SCALE_INNER',
                        'boundsWidth': video_settings.base_width,
                        'boundsHeight': video_settings.base_height,
                        'positionX': 0,
                        'positionY': 0,
                        'alignment': 5
                    })
                except Exception as e:
                    print(f"Napomena prilikom podešavanja {source_name}: {e}")
        except Exception as e:
            print(f"Greška prilikom inicijalizacije OBS-a: {e}")

    def add_to_playlist(self, video_name):
        """Funkcija koja ubacuje video u niz (plejlistu)."""
        video_path = os.path.join(self.videos_dir, video_name)
        if os.path.exists(video_path):
            self.playlist.append(video_name)
            print(f"Dodat video u plejlistu: {video_name}")
        else:
            print(f"Greška: Video {video_name} ne postoji u folderu {self.videos_dir}")

    def preload_next(self):
        """Učitava sledeći video iz plejliste u pozadinsku scenu."""
        if len(self.playlist) < 2:
            # Nema sledećeg videa za učitavanje
            return
            
        video_name = self.playlist[1] # Sledeći je uvek na indeksu 1 (pomeramo ga posle)
        video_path = os.path.abspath(os.path.join(self.videos_dir, video_name))
        
        print(f"Pripremam sledeći video: {video_name} u {self.next_source}")
        try:
            self.cl.set_input_settings(self.next_source, {
                'local_file': video_path,
                'restart_on_activate': True,
                'close_when_inactive': True
            }, True)
        except Exception as e:
            print(f"Greška pri pripremanju videa {video_name}: {e}")

    def play_initial(self):
        """Pušta prvi video iz plejliste."""
        if not self.playlist:
            return
            
        video_name = self.playlist[0]
        video_path = os.path.abspath(os.path.join(self.videos_dir, video_name))
        print(f"Puštam prvi video: {video_name} u {self.current_scene}")
        
        try:
            self.cl.set_input_settings(self.current_source, {
                'local_file': video_path,
                'restart_on_activate': True,
                'close_when_inactive': True
            }, True)
            self.cl.set_current_program_scene(self.current_scene)
        except Exception as e:
            print(f"Greška pri puštanju prvog videa: {e}")

    def is_video_finished(self):
        """Proverava da li je video pri kraju ili završen."""
        if not self.playlist:
            return False
            
        try:
            status = self.cl.get_media_input_status(self.current_source)
            # Prag za prebacivanje (500ms pre kraja)
            threshold = 500 
            
            if status.media_state == "OBS_MEDIA_STATE_ENDED":
                return True
            
            if status.media_duration > 0:
                remaining = status.media_duration - status.media_cursor
                if 0 < remaining < threshold:
                    print(f"Prebacujem scenu (ostalo je još {remaining}ms)...")
                    return True
        except Exception:
            pass
        return False

    def switch_scenes_and_pop(self):
        """Prebacuje scenu i izbacuje završeni video iz plejliste."""
        if not self.playlist:
            return

        finished_video = self.playlist.pop(0)
        print(f"Video završen i izbačen: {finished_video}")

        if not self.playlist:
            print("Plejlista je sada prazna.")
            return

        print(f"Smena scena: {self.current_scene} -> {self.next_scene}")
        
        # Zamenimo uloge trenutne i sledeće scene/izvora
        self.current_scene, self.next_scene = self.next_scene, self.current_scene
        self.current_source, self.next_source = self.next_source, self.current_source
        
        # Izvršimo promenu u OBS-u
        try:
            self.cl.set_current_program_scene(self.current_scene)
        except Exception as e:
            print(f"Greška prilikom promene scene u OBS-u: {e}")

    def run(self):
        self.setup_obs()
        
        # Ubacivanje inicijalnih videa
        self.add_to_playlist("video1.mp4")
        self.add_to_playlist("video2.mp4")
        # Možeš dodati još videa ovde:
        # self.add_to_playlist("video3.mp4")

        if not self.playlist:
            print("Plejlista je prazna.")
            return

        # Početak emitovanja
        self.play_initial()
        time.sleep(1.5)
        self.preload_next()

        print("Program radi. Naizmenično menjam Scene_A i Scene_B uz uklanjanje iz plejliste.")
        try:
            while True:
                if self.is_video_finished():
                    self.switch_scenes_and_pop()
                    self.preload_next()
                    time.sleep(2) 
                
                # Ako se plejlista isprazni, program može da čeka ili da se ugasi
                if not self.playlist:
                    print("Svi videi su pušteni. Čekam nove ili ugasi program (Ctrl+C).")
                    while not self.playlist:
                        time.sleep(5)
                    # Ako su dodati novi, nastavljamo
                    self.play_initial()
                    time.sleep(1.5)
                    self.preload_next()

                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Gašenje programa...")

if __name__ == "__main__":
    switcher = DualVideoSwitcher()
    switcher.run()
