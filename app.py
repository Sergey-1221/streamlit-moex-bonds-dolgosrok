import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

# Функция для запроса данных по SECID
def get_data(secid):
    url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/trades.html?securities={secid}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        st.error("Не удалось получить данные с сайта MOEX.")
        return None

# Функция для парсинга данных
def parse_data(html_data):
    soup = BeautifulSoup(html_data, 'html.parser')

    headers = soup.find_all('h1')
    tables = soup.find_all('table')

    # Dictionary to store DataFrames
    dataframes = {}

    # Iterate over each header and corresponding table
    for header, table in zip(headers, tables):
        # Get the text inside the <h1> tag to use as a key
        table_name = header.text.strip()

        # Get all rows from the table
        rows = table.find_all('tr')

        # Extract the headers
        column_headers = [header.text for header in rows[0].find_all('th')]

        # Extract the table data
        data = []
        for row in rows[1:]:
            values = [td.text for td in row.find_all('td')]
            data.append(values)

        # Create a Pandas DataFrame
        df = pd.DataFrame(data, columns=column_headers)

        # Convert data types based on column names
        for column in df.columns:
            if "int" in column.lower():
                df[column] = pd.to_numeric(df[column], errors='coerce', downcast='integer')
            elif "double" in column.lower() or "float" in column.lower():
                df[column] = pd.to_numeric(df[column], errors='coerce', downcast='float')
            elif "datetime" in column.lower():
                try:
                    df[column] = pd.to_datetime(df[column], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                except Exception as e:
                    print(f"Error converting column {column} to datetime: {e}")
            elif "time" in column.lower():
                try:
                    df[column] = pd.to_datetime(df[column], format='%H:%M:%S', errors='coerce').dt.time
                except Exception as e:
                    print(f"Error converting column {column} to time: {e}")



        # Store each DataFrame with the <h1> text as the key
        dataframes[table_name] = df

    return dataframes

# Основной код приложения Streamlit
st.title("Данные о торгах облигациями MOEX")

secid = st.text_input("Введите SECID облигации", "RU000A1097X8")

if secid:
    data_html = get_data(secid)

    if data_html:
        df = parse_data(data_html)

        # Отображаем таблицы
        for key, value in df.items():
            st.header(f"{key}")
            st.dataframe(value)

            if key == "trades":
                # Группировка данных по времени торговли для Sell
                grouped_sell = value[value['BUYSELL (string:3)'] == 'S'].groupby('TRADETIME (time:10)', as_index=False)[
                    'VALUE (double)'].sum()

                # Группировка данных по времени торговли для Buy
                grouped_buy = value[value['BUYSELL (string:3)'] == 'B'].groupby('TRADETIME (time:10)', as_index=False)[
                    'VALUE (double)'].sum()

                # Объединение данных по времени торговли, чтобы оба набора были на одной оси X
                merged_data = pd.merge(grouped_sell, grouped_buy, on='TRADETIME (time:10)', how='outer',
                                       suffixes=('_sell', '_buy'))

                # Создание линий для каждого типа сделок
                fig = go.Figure()

                # Линия для Sell
                fig.add_trace(go.Scatter(
                    x=merged_data['TRADETIME (time:10)'],
                    y=merged_data['VALUE (double)_sell'].fillna(0),  # Заполняем пропуски нулями
                    mode='lines',
                    name='Sell Trades (S)',
                    line=dict(color='red', width=2),
                    opacity=0.7  # Полупрозрачность
                ))

                # Линия для Buy
                fig.add_trace(go.Scatter(
                    x=merged_data['TRADETIME (time:10)'],
                    y=merged_data['VALUE (double)_buy'].fillna(0),  # Заполняем пропуски нулями
                    mode='lines',
                    name='Buy Trades (B)',
                    line=dict(color='green', width=2),
                    opacity=0.7  # Полупрозрачность
                ))

                # Настройка графика
                fig.update_layout(
                    title='Объем (Buy vs Sell)',
                    xaxis_title='TRADETIME',
                    yaxis_title='VALUE',
                    legend_title='Trade Type',
                    hovermode='x unified',
                )

                # Показать график
                st.plotly_chart(fig)

            elif key == "trades_yields":
                # Преобразование данных времени в формат datetime
                df = pd.DataFrame(value)
                df['SYSTIME (datetime:19)'] = pd.to_datetime(df['SYSTIME (datetime:19)'])

                # График 1: Линейный график EFFECTIVEYIELD
                fig1 = px.line(df, x='SYSTIME (datetime:19)', y='EFFECTIVEYIELD (double)',
                               title="Effective Yield Over Time")

                # График 2: Линейный график DURATION
                fig2 = px.line(df, x='SYSTIME (datetime:19)', y='DURATION (int32)', title="Duration Over Time")

                # График 3: Линейный график ZSPREADBP
                fig3 = px.line(df, x='SYSTIME (datetime:19)', y='ZSPREADBP (int32)', title="ZSPREADBP Over Time")

                # График 4: Линейный график GSPREADBP
                fig4 = px.line(df, x='SYSTIME (datetime:19)', y='GSPREADBP (int32)', title="GSPREADBP Over Time")

                # Показать все графики в Streamlit
                st.plotly_chart(fig1)
                st.plotly_chart(fig2)
                st.plotly_chart(fig3)
                st.plotly_chart(fig4)

