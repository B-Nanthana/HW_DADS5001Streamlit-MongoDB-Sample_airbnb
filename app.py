import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="Airbnb Global Market Analytics", layout="wide")

# --- ส่วนตกแต่งสไตล์ Dark Hero & Glass Container (เน้นแก้สีตัวเลข Slider เป็นสีขาวทั้งหมด) ---
def add_premium_glass_style():
    st.markdown(
         f"""
         <style>
         /* 1. พื้นหลังหลัก */
         .stApp {{
             background: linear-gradient(rgba(14, 17, 23, 0.85), rgba(14, 17, 23, 0.85)), 
                         url("https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=80&w=2070&auto=format&fit=crop");
             background-attachment: fixed;
             background-size: cover;
         }}
         
         .main .block-container {{
             background-color: transparent;
             padding-top: 2rem;
         }}
         
         /* 2. หัวข้อและข้อความทั่วไปสีขาว */
         h1, h2, h3, p, span, label, li {{
             color: #ffffff !important; 
         }}

         /* 3. กล่องโปร่งแสง (Glass Box) */
         [data-testid="stMetric"], .stPlotlyChart, .stDataFrame, .stTable, div[data-testid="stExpander"] {{
             background-color: rgba(255, 255, 255, 0.07) !important;
             border: 1px solid rgba(255, 255, 255, 0.12) !important;
             border-radius: 15px !important;
             padding: 15px !important;
             backdrop-filter: blur(10px) !important;
             box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
             margin-bottom: 20px !important;
         }}
         
         [data-testid="stMetricValue"] {{
             color: #ffffff !important;
             font-size: 2.2rem !important;
         }}
         
         /* 4. Dropdown List พื้นหลังเข้มตัวหนังสือขาว */
         div[data-baseweb="popover"] div, div[role="listbox"] {{
             background-color: #262730 !important;
         }}
         
         div[role="option"] {{
             background-color: #262730 !important;
             color: #ffffff !important;
         }}

         div[data-baseweb="select"] {{
             color: #000000 !important;
         }}
         
         /* 5. Multiselect Tags - พื้นเทาอ่อนตัวหนังสือดำ */
         span[data-baseweb="tag"] {{
             background-color: #e2e8f0 !important; 
             color: #000000 !important; 
         }}
         
         span[data-baseweb="tag"] span {{
             color: #000000 !important;
         }}

         /* 6. แก้ไข Slider (จุดที่เน้น): ทำให้ตัวเลขทุกตัวเป็นสีขาว และไม่มีไฮไลท์เทา */
         /* ตัวเลขที่วิ่งตามปุ่ม (Thumb Value) */
         div[data-testid="stThumbValue"] {{
             background-color: transparent !important;
             color: #ffffff !important;
             font-size: 1rem !important;
         }}
         
         /* ตัวเลขขอบซ้าย-ขวาของ Slider (Tick Bar) */
         div[data-baseweb="slider"] div {{
             color: #ffffff !important;
         }}
         
         /* บังคับสีตัวเลขในทุกระดับชั้นของ Slider */
         .stSlider [data-baseweb="slider"] span {{
             color: #ffffff !important;
         }}

         .stSlider [data-baseweb="slider"] > div > div {{
             background: #475569 !important; /* สีเส้น Slider */
         }}

         /* 7. Sidebar */
         [data-testid="stSidebar"] {{
             background-color: rgba(15, 23, 42, 0.98);
         }}
         </style>
         """,
         unsafe_allow_html=True
     )

add_premium_glass_style()

# 2. Connection & Data Loading
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo_uri"])

client = init_connection()

@st.cache_data
def load_data():
    db = client.sample_airbnb
    collection = db.listingsAndReviews
    cursor = collection.find({}, {
        "name": 1, "room_type": 1, "property_type": 1, "price": 1,
        "address.country": 1, "address.location.coordinates": 1,
        "review_scores.review_scores_rating": 1, "number_of_reviews": 1,
        "accommodates": 1, "bedrooms": 1, "beds": 1, "images.picture_url": 1,
        "summary": 1, "amenities": 1
    })
    
    df = pd.DataFrame(list(cursor))
    if not df.empty:
        df['price'] = df['price'].apply(lambda x: float(str(x)))
        df['country'] = df['address'].apply(lambda x: x.get('country'))
        df['lon'] = df['address'].apply(lambda x: x['location']['coordinates'][0])
        df['lat'] = df['address'].apply(lambda x: x['location']['coordinates'][1])
        df['rating'] = df['review_scores'].apply(lambda x: x.get('review_scores_rating', 0) if isinstance(x, dict) else 0)
        df['image_url'] = df['images'].apply(lambda x: x.get('picture_url') if isinstance(x, dict) else None)
        df['short_name'] = df['name'].apply(lambda x: x[:25] + '...' if len(x) > 25 else x)
    return df

df = load_data()

# 3. Sidebar Filters
with st.sidebar:
    st.header("🎯 Filters")
    countries = sorted(df['country'].unique())
    f_country = st.multiselect("เลือกประเทศ", options=countries)
    temp_df = df[df['country'].isin(f_country)] if f_country else df
    props = sorted(temp_df['property_type'].unique())
    f_prop = st.multiselect("ประเภทอสังหาฯ", options=props)
    temp_df = temp_df[temp_df['property_type'].isin(f_prop)] if f_prop else temp_df
    rooms = sorted(temp_df['room_type'].unique())
    f_room = st.multiselect("ประเภทห้องพัก", options=rooms)
    
    st.markdown("---")
    p_min, p_max = int(df['price'].min()), int(df['price'].max())
    f_price = st.slider("ช่วงราคา ($)", p_min, p_max, (p_min, p_max))
    f_rate = st.slider("Rating ขั้นต่ำ (%)", 0, 100, 0)

# 4. Final Filter Logic
filtered_df = df.copy()
if f_country: filtered_df = filtered_df[filtered_df['country'].isin(f_country)]
if f_prop: filtered_df = filtered_df[filtered_df['property_type'].isin(f_prop)]
if f_room: filtered_df = filtered_df[filtered_df['room_type'].isin(f_room)]
filtered_df = filtered_df[(filtered_df['price'].between(f_price[0], f_price[1])) & (filtered_df['rating'] >= f_rate)]

# 5. Header Section
st.title("🏡 Airbnb Global Market Analytics")

tab1, tab2 = st.tabs(["📊 Analytics Overview", "⚔️ Comparison Center"])

# --- หน้าที่ 1: วิเคราะห์ภาพรวม ---
with tab1:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Price", f"${filtered_df['price'].mean():,.0f}")
    m2.metric("Total Reviews", f"{filtered_df['number_of_reviews'].sum():,}")
    m3.metric("Avg Rating", f"{filtered_df['rating'].mean()/10:,.1f} / 10")
    m4.metric("Total Listings", f"{len(filtered_df):,}")

    st.markdown("---")
    
    st.subheader("🌐 Global Price Comparison (All Countries)")
    no_country_filter_df = df.copy()
    if f_prop: no_country_filter_df = no_country_filter_df[no_country_filter_df['property_type'].isin(f_prop)]
    if f_room: no_country_filter_df = no_country_filter_df[no_country_filter_df['room_type'].isin(f_room)]
    no_country_filter_df = no_country_filter_df[(no_country_filter_df['price'].between(f_price[0], f_price[1])) & (no_country_filter_df['rating'] >= f_rate)]
    
    avg_data = no_country_filter_df.groupby('country').agg({'price': 'mean', 'rating': 'mean'}).reset_index().sort_values('price', ascending=False)
    
    fig_avg = px.bar(avg_data, x='country', y='price', color='rating', color_continuous_scale="Viridis", text_auto='.2f')
    fig_avg.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white',
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'))
    st.plotly_chart(fig_avg, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🗺️ Global Price Density Heatmap")
    fig_heatmap = px.density_mapbox(filtered_df, lat="lat", lon="lon", z="price", radius=12, zoom=1, height=500, mapbox_style="carto-darkmatter", color_continuous_scale="YlOrRd")
    fig_heatmap.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Top 10 Most Visited (By Review Count)")
    top_visited = filtered_df.sort_values('number_of_reviews', ascending=False).head(10)
    fig_v = px.bar(top_visited, x="number_of_reviews", y="short_name", orientation='h', color="number_of_reviews", color_continuous_scale="Blues")
    fig_v.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")
    st.subheader("⭐ Top 10 Highest Rated Listings")
    top_rate = filtered_df.sort_values(['rating', 'number_of_reviews'], ascending=False).head(10)
    fig_r = px.bar(top_rate, x="rating", y="short_name", orientation='h', color="rating", color_continuous_scale="Magma")
    fig_r.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📋 Full Data Explorer")
    st.dataframe(filtered_df[['name', 'country', 'property_type', 'room_type', 'price', 'rating', 'number_of_reviews', 'accommodates']], use_container_width=True, hide_index=True)

# --- หน้าที่ 2: Compare ---
with tab2:
    st.title("⚔️ Comparison Engine")
    s1, s2 = st.columns(2)
    with s1: choice1 = st.selectbox("เลือกที่พักที่ 1:", options=df['name'].unique(), key="comp1")
    with s2: choice2 = st.selectbox("เลือกที่พักที่ 2:", options=df['name'].unique(), key="comp2")
    st.markdown("---")
    d1, d2 = df[df['name'] == choice1].iloc[0], df[df['name'] == choice2].iloc[0]
    left, right = st.columns(2)
    def display_comparison(data, column):
        with column:
            st.subheader(data['name'])
            if data['image_url']: st.image(data['image_url'], use_container_width=True)
            else: st.warning("⚠️ No Image Available")
            m_c1, m_c2 = st.columns(2)
            m_c1.metric("Price", f"${data['price']:,.2f}")
            m_c2.metric("Satisfaction", f"{data['rating']}%")
            info_df = pd.DataFrame({"Category": ["Type", "Room", "Guests", "Bedrooms", "Beds", "Reviews"], "Details": [data['property_type'], data['room_type'], f"{data['accommodates']}", f"{data['bedrooms']}", f"{data['beds']}", f"{data['number_of_reviews']}"]})
            st.table(info_df.set_index('Category'))
            with st.expander("📄 Summary"): st.write(data['summary'] if data['summary'] else "None.")
            with st.expander("✨ Amenities"): st.write(", ".join(data['amenities']) if data['amenities'] else "None.")
    display_comparison(d1, left)
    display_comparison(d2, right)