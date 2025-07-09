import streamlit as st
import pandas as pd
import json
import base64
from datetime import datetime

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Rightpay Analytics",
    page_icon="📊",
    layout="wide"
)

# --- Veri Yükleme ve Hazırlama Fonksiyonu (DOKUNULMADI) ---
@st.cache_data
def load_data(uploaded_files):
    if not uploaded_files: return pd.DataFrame()
    df_list = []
    for file in uploaded_files:
        try:
            file.seek(0)
            temp_df = pd.read_csv(file, low_memory=False)
            temp_df.columns = temp_df.columns.str.strip()
            for col in ['ROYALTY AMOUNT', 'PERF COUNT']:
                if col in temp_df.columns:
                    temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce').fillna(0)
            if 'PERIOD' in temp_df.columns:
                temp_df['PERIOD'] = temp_df['PERIOD'].astype(str)
            df_list.append(temp_df)
        except Exception as e:
            st.warning(f"'{file.name}' okunamadı: {e}")
    if not df_list: return pd.DataFrame()
    return pd.concat(df_list, ignore_index=True)

# --- Yazdırma Fonksiyonu (DOKUNULMADI) ---
def generate_printable_html(report_df, group_by_labels, filter_selections):
    report_table_html = report_df.to_html(index=False, classes="styled-table", escape=False, formatters={'TOTAL_ROYALTY': lambda x: f"${x:,.2f}", 'TOTAL_PERF_COUNT': lambda x: f"{x:,.0f}"})
    group_html = f"<ul><li><b>Rapor Hiyerarşisi:</b> {' → '.join(group_by_labels)}</li></ul>"
    filters_html_parts = []
    if filter_selections['periods']: filters_html_parts.append(f"<li><b>Dönemler:</b> {', '.join(filter_selections['periods'])}</li>")
    if filter_selections['titles']: filters_html_parts.append(f"<li><b>Eserler:</b> {', '.join(filter_selections['titles'])}</li>")
    if filter_selections['countries']: filters_html_parts.append(f"<li><b>Ülkeler:</b> {', '.join(filter_selections['countries'])}</li>")
    if filter_selections['sources']: filters_html_parts.append(f"<li><b>Kaynaklar:</b> {', '.join(filter_selections['sources'])}</li>")
    if filter_selections['shows']: filters_html_parts.append(f"<li><b>Showlar:</b> {', '.join(filter_selections['shows'])}</li>")
    filters_html = "<ul>" + "".join(filters_html_parts) + "</ul>" if filters_html_parts else "<p>Filtre uygulanmadı.</p>"
    report_date = datetime.now().strftime("%d %B %Y, %H:%M")
    html_template = f"""
    <html><head><meta charset="UTF-8"><title>Rightpay Analytics Raporu</title><style>body{{font-family:Arial,sans-serif;margin:25px}}h1,h3{{color:#333}}.styled-table{{width:100%;border-collapse:collapse;margin-top:20px;font-size:10pt}}.styled-table th,.styled-table td{{border:1px solid #ddd;padding:8px;text-align:left}}.styled-table th{{background-color:#f2f2f2;font-weight:bold}}.header{{text-align:center}}hr{{border:0;border-top:1px solid #eee;margin:20px 0}}</style></head>
    <body><div class="header"><h1>Rightpay Analytics Raporu</h1><p>Rapor Tarihi: {report_date}</p></div><hr><h3>Rapor Yapısı</h3>{group_html}<hr><h3>Uygulanan Filtreler</h3>{filters_html}<hr><h3>Detaylı Rapor</h3>{report_table_html}</body></html>"""
    return html_template

# --- Çizgi Grafiği Fonksiyonu (DOKUNULMADI) ---
def create_line_chart_html(df, breakdown_col, top_n):
    if 'PERIOD' not in df.columns or df['PERIOD'].nunique() < 2: return None
    top_items = df.groupby(breakdown_col)['ROYALTY AMOUNT'].sum().nlargest(top_n).index.tolist()
    chart_df = df[df[breakdown_col].isin(top_items)]
    pivot_df = chart_df.pivot_table(index=breakdown_col, columns='PERIOD', values='ROYALTY AMOUNT', aggfunc='sum').fillna(0)
    periods = sorted(pivot_df.columns.tolist())
    series_data = []
    for index, row in pivot_df.iterrows():
        series_data.append({'name': str(index), 'data': [row.get(period, 0) for period in periods]})
    periods_json = json.dumps(periods)
    series_json = json.dumps(series_data)
    html_template = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><style> #container {{ height: 500px; }} </style></head><body>
    <div id="container"></div><script src="https://code.highcharts.com/highcharts.js"></script>
    <script>
        Highcharts.chart('container', {{
            chart: {{ type: 'line' }}, title: {{ text: 'Dönemlere Göre Royalty Trend Analizi' }},
            subtitle: {{ text: 'En Çok Kazandıran {top_n} Kategori' }},
            xAxis: {{ categories: {periods_json} }}, yAxis: {{ title: {{ text: 'Toplam Royalty Tutarı ($)' }} }},
            tooltip: {{ shared: true, crosshairs: true, headerFormat: '<b>Dönem: {{point.key}}</b><br/>', pointFormat: '<span style="color:{{series.color}}">●</span> {{series.name}}: <b>${{point.y:,.2f}}</b><br/>' }},
            plotOptions: {{ line: {{ marker: {{ enabled: true }}, enableMouseTracking: true }} }}, series: {series_json}
        }});
    </script></body></html>
    """
    return html_template

# --- ANA UYGULAMA ---

# --- DEĞİŞİKLİK: Dosya yükleyici kenar çubuğuna taşındı ---
st.sidebar.title("📊 Rapor Kontrol Paneli")
uploaded_files = st.sidebar.file_uploader(
    "CSV Dosyalarını Yükleyin",
    type="csv",
    accept_multiple_files=True
)

if not uploaded_files:
    # Açılış ekranı
    st.set_page_config(page_title="Rightpay Analytics", layout="centered")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except FileNotFoundError:
            st.error("logo.png dosyası bulunamadı. Lütfen logonuzu Python betiği ile aynı klasöre kaydedin.")
        st.write("")
        st.markdown(
            """
            <div style="text-align: center;">
                <h2>Verilerinizi Anlamlı Hale Getirin</h2>
                <p>Başlamak için lütfen sol taraftaki panelden bir veya daha fazla CSV raporu yükleyin.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

else:
    # Raporlama ekranı
    st.set_page_config(page_title="Rightpay Analytics", page_icon="📊", layout="wide")
    st.title("📊 Rightpay Analytics")
    
    df = load_data(uploaded_files)

    if df.empty:
        st.error("Yüklenen dosyalardan geçerli veri okunamadı.")
    else:
        # --- Sidebar'ın geri kalanı ---
        DIMENSION_MAP = {'Dönem': 'PERIOD', 'Eser Adı': 'TITLE NAME', 'Ülke': 'COUNTRY OF PERFORMANCE', 'Performans Kaynağı': 'PERF SOURCE', 'Show Adı': 'SHOW NAME'}
        
        st.sidebar.markdown("### 1. Rapor Hiyerarşisi")
        group_by_labels = st.sidebar.multiselect("Gruplama Sırası:", options=list(DIMENSION_MAP.keys()), default=['Eser Adı', 'Ülke'])
        
        st.sidebar.markdown("### 2. Rapor Metrikleri")
        selected_metrics = st.sidebar.multiselect("Görülecek Değerler:", options=['Royalty Tutarı', 'Performans Sayısı'], default=['Royalty Tutarı'])
        
        st.sidebar.markdown("### 3. Genel Filtreler")
        with st.sidebar.expander("Filtreleri Göster/Gizle", expanded=True):
            def create_filter_ui(label, session_key, options):
                st.markdown(f"**{label}:**")
                if session_key not in st.session_state: st.session_state[session_key] = options
                if f"{session_key}_all" not in st.session_state: st.session_state[f"{session_key}_all"] = True
                def update_checkbox(): st.session_state[f"{session_key}_all"] = set(st.session_state[session_key]) == set(options)
                def checkbox_changed(): st.session_state[session_key] = options if st.session_state[f"{session_key}_all"] else []
                st.checkbox("Tümü", key=f"{session_key}_all", on_change=checkbox_changed)
                st.multiselect(label, options=options, key=session_key, on_change=update_checkbox, label_visibility="collapsed")
                return st.session_state[session_key]
            
            filter_options = {col: sorted(df[col].dropna().unique()) for col in DIMENSION_MAP.values()}
            selected_periods = create_filter_ui("Dönemler", "periods_selection", filter_options['PERIOD'])
            selected_titles = create_filter_ui("Eser Adları", "titles_selection", filter_options['TITLE NAME'])
            selected_countries = create_filter_ui("Ülkeler", "countries_selection", filter_options['COUNTRY OF PERFORMANCE'])
            selected_sources = create_filter_ui("Performans Kaynakları", "sources_selection", filter_options['PERF SOURCE'])
            selected_shows = create_filter_ui("Show Adları", "shows_selection", filter_options['SHOW NAME'])

        # Filtreleme ve raporlama mantığı (DOKUNULMADI)
        query_parts = []
        if selected_periods: query_parts.append("`PERIOD` in @selected_periods")
        if selected_titles: query_parts.append("`TITLE NAME` in @selected_titles")
        if selected_countries: query_parts.append("`COUNTRY OF PERFORMANCE` in @selected_countries")
        if selected_sources: query_parts.append("`PERF SOURCE` in @selected_sources")
        if selected_shows: query_parts.append("(`SHOW NAME` in @selected_shows or `SHOW NAME`.isnull())")
        
        filtered_df = df.query(" and ".join(query_parts), engine='python') if query_parts else pd.DataFrame(columns=df.columns)

        if filtered_df.empty:
            st.warning("Seçtiğiniz filtrelere uygun veri bulunamadı.")
        else:
            # Raporlama ekranının ana gövdesi
            st.header("Genel Bakış")
            total_royalty = filtered_df['ROYALTY AMOUNT'].sum()
            total_perf_count = filtered_df['PERF COUNT'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Filtrelenmiş Satır", f"{len(filtered_df):,}")
            col2.metric("Toplam Royalty", f"${total_royalty:,.2f}")
            col3.metric("Toplam Performans", f"{int(total_perf_count):,}")

            group_by_cols = [DIMENSION_MAP[label] for label in group_by_labels]
            if group_by_cols and selected_metrics:
                st.markdown("---")
                col_header, col_button = st.columns([0.8, 0.2])
                with col_header:
                    st.header("Analiz Raporu Tablosu")
                
                agg_dict = {}
                if 'Royalty Tutarı' in selected_metrics: agg_dict['TOTAL_ROYALTY'] = ('ROYALTY AMOUNT', 'sum')
                if 'Performans Sayısı' in selected_metrics: agg_dict['TOTAL_PERF_COUNT'] = ('PERF COUNT', 'sum')
                report_df = filtered_df.groupby(group_by_cols, as_index=False).agg(**agg_dict)
                if 'TOTAL_ROYALTY' in report_df.columns:
                    report_df = report_df.sort_values(by='TOTAL_ROYALTY', ascending=False)
                
                with col_button:
                    st.write("") 
                    if st.button("🖨️ Raporu Yazdır", use_container_width=True):
                        filter_selections = {'periods': [p for p in selected_periods if p not in filter_options['PERIOD']],'titles': [t for t in selected_titles if t not in filter_options['TITLE NAME']],'countries': [c for c in selected_countries if c not in filter_options['COUNTRY OF PERFORMANCE']],'sources': [s for s in selected_sources if s not in filter_options['PERF SOURCE']],'shows': [s for s in selected_shows if s not in filter_options['SHOW NAME']]}
                        printable_html = generate_printable_html(report_df, group_by_labels, filter_selections)
                        b64_html = base64.b64encode(printable_html.encode('utf-8')).decode()
                        print_js = f'<script>var win=window.open();win.document.write(\'<iframe src="data:text/html;charset=utf-8;base64,{b64_html}" frameborder="0" style="border:0;top:0;left:0;bottom:0;right:0;width:100%;height:100%" allowfullscreen></iframe>\');win.document.close();setTimeout(function(){{win.focus();win.print();win.close();}}, 500);</script>'
                        st.components.v1.html(print_js, height=0)

                st.dataframe(report_df.style.format({'TOTAL_ROYALTY': '${:,.2f}', 'TOTAL_PERF_COUNT': '{:,.0f}'}), use_container_width=True)
            
            st.markdown("---")
            st.header("Trend Analizi Grafiği")
            col_chart1, col_chart2 = st.columns(2)
            breakdown_label = col_chart1.selectbox("Grafik Kırılımını Seçin:", options=['Ülke', 'Eser Adı', 'Performans Kaynağı'], key="line_chart_breakdown")
            top_n = col_chart2.slider(f"Gösterilecek En İyi Kaç {breakdown_label}?", min_value=1, max_value=20, value=5, step=1, key="line_chart_top_n")
            
            breakdown_col_name = DIMENSION_MAP[breakdown_label]
            line_chart_html = create_line_chart_html(filtered_df, breakdown_col_name, top_n)
            
            if line_chart_html:
                st.components.v1.html(line_chart_html, height=520, scrolling=False)
            else:
                st.warning("Trend grafiği oluşturmak için verilerde en az iki farklı 'Dönem (PERIOD)' bulunmalıdır.")

            # --- DEĞİŞİKLİK: Yüklenen dosyalar için şık alt panel ---
            st.markdown("---")
            with st.expander("Yönetilen Dosyalar"):
                for uploaded_file in uploaded_files:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text(uploaded_file.name)
                    with col2:
                        size_kb = uploaded_file.size / 1024
                        st.text(f"{size_kb:.1f} KB")
