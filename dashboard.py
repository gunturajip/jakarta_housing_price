import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import os
import tempfile

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from google.cloud import bigquery
from cryptography.fernet import Fernet

st.set_page_config(
    page_title="Jakarta Housing Prices Dashboard",
    layout="wide"
)

reduce_header_height_style = """
    <style>
        div.block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
"""
st.markdown(reduce_header_height_style, unsafe_allow_html=True)

hide_decoration_bar_style = """
    <style>
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

st.markdown(f"<h1 style='text-align: center;'>Jakarta Housing Prices Dashboard</h1>", unsafe_allow_html=True)

today = datetime.now() + timedelta(hours=7)
today = today.date()

date_filter = st.date_input(
    label="Select here to choose the dates",
    value=[today - timedelta(weeks=1), today]
    # value=[today - timedelta(days=1), today]
)

with st.sidebar:
    st.markdown("<p>This dashboard shows house prices in Jakarta based on data taken from <a href='http://rumah123.com/'>Rumah123</a>. It is updated daily.</p>", unsafe_allow_html=True)

    st.markdown("""
        <p>Libraries that are used for creating this dashboard:</p>
        <ul>
            <li><div style="width:20px; height:20px; display:inline-block; vertical-align: middle; background:url('https://raw.githubusercontent.com/darren7753/jakarta_housing_price/main/icons/selenium.png') no-repeat center center; background-size: contain;"></div> <b>Selenium</b> for scraping the data</li>
            <li><div style="width:20px; height:20px; display:inline-block; vertical-align: middle; background:url('https://raw.githubusercontent.com/darren7753/jakarta_housing_price/main/icons/numpy.png') no-repeat center center; background-size: contain;"></div> <b>NumPy</b> and <div style="width:20px; height:20px; display:inline-block; vertical-align: middle; background:url('https://raw.githubusercontent.com/darren7753/jakarta_housing_price/main/icons/pandas.png') no-repeat center center; background-size: contain;"></div> <b>Pandas</b> for cleaning the data</li>
            <li><div style="width:20px; height:20px; display:inline-block; vertical-align: middle; background:url('https://raw.githubusercontent.com/darren7753/jakarta_housing_price/main/icons/altair.png') no-repeat center center; background-size: contain;"></div> <b>Altair</b> for creating the graphs</li>
            <li><div style="width:20px; height:20px; display:inline-block; vertical-align: middle; background:url('https://raw.githubusercontent.com/darren7753/jakarta_housing_price/main/icons/streamlit.png') no-repeat center center; background-size: contain;"></div> <b>Streamlit</b> for building the dashboard</li>
        </ul>
    """, unsafe_allow_html=True)

    font_awesome = '<link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.12.1/css/all.css" crossorigin="anonymous">'

    st.markdown(font_awesome + """
        <br>
        <p>Made by <b>Mathew Darren</b></p>
        <a href='https://github.com/darren7753'><i class='fab fa-github' style='font-size: 30px; color: #fafafa;'></i></a>&nbsp;
        <a href='https://www.linkedin.com/in/mathewdarren/'><i class='fab fa-linkedin' style='font-size: 30px; color: #fafafa;'></i></a>&nbsp;
        <a href='https://www.instagram.com/darren_matthew_/'><i class='fab fa-instagram' style='font-size: 30px; color: #fafafa;'></i></a>
    """, unsafe_allow_html=True)

key = os.environ.get("FERNET_KEY")
cipher_suite = Fernet(key)

with open("encryption/encrypted_data.bin", "rb") as file:
    encrypted_data = file.read()
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()

with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
    temp_file.write(decrypted_data.encode())
    temp_file_path = temp_file.name

target_table = "real_estate.jakarta"
project_id = "jakarta-housing-price"
job_location = "asia-southeast2"

credentials = Credentials.from_service_account_file(temp_file_path)
client = bigquery.Client(credentials=credentials, project=project_id)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path

def fetch_data_from_bigquery(query):
    """Fetch data using BigQuery."""
    client = bigquery.Client()
    return client.query(query).to_dataframe()

@st.cache_data
def fetch_data(start_date, end_date):
    """Fetch data based on date range."""
    sql_query = f"""
        SELECT * FROM `{project_id}.{target_table}`
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
    """
    return fetch_data_from_bigquery(sql_query)

os.remove(temp_file_path)

start_date, end_date = date_filter
previous_start_date = start_date - (end_date - start_date)
previous_end_date = start_date

df = fetch_data(start_date, end_date)
previous_df = fetch_data(previous_start_date, previous_end_date)

def cleaning_data(data):
    data["date"] = pd.to_datetime(data["date"])
    data = data.drop(["address", "kemendagri_code", "latitude_longitude"], axis=1)
    data["city"] = data["district"].str.split(",").str[1].str.strip()
    data["district"] = data["district"].str.split(",").str[0].str.strip()

    outlier_columns = ["price_idr", "land_m2", "building_m2"]   

    for col in outlier_columns:
        q1 = data[col].quantile(0.25)
        q3 = data[col].quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        data = data[(data[col] >= lower_bound) & (data[col] <= upper_bound)].reset_index(drop=True)

    return data

df = cleaning_data(df)
previous_df = cleaning_data(previous_df)

st.markdown("""
    <style type="text/css">
    div[data-testid="stHorizontalBlock"] > div {
        padding: 15px;
        margin: 0px;
        border-radius: 10px;
        background: #2c3858;
    }
    </style>
""", unsafe_allow_html=True)

metric_css = '''
    [data-testid="metric-container"] {
        width: fit-content;
        margin: auto;
    }

    [data-testid="metric-container"] > div {
        width: fit-content;
        margin: auto;
    }

    [data-testid="metric-container"] label {
        width: fit-content;
        margin: auto;
    }
'''

def calculate_growth_and_style(current_metric, previous_metric):
    try:
        growth = ((current_metric - previous_metric) / previous_metric) * 100
        if growth > 0:
            return growth, "normal"
        elif growth < 0:
            return growth, "normal"
        elif growth == 0:
            return "No change", "off"
        else:
            return "No previous data", "off"
    except ZeroDivisionError:
        return "No previous data", "off"
    
label_expr_price = "datum.value >= 1000000000000 ? 'Rp' + datum.value / 1000000000000 + 'T' : (datum.value >= 1000000000 ? 'Rp' + datum.value / 1000000000 + 'B' : (datum.value >= 1000000 ? 'Rp' + datum.value / 1000000 + 'M' : (datum.value >= 1000 ? 'Rp' + datum.value / 1000 + 'K' : 'Rp' + datum.value)))"

col1, col2, col3 = st.columns(3)

with col1:
    avg = df["price_idr"].mean()
    previous_avg = previous_df["price_idr"].mean()
    growth, color = calculate_growth_and_style(avg, previous_avg)
    if type(growth) != str:
        st.metric(label="Average House Prices", value=f"Rp{avg:,.2f}", delta=f"{growth:,.2f}% from the previous period", delta_color=color)
    else:
        st.metric(label="Average House Prices", value=f"Rp{avg:,.2f}", delta=f"{growth} from the previous period", delta_color=color)
    st.markdown(f"<style>{metric_css}</style>", unsafe_allow_html=True)

with col2:
    med = df["price_idr"].median()
    previous_med = previous_df["price_idr"].median()
    growth, color = calculate_growth_and_style(med, previous_med)
    if type(growth) != str:
        st.metric(label="Median House Prices", value=f"Rp{med:,.2f}", delta=f"{growth:,.2f}% from the previous period", delta_color=color)
    else:
        st.metric(label="Median House Prices", value=f"Rp{med:,.2f}", delta=f"{growth} from the previous period", delta_color=color)
    st.markdown(f"<style>{metric_css}</style>", unsafe_allow_html=True)

with col3:
    no_houses = len(df)
    previous_no_houses = len(previous_df)
    growth, color = calculate_growth_and_style(no_houses, previous_no_houses)
    if type(growth) != str:
        st.metric(label="Number of Houses Scraped", value=f"{no_houses:,}", delta=f"{growth:,.2f}% from the previous period", delta_color=color)
    else:
        st.metric(label="Number of Houses Scraped", value=f"{no_houses:,}", delta=f"{growth} from the previous period", delta_color=color)
    st.markdown(f"<style>{metric_css}</style>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"<h4 style='text-align: center;'>Average & Median House Prices by District</h4>", unsafe_allow_html=True)

    agg_price_district_df = df.groupby("district").agg(
        average = ("price_idr", np.mean),
        median = ("price_idr", np.median)
    ).reset_index()

    regions = alt.topo_feature("https://raw.githubusercontent.com/darren7753/jakarta_housing_price/main/Kecamatan-DKI-Jakarta.topojson", "data")

    tabs = st.tabs(["Average", "Median"])

    with tabs[0]:
        base = alt.Chart(regions).mark_geoshape(
            stroke="black",
            strokeWidth=1
        ).encode(
        ).properties(
            # width=450,
            # height=450
        )

        choro = alt.Chart(regions).mark_geoshape(
            stroke="black",
            strokeWidth=1
        ).encode(
            color=alt.Color(
                "average:Q", 
                scale=alt.Scale(scheme="blues"),
                legend=alt.Legend(
                    title="Average Price",
                    labelFontSize=18,
                    titleFontSize=18,
                    labelExpr=label_expr_price
                )
            ),
            tooltip=[
                alt.Tooltip("properties.name:N", title="District"),
                alt.Tooltip("formatted_price:N", title="Average Price")
            ]
        ).transform_lookup(
            lookup="properties.name",
            from_=alt.LookupData(agg_price_district_df, "district", ["average"])
        ).transform_calculate(
            formatted_price="('Rp' + format(datum.average, ',.2f'))"
        )

        chart = (base + choro).configure_view(
            strokeOpacity=0
        ).configure(
            background="transparent"
        )

        st.altair_chart(chart, use_container_width=True)

    with tabs[1]:
        base = alt.Chart(regions).mark_geoshape(
            stroke="black",
            strokeWidth=1
        ).encode(
        ).properties(
            # width=450,
            # height=450
        )

        choro = alt.Chart(regions).mark_geoshape(
            stroke="black",
            strokeWidth=1
        ).encode(
            color=alt.Color(
                "median:Q", 
                scale=alt.Scale(scheme="blues"),
                legend=alt.Legend(
                    title="Median Price",
                    labelFontSize=18,
                    titleFontSize=18,
                    labelExpr=label_expr_price
                )
            ),
            tooltip=[
                alt.Tooltip("properties.name:N", title="District"),
                alt.Tooltip("formatted_price:N", title="Median Price")
            ]
        ).transform_lookup(
            lookup="properties.name",
            from_=alt.LookupData(agg_price_district_df, "district", ["median"])
        ).transform_calculate(
            formatted_price="('Rp' + format(datum.median, ',.2f'))"
        )

        chart = (base + choro).configure_view(
            strokeOpacity=0
        ).configure(
            background="transparent"
        )

        st.altair_chart(chart, use_container_width=True)

with col2:
    st.markdown(f"<h4 style='text-align: center;'>Average & Median House Prices by City</h4>", unsafe_allow_html=True)

    agg_price_city_df = df.groupby("city").agg(
        average = ("price_idr", np.mean),
        median = ("price_idr", np.median)
    ).reset_index()

    sorted_cities = agg_price_city_df.sort_values("average", ascending=False)["city"].tolist()

    agg_price_city_df = agg_price_city_df.melt(
        id_vars=["city"], 
        value_vars=["average", "median"],
        var_name="measure", 
        value_name="price"
    )

    chart = alt.Chart(agg_price_city_df).transform_calculate(
        formatted_price="('Rp' + format(datum.price, ',.2f'))"
    ).mark_bar(
        cornerRadiusTopLeft=7,
        cornerRadiusTopRight=7
    ).encode(
        x=alt.X("city", title="", sort=sorted_cities, axis=alt.Axis(labelAngle=-90, labelFontSize=18, labelLimit=200)),
        xOffset="measure",
        y=alt.Y(
            "price",
            title="Price",
            axis=alt.Axis(
                grid=False,
                labelFontSize=18,
                titleFontSize=18,
                labelExpr=label_expr_price
            )
        ),
        color=alt.Color("measure", legend=alt.Legend(title="", labelFontSize=14, columns=1, orient="right")),
        tooltip=[alt.Tooltip("city", title="City"), alt.Tooltip("formatted_price:N", title="Price")]
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    ).properties(
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"<h4 style='text-align: center;'>Distribution of House Prices</h4>", unsafe_allow_html=True)

    chart = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=7,
        cornerRadiusTopRight=7
    ).transform_calculate(
        formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
    ).encode(
        x=alt.X(
            "price_idr:Q",
            title="Price",
            bin=alt.BinParams(maxbins=20),
            axis=alt.Axis(
                labelFontSize=18,
                titleFontSize=18,
                labelExpr=label_expr_price
            )
        ),
        y=alt.Y("count()", axis=alt.Axis(grid=False, labelFontSize=18, titleFontSize=18)),
        tooltip=[
            alt.Tooltip("formatted_price:N", title="Price"),
            alt.Tooltip("count()", title="Count of Records")
        ]
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    ).properties(
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

with col2:
    st.markdown(f"<h4 style='text-align: center;'>Correlation of Features & House Prices</h4>", unsafe_allow_html=True)
    regression_checkbox = st.checkbox("Add a regression line")
    tabs = st.tabs(["Land Area", "Building Area", "Bedroom", "Bathroom", "Garage"])

    # with tabs[0]:
    #     x = "monthly_payment_idr"
    #     title_x = "Monthly Payment"
    #     y = "price_idr"
    #     title_y = "Price"

    #     scatter_plot = alt.Chart(df).transform_calculate(
    #         formatted_monthly_payment="('Rp' + format(datum.monthly_payment_idr, ',.2f'))",
    #         formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
    #     ).mark_point(
    #         size=100
    #     ).encode(
    #         x=alt.X(x, title=title_x, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
    #         y=alt.Y(y, title=title_y, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
    #         tooltip=[alt.Tooltip("formatted_monthly_payment:N", title=title_x), alt.Tooltip("formatted_price:N", title=title_y)]
    #     )

    #     if regression_checkbox:
    #         regression_line = scatter_plot.transform_regression(x, y).mark_line(size=3, color="#4b90ff")

    #         chart = (scatter_plot + regression_line).configure_view(
    #             stroke=None
    #         ).configure(
    #             background="transparent"
    #         ).properties(
    #             height=300
    #         )

    #     else:
    #         chart = scatter_plot.configure_view(
    #             stroke=None
    #         ).configure(
    #             background="transparent"
    #         ).properties(
    #             height=300
    #         )

    #     st.altair_chart(chart, use_container_width=True)

    with tabs[0]:
        x = "land_m2"
        title_x = "Land Area"
        y = "price_idr"
        title_y = "Price"

        scatter_plot = alt.Chart(df).transform_calculate(
            formatted_land_area="(format(datum.land_m2, ',') + ' m²')",
            formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
        ).mark_point(
            size=100
        ).encode(
            x=alt.X(x, title=title_x, axis=alt.Axis(grid=False, labelExpr="datum.value + ' m²'", labelFontSize=18, titleFontSize=18)),
            y=alt.Y(y, title=title_y, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
            tooltip=[alt.Tooltip("formatted_land_area:N", title=title_x), alt.Tooltip("formatted_price:N", title=title_y)]
        )

        if regression_checkbox:
            regression_line = scatter_plot.transform_regression(x, y).mark_line(size=3, color="#4b90ff")

            chart = (scatter_plot + regression_line).configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        else:
            chart = scatter_plot.configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        st.altair_chart(chart, use_container_width=True)

    with tabs[1]:
        x = "building_m2"
        title_x = "Building Area"
        y = "price_idr"
        title_y = "Price"

        scatter_plot = alt.Chart(df).transform_calculate(
            formatted_building_area="(format(datum.building_m2, ',') + ' m²')",
            formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
        ).mark_point(
            size=100
        ).encode(
            x=alt.X(x, title=title_x, axis=alt.Axis(grid=False, labelExpr="datum.value + ' m²'", labelFontSize=18, titleFontSize=18)),
            y=alt.Y(y, title=title_y, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
            tooltip=[alt.Tooltip("formatted_building_area:N", title=title_x), alt.Tooltip("formatted_price:N", title=title_y)]
        )

        if regression_checkbox:
            regression_line = scatter_plot.transform_regression(x, y).mark_line(size=3, color="#4b90ff")

            chart = (scatter_plot + regression_line).configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        else:
            chart = scatter_plot.configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        st.altair_chart(chart, use_container_width=True)

    with tabs[2]:
        x = "bedroom"
        title_x = "Bedroom"
        y = "price_idr"
        title_y = "Price"

        scatter_plot = alt.Chart(df).transform_calculate(
            formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
        ).mark_point(
            size=100
        ).encode(
            x=alt.X(x, title=title_x, axis=alt.Axis(grid=False, labelFontSize=18, titleFontSize=18)),
            y=alt.Y(y, title=title_y, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
            tooltip=[alt.Tooltip(x, title=title_x), alt.Tooltip("formatted_price:N", title=title_y)]
        )

        if regression_checkbox:
            regression_line = scatter_plot.transform_regression(x, y).mark_line(size=3, color="#4b90ff")

            chart = (scatter_plot + regression_line).configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        else:
            chart = scatter_plot.configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        st.altair_chart(chart, use_container_width=True)

    with tabs[3]:
        x = "bathroom"
        title_x = "Bathroom"
        y = "price_idr"
        title_y = "Price"

        scatter_plot = alt.Chart(df).transform_calculate(
            formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
        ).mark_point(
            size=100
        ).encode(
            x=alt.X(x, title=title_x, axis=alt.Axis(grid=False, labelFontSize=18, titleFontSize=18)),
            y=alt.Y(y, title=title_y, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
            tooltip=[alt.Tooltip(x, title=title_x), alt.Tooltip("formatted_price:N", title=title_y)]
        )

        if regression_checkbox:
            regression_line = scatter_plot.transform_regression(x, y).mark_line(size=3, color="#4b90ff")

            chart = (scatter_plot + regression_line).configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        else:
            chart = scatter_plot.configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        st.altair_chart(chart, use_container_width=True)

    with tabs[4]:
        x = "garage"
        title_x = "Garage"
        y = "price_idr"
        title_y = "Price"

        scatter_plot = alt.Chart(df).transform_calculate(
            formatted_price="('Rp' + format(datum.price_idr, ',.2f'))"
        ).mark_point(
            size=100
        ).encode(
            x=alt.X(x, title=title_x, axis=alt.Axis(grid=False, labelFontSize=18, titleFontSize=18)),
            y=alt.Y(y, title=title_y, axis=alt.Axis(grid=False, labelExpr=label_expr_price, labelFontSize=18, titleFontSize=18)),
            tooltip=[alt.Tooltip(x, title=title_x), alt.Tooltip("formatted_price:N", title=title_y)]
        )

        if regression_checkbox:
            regression_line = scatter_plot.transform_regression(x, y).mark_line(size=3, color="#4b90ff")

            chart = (scatter_plot + regression_line).configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        else:
            chart = scatter_plot.configure_view(
                stroke=None
            ).configure(
                background="transparent"
            ).properties(
                height=300
            )

        st.altair_chart(chart, use_container_width=True)