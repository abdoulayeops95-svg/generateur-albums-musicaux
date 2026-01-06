# Générateur algorithmique d'album musical avec IA
# Version avec analyse réelle des artistes via API Deezer

import random
import json
import csv
import urllib.request
import urllib.parse
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Set, Optional
from datetime import datetime
import os

# ==================================================
# GUI (Tkinter) – optionnel
# ==================================================

GUI_AVAILABLE = True
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ModuleNotFoundError:
    GUI_AVAILABLE = False

# ==================================================
# Genres / styles musicaux
# ==================================================

STYLES: Dict[str, Dict] = {
    "rap": {"tempo": (80, 110), "moods": ["brut", "introspectif", "réaliste"]},
    "trap": {"tempo": (120, 150), "moods": ["tendu", "minimal", "sombre"]},
    "drill": {"tempo": (130, 150), "moods": ["froid", "menaçant", "urbain"]},
    "boom bap": {"tempo": (85, 100), "moods": ["authentique", "old-school", "lyrical"]},
    "pop": {"tempo": (90, 120), "moods": ["émotionnel", "lumineux", "accessible"]},
    "r&b": {"tempo": (70, 100), "moods": ["sensuel", "intime", "doux"]},
    "electro": {"tempo": (115, 140), "moods": ["futuriste", "énergique", "hypnotique"]},
    "techno": {"tempo": (125, 145), "moods": ["industriel", "transe", "sombre"]},
    "house": {"tempo": (118, 130), "moods": ["groove", "festif", "solaire"]},
    "ambient": {"tempo": (50, 80), "moods": ["planant", "méditatif", "minimal"]},
    "lofi": {"tempo": (60, 90), "moods": ["nostalgique", "calme", "intimiste"]},
    "jazz": {"tempo": (90, 140), "moods": ["libre", "nocturne", "chaleureux"]},
    "neo-jazz": {"tempo": (95, 125), "moods": ["fluide", "moderne", "atmosphérique"]},
    "rock": {"tempo": (100, 140), "moods": ["rebelle", "organique", "brut"]},
    "indie": {"tempo": (95, 130), "moods": ["introspectif", "mélodique", "libre"]},
    "metal": {"tempo": (120, 180), "moods": ["violent", "épique", "sombre"]},
    "cinematic": {"tempo": (60, 100), "moods": ["épique", "immersif", "dramatique"]},
}

# Mapping des genres Deezer vers nos styles
DEEZER_GENRE_MAPPING = {
    "Rap/Hip Hop": "rap",
    "Hip Hop": "rap",
    "French Rap": "rap",
    "Trap": "trap",
    "Drill": "drill",
    "Pop": "pop",
    "R&B": "r&b",
    "Electro": "electro",
    "Dance": "house",
    "Electronic": "electro",
    "Techno": "techno",
    "House": "house",
    "Jazz": "jazz",
    "Rock": "rock",
    "Alternative": "indie",
    "Metal": "metal",
}

# Préréglages d'albums
PRESETS: Dict[str, Dict] = {
    "Introspectif": {
        "styles": ["lofi", "ambient", "neo-jazz"],
        "theme": "introspection",
        "description": "Album calme et contemplatif"
    },
    "Énergique": {
        "styles": ["trap", "electro", "techno"],
        "theme": "énergie",
        "description": "Album dynamique et puissant"
    },
    "Nocturne": {
        "styles": ["ambient", "jazz", "r&b"],
        "theme": "nuit",
        "description": "Ambiance de fin de soirée"
    },
    "Urbain": {
        "styles": ["rap", "drill", "trap"],
        "theme": "ville",
        "description": "Sonorités street"
    },
    "Expérimental": {
        "styles": ["techno", "ambient", "neo-jazz"],
        "theme": "exploration",
        "description": "Mélange audacieux"
    }
}

# ==================================================
# Modèles de données
# ==================================================

@dataclass
class ArtistProfile:
    name: str
    tempo_range: Tuple[int, int]
    mood: str
    keywords: List[str]
    themes: List[str]
    genres: List[str]
    language: str
    real_data: bool  # True si données viennent de l'API


@dataclass
class Track:
    title: str
    duration: int
    tempo: int
    mood: str
    theme: str
    link: str


@dataclass
class Album:
    title: str
    styles: List[str]
    artists: List[str]
    theme: str
    narration: str
    tracks: List[Track]
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==================================================
# Cache et persistance
# ==================================================

_deezer_cache: Dict[str, str] = {}
_artist_cache: Dict[str, Dict] = {}
_album_history: List[Album] = []

def load_cache():
    """Charge les caches depuis des fichiers"""
    global _deezer_cache, _artist_cache
    
    if os.path.exists("deezer_cache.json"):
        try:
            with open("deezer_cache.json", "r", encoding="utf-8") as f:
                _deezer_cache = json.load(f)
        except Exception:
            pass
    
    if os.path.exists("artist_cache.json"):
        try:
            with open("artist_cache.json", "r", encoding="utf-8") as f:
                _artist_cache = json.load(f)
        except Exception:
            pass

def save_cache():
    """Sauvegarde les caches"""
    try:
        with open("deezer_cache.json", "w", encoding="utf-8") as f:
            json.dump(_deezer_cache, f, ensure_ascii=False, indent=2)
        with open("artist_cache.json", "w", encoding="utf-8") as f:
            json.dump(_artist_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ==================================================
# API Deezer - Analyse complète des artistes
# ==================================================

def fetch_artist_data(artist_name: str) -> Optional[Dict]:
    """Récupère les données complètes d'un artiste depuis Deezer"""
    if artist_name in _artist_cache:
        return _artist_cache[artist_name]
    
    try:
        # Recherche de l'artiste
        query = urllib.parse.quote(artist_name)
        url = f"https://api.deezer.com/search/artist?q={query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'AlbumGenerator/2.0'})
        
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            
            if not data.get("data"):
                return None
            
            # Prendre le premier résultat (le plus pertinent)
            artist = data["data"][0]
            artist_id = artist["id"]
            
            # Récupérer les top tracks de l'artiste pour analyser son style
            tracks_url = f"https://api.deezer.com/artist/{artist_id}/top?limit=10"
            tracks_req = urllib.request.Request(tracks_url, headers={'User-Agent': 'AlbumGenerator/2.0'})
            
            with urllib.request.urlopen(tracks_req, timeout=5) as tr:
                tracks_data = json.loads(tr.read().decode())
                
                if not tracks_data.get("data"):
                    return None
                
                # Analyser les genres et caractéristiques
                genres = set()
                durations = []
                
                for track in tracks_data["data"]:
                    if track.get("duration"):
                        durations.append(track["duration"])
                    
                    # Récupérer l'album pour avoir le genre
                    if track.get("album", {}).get("id"):
                        try:
                            album_url = f"https://api.deezer.com/album/{track['album']['id']}"
                            album_req = urllib.request.Request(album_url, headers={'User-Agent': 'AlbumGenerator/2.0'})
                            with urllib.request.urlopen(album_req, timeout=3) as ar:
                                album_data = json.loads(ar.read().decode())
                                if album_data.get("genres", {}).get("data"):
                                    for genre in album_data["genres"]["data"]:
                                        genres.add(genre.get("name", ""))
                        except:
                            pass
                
                # Calculer la durée moyenne
                avg_duration = int(sum(durations) / len(durations)) if durations else 180
                
                artist_info = {
                    "name": artist.get("name", artist_name),
                    "genres": list(genres),
                    "avg_duration": avg_duration,
                    "link": artist.get("link", "https://www.deezer.com"),
                    "picture": artist.get("picture_medium", ""),
                    "nb_fan": artist.get("nb_fan", 0)
                }
                
                _artist_cache[artist_name] = artist_info
                save_cache()
                return artist_info
                
    except Exception as e:
        print(f"Erreur API pour {artist_name}: {e}")
        return None

def fetch_deezer_track(artist: str) -> str:
    """Recherche un lien vers un artiste sur Deezer (avec cache)"""
    if artist in _deezer_cache:
        return _deezer_cache[artist]
    
    artist_data = fetch_artist_data(artist)
    if artist_data:
        link = artist_data.get("link", "https://www.deezer.com")
        _deezer_cache[artist] = link
        save_cache()
        return link
    
    default_link = "https://www.deezer.com"
    _deezer_cache[artist] = default_link
    return default_link

# ==================================================
# Détection de langue améliorée
# ==================================================

def detect_language(artist_name: str, genres: List[str] = None) -> str:
    """Détecte la langue principale de l'artiste"""
    # Si on a des genres français explicites
    if genres:
        french_genres = ["French Rap", "Rap Français", "Chanson Française"]
        if any(fg in " ".join(genres) for fg in french_genres):
            return "fr"
    
    french_artists = [
        "pnl", "nekfeu", "orelsan", "stromae", "booba", "ninho", "soolking",
        "jul", "aya nakamura", "naps", "damso", "alpha wann", "freeze corleone",
        "dinos", "laylow", "lomepal", "eddy de pretto", "therapie taxi", "angele",
        "pomme", "videoclub", "benjamin biolay", "air", "phoenix", "kavinsky",
        "justice", "daft punk", "sebastien tellier", "m83", "yelle", "plk",
        "1pliké140", "1plike140", "koba lad", "kalash criminel", "kaaris",
        "rim'k", "gradur", "sch", "sofiane", "niska", "vald", "lacrim",
        "heuss l'enfoiré", "leto", "zola", "soso maness", "kekra",
        "hamza", "mhd", "gims", "black m", "dadju", "maître gims", "slimane"
    ]
    
    name_lower = artist_name.lower().strip()
    name_lower = name_lower.replace("é", "e").replace("è", "e").replace("ê", "e")
    
    return "fr" if any(a in name_lower for a in french_artists) else "en"

# ==================================================
# Interprétation artistique avec vraies données
# ==================================================

def interpret_artist(name: str) -> ArtistProfile:
    """Génère un profil artistique basé sur les vraies données API ou fallback"""
    
    # ÉTAPE 1: Tentative de récupération des données réelles
    artist_data = fetch_artist_data(name)
    
    if artist_data:
        # DONNÉES RÉELLES TROUVÉES
        print(f"✅ Données réelles trouvées pour {name}")
        
        genres = artist_data.get("genres", [])
        avg_duration = artist_data.get("avg_duration", 180)
        
        # Mapper les genres Deezer vers nos styles
        detected_styles = []
        for genre in genres:
            for deezer_genre, our_style in DEEZER_GENRE_MAPPING.items():
                if deezer_genre.lower() in genre.lower():
                    detected_styles.append(our_style)
        
        # Si on n'a pas trouvé de style, fallback
        if not detected_styles:
            detected_styles = ["rap"]  # Défaut
        
        # Récupérer les caractéristiques du premier style détecté
        main_style = detected_styles[0]
        style_info = STYLES.get(main_style, STYLES["rap"])
        
        # Calculer un tempo basé sur le style et la durée
        tempo_range = style_info["tempo"]
        # Ajuster légèrement selon la durée moyenne
        if avg_duration < 150:  # Tracks courtes = tempo plus rapide
            tempo_low = tempo_range[0] + 10
            tempo_high = tempo_range[1] + 10
        else:
            tempo_low = tempo_range[0]
            tempo_high = tempo_range[1]
        
        language = detect_language(name, genres)
        
        # Mots-clés adaptés
        keywords_fr = [
            "Nuit", "Ombre", "Lueur", "Silence", "Âme", "Vertige",
            "Brume", "Écho", "Aube", "Ciel", "Larme", "Souffle"
        ]
        keywords_en = [
            "Shadow", "Light", "Echo", "Dream", "Night", "Fire",
            "Silence", "Road", "Sky", "Time", "Soul", "Wind"
        ]
        
        themes_fr = [
            "solitude", "mélancolie", "révolte", "liberté", "errance",
            "nostalgie", "espoir", "quête", "transformation"
        ]
        themes_en = [
            "loneliness", "freedom", "rebellion", "hope", "melancholy",
            "search", "truth", "transformation", "wandering"
        ]
        
        keywords = keywords_fr if language == "fr" else keywords_en
        themes = themes_fr if language == "fr" else themes_en
        
        random.shuffle(keywords)
        random.shuffle(themes)
        
        return ArtistProfile(
            name=name,
            tempo_range=(tempo_low, tempo_high),
            mood=random.choice(style_info["moods"]),
            keywords=keywords[:5],
            themes=themes[:7],
            genres=detected_styles,
            language=language,
            real_data=True
        )
    
    else:
        # FALLBACK: Génération aléatoire
        print(f"⚠️  Fallback pour {name} (artiste non trouvé)")
        
        language = detect_language(name)
        
        keywords_fr = [
            "Nuit", "Ombre", "Lueur", "Silence", "Âme", "Vertige",
            "Brume", "Écho", "Aube", "Ciel", "Larme", "Souffle"
        ]
        keywords_en = [
            "Shadow", "Light", "Echo", "Dream", "Night", "Fire",
            "Silence", "Road", "Sky", "Time", "Soul", "Wind"
        ]
        
        themes_fr = [
            "solitude", "mélancolie", "révolte", "liberté", "errance",
            "nostalgie", "espoir", "quête", "transformation"
        ]
        themes_en = [
            "loneliness", "freedom", "rebellion", "hope", "melancholy",
            "search", "truth", "transformation", "wandering"
        ]
        
        all_moods = sum((v["moods"] for v in STYLES.values()), [])
        
        keywords = keywords_fr if language == "fr" else keywords_en
        themes = themes_fr if language == "fr" else themes_en
        
        random.shuffle(keywords)
        random.shuffle(themes)
        
        low = random.randint(60, 100)
        high = random.randint(max(low + 10, 90), 160)
        
        return ArtistProfile(
            name=name,
            tempo_range=(low, high),
            mood=random.choice(all_moods),
            keywords=keywords[:5],
            themes=themes[:7],
            genres=["rap"],  # Genre par défaut
            language=language,
            real_data=False
        )

# ==================================================
# Génération de titres
# ==================================================

def generate_title(words: List[str], theme: str, language: str = "en") -> str:
    """Génère un titre de track cohérent selon la langue"""
    if len(words) < 2:
        words = (words * 2) if words else (["Écho", "Son", "Rêve"] if language == "fr" else ["Echo", "Sound", "Dream"])
    
    if len(words) >= 2:
        a, b = random.sample(words, 2)
    else:
        a = words[0]
        b = theme
    
    if language == "fr":
        patterns = [
            f"{a} {theme}",
            f"{a} // {b}",
            f"{theme.capitalize()} de {a.lower()}",
            f"{a} dans la {theme}",
            f"{a} et {b}",
            f"Le {a.lower()} {theme}",
            f"{a} sans {b.lower()}",
            f"{theme.capitalize()} : {a}",
        ]
    else:
        patterns = [
            f"{a} {theme}",
            f"{a} // {b}",
            f"{theme.capitalize()} of {a}",
            f"{a} in the {theme}",
            f"{a} & {b}",
            f"The {a} {theme}",
            f"{a} without {b}",
            f"{theme.capitalize()}: {a}",
        ]
    
    return random.choice(patterns)

# ==================================================
# Validation des inputs
# ==================================================

def validate_inputs(styles: List[str], artists: List[str], n_tracks: int) -> Tuple[bool, str]:
    """Valide les entrées utilisateur"""
    if not styles:
        return False, "Sélectionnez au moins un genre musical"
    if not artists:
        return False, "Ajoutez au moins un artiste"
    if len(artists) > 15:
        return False, "Maximum 15 artistes"
    if n_tracks < 3:
        return False, "Minimum 3 tracks"
    if n_tracks > 30:
        return False, "Maximum 30 tracks"
    return True, ""

# ==================================================
# Génération d'album avec analyse réelle
# ==================================================

def generate_album(styles: List[str], artists: List[str], n_tracks: int, album_theme: str) -> Optional[Album]:
    """Génère un album complet avec analyse des vrais artistes"""
    valid, error = validate_inputs(styles, artists, n_tracks)
    if not valid:
        raise ValueError(error)
    
    print("\n🎵 Analyse des artistes en cours...")
    profiles = [interpret_artist(a) for a in artists]
    
    # Afficher un résumé
    real_data_count = sum(1 for p in profiles if p.real_data)
    print(f"✅ {real_data_count}/{len(profiles)} artistes analysés via API")
    
    used_themes: Set[str] = set()
    
    # Détecter la langue dominante
    lang_count = {"fr": 0, "en": 0}
    for profile in profiles:
        lang_count[profile.language] += 1
    album_language = "fr" if lang_count["fr"] > lang_count["en"] else "en"

    narration = (
        f"Album narratif explorant le thème '{album_theme}', "
        "à travers des esthétiques musicales et émotionnelles variées."
    )

    tracks: List[Track] = []

    for _ in range(n_tracks):
        artist = random.choice(profiles)
        track_language = artist.language

        available = [t for t in artist.themes if t not in used_themes]
        if not available:
            used_themes.clear()
            available = artist.themes
        theme = random.choice(available)
        used_themes.add(theme)

        style_moods = sum((STYLES[s]["moods"] for s in styles if s in STYLES), [])
        title = generate_title(artist.keywords + style_moods, theme, track_language)

        tracks.append(
            Track(
                title=title,
                duration=random.randint(150, 300),
                tempo=random.randint(*artist.tempo_range),
                mood=artist.mood,
                theme=theme,
                link=fetch_deezer_track(artist.name),
            )
        )

    album_title_words = ["Écho", "Cycle", "Vision", "Nuit", "Odyssée"] if album_language == "fr" else ["Echo", "Cycle", "Vision", "Night", "Odyssey"]
    album_title = generate_title(album_title_words, album_theme, album_language)

    album = Album(album_title, styles, artists, album_theme, narration, tracks)
    _album_history.append(album)
    
    return album

# ==================================================
# Export de données
# ==================================================

def export_album_json(album: Album, filename: str):
    """Exporte l'album en JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        data = asdict(album)
        json.dump(data, f, ensure_ascii=False, indent=2)

def export_album_csv(album: Album, filename: str):
    """Exporte l'album en CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['#', 'Titre', 'Durée (s)', 'Tempo (BPM)', 'Mood', 'Thème', 'Lien'])
        for i, track in enumerate(album.tracks, 1):
            writer.writerow([
                i, track.title, track.duration, track.tempo, 
                track.mood, track.theme, track.link
            ])

def export_album_txt(album: Album, filename: str):
    """Exporte l'album en texte formaté"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"🎼 {album.title}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"🎭 Thème : {album.theme}\n")
        f.write(f"🎵 Styles : {', '.join(album.styles)}\n")
        f.write(f"👥 Artistes : {', '.join(album.artists)}\n")
        f.write(f"📅 Créé le : {album.created_at}\n\n")
        f.write(f"📖 {album.narration}\n\n")
        f.write(f"TRACKLIST\n")
        f.write(f"{'-'*60}\n\n")
        
        for i, t in enumerate(album.tracks, 1):
            mins = t.duration // 60
            secs = t.duration % 60
            f.write(f"{i:2d}. {t.title}\n")
            f.write(f"    ⏱️  {mins}:{secs:02d}  |  🎚️  {t.tempo} BPM  |  💭 {t.mood}\n")
            f.write(f"    🎯 Thème : {t.theme}\n")
            f.write(f"    🔗 {t.link}\n\n")

# ==================================================
# Interface graphique améliorée
# ==================================================

if GUI_AVAILABLE:
    root = tk.Tk()
    root.title("🎧 Album Generator AI - Version Pro (API Analysis)")
    root.geometry("1000x750")

    BG = "#0b0f14"
    CARD = "#151a21"
    FG = "#e6edf3"
    ACCENT = "#10a37f"
    ACCENT2 = "#2ea89f"

    root.configure(bg=BG)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=CARD, foreground=FG, font=("Segoe UI", 10))
    style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 20, "bold"))
    style.configure("TButton", background=ACCENT, foreground="#ffffff", padding=8, font=("Segoe UI", 9))
    style.configure("Secondary.TButton", background=ACCENT2, foreground="#ffffff", padding=6)
    style.configure("TCheckbutton", background=CARD, foreground=FG, padding=6)

    load_cache()

    current_album: Optional[Album] = None

    canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    container = ttk.Frame(scrollable_frame, padding=20)
    container.pack(fill="both", expand=True)

    ttk.Label(container, text="🎶 Générateur d'Album Musical (API Analysis)", style="Title.TLabel").pack(pady=10)

    card_presets = ttk.Frame(container, padding=12, style="Card.TFrame")
    card_presets.pack(fill="x", pady=6)
    ttk.Label(card_presets, text="⚡ Préréglages rapides").pack(anchor="w", pady=(0, 5))
    
    preset_frame = ttk.Frame(card_presets, style="Card.TFrame")
    preset_frame.pack(fill="x", pady=5)
    
    preset_var = tk.StringVar()
    preset_combo = ttk.Combobox(preset_frame, textvariable=preset_var, 
                                values=list(PRESETS.keys()), state="readonly", width=25)
    preset_combo.pack(side="left", padx=(0, 10))

    genre_vars: Dict[str, tk.BooleanVar] = {}

    def apply_preset():
        preset_name = preset_var.get()
        if preset_name in PRESETS:
            preset = PRESETS[preset_name]
            for var in genre_vars.values():
                var.set(False)
            for style in preset["styles"]:
                if style in genre_vars:
                    genre_vars[style].set(True)
            theme_entry.delete(0, tk.END)
            theme_entry.insert(0, preset["theme"])
            messagebox.showinfo("Préréglage", f"✅ {preset['description']}")

    ttk.Button(preset_frame, text="Appliquer", command=apply_preset, 
               style="Secondary.TButton").pack(side="left")

    card_styles = ttk.Frame(container, padding=12, style="Card.TFrame")
    card_styles.pack(fill="x", pady=6)
    ttk.Label(card_styles, text="🎵 Genres musicaux").pack(anchor="w", pady=(0, 5))

    grid = ttk.Frame(card_styles, style="Card.TFrame")
    grid.pack(fill="x")

    for i, s in enumerate(STYLES.keys()):
        var = tk.BooleanVar()
        chk = ttk.Checkbutton(grid, text=s, variable=var)
        chk.grid(row=i // 4, column=i % 4, sticky="w", padx=8, pady=4)
        genre_vars[s] = var

    card_artists = ttk.Frame(container, padding=12, style="Card.TFrame")
    card_artists.pack(fill="x", pady=6)
    ttk.Label(card_artists, text="👥 Artistes (séparés par virgules)").pack(anchor="w", pady=(0, 5))
    artist_entry = ttk.Entry(card_artists, font=("Segoe UI", 10))
    artist_entry.pack(fill="x")
    artist_entry.insert(0, "1pliké140, Freeze Corleone, Koba LaD")

    card_theme = ttk.Frame(container, padding=12, style="Card.TFrame")
    card_theme.pack(fill="x", pady=6)
    ttk.Label(card_theme, text="🎭 Thématique globale").pack(anchor="w", pady=(0, 5))
    theme_entry = ttk.Entry(card_theme, font=("Segoe UI", 10))
    theme_entry.pack(fill="x")
    theme_entry.insert(0, "liberté")

    card_tracks = ttk.Frame(container, padding=12, style="Card.TFrame")
    card_tracks.pack(fill="x", pady=6)
    ttk.Label(card_tracks, text="📀 Nombre de tracks").pack(anchor="w", pady=(0, 5))
    track_spin = ttk.Spinbox(card_tracks, from_=3, to=30, font=("Segoe UI", 10))
    track_spin.set(8)
    track_spin.pack(fill="x")

    # Output
    card_output = ttk.Frame(container, padding=12, style="Card.TFrame")
    card_output.pack(fill="both", expand=True, pady=10)
    
    output = tk.Text(card_output, bg=BG, fg=FG, relief="flat", wrap="word", 
                     font=("Consolas", 9), height=15)
    output.pack(fill="both", expand=True)
    
    output.tag_configure("title", foreground=ACCENT, font=("Segoe UI", 14, "bold"))
    output.tag_configure("track", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
    output.tag_configure("link", foreground="#6e9ae1")
    output.tag_configure("api", foreground="#10a37f", font=("Consolas", 9, "italic"))

    def display_album(album: Album):
        output.delete("1.0", tk.END)
        output.insert(tk.END, f"🎼 {album.title}\n", "title")
        output.insert(tk.END, f"{'='*70}\n\n")
        output.insert(tk.END, f"🎭 Thème : {album.theme}\n")
        output.insert(tk.END, f"🎵 Styles : {', '.join(album.styles)}\n")
        output.insert(tk.END, f"👥 Artistes : {', '.join(album.artists)}\n\n")
        output.insert(tk.END, f"📖 {album.narration}\n\n")
        output.insert(tk.END, f"TRACKLIST\n", "title")
        output.insert(tk.END, f"{'-'*70}\n\n")

        for i, t in enumerate(album.tracks, 1):
            mins, secs = divmod(t.duration, 60)
            output.insert(tk.END, f"{i:2d}. {t.title}\n", "track")
            output.insert(tk.END, f"    {mins}:{secs:02d} | {t.tempo} BPM | {t.mood} | {t.theme}\n")
            output.insert(tk.END, f"    {t.link}\n\n", "link")
        
        avg_tempo = sum(t.tempo for t in album.tracks) // len(album.tracks)
        total_mins = sum(t.duration for t in album.tracks) // 60
        
        output.insert(tk.END, f"\n📊 Stats : {total_mins} min | {avg_tempo} BPM moyen | {len(album.tracks)} tracks\n")

    def run_generation():
        global current_album
        styles = [s for s, v in genre_vars.items() if v.get()]
        artists = [a.strip() for a in artist_entry.get().split(",") if a.strip()]
        theme = theme_entry.get().strip() or "libre"

        # Afficher message d'analyse
        output.delete("1.0", tk.END)
        output.insert(tk.END, "🎵 Analyse des artistes via API Deezer...\n\n", "api")
        output.insert(tk.END, "Veuillez patienter...\n", "api")
        root.update()

        try:
            current_album = generate_album(styles, artists, int(track_spin.get()), theme)
            display_album(current_album)
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de générer l'album:\n{str(e)}")

    def export_album():
        if not current_album:
            messagebox.showwarning("Attention", "Générez d'abord un album")
            return
        
        export_win = tk.Toplevel(root)
        export_win.title("💾 Exporter")
        export_win.geometry("350x200")
        export_win.configure(bg=BG)
        
        ttk.Label(export_win, text="Format d'export:", style="TLabel").pack(pady=20)
        
        def do_export(fmt):
            name = current_album.title.replace(" ", "_").replace("/", "-")
            if fmt == "json":
                f = filedialog.asksaveasfilename(defaultextension=".json", 
                    filetypes=[("JSON", "*.json")], initialfile=f"{name}.json")
                if f:
                    export_album_json(current_album, f)
                    messagebox.showinfo("Succès", f"✅ Exporté: {f}")
            elif fmt == "csv":
                f = filedialog.asksaveasfilename(defaultextension=".csv",
                    filetypes=[("CSV", "*.csv")], initialfile=f"{name}.csv")
                if f:
                    export_album_csv(current_album, f)
                    messagebox.showinfo("Succès", f"✅ Exporté: {f}")
            elif fmt == "txt":
                f = filedialog.asksaveasfilename(defaultextension=".txt",
                    filetypes=[("Text", "*.txt")], initialfile=f"{name}.txt")
                if f:
                    export_album_txt(current_album, f)
                    messagebox.showinfo("Succès", f"✅ Exporté: {f}")
            export_win.destroy()
        
        ttk.Button(export_win, text="📄 JSON", command=lambda: do_export("json")).pack(pady=5)
        ttk.Button(export_win, text="📊 CSV", command=lambda: do_export("csv")).pack(pady=5)
        ttk.Button(export_win, text="📝 TXT", command=lambda: do_export("txt")).pack(pady=5)

    def show_history():
        if not _album_history:
            messagebox.showinfo("Historique", "Aucun album généré")
            return
        
        hist_win = tk.Toplevel(root)
        hist_win.title("📚 Historique")
        hist_win.geometry("550x350")
        hist_win.configure(bg=BG)
        
        listbox = tk.Listbox(hist_win, bg=CARD, fg=FG, font=("Segoe UI", 10))
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        for i, album in enumerate(reversed(_album_history), 1):
            listbox.insert(tk.END, f"{i}. {album.title} - {album.created_at}")
        
        def load_sel():
            global current_album
            sel = listbox.curselection()
            if sel:
                idx = len(_album_history) - 1 - sel[0]
                current_album = _album_history[idx]
                display_album(current_album)
                hist_win.destroy()
        
        ttk.Button(hist_win, text="Charger", command=load_sel).pack(pady=10)

    # Boutons
    action_frame = ttk.Frame(container, style="TFrame")
    action_frame.pack(pady=12)

    ttk.Button(action_frame, text="🎧 Générer", command=run_generation).pack(side="left", padx=4)
    ttk.Button(action_frame, text="💾 Exporter", command=export_album, 
               style="Secondary.TButton").pack(side="left", padx=4)
    ttk.Button(action_frame, text="📚 Historique", command=show_history,
               style="Secondary.TButton").pack(side="left", padx=4)

    # Message initial
    output.insert(tk.END, "👋 Bienvenue!\n\n", "title")
    output.insert(tk.END, "🆕 Version avec analyse API Deezer\n", "api")
    output.insert(tk.END, "Les artistes sont analysés en temps réel pour des résultats authentiques!\n\n")
    output.insert(tk.END, "Configurez vos préférences et cliquez sur 'Générer'\n")
    output.insert(tk.END, "💡 Astuce : Utilisez les préréglages rapides!")

    root.mainloop()

# ==================================================
# Mode console
# ==================================================

if __name__ == "__main__" and not GUI_AVAILABLE:
    print("🎵 Générateur d'Albums - Mode Console (API Analysis)")
    load_cache()
    
    try:
        album = generate_album(["drill", "trap"], ["1pliké140", "Freeze Corleone"], 6, "rue")
        print(f"\n🎼 {album.title}")
        for i, t in enumerate(album.tracks, 1):
            print(f"{i}. {t.title} | {t.tempo} BPM | {t.link}")
        
        export_album_json(album, "album.json")
        print("\n✅ Exporté: album.json")
    except Exception as e:
        print(f"❌ Erreur: {e}")