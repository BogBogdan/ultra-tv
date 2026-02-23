import obsws_python as obs
import os
import sys

# Konfiguracija OBS-a (Mora se podudarati sa podešavanjima u OBS-u)
OBS_HOST = "127.0.0.1"
OBS_PORT = 4455
OBS_PASSWORD = "[PASSWORD]"  # Tvoja lozinka
OBS_SOURCE_NAME = "TV_Video_Source"  # Ime Media Source-a u OBS-u

def play_video_in_obs(video_filename, scene_name=None):
    """
    Postavlja video fajl iz 'videos' foldera u OBS Media Source i pušta ga.
    """
    # Apsolutna putanja do fajla
    video_path = os.path.join(os.getcwd(), 'videos', video_filename)
    
    if not os.path.exists(video_path):
        print(f"Greška: Fajl '{video_filename}' ne postoji u 'videos' folderu.")
        return

    abs_path = os.path.abspath(video_path)

    try:
        # Povezivanje sa OBS-om (v5)
        cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
        
        # Ako scena nije zadata, uzmi trenutnu
        if not scene_name:
            scene_name = cl.get_current_program_scene().current_program_scene_name

        # Provera da li izvor postoji
        inputs = cl.get_input_list().inputs
        source_exists = any(i['inputName'] == OBS_SOURCE_NAME for i in inputs)

        if not source_exists:
            print(f"Izvor '{OBS_SOURCE_NAME}' ne postoji. Kreiram ga u sceni '{scene_name}'...")
            cl.create_input(
                sceneName=scene_name,
                inputName=OBS_SOURCE_NAME,
                inputKind="ffmpeg_source",
                inputSettings={'local_file': abs_path},
                sceneItemEnabled=True
            )
        else:
            if scene_name:
                cl.set_current_program_scene(scene_name)
            cl.set_input_settings(OBS_SOURCE_NAME, {'local_file': abs_path}, True)

        # Audio podešavanja
        try:
            # Postavi jačinu zvuka na 100%
            cl.set_input_volume(OBS_SOURCE_NAME, 1.0)
            # Omogući monitoring tako da ti čuješ zvuk (Monitor and Output)
            cl.set_input_audio_monitor_type(OBS_SOURCE_NAME, 'OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT')
            print("Zvuk je pojačan i monitoring je uključen.")
        except Exception as e:
            print(f"Napomena: Nisam uspeo da podesim zvuk: {e}")

        # Skaliranje na ceo ekran
        try:
            # Uzmi ID elementa u sceni
            item_id = cl.get_scene_item_id(scene_name, OBS_SOURCE_NAME).scene_item_id
            # Uzmi dimenzije platna (canvas)
            video_settings = cl.get_video_settings()
            canvas_width = video_settings.base_width
            canvas_height = video_settings.base_height

            # Postavi transformaciju da popuni ekran
            cl.set_scene_item_transform(scene_name, item_id, {
                'boundsType': 'OBS_BOUNDS_SCALE_INNER', # Čuva proporcije (Fit to screen)
                'boundsWidth': canvas_width,
                'boundsHeight': canvas_height,
                'positionX': 0,
                'positionY': 0,
                'alignment': 5 # Centrirano
            })
            print(f"Video je skaliran na {canvas_width}x{canvas_height}.")
        except Exception as e:
            print(f"Napomena: Nisam uspeo da automatski skaliram video: {e}")

        print(f"Uspešno postavljen video: {video_filename}")
        print(f"Video se sada emituje u OBS-u (Izvor: {OBS_SOURCE_NAME}, Scena: {scene_name}).")
        
    except Exception as e:
        print(f"Greška prilikom povezivanja ili puštanja videa: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Uzima ime fajla iz argumenata komandne linije (npr. python switch_scene.py video1.mp4)
        video_file = sys.argv[1]
        
        # Provera da li ima i drugog argumenta za scenu
        scene = sys.argv[2] if len(sys.argv) > 2 else None
        
        play_video_in_obs(video_file, scene)
    else:
        # Interaktivni unos
        print("Dostupni videi u 'videos' folderu:")
        if os.path.exists('videos'):
            files = [f for f in os.listdir('videos') if os.path.isfile(os.path.join('videos', f))]
            for i, f in enumerate(files):
                print(f"{i+1}. {f}")
            
            choice = input("\nUnesite broj ili ime fajla koji želite da pustite: ").strip()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(files):
                    video_file = files[idx]
                else:
                    print("Nevalidan broj.")
                    sys.exit()
            else:
                video_file = choice
            
            scene = input("Ime scene (opciono, pritisni Enter za trenutnu): ").strip()
            scene = scene if scene else None
            
            if video_file:
                play_video_in_obs(video_file, scene)
        else:
            print("Folder 'videos' ne postoji.")
