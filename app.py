import streamlit as st
import pandas as pd
import altair as alt
import joblib

# Charger le modèle Random Forest
model = joblib.load("rf_model_maintenance.pkl")

from PIL import Image

# Config page
st.set_page_config(page_title="Smart Maintenance KPIs", layout="wide")

# Charger logo
logo = Image.open("assets/Logo.png")

# Header avec titre à gauche et logo à droite
col1, col2 = st.columns([8, 1])  # 8:1 ratio pour titre/logo
with col1:
    st.title("⚙️ Smart Maintenance — KPIs Atelier Tôlerie")
    st.markdown("Prototype Data Engineering / Data Analytics pour suivi maintenance")
with col2:
    st.image(logo, use_column_width=True)
# --- Charger les KPIs ---
@st.cache_data
def load_data():
    return pd.read_csv("kpis_summary.csv")

df = load_data()

# Filtre machine
machines = ["Toutes"] + list(df["machine"].unique())
choice = st.selectbox("Sélectionner une machine :", machines)

if choice != "Toutes":
    data = df[df["machine"] == choice]
else:
    data = df

# Tableau KPIs
st.subheader("📊 Tableau des KPIs")
st.dataframe(data, use_container_width=True)

# Graphiques
st.subheader("💶 Coût total de maintenance par machine")
chart_cost = alt.Chart(df).mark_bar().encode(
    x="machine",
    y="Cost_total_eur",
    tooltip=["Cost_total_eur"]
).properties(width=600, height=300)
st.altair_chart(chart_cost, use_container_width=True)

st.subheader("⏱️ Downtime total par machine (heures)")
chart_downtime = alt.Chart(df).mark_bar(color="orange").encode(
    x="machine",
    y="Downtime_total_h",
    tooltip=["Downtime_total_h"]
).properties(width=600, height=300)
st.altair_chart(chart_downtime, use_container_width=True)

st.subheader("📦 Scrap total par machine")
chart_scrap = alt.Chart(df).mark_bar(color="red").encode(
    x="machine",
    y="Scrap_total",
    tooltip=["Scrap_total"]
).properties(width=600, height=300)
st.altair_chart(chart_scrap, use_container_width=True)

st.markdown("🔧 *Prototype Streamlit — Données synthétiques pour démonstration.*")

st.subheader("🕒 Historique des pannes — Timeline par machine")

# Charger données événements
@st.cache_data
def load_events():
    df_events = pd.read_csv("maintenance_events.csv", parse_dates=["failure_date"])
    return df_events

df_events = load_events()

# Filtrer par machine
if choice != "Toutes":
    events_data = df_events[df_events["machine"] == choice]
else:
    events_data = df_events

# Créer timeline avec Altair
timeline_chart = alt.Chart(events_data).mark_circle().encode(
    x='failure_date:T',
    y='machine:N',
    size='downtime_h:Q',
    color=alt.condition('datum.downtime_h > 5', alt.value('darkred'), alt.value('orange')),
    tooltip=['machine', 'failure_date', 'downtime_h', 'cost_eur', 'scrap_units']
)


st.altair_chart(timeline_chart, use_container_width=True)

st.subheader("🤖 Prédiction risque de panne (7 prochains jours)")

# Sélection de la machine
machine_pred = st.selectbox("Choisir la machine pour prédiction :", machines[1:])  # exclut "Toutes"

# Dernier événement pour la machine
latest_event = df_events[df_events["machine"] == machine_pred].sort_values("failure_date").iloc[-1]

# Calcul features rolling 7 jours
window = df_events[(df_events["machine"] == machine_pred) &
                   (df_events["failure_date"] >= latest_event["failure_date"] - pd.Timedelta(days=7)) &
                   (df_events["failure_date"] < latest_event["failure_date"])]

avg_downtime_7d = window["downtime_h"].mean() if not window.empty else 0
avg_cost_7d = window["cost_eur"].mean() if not window.empty else 0
avg_scrap_7d = window["scrap_units"].mean() if not window.empty else 0

days_since_last = (latest_event["failure_date"] - window["failure_date"].max()).days if not window.empty else 7

# Préparer DataFrame pour prédiction
X_pred = pd.DataFrame([{
    "avg_downtime_7d": avg_downtime_7d,
    "avg_cost_7d": avg_cost_7d,
    "avg_scrap_7d": avg_scrap_7d,
    "days_since_last": days_since_last
}])

# Prédiction probabilité
proba = model.predict_proba(X_pred)
if proba.shape[1] == 1:
    pred_percent = 100.0 if model.classes_[0] == 1 else 0.0
else:
    pred_percent = round(proba[0][1]*100, 2)

# Couleur dynamique selon le risque
color = "green" if pred_percent < 30 else "orange" if pred_percent < 60 else "red"

# Affichage
st.markdown(f"<h2 style='color:{color}'>{pred_percent}%</h2>", unsafe_allow_html=True)
st.markdown(f"Risque de panne pour **{machine_pred}** dans les **7 prochains jours**.")
