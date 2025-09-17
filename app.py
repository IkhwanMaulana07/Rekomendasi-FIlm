import streamlit as st
import pandas as pd
import requests
import pickle
import base64
import gdown
import os

# === Streamlit UI config ===
st.set_page_config(page_title="Movie Recommender", layout="wide")

# === Session State Initialization ===
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"
if "screen_width" not in st.session_state:
    st.session_state.screen_width = 1200

# === Responsive Column Settings ===
width = st.session_state.screen_width
if width >= 1200:
    cols_per_row = 5
elif 768 <= width < 1200:
    cols_per_row = 3
else:
    cols_per_row = 2

# === Load movie data ===
file_id = "1BNr0_2ypf0GCqzN6_43HhoLKx0caGaD5"
gdrive_url = f"https://drive.google.com/uc?id={file_id}"
destination = "movie_data.pkl"

if not os.path.exists(destination):
    try:
        gdown.download(gdrive_url, destination, quiet=False)
    except Exception as e:
        st.error(f"Gagal mendownload movie_data.pkl: {e}")

if not os.path.exists(destination):
    st.stop()

with open(destination, "rb") as f:
    movies, cosine_sim = pickle.load(f)

# === Navbar ===
options = ["Home", "Genre", "Actor", "Watchlist"]
current_page = st.session_state.get("current_page", "Home")
if current_page in options:
    default_index = options.index(current_page)
    st.session_state.current_page = st.radio(
        "", options, horizontal=True, index=default_index
    )


# === Background & Custom CSS ===
def get_base64_of_bg(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


bg_image_base64 = get_base64_of_bg("LUCES GAMER.jpeg")
if bg_image_base64:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{bg_image_base64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: #f0f0f0;
        }}
        h1,h2,h3,h4,h5,h6,.stSelectbox label {{
            color: #ffffff !important;
            text-shadow: 1px 1px 5px #000000;
        }}
        /* Card */
        .movie-card {{
            text-align: center;
            padding: 4px;
            margin: 0.1em; /* jarak antar poster kecil saja */
        }}
        /* Poster */
        .stImage > img {{
            display: block;
            margin-left: auto;
            margin-right: auto;
            border-radius: 10px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.6);
        }}
        /* Semua tombol (judul + watchlist) serasi */
        .stButton button {{
            display: block;
            margin: 6px auto;
            border-radius: 8px;
            padding: 6px 12px;
            width: 220px;   /* pas dengan lebar poster */
            text-align: center;
        }}
        .center {{
            text-align: center;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# === Fetch Movie Details (poster + detail + cast) ===
@st.cache_data(show_spinner=False)
def fetch_movie_details(movie_id):
    api_key = "7b995d3c6fd91a2284b4ad8cb390c7b8"
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
    credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={api_key}&language=en-US"
    try:
        response = requests.get(url, timeout=5).json()
        poster_path = response.get("poster_path", "")
        overview = response.get("overview", "No description available.")
        rating = response.get("vote_average", "N/A")
        genres = ", ".join([g["name"] for g in response.get("genres", [])])
        poster_url = (
            f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        )
        credits_resp = requests.get(credits_url, timeout=5).json()
        cast_list = credits_resp.get("cast", [])
        actors = ", ".join([c["name"] for c in cast_list[:5]]) if cast_list else "N/A"
        return poster_url, overview, rating, genres, actors
    except Exception:
        return "", "No description available.", "N/A", "", "N/A"


# === Recommendation helpers ===
def get_recommendations(title, cosine_sim):
    if title not in movies["title"].values:
        return pd.DataFrame(columns=["title", "movie_id"])
    idx = movies[movies["title"] == title].index[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:7]
    movie_indices = [i[0] for i in sim_scores]
    return movies[["title", "movie_id"]].iloc[movie_indices]


def genre_match(row_genres, selected_genre):
    if pd.isna(row_genres):
        return False
    genres = [g.strip().lower() for g in row_genres.split(",")]
    return selected_genre.strip().lower() in genres


def search_movies(genre=None, actor=None):
    if not genre and not actor:
        return pd.DataFrame(columns=["title", "movie_id"])
    df = movies.copy()
    if genre:
        df = df[df["genres"].apply(lambda x: genre_match(x, genre))]
    if actor:
        df = df[df["actors"].str.contains(actor, case=False, na=False)]
    return df[["title", "movie_id"]]


# === Watchlist functions ===
def add_to_watchlist(title):
    if title not in st.session_state.watchlist:
        st.session_state.watchlist.append(title)
        st.toast(f"✅ Ditambahkan: {title}")
    else:
        st.toast(f"⚠️ {title} sudah ada di Watchlist")


def remove_from_watchlist(title):
    if title in st.session_state.watchlist:
        st.session_state.watchlist.remove(title)
        st.rerun()


# === Helper render card (rapih & tombol serasi) ===
def render_movie_card(title, movie_id, key_prefix=""):
    poster_url, _, _, _, _ = fetch_movie_details(movie_id)
    st.markdown("<div class='movie-card'>", unsafe_allow_html=True)

    # Poster
    if poster_url:
        st.image(poster_url, use_container_width=True)
    else:
        st.image(
            "https://via.placeholder.com/220x330?text=No+Poster",
            use_container_width=True,
        )

    # Judul
    if st.button(
        f"🎬 {title}",
        key=f"{key_prefix}_titlebtn_{movie_id}",
        help=f"Klik untuk melihat detail {title}",
    ):
        st.session_state.selected_movie = title
        st.session_state.current_page = "Details"
        st.rerun()

    # Tombol Add
    if st.button("➕ Add to Watchlist", key=f"{key_prefix}_add_{movie_id}"):
        add_to_watchlist(title)

    # Tombol Remove (khusus untuk Watchlist)
    if st.session_state.current_page == "Watchlist":
        if st.button("❌ Remove", key=f"{key_prefix}_remove_{movie_id}"):
            remove_from_watchlist(title)

    st.markdown("</div>", unsafe_allow_html=True)


# === Pages ===
if st.session_state.current_page == "Home":
    st.markdown("<h2 class='center'>🎬 All Movies</h2>", unsafe_allow_html=True)

    title_search = st.text_input("🔍 Cari Film berdasarkan Judul")

    if "home_results" not in st.session_state:
        st.session_state.home_results = movies[["title", "movie_id"]]
    if "home_searched" not in st.session_state:
        st.session_state.home_searched = False

    if st.button("🔍 Search by Title"):
        if title_search.strip():
            st.session_state.home_results = movies[
                movies["title"].str.contains(title_search, case=False, na=False)
            ][["title", "movie_id"]]
        else:
            st.session_state.home_results = movies[["title", "movie_id"]]
        st.session_state.home_searched = True

    if st.session_state.home_results.empty and st.session_state.home_searched:
        st.warning(f"❌ Film dengan judul '{title_search}' tidak ditemukan.")
    else:
        for i in range(0, len(st.session_state.home_results), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(st.session_state.home_results):
                    row = st.session_state.home_results.iloc[i + j]
                    with cols[j]:
                        render_movie_card(
                            row["title"], row["movie_id"], key_prefix=f"home_{i+j}"
                        )

elif st.session_state.current_page == "Genre":
    st.markdown("<h2 class='center'>🎭 Filter by Genre</h2>", unsafe_allow_html=True)
    all_genres = sorted(
        set(g.strip() for gs in movies["genres"].dropna() for g in gs.split(","))
    )
    selected_genre = st.selectbox("Select Genre", all_genres)

    # inisialisasi session state
    if "genre_results" not in st.session_state:
        st.session_state.genre_results = pd.DataFrame(columns=["title", "movie_id"])
    if "genre_searched" not in st.session_state:
        st.session_state.genre_searched = False

    if st.button("🔍 Search by Genre"):
        st.session_state.genre_results = search_movies(genre=selected_genre)
        st.session_state.genre_searched = True

    if st.session_state.genre_searched:  # hanya cek kalau sudah search
        if not st.session_state.genre_results.empty:
            for i in range(0, len(st.session_state.genre_results), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(st.session_state.genre_results):
                        row = st.session_state.genre_results.iloc[i + j]
                        with cols[j]:
                            render_movie_card(
                                row["title"], row["movie_id"], key_prefix=f"genre_{i+j}"
                            )
        else:
            st.warning(f"Tidak ada film ditemukan untuk genre '{selected_genre}'.")


elif st.session_state.current_page == "Actor":
    st.markdown("<h2 class='center'>👤 Filter by Actor</h2>", unsafe_allow_html=True)
    all_actors = sorted(
        set(a.strip() for ac in movies["actors"].dropna() for a in ac.split(","))
    )
    selected_actor = st.selectbox("Select Actor", all_actors)

    # inisialisasi session state
    if "actor_results" not in st.session_state:
        st.session_state.actor_results = pd.DataFrame(columns=["title", "movie_id"])
    if "actor_searched" not in st.session_state:
        st.session_state.actor_searched = False

    if st.button("🔍 Search by Actor"):
        st.session_state.actor_results = search_movies(actor=selected_actor)
        st.session_state.actor_searched = True

    if st.session_state.actor_searched:  # hanya cek kalau sudah search
        if not st.session_state.actor_results.empty:
            for i in range(0, len(st.session_state.actor_results), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(st.session_state.actor_results):
                        row = st.session_state.actor_results.iloc[i + j]
                        with cols[j]:
                            render_movie_card(
                                row["title"], row["movie_id"], key_prefix=f"actor_{i+j}"
                            )
        else:
            st.warning(f"Tidak ada film ditemukan untuk aktor '{selected_actor}'.")


elif st.session_state.current_page == "Watchlist":
    st.markdown("<h2 class='center'>📋 My Watchlist</h2>", unsafe_allow_html=True)
    if not st.session_state.watchlist:
        st.info("Daftar film kosong.")
    else:
        for i in range(0, len(st.session_state.watchlist), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(st.session_state.watchlist):
                    title = st.session_state.watchlist[i + j]
                    movie_id = movies[movies["title"] == title]["movie_id"].values[0]
                    with cols[j]:
                        render_movie_card(
                            title, movie_id, key_prefix=f"watchlist_{i+j}"
                        )


elif st.session_state.current_page == "Details":
    if not st.session_state.selected_movie:
        st.warning("Belum ada film yang dipilih.")
    else:
        title = st.session_state.selected_movie
        if title not in movies["title"].values:
            st.warning("Film tidak ditemukan di dataset.")
        else:
            movie_id = movies[movies["title"] == title]["movie_id"].values[0]
            poster_url, overview, rating, genres, actors = fetch_movie_details(movie_id)

            # Semua detail di tengah
            st.markdown(f"<h1 class='center'>{title}</h1>", unsafe_allow_html=True)
            st.markdown("<div class='center'>", unsafe_allow_html=True)

            if poster_url:
                st.image(poster_url, width=300)

            st.markdown(f"<p><b>Genres:</b><br>{genres}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Rating:</b><br>⭐ {rating}</p>", unsafe_allow_html=True)
            st.markdown(
                f"<p><b>Actors / Cast:</b><br>{actors}</p>", unsafe_allow_html=True
            )
            st.markdown(
                f"<p><b>Description:</b><br>{overview}</p>", unsafe_allow_html=True
            )

            # Tombol center
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("➕ Add to Watchlist", key="details_add"):
                    add_to_watchlist(title)
                if st.button("⬅️ Back to Home"):
                    st.session_state.current_page = "Home"
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

            # Rekomendasi serupa juga di tengah
            st.markdown(
                "<h3 class='center'>🔎 Rekomendasi serupa</h3>", unsafe_allow_html=True
            )
            recs = get_recommendations(title, cosine_sim)
            for i in range(0, len(recs), cols_per_row):
                rec_cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(recs):
                        row = recs.iloc[i + j]
                        with rec_cols[j]:
                            render_movie_card(
                                row["title"], row["movie_id"], key_prefix=f"rec_{i+j}"
                            )
