import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import MinMaxScaler
import json
import os

# Configuration page
st.set_page_config(layout="wide", page_title="Dashboard Agents")


# Chargement des données
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data.csv")
        df['date'] = pd.to_datetime(df['date'])
        return df
    except FileNotFoundError:
        st.error("❌ Fichier data.csv introuvable")
        return pd.DataFrame()


df = load_data()

if df.empty:
    st.stop()

st.title("Dashboard Performance Agents")

# Sidebar filtres
with st.sidebar:
    st.header("Filtres")
    dates = st.date_input("Période", [df['date'].min(), df['date'].max()])

    # Option "Tous" pour les agents
    all_agents = list(df['agent'].unique())
    agent_choice = st.selectbox("Sélection Agents", ["Tous", "Sélection personnalisée"])
    if agent_choice == "Tous":
        agents = all_agents
        st.info(f"Tous les agents sélectionnés ({len(all_agents)})")
    else:
        agents = st.multiselect("Agents", all_agents, default=all_agents)

    # Option "Tous" pour les zones
    all_zones = list(df['zone'].unique())
    zone_choice = st.selectbox("Sélection Zones", ["Tous", "Sélection personnalisée"])
    if zone_choice == "Tous":
        zones = all_zones
        st.info(f"Toutes les zones sélectionnées ({len(all_zones)})")
    else:
        zones = st.multiselect("Zones", all_zones, default=all_zones)

# Filtre données
filtered_df = df[
    (df['date'] >= pd.to_datetime(dates[0])) &
    (df['date'] <= pd.to_datetime(dates[1])) &
    (df['agent'].isin(agents)) &
    (df['zone'].isin(zones))
    ]

# KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Commandes", f"{filtered_df['total_commandes_journalier'].sum():,}")

with col2:
    st.metric("Total Appels", f"{filtered_df['total_interaction_appel_par_agent'].sum():,}")

with col3:
    st.metric("Réclamations", f"{filtered_df['total_reclamation_par_agent'].sum():,}")

with col4:
    st.metric("Livraisons Impossibles", f"{filtered_df['total_suivi_livraison_impossible_par_agent'].sum():,}")

# KPIs supplémentaires - Ligne 2
col5, col6, col7, col8 = st.columns(4)

with col5:
    # Notation Livreur (moyenne si la colonne existe)
    if 'notation_livreur' in filtered_df.columns:
        notation_moyenne = filtered_df['notation_livreur'].mean()
        st.metric("Notation Livreur", f"{notation_moyenne:.1f}/5" if not pd.isna(notation_moyenne) else "N/A")
    else:
        st.metric("Notation Livreur", "N/A")

with col6:
    # Moyenne SKU par commande
    if 'total_sku' in filtered_df.columns and filtered_df['total_commandes_journalier'].sum() > 0:
        moy_sku = filtered_df['total_sku'].sum() / filtered_df['total_commandes_journalier'].sum()
        st.metric("Moy. SKU/Commande", f"{moy_sku:.1f}")
    else:
        st.metric("Moy. SKU/Commande", "N/A")

with col7:
    # Total SKU
    if 'total_sku' in filtered_df.columns:
        st.metric("Total SKU", f"{filtered_df['total_sku'].sum():,}")
    else:
        st.metric("Total SKU", "N/A")

with col8:
    # Suivi Réclamation
    if 'suivi_reclamation' in filtered_df.columns:
        st.metric("Suivi Réclamation", f"{filtered_df['suivi_reclamation'].sum():,}")
    else:
        st.metric("Suivi Réclamation", "N/A")

# KPIs supplémentaires - Ligne 3
col9, col10, col11, col12 = st.columns(4)

with col9:
    # Réclamation Agent (si différent de total_reclamation_par_agent)
    if 'reclamation_agent' in filtered_df.columns:
        st.metric("Réclamation Agent", f"{filtered_df['reclamation_agent'].sum():,}")
    else:
        st.metric("Réclamation Agent", f"{filtered_df['total_reclamation_par_agent'].sum():,}")

with col10:
    # Agents Actifs
    nb_agents = len(filtered_df['agent'].unique())
    st.metric("Agents Actifs", f"{nb_agents}")

with col11:
    # Zones Actives
    nb_zones = len(filtered_df['zone'].unique())
    st.metric("Zones Actives", f"{nb_zones}")

with col12:
    # Moyenne Commandes/Agent
    if nb_agents > 0:
        moy_cmd_agent = filtered_df['total_commandes_journalier'].sum() / nb_agents
        st.metric("Moy. Cmd/Agent", f"{moy_cmd_agent:.0f}")
    else:
        st.metric("Moy. Cmd/Agent", "0")

# Graphique principal
fig = px.bar(filtered_df, x='agent', y='total_commandes_journalier',
             title="Commandes par Agent", color='agent')
st.plotly_chart(fig, use_container_width=True)

# *** SOLUTION : TABLEAU SIMPLE SANS STYLING ***
st.subheader("Détails des Performances")
st.dataframe(filtered_df, use_container_width=True)

# Système notation
st.subheader("Notation Agents")
scores = filtered_df.groupby("agent").agg({
    "total_commandes_journalier": "sum",
    "total_interaction_appel_par_agent": "sum",
    "total_reclamation_par_agent": "sum",
    "total_suivi_livraison_impossible_par_agent": "sum"
}).reset_index()

# Calcul scores
scores["reclam_score"] = 1 / (1 + scores["total_reclamation_par_agent"])
scores["livr_score"] = 1 / (1 + scores["total_suivi_livraison_impossible_par_agent"])

# Normalisation
scaler = MinMaxScaler()
cols_to_scale = ["total_commandes_journalier", "total_interaction_appel_par_agent", "reclam_score", "livr_score"]
scores_norm = pd.DataFrame(
    scaler.fit_transform(scores[cols_to_scale]),
    columns=["cmd", "appels", "reclam", "livr"],
    index=scores["agent"]
)

# Note finale
scores_norm["note"] = (
                              scores_norm["cmd"] * 0.40 +
                              scores_norm["appels"] * 0.25 +
                              scores_norm["reclam"] * 0.20 +
                              scores_norm["livr"] * 0.15
                      ) * 100

scores_final = scores_norm[["note"]].round(1).sort_values("note", ascending=False)

# *** SOLUTION : TABLEAU SCORES SANS STYLING ***
st.dataframe(scores_final, use_container_width=True)

# Graphique scores
fig_score = px.bar(scores_final.reset_index(), x="agent", y="note",
                   title="Classement par Performance", color="note",
                   color_continuous_scale="viridis")
st.plotly_chart(fig_score, use_container_width=True)

# Commentaires
st.subheader("Commentaires")
selected_agent = st.selectbox("Agent", scores_final.index)
feedback = st.text_area(f"Commentaire pour {selected_agent}")

# Gestion commentaires
COMMENT_FILE = "commentaires.json"


def load_comments():
    if os.path.exists(COMMENT_FILE):
        with open(COMMENT_FILE, "r") as f:
            return json.load(f)
    return {}


if st.button("Enregistrer"):
    comments = load_comments()
    comments[selected_agent] = feedback
    with open(COMMENT_FILE, "w") as f:
        json.dump(comments, f)
    st.success(f"✅ Commentaire enregistré pour {selected_agent}")