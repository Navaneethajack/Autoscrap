import streamlit as st
import urllib.parse
import hashlib
import json
import os
import random
import pandas as pd
import requests
import ollama

# 🔄 Loader Animation
def show_loader(placeholder):
    placeholder.markdown("""
    <style>
        .loader-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
        }
        .ring {
            border: 8px solid #f3f3f3;
            border-top: 8px solid #4CAF50;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    <div class="loader-wrapper"><div class="ring"></div></div>
    """, unsafe_allow_html=True)

# 🔗 Generate search URL for a site
def get_search_url(site, query):
    encoded_query = urllib.parse.quote_plus(query)
    urls = {
        "amazon": f"https://www.amazon.in/s?k={encoded_query}",
        "flipkart": f"https://www.flipkart.com/search?q={encoded_query}",
        "ebay": f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}",
        "snapdeal": f"https://www.snapdeal.com/search?keyword={encoded_query}",
        "indiamart": f"https://dir.indiamart.com/search.mp?ss={encoded_query}",
        "boodmo": f"https://boodmo.com/catalog/search/?q={encoded_query}",
        "pricerunner": f"https://www.pricerunner.com/search?q={encoded_query}",
        "gomechanic": f"https://gomechanic.in/spares/search?query={encoded_query}",
        "cardekho": f"https://www.cardekho.com/search/result?q={encoded_query}",
        "autodoc": f"https://www.autodoc.co.uk/search?keyword={encoded_query}",
        "motointegrator": f"https://www.motointegrator.com/search?query={encoded_query}",
        "partslink24": f"https://www.partslink24.com/partslink24-web/pages/home.jsf?search={encoded_query}",
        "tecalliance": f"https://www.tecalliance.net/en/search?q={encoded_query}",
        "camelcamelcamel": f"https://in.camelcamelcamel.com/search?sq={encoded_query}"
    }
    return urls.get(site, "")

# 🧠 Query refinement with Ollama
def refine_query_with_ollama(user_query):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"Refine this auto part search query to be more specific for product search: {user_query}",
                "stream": False
            }
        )
        return response.json().get("response", "").strip() or user_query
    except Exception as e:
        st.warning(f"Ollama model not available. Using original query.\nError: {e}")
        return user_query

# 🕸️ Simulated scraping with caching
def scrape_live_results(site, query):
    os.makedirs("cache", exist_ok=True)
    cache_file = f"cache/{hashlib.md5((query + site).encode()).hexdigest()}.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    results = []
    for i in range(1, 6):
        results.append({
            "name": f"{query} - Result {i} from {site}",
            "price": random.randint(1000, 5000),
            "rating": round(random.uniform(3.0, 5.0), 2),
            "link": get_search_url(site, query)
        })

    with open(cache_file, "w") as f:
        json.dump(results, f)
    return results

# ✅ Optimal product selection
def choose_optimal(results):
    df = pd.DataFrame(results)
    if df.empty:
        return pd.DataFrame()
    df["norm_price"] = (df["price"] - df["price"].min()) / (df["price"].max() - df["price"].min() + 1e-6)
    df["norm_rating"] = (df["rating"] - df["rating"].min()) / (df["rating"].max() - df["rating"].min() + 1e-6)
    df["score"] = (1 - df["norm_price"]) * 0.6 + df["norm_rating"] * 0.4
    return df.sort_values(by="score", ascending=False).head(1)

# 🌐 Supported e-commerce platforms
supported_sites = [
    "amazon", "ebay", "flipkart", "snapdeal", "indiamart", "boodmo", "pricerunner",
    "gomechanic", "cardekho", "autodoc", "motointegrator", "partslink24", "tecalliance", "camelcamelcamel"
]

# 🌟 UI Setup
st.set_page_config(page_title="Auto Part Finder", layout="wide")
st.title("🔧 Auto Part Finder Chatbot")

# 🔁 Refresh search results
if st.button("🔄 Refresh Search"):
    st.session_state.pop("search_results", None)
    st.session_state.pop("optimal_result", None)
    st.rerun()

# 🔎 Search input
query = st.text_input("Search for an auto part (e.g., 'brake pad for Honda City')")

# 🔍 Perform search
if query and "search_results" not in st.session_state:
    loader = st.empty()
    show_loader(loader)

    refined_query = refine_query_with_ollama(query)
    all_results = []

    for site in supported_sites:
        results = scrape_live_results(site, refined_query)
        all_results.extend(results)

    df_results = pd.DataFrame(all_results)
    st.session_state["search_results"] = df_results
    st.session_state["optimal_result"] = choose_optimal(all_results)
    loader.empty()
    st.rerun()

# 📊 Display results
if "search_results" in st.session_state:
    st.subheader("📊 All Search Results")
    st.dataframe(st.session_state["search_results"])

    csv = st.session_state["search_results"].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "auto_parts_results.csv", "text/csv")

    st.subheader("✅ Suggested Optimal Product")
    if not st.session_state["optimal_result"].empty:
        st.dataframe(st.session_state["optimal_result"][["name", "price", "rating", "link"]])
    else:
        st.warning("No optimal product found.")
