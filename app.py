import streamlit as st
import pandas as pd
import requests
import pickle
import base64
import gdown
import os  # ← untuk cek file lokal

# === Streamlit UI config ===
st.set_page_config(page_title="Movie Recommender", layout="wide")

# === Responsive Column Settings (Auto based on screen width) ===
if 'screen_width' not in st.session_state:
    st.session_state.screen_width = 1200  # Nilai default, misalnya untuk desktop

width = st.session_state.screen_width

if width >= 1200:
    cols_per_row = 5
elif 768 <= width < 1200:
    cols_per_row = 3
else:
    cols_per_row = 2


# === Navigation Tab ===
nav = st.radio("", ["Home", "Genre", "Actor", "Watchlist"], horizontal=True)

# ID Google Drive file
file_id = "1BNr0_2ypf0GCqzN6_43HhoLKx0caGaD5"
gdrive_url = f"https://drive.google.com/uc?id={file_id}"
destination = "movie_data.pkl"

if not os.path.exists(destination):
    gdown.download(gdrive_url, destination, quiet=False)


# Load movie data & similarity matrix
try:
    with open("movie_data.pkl", "rb") as file:
        movies, cosine_sim = pickle.load(file)
except Exception as e:
    import traceback
    traceback.print_exc()
    st.error("Gagal memuat data film. Pastikan file 'movie_data.pkl' valid dan tersedia.")
    movies = None
    cosine_sim = None
    
if movies is not None:
    all_movies = movies[['title', 'movie_id']]
    # lanjut proses
else:
    st.error("Data film tidak tersedia.")


# === Caching fetch_poster ===
@st.cache_data(show_spinner=False)
def fetch_poster(movie_id):
    api_key = '7b995d3c6fd91a2284b4ad8cb390c7b8'
    url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        poster_path = data.get('poster_path', '')
        return f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
    except:
        return ""

# === Content-based recommendation ===
def get_recommendations(title, cosine_sim):  # ✅ ini benar
    idx = movies[movies['title'] == title].index[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:11]
    movie_indices = [i[0] for i in sim_scores]
    return movies[['title', 'movie_id']].iloc[movie_indices]

# === Expert system based recommendation ===
def expert_system_recommendation(genre=None, actor=None):
    df = movies.copy()
    if genre:
        df = df[df['genres'].apply(lambda x: genre_match(x, genre))]
    if actor:
        df = df[df['actors'].str.contains(actor, case=False, na=False)]
    if 'vote_average' in df.columns:
        df = df[df['vote_average'] >= 8.0]
    return df[['title', 'movie_id']].head(10)

# === Helper function to match genre accurately ===
def genre_match(row_genres, selected_genre):
    if pd.isna(row_genres):
        return False
    genres = [g.strip().lower() for g in row_genres.split(",")]
    return selected_genre.strip().lower() in genres

# === Search by genre or actor ===
def search_movies(genre=None, actor=None):
    if not genre and not actor:
        return pd.DataFrame(columns=['title', 'movie_id'])
    df = movies.copy()
    if genre:
        df = df[df['genres'].apply(lambda x: genre_match(x, genre))]
    if actor:
        df = df[df['actors'].str.contains(actor, case=False, na=False)]
    return df[['title', 'movie_id']]

# === Session state ===
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# === Background image setup ===
def get_base64_of_bg(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image_base64 = get_base64_of_bg("LUCES GAMER.jpeg")

st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpeg;base64,{bg_image_base64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #f0f0f0;
    }}
    h1, h2, h3, h4, h5, h6, .stSelectbox label {{
        color: #ffffff !important;
        text-shadow: 1px 1px 5px #000000;
    }}
    .movie-card {{
        padding: 15px;
        text-align: center;
        background: rgba(0, 0, 0, 0.55);
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        color: #fff;
        margin-bottom: 20px;
        transition: transform 0.3s ease-in-out;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .movie-card:hover {{
        transform: scale(1.05);
        background: rgba(0, 0, 0, 0.75);
        border: 1px solid #00ffff;
    }}
    .movie-title {{
        font-size: 15px;
        font-weight: 700;
        margin-top: 10px;
        color: #00ffff;
        text-shadow: 0 0 6px #00ffff;
    }}
    .stButton > button {{
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        font-size: 16px;
        font-weight: bold;
        color: white;
        background-color: #222;
        transition: 0.2s ease-in-out;
    }}
    .stButton > button:hover {{
        background-color: #00ffff;
        color: black;
        transform: scale(1.05);
    }}
    </style>
""", unsafe_allow_html=True)

# === Inject JS to get screen width ===
st.markdown("""
    <script>
    const sendScreenWidth = () => {
        const width = window.innerWidth;
        const data = { width: width };
        window.parent.postMessage(data, "*");
    };
    window.addEventListener("load", sendScreenWidth);
    window.addEventListener("resize", sendScreenWidth);
    </script>
""", unsafe_allow_html=True)

# === Receive screen width and store in session_state ===
if 'screen_width' not in st.session_state:
    st.session_state.screen_width = 1200  # Default desktop width

screen_width = st.query_params.get("width", [None])[0]
if screen_width:
    st.session_state.screen_width = int(screen_width)

def add_to_watchlist(title):
    if title not in st.session_state.watchlist:
        st.session_state.watchlist.append(title)
        st.rerun()

def remove_from_watchlist(title):
    if title in st.session_state.watchlist:
        st.session_state.watchlist.remove(title)
        st.rerun()

if nav == "Home":
    st.markdown("## 🎬 All Movies")
    search_term = st.text_input("🔍 Search Movies by Title")
    if search_term:
        all_movies = movies[movies['title'].str.contains(search_term, case=False, na=False)][['title', 'movie_id']]
        if all_movies.empty:
            st.warning("Film tidak ditemukan.")
            st.stop()
    else:
        all_movies = movies[['title', 'movie_id']]
        
        selected_title = all_movies.iloc[0]['title']  # Ambil judul pertama sebagai contoh
        recommendations = get_recommendations(selected_title, cosine_sim)

    for i in range(0, len(all_movies), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(all_movies):
                title = all_movies.iloc[i+j]['title']
                movie_id = all_movies.iloc[i+j]['movie_id']
                poster_url = fetch_poster(movie_id)
                with cols[j]:
                    st.markdown(f"""
                        <div class='movie-card'>
                            <img src='{poster_url}' width='100%' style='border-radius:10px'><br>
                            <div class='movie-title'>{title}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"➕ Add to Watchlist", key=f"add_{i+j}"):
                        add_to_watchlist(title)


elif nav == "Genre":
    st.markdown("## 🎭 Filter by Genre")
    all_genres = sorted(set(g.strip() for gs in movies['genres'].dropna() for g in gs.split(",")))
    selected_genre = st.selectbox("Select Genre", all_genres)
    if st.button("🔍 Search by Genre"):
        filtered = search_movies(genre=selected_genre)
        if filtered.empty:
            st.warning("Tidak ada film yang ditemukan untuk genre yang dipilih.")
        else:
            for i in range(0, len(filtered), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(filtered):
                        title = filtered.iloc[i+j]['title']
                        movie_id = filtered.iloc[i+j]['movie_id']
                        poster_url = fetch_poster(movie_id)
                        with cols[j]:
                            st.markdown(f"""
                                <div class='movie-card'>
                                    <img src='{poster_url}' width='100%' style='border-radius:10px'><br>
                                    <div class='movie-title'>{title}</div>
                                </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"➕ Add to Watchlist", key=f"genre_add_{i+j}"):
                                add_to_watchlist(title)


elif nav == "Actor":
    st.markdown("## 👤 Filter by Actor")
    all_actors = sorted(set(a.strip() for ac in movies['actors'].dropna() for a in ac.split(",")))
    selected_actor = st.selectbox("Select Actor", all_actors)
    if st.button("🔍 Search by Actor"):
        filtered = search_movies(actor=selected_actor)
        if filtered.empty:
            st.warning("Tidak ada film yang ditemukan untuk aktor yang dipilih.")
        else:
            for i in range(0, len(filtered), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(filtered):
                        title = filtered.iloc[i+j]['title']
                        movie_id = filtered.iloc[i+j]['movie_id']
                        poster_url = fetch_poster(movie_id)
                        with cols[j]:
                            st.markdown(f"""
                                <div class='movie-card'>
                                    <img src='{poster_url}' width='100%' style='border-radius:10px'><br>
                                    <div class='movie-title'>{title}</div>
                                </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"➕ Add to Watchlist", key=f"actor_add_{i+j}"):
                                add_to_watchlist(title)


elif nav == "Watchlist":
    st.markdown("## 📋 My Watchlist")
    if not st.session_state.watchlist:
        st.info("Daftar film kosong.")
    else:
        for i in range(0, len(st.session_state.watchlist), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(st.session_state.watchlist):
                    title = st.session_state.watchlist[i+j]
                    movie_id = movies[movies['title'] == title]['movie_id'].values[0]
                    poster_url = fetch_poster(movie_id)
                    with cols[j]:
                        st.markdown(f"""
                            <div class='movie-card'>
                                <img src='{poster_url}' width='100%' style='border-radius:10px'><br>
                                <div class='movie-title'>{title}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"❌ Remove", key=f"remove_{i+j}"):
                            remove_from_watchlist(title)
