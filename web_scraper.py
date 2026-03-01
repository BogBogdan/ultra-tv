import requests
from bs4 import BeautifulSoup
import os

def scrape_episodes(url):
    """
    Učitava URL, traži <div class="lista_ep"> i izvlači linkove i tekst iz button-a.
    Rezultate čuva u folderu 'scripts'.
    """
    print(f"\nPokušavam da učitam: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 1. Preuzimamo HTML sadržaj
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 2. Parsiramo HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Tražimo glavni kontejner
        lista_ep_div = soup.find('div', class_='lista_ep')
        
        if not lista_ep_div:
            print("Greška: Nije pronađen element <div class='lista_ep'> na ovoj stranici.")
            return

        links = lista_ep_div.find_all('a')
        
        # --- PRIPREMA FOLDERA I FAJLA ---
        folder_name = "scripts"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            print(f"Kreiran folder: {folder_name}")

        file_path = os.path.join(folder_name, "izvucene_epizode.txt")
        # -------------------------------

        print(f"Pronađeno elemenata: {len(links)}\n")
        
        with open(file_path, "w", encoding="utf-8") as f:
            # Zaglavlje u fajlu
            f.write(f"Rezultati skeniranja za: {url}\n")
            f.write(f"{'TEKST (Button)':<40} | {'LINK (href)'}\n")
            f.write("-" * 85 + "\n")

            for a_tag in links:
                href = a_tag.get('href', 'Nema linka')
                button = a_tag.find('button')
                button_text = "Nema teksta"
                
                if button:
                    span = button.find('span')
                    button_text = span.get_text(strip=True) if span else button.get_text(strip=True)
                
                # Upisivanje u fajl
                line = f"{button_text[:40]:<40} | {href}"
                f.write(line + "\n")
                # Ispis u konzolu (opciono)
                print(line)

        print(f"\nUspisano! Fajl se nalazi na: {file_path}")

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP greška: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Greška pri povezivanju: {errc}")
    except Exception as e:
        print(f"Neočekivana greška: {e}")

if __name__ == "__main__":
    target_url = input("Unesite URL stranice: ").strip()
    if target_url:
        scrape_episodes(target_url)
    else:
        print("URL nije unet.")