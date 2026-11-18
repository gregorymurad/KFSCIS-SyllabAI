import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="KFSCIS Course Explorer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    artifacts = Path(__file__).parent
    csv_files = sorted(artifacts.glob("kfscis_*.csv"))
    # Prefer the individual prefix files; skip the combined one if present
    csv_files = [f for f in csv_files if f.name != "kfscis_courses.csv"]
    if not csv_files:
        st.error("No course CSV files found. Place the kfscis_*.csv files next to this script.")
        return pd.DataFrame()
    frames = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            frames.append(df)
        except Exception as e:
            st.warning(f"Could not read {f.name}: {e}")
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, ignore_index=True)
    # Clean up
    for col in data.columns:
        if data[col].dtype == object:
            data[col] = data[col].fillna("").astype(str).str.strip()
    data["Full Code"] = data["Course Prefix"].str.strip() + " " + data["Course Number"].astype(str).str.strip()
    return data

df = load_data()

if df.empty:
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

prefixes = sorted(df["Course Prefix"].unique())
selected_prefixes = st.sidebar.multiselect(
    "Course Prefix",
    options=prefixes,
    default=prefixes,
    help="Select one or more prefixes (CAI, CAP, CEN, etc.)"
)

# Numbers depend on selected prefixes
if selected_prefixes:
    number_options = sorted(
        df[df["Course Prefix"].isin(selected_prefixes)]["Course Number"].unique(),
        key=lambda x: str(x)
    )
else:
    number_options = sorted(df["Course Number"].unique(), key=lambda x: str(x))

selected_numbers = st.sidebar.multiselect(
    "Course Number",
    options=number_options,
    default=[],
    help="Optional: narrow by specific course numbers"
)

search_text = st.sidebar.text_input(
    "Search (title or description)",
    placeholder="e.g. machine learning, data structures, cloud..."
)

has_prereq = st.sidebar.checkbox("Has prerequisites", value=False)
has_coreq = st.sidebar.checkbox("Has corequisites", value=False)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
filtered = df.copy()

if selected_prefixes:
    filtered = filtered[filtered["Course Prefix"].isin(selected_prefixes)]

if selected_numbers:
    filtered = filtered[filtered["Course Number"].isin(selected_numbers)]

if search_text:
    mask = (
        filtered["Course Title Long"].str.contains(search_text, case=False, na=False) |
        filtered["Course Description"].str.contains(search_text, case=False, na=False) |
        filtered["Full Code"].str.contains(search_text, case=False, na=False)
    )
    filtered = filtered[mask]

if has_prereq:
    filtered = filtered[filtered["Course prerequisites"].str.len() > 0]

if has_coreq:
    filtered = filtered[filtered["Course corequisites"].str.len() > 0]

# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------
st.title("📚 KFSCIS Course Explorer")
st.caption("Knight Foundation School of Computing and Information Sciences · Florida International University")

col1, col2, col3 = st.columns(3)
col1.metric("Total Courses", len(df))
col2.metric("Showing", len(filtered))
col3.metric("Prefixes", filtered["Course Prefix"].nunique() if not filtered.empty else 0)

st.divider()

if filtered.empty:
    st.info("No courses match your filters. Try adjusting the sidebar.")
else:
    # Sort for display
    filtered = filtered.sort_values(["Course Prefix", "Course Number"]).reset_index(drop=True)

    # Summary table
    display_cols = [
        "Full Code",
        "Course Title Long",
        "Number of credit hours",
        "Course prerequisites",
        "Course corequisites",
    ]
    st.subheader("Course List")
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Full Code": st.column_config.TextColumn("Code", width="small"),
            "Course Title Long": st.column_config.TextColumn("Title"),
            "Number of credit hours": st.column_config.TextColumn("Credits", width="small"),
            "Course prerequisites": st.column_config.TextColumn("Prerequisites"),
            "Course corequisites": st.column_config.TextColumn("Corequisites"),
        }
    )

    st.divider()

    # Detail cards
    st.subheader("Course Details")
    for _, row in filtered.iterrows():
        with st.expander(f"**{row['Full Code']}** — {row['Course Title Long']}", expanded=False):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**Title:** {row['Course Title Long']}")
                if row["Course Title Abbreviated"] and row["Course Title Abbreviated"] != row["Course Title Long"]:
                    st.markdown(f"**Abbreviated:** {row['Course Title Abbreviated']}")
                st.markdown(f"**Credits:** {row['Number of credit hours'] or '—'}")
                st.markdown(f"**Designation:** {row['Course Designation'] or 'N/A'}")
                if row["Global Learning designation"] and row["Global Learning designation"].lower() == "true":
                    st.markdown("**Global Learning:** Yes")
            with c2:
                prereq = row["Course prerequisites"] or "None listed"
                coreq = row["Course corequisites"] or "None listed"
                st.markdown(f"**Prerequisites:** {prereq}")
                st.markdown(f"**Corequisites:** {coreq}")
                if row["Category (Mandatory/Elective by major)"]:
                    st.markdown(f"**Category:** {row['Category (Mandatory/Elective by major)']}")

            if row["Course Description"]:
                st.markdown("**Description**")
                st.write(row["Course Description"])

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Data sourced from the official FIU University Catalog (catalog.fiu.edu). "
    "Category information is supplemented from KFSCIS syllabi where available. "
    "Always verify with the official catalog or your advisor for the most current requirements."
)
