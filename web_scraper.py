import requests
from bs4 import BeautifulSoup

def scrape_episodes(url):
    """
    Učitava URL, traži <div class="lista_ep"> i izvlači linkove i tekst iz button-a.
    """
    print(f"\nPokušavam da učitam: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 1. Preuzimamo HTML sadržaj stranice
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 2. Parsiramo HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Tražimo glavni kontejner sa klasom "lista_ep"
        lista_ep_div = soup.find('div', class_='lista_ep')
        
        if not lista_ep_div:
            print("Greška: Nije pronađen element <div class='lista_ep'> na ovoj stranici.")
            return

        # 4. Tražimo sve linkove (<a> elemente) unutar tog diva
        # Prema slici, button je unutar <a> taga
        links = lista_ep_div.find_all('a')
        
        print(f"Pronađeno elemenata: {len(links)}\n")
        print(f"{'TEKST (Button)':<40} | {'LINK (href)'}")
        print("-" * 85)

        for a_tag in links:
            href = a_tag.get('href', 'Nema linka')
            
            # Tražimo button unutar ovog taga
            button = a_tag.find('button')
            button_text = "Nema teksta"
            
            if button:
                # Tražimo span unutar button-a (za boju/stil)
                span = button.find('span')
                if span:
                    button_text = span.get_text(strip=True)
                else:
                    button_text = button.get_text(strip=True)
            
            print(f"{button_text[:40]:<40} | {href}")

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP greška: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Greška pri povezivan lax: {errc}")
    except Exception as e:
        print(f"Neočekivana greška: {e}")

if __name__ == "__main__":
    # Primer korišćenja
    target_url = input("Unesite URL stranice koju želite da skenirate: ").strip()
    
    if target_url:
        scrape_episodes(target_url)
    else:
        print("URL nije unet.")
