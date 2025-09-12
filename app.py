import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# Configuración de la página
st.set_page_config(
    page_title="🚀 Analizador de Ciclos RSI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def calculate_rsi(prices, period=14):
    """Calcula el RSI para una serie de precios"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def detect_rsi_crosses(rsi_series, overbought=70, oversold=30):
    """Detecta cruces del RSI por encima de 70 o por debajo de 30"""
    crosses = []
    for i in range(1, len(rsi_series)):
        current_rsi = rsi_series.iloc[i]
        prev_rsi = rsi_series.iloc[i-1]
        if prev_rsi <= overbought and current_rsi > overbought:
            crosses.append((i, 'overbought', current_rsi))
        elif prev_rsi >= oversold and current_rsi < oversold:
            crosses.append((i, 'oversold', current_rsi))
    return crosses

def calculate_ohlc_average(row):
    """Calcula el promedio de Open, High, Low, Close"""
    return (row['Open'] + row['High'] + row['Low'] + row['Close']) / 4

def create_cycles(crosses, data_length):
    """Crea ciclos desde un cruce hasta el siguiente"""
    cycles = []
    for i in range(len(crosses)):
        start_idx = crosses[i][0]
        if i < len(crosses) - 1:
            end_idx = crosses[i+1][0] - 1
        else:
            end_idx = data_length - 1
        cycles.append({
            'start': start_idx,
            'end': end_idx,
            'cross_type': crosses[i][1],
            'cross_rsi': crosses[i][2]
        })
    return cycles

def create_interactive_plot(symbol, data, crosses, cycles):
    """Crea un gráfico interactivo con Plotly"""
    
    # Crear subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=[f'{symbol} - Ciclos RSI', 'RSI']
    )
    
    # Determinar colores de los ciclos
    cycle_colors = []
    for cycle in cycles:
        cross_price = data['OHLC_Avg'].iloc[cycle['start']]
        last_close = data['Close'].iloc[cycle['end']]
        color = 'green' if last_close > cross_price else 'red'
        cycle_colors.append(color)
    
    # Crear candlestick por ciclos
    for i, cycle in enumerate(cycles):
        start_idx = cycle['start']
        end_idx = min(cycle['end'], len(data) - 1)
        color = cycle_colors[i]
        
        cycle_data = data.iloc[start_idx:end_idx + 1]
        
        # Candlestick para este ciclo
        fig.add_trace(
            go.Candlestick(
                x=cycle_data.index,
                open=cycle_data['Open'],
                high=cycle_data['High'],
                low=cycle_data['Low'],
                close=cycle_data['Close'],
                increasing_line_color='darkgreen' if color == 'green' else 'green',
                decreasing_line_color='darkred' if color == 'red' else 'red',
                increasing_fillcolor='rgba(0, 255, 0, 0.7)' if color == 'green' else 'rgba(0, 128, 0, 0.7)',
                decreasing_fillcolor='rgba(255, 0, 0, 0.7)' if color == 'red' else 'rgba(128, 0, 0, 0.7)',
                name=f'Ciclo {i+1} ({cycle["cross_type"]})',
                showlegend=i == 0  # Solo mostrar leyenda para el primer ciclo
            ),
            row=1, col=1
        )
    
    # Puntos de cruce
    cross_dates = [data.index[idx] for idx, _, _ in crosses if idx < len(data)]
    cross_prices = [data['OHLC_Avg'].iloc[idx] for idx, _, _ in crosses if idx < len(data)]
    cross_rsi = [rsi_val for idx, _, rsi_val in crosses if idx < len(data)]
    
    # Puntos de cruce en el gráfico de precios
    fig.add_trace(
        go.Scatter(
            x=cross_dates,
            y=cross_prices,
            mode='markers+text',
            marker=dict(color='blue', size=10),
            text=[f'${price:.2f}' for price in cross_prices],
            textposition='middle left',
            name='Cruces RSI',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Gráfico RSI
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data['RSI'],
            mode='lines',
            name='RSI',
            line=dict(color='purple', width=2)
        ),
        row=2, col=1
    )
    
    # Líneas de RSI 70 y 30
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # Puntos de cruce en RSI
    fig.add_trace(
        go.Scatter(
            x=cross_dates,
            y=cross_rsi,
            mode='markers',
            marker=dict(color='blue', size=8),
            name='Cruces RSI',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Configurar layout
    fig.update_layout(
        title=dict(
            text=f'{symbol} - Análisis de Ciclos RSI',
            x=0.5,
            font=dict(size=20)
        ),
        xaxis_rangeslider_visible=False,
        height=700,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(title_text="Fecha", row=2, col=1)
    fig.update_yaxes(title_text="Precio ($)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
    
    return fig

def main():
    # Título y descripción
    st.title("🚀 Analizador de Ciclos RSI")
    st.markdown("""
    Esta aplicación analiza ciclos RSI y colorea las velas según el resultado final de cada ciclo:
    - **Verde**: Cierre final > Precio de cruce
    - **Rojo**: Cierre final < Precio de cruce
    """)
    
    # Sidebar para parámetros
    st.sidebar.header("📊 Parámetros de Análisis")
    
    # Inputs del usuario
    symbol = st.sidebar.text_input(
        "📈 Símbolo:",
        value="BTC-USD",
        help="Ejemplo: AAPL, TSLA, BTC-USD, ETH-USD"
    ).strip().upper()
    
    interval_options = {
        "1 minuto": "1m",
        "5 minutos": "5m", 
        "15 minutos": "15m",
        "1 hora": "1h",
        "1 día": "1d",
        "1 semana": "1wk"
    }
    
    interval_display = st.sidebar.selectbox(
        "⏱️ Temporalidad:",
        options=list(interval_options.keys()),
        index=4  # 1d por defecto
    )
    interval = interval_options[interval_display]
    
    period_options = {
        "7 días": "7d",
        "1 mes": "1mo",
        "3 meses": "3mo", 
        "6 meses": "6mo",
        "1 año": "1y",
        "2 años": "2y",
        "5 años": "5y",
        "Máximo": "max"
    }
    
    period_display = st.sidebar.selectbox(
        "📅 Período:",
        options=list(period_options.keys()),
        index=4  # 1 año por defecto
    )
    period = period_options[period_display]
    
    # Parámetros RSI
    st.sidebar.subheader("⚙️ Configuración RSI")
    rsi_period = st.sidebar.slider("Período RSI:", 5, 50, 14)
    overbought = st.sidebar.slider("Nivel sobrecompra:", 60, 90, 70)
    oversold = st.sidebar.slider("Nivel sobreventa:", 10, 40, 30)
    
    # Botón de análisis
    if st.sidebar.button("🚀 Ejecutar Análisis", type="primary"):
        
        with st.spinner(f"📡 Descargando datos de {symbol}..."):
            try:
                # Descargar datos
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period, interval=interval)
                
                if data.empty:
                    st.error("❌ No se pudieron descargar los datos. Verifica el símbolo.")
                    return
                
                # Calcular indicadores
                data['RSI'] = calculate_rsi(data['Close'], rsi_period)
                data['OHLC_Avg'] = data.apply(calculate_ohlc_average, axis=1)
                
                # Detectar cruces
                crosses = detect_rsi_crosses(data['RSI'], overbought, oversold)
                
                if not crosses:
                    st.warning("⚠️ No se detectaron cruces del RSI en el período analizado.")
                    return
                
                # Crear ciclos
                cycles = create_cycles(crosses, len(data))
                
                # Mostrar métricas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📊 Total Velas", len(data))
                
                with col2:
                    st.metric("🔄 Cruces RSI", len(crosses))
                
                with col3:
                    green_cycles = sum(1 for i, cycle in enumerate(cycles) 
                                     if data['Close'].iloc[cycle['end']] > data['OHLC_Avg'].iloc[cycle['start']])
                    st.metric("🟢 Ciclos Verdes", green_cycles)
                
                with col4:
                    red_cycles = len(cycles) - green_cycles
                    st.metric("🔴 Ciclos Rojos", red_cycles)
                
                # Crear y mostrar gráfico
                fig = create_interactive_plot(symbol, data, crosses, cycles)
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabla de cruces
                st.subheader("📋 Detalle de Cruces")
                
                crosses_data = []
                for i, (idx, cross_type, rsi_value) in enumerate(crosses):
                    if idx < len(data):
                        date = data.index[idx].strftime('%Y-%m-%d %H:%M')
                        price = data['OHLC_Avg'].iloc[idx]
                        crosses_data.append({
                            'Fecha': date,
                            'Tipo': cross_type.capitalize(),
                            'Precio': f"${price:.2f}",
                            'RSI': f"{rsi_value:.1f}"
                        })
                
                crosses_df = pd.DataFrame(crosses_data)
                st.dataframe(crosses_df, use_container_width=True)
                
                # Estadísticas de ciclos
                if cycles:
                    st.subheader("📈 Estadísticas de Ciclos")
                    
                    win_rate = (green_cycles / len(cycles)) * 100
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("🎯 Tasa de Éxito", f"{win_rate:.1f}%")
                    
                    with col2:
                        avg_cycle_length = sum(cycle['end'] - cycle['start'] + 1 for cycle in cycles) / len(cycles)
                        st.metric("📏 Duración Promedio", f"{avg_cycle_length:.1f} velas")
                
            except Exception as e:
                st.error(f"❌ Error durante el análisis: {str(e)}")
    
    # Información adicional
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### ℹ️ Información
    - **Verde**: El precio de cierre final del ciclo está por encima del precio de cruce
    - **Rojo**: El precio de cierre final del ciclo está por debajo del precio de cruce
    - Los puntos azules indican los momentos de cruce del RSI
    """)
    
    # Footer
    st.markdown("---")
    st.markdown("🔧 Desarrollado con Streamlit • 📊 Datos de Yahoo Finance")

if __name__ == "__main__":
    main()