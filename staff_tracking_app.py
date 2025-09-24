import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from datetime import datetime, date
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
        df = pd.read_csv(DATA_FILE)
        # ✅ Ensure new columns exist for backward compatibility
        for col in ["pt_date", "ptp_feedback"]:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=[
            "username","role","action","lat","lon","timestamp",
            "km_travelled","collection_amount","pt_date",
            "customer_name","product","ptp_feedback"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ------------------ HELPER: DISTANCE ------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ------------------ AUTH ------------------
CREDENTIALS = {
    "8760098358": {"role": "staff", "password": "pwd1"},
    "9876543210": {"role": "staff", "password": "pwd2"},
    "9876543211": {"role": "staff", "password": "pwd3"},
    "9876543212": {"role": "staff", "password": "pwd4"},
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
        st.rerun()

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

    today = date.today().strftime("%Y-%m-%d")

    # ------------------ STEP 1: PTP CUSTOMERS (Due Today) ------------------
    ptp_df = df[
        (df["username"] == username) &
        (df["pt_date"].notna()) &
        (df["pt_date"].astype(str) == today)
    ].fillna("")

    allow_clockin = True
    if not ptp_df.empty:
        # 🔔 Banner Notification if pending
        pending = ptp_df[(ptp_df["ptp_feedback"] == "")]
        if not pending.empty:
            st.markdown(
                "<div style='background-color:#ffcccc;padding:10px;border-radius:5px;'>"
                "🔔 <b>ALERT:</b> You still have PTP feedback pending for today!</div>",
                unsafe_allow_html=True
            )
            allow_clockin = False

        st.subheader("📌 PTP Customer List (Due Today)")
        for idx, row in ptp_df.iterrows():
            st.markdown(
                f"**{row['customer_name']}** | Product: {row['product']} | "
                f"Amount: ₹{row['collection_amount']} | Date: {row['pt_date']} | "
                f"PTP Feedback: {row['ptp_feedback'] or 'Not Given'}"
            )

            # PTP Feedback
            new_ptp = st.text_input(
                f"Update PTP Feedback for {row['customer_name']}",
                value=row['ptp_feedback'],
                key=f"ptp_{idx}"
            )

            # Upcoming PTP Date
            new_date = st.date_input(
                f"Set Next PTP Date for {row['customer_name']}",
                value=date.today(),
                key=f"nextptp_{idx}"
            )

            if st.button(f"Save for {row['customer_name']}", key=f"btn_ptp_{idx}"):
                df.at[idx, "ptp_feedback"] = new_ptp
                df.at[idx, "pt_date"] = new_date.strftime("%Y-%m-%d")
                save_data(df)
                st.success(f"✅ Saved PTP Feedback & Next PTP Date for {row['customer_name']}")
    else:
        st.info("✅ No PTP due today. You can Clock In directly.")

    # ------------------ STEP 2: ACTIONS ------------------
    st.subheader("Work Actions")
    col1, col2, col3 = st.columns(3)

    # Punch In
    with col1:
        if st.button("Punch In"):
            new_row = {
                "username": username,
                "role": "staff",
                "action": "punch_in",
                "lat": lat, "lon": lon,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "km_travelled": 0,
                "collection_amount": 0,
                "pt_date": "", "customer_name": "",
                "product": "", "ptp_feedback": ""
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success("Punch In recorded")

    # Clock In
    with col2:
        cust = st.text_input("Customer Name")
        prod = st.text_input("Product")
        amt = st.number_input("Collection Amount", min_value=0)
        pt_date = st.date_input("Payment Date")

        if st.button("Clock In"):
            if not allow_clockin:
                st.error("⚠️ Complete today's PTP feedback before Clock In")
            else:
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
                    "lat": lat, "lon": lon,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "km_travelled": km,
                    "collection_amount": amt,
                    "pt_date": pt_date.strftime("%Y-%m-%d") if pt_date else "",
                    "customer_name": cust,
                    "product": prod,
                    "ptp_feedback": ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.success(f"Clock In recorded (Travel: {km:.2f} km)")

    # Clock Out
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
                "lat": lat, "lon": lon,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "km_travelled": km,
                "collection_amount": 0,
                "pt_date": "", "customer_name": "",
                "product": "", "ptp_feedback": ""
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success(f"Clock Out recorded (Travel: {km:.2f} km)")

        # ------------------ MAP + SUMMARY ------------------
    st.subheader("Travel History Map")
    user_df = df[df["username"] == username]
    if not user_df.empty:
        m = folium.Map(location=[user_df["lat"].iloc[-1], user_df["lon"].iloc[-1]], zoom_start=12)
        mc = MarkerCluster().add_to(m)

        coords = []  # store lat/lon for line
        for _, row in user_df.iterrows():
            if pd.notna(row["lat"]) and pd.notna(row["lon"]):
                coords.append([row["lat"], row["lon"]])
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    popup=(f"{row['action']} @ {row['timestamp']}<br>"
                           f"Cust:{row['customer_name']} Amt:{row['collection_amount']}<br>"
                           f"Date:{row['pt_date']}<br>"
                           f"PTP:{row['ptp_feedback']}<br>"
                           f"KM:{row['km_travelled']:.2f}"),
                    tooltip=row["action"]
                ).add_to(mc)

        # 🔹 Add travel line (PolyLine) if multiple points
        if len(coords) > 1:
            folium.PolyLine(
                coords, color="blue", weight=3, opacity=0.7
            ).add_to(m)

        st_folium(m, width=700, height=500)

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

    today = date.today().strftime("%Y-%m-%d")

    # 🔔 Pending PTP Customers
    pending_ptp = df[
        (df["pt_date"].astype(str) == today) &
        ((df["ptp_feedback"].isna()) | (df["ptp_feedback"] == ""))
    ]

    pending_users = pending_ptp["username"].unique().tolist()

    if not pending_ptp.empty:
        st.markdown(
            "<div style='background-color:#ffcccc;padding:10px;border-radius:5px;'>"
            "🔔 <b>Pending PTP Customers (Today)</b></div>",
            unsafe_allow_html=True
        )
        st.dataframe(pending_ptp[["username","customer_name","product","collection_amount","pt_date"]])
    else:
        st.success("✅ All PTP feedback completed for today.")

    # ------------------ STAFF FILTER ------------------
    staff_list = df["username"].unique().tolist()
    staff_filter = st.selectbox("Filter by Staff", ["All"] + staff_list)

    if staff_filter != "All":
        df = df[df["username"] == staff_filter]

    # ------------------ SUMMARY ------------------
    st.subheader("Summary")
    summary = df.groupby("username").agg(
        total_km=("km_travelled","sum"),
        total_amount=("collection_amount","sum"),
        visits=("action","count")
    ).reset_index()

    # Highlight staff with pending PTP in red
    def highlight_pending(val):
        color = "red" if val in pending_users else "black"
        return f"color: {color}; font-weight: bold;"

    st.dataframe(summary.style.applymap(highlight_pending, subset=["username"]))

    # ------------------ DETAILED RECORDS ------------------
    st.subheader("Detailed Records")
    st.dataframe(df)

        # ------------------ MAP ------------------
    if not df.empty:
        m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=7)
        mc = MarkerCluster().add_to(m)

        # 🔹 Staff-wise group
        for staff, staff_df in df.groupby("username"):
            staff_df = staff_df.dropna(subset=["lat","lon"]).sort_values("timestamp")
            coords = staff_df[["lat","lon"]].values.tolist()

            # Staff route markers
            for _, row in staff_df.iterrows():
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    popup=(f"{row['username']} - {row['action']} @ {row['timestamp']}<br>"
                           f"Cust:{row['customer_name']} Amt:{row['collection_amount']}<br>"
                           f"Date:{row['pt_date']}<br>"
                           f"PTP:{row['ptp_feedback']}<br>"
                           f"KM:{row['km_travelled']:.2f}"),
                    tooltip=f"{row['username']} ({row['action']})"
                ).add_to(mc)

            # 🔹 Staff travel line
            if len(coords) > 1:
                folium.PolyLine(
                    coords,
                    color="blue",   # optional: assign unique color per staff
                    weight=3,
                    opacity=0.6,
                    tooltip=f"Path of {staff}"
                ).add_to(m)

        st_folium(m, width=800, height=600)


# ------------------ MAIN ------------------
def main():
    st.title("Staff Location Tracking")

    if "username" not in st.session_state:
        login()
    else:
        logout()
        if st.session_state["role"] == "staff":
            staff_dashboard(st.session_state["username"])
        else:
            admin_dashboard()

if __name__ == "__main__":
    main()
