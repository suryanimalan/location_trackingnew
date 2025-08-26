import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from datetime import datetime
import os
import math

# GPS location
try:
    from streamlit_js_eval import get_geolocation
    GEO_AVAILABLE = True
except:
    GEO_AVAILABLE = False

DATA_FILE = "staff_locations.csv"

# ------------------ DATA HANDLING ------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "username","role","action","lat","lon","timestamp",
            "km_travelled","collection_amount","customer_name","product"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ------------------ HELPER: DISTANCE ------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ------------------ AUTH ------------------
# Username-specific credentials
CREDENTIALS = {
    "staff1": {"role": "staff", "password": "pwd1"},
    "staff2": {"role": "staff", "password": "pwd2"},
    "staff3": {"role": "staff", "password": "pwd3"},
    "staff4": {"role": "staff", "password": "pwd4"},
    "staff5": {"role": "staff", "password": "pwd5"},
    "admin":  {"role": "admin", "password": "admin123"}
}

def login():
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        if username in CREDENTIALS and password == CREDENTIALS[username]["password"]:
            st.session_state["username"] = username
            st.session_state["role"] = CREDENTIALS[username]["role"]
            st.success(f"Welcome {username} ({st.session_state['role']})")
        else:
            st.error("Invalid credentials")

# ------------------ LOGOUT ------------------
def logout():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()   # ✅ updated for new Streamlit versions

# ------------------ STAFF DASHBOARD ------------------
def staff_dashboard(username):
    st.header(f"Staff Dashboard - {username}")
    df = load_data()

    # Auto GPS location
    lat, lon = None, None
    if GEO_AVAILABLE:
        loc = get_geolocation()
        if loc and "coords" in loc:
            lat = loc["coords"]["latitude"]
            lon = loc["coords"]["longitude"]

    col1, col2, col3 = st.columns(3)

    # Punch In (required before Clock In)
    with col1:
        if st.button("Punch In"):
            new_row = {
                "username": username,
                "role": "staff",
                "action": "punch_in",
                "lat": lat,
                "lon": lon,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "km_travelled": 0,
                "collection_amount": 0,
                "customer_name": "",
                "product": ""
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success("Punch In recorded")

    # Clock In (visit/customer)
    with col2:
        cust = st.text_input("Customer Name")
        prod = st.text_input("Product")
        amt = st.number_input("Collection Amount", min_value=0)
        if st.button("Clock In"):
            km = 0
            user_df = df[df["username"] == username]
            if not user_df.empty and pd.notna(lat) and pd.notna(lon):
                prev = user_df.iloc[-1]
                if pd.notna(prev["lat"]) and pd.notna(prev["lon"]):
                    km = haversine(prev["lat"], prev["lon"], lat, lon)

            new_row = {
                "username": username,
                "role": "staff",
                "action": "clock_in",
                "lat": lat,
                "lon": lon,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "km_travelled": km,
                "collection_amount": amt,
                "customer_name": cust,
                "product": prod
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success(f"Clock In recorded (Travel: {km:.2f} km)")

    # Clock Out (end of day)
    with col3:
        if st.button("Clock Out"):
            km = 0
            user_df = df[df["username"] == username]
            if not user_df.empty and pd.notna(lat) and pd.notna(lon):
                prev = user_df.iloc[-1]
                if pd.notna(prev["lat"]) and pd.notna(prev["lon"]):
                    km = haversine(prev["lat"], prev["lon"], lat, lon)

            new_row = {
                "username": username,
                "role": "staff",
                "action": "clock_out",
                "lat": lat,
                "lon": lon,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "km_travelled": km,
                "collection_amount": 0,
                "customer_name": "",
                "product": ""
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success(f"Clock Out recorded (Travel: {km:.2f} km)")

    # Travel Map
    st.subheader("Travel History Map")
    user_df = df[df["username"] == username]

    if not user_df.empty:
	
        m = folium.Map(location=[user_df["lat"].iloc[-1], user_df["lon"].iloc[-1]], zoom_start=12)
        mc = MarkerCluster().add_to(m)

        for _, row in user_df.iterrows():
            if pd.notna(row["lat"]) and pd.notna(row["lon"]):
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    popup=f"{row['action']} @ {row['timestamp']}<br>Cust:{row['customer_name']} Amt:{row['collection_amount']}<br>KM:{row['km_travelled']:.2f}",
                    tooltip=row["action"]
                ).add_to(mc)

        st_folium(m, width=700, height=500)
# ✅ Add summary for staff
        total_km = user_df["km_travelled"].sum()
        total_amt = user_df["collection_amount"].sum()
        st.metric("Total KM Travelled", f"{total_km:.2f} km")
        st.metric("Total Collection Amount", f"₹ {total_amt:.2f}")		
  
    
    else:
        st.info("No travel history yet.")

# ------------------ ADMIN DASHBOARD ------------------
def admin_dashboard():
    st.header("Admin Dashboard")
    df = load_data()

    if df.empty:
        st.warning("No data available")
        return

    staff_list = df["username"].unique().tolist()
    staff_filter = st.selectbox("Filter by Staff", ["All"] + staff_list)

    if staff_filter != "All":
        df = df[df["username"] == staff_filter]

    # Summary stats
    st.subheader("Summary")
    summary = df.groupby("username").agg(
        total_km=("km_travelled","sum"),
        total_amount=("collection_amount","sum"),
        visits=("action","count")
    ).reset_index()
    st.dataframe(summary)

    # Detailed logs
    st.subheader("Detailed Records")
    st.dataframe(df)

    # Map
    if not df.empty:
        m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=7)
        mc = MarkerCluster().add_to(m)

        for _, row in df.iterrows():
            if pd.notna(row["lat"]) and pd.notna(row["lon"]):
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    popup=f"{row['username']} - {row['action']} @ {row['timestamp']}<br>Cust:{row['customer_name']} Amt:{row['collection_amount']}<br>KM:{row['km_travelled']:.2f}",
                    tooltip=row["action"]
                ).add_to(mc)

        st_folium(m, width=800, height=600)

# ------------------ MAIN ------------------
def main():
    st.title("Staff Location Tracking")

    if "username" not in st.session_state:
        login()
    else:
        # ✅ Logout button in sidebar
        logout()

        if st.session_state["role"] == "staff":
            staff_dashboard(st.session_state["username"])
        else:
            admin_dashboard()

if __name__ == "__main__":
    main()
