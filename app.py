import streamlit as st
from googleapiclient.discovery import build
import requests
import pandas as pd
import time

# --- Configuração Visual ---
st.set_page_config(page_title="SEO Link Auditor", layout="wide", page_icon="🕵️‍♀️")

st.title("🕵️‍♀️ Auditor de Backlinks & Menções")
st.markdown("Monitoramento de onde seu site está aparecendo na web.")

# --- Credenciais ---
if 'GOOGLE_API_KEY' in st.secrets and 'SEARCH_ENGINE_ID' in st.secrets:
    api_key = st.secrets['GOOGLE_API_KEY']
    cse_id = st.secrets['SEARCH_ENGINE_ID']
    credentials_ok = True
else:
    st.warning("⚠️ Configure suas chaves no .streamlit/secrets.toml")
    with st.sidebar:
        api_key = st.text_input("API Key", type="password")
        cse_id = st.text_input("Engine ID")
    credentials_ok = bool(api_key and cse_id)

# --- Funções do Core ---

def google_search(query, api_key, cse_id, num_results):
    results = []
    service = build("customsearch", "v1", developerKey=api_key)
    
    # Área visual de progresso
    status_box = st.status("Iniciando varredura...", expanded=True)
    
    for start_index in range(1, num_results + 1, 10):
        try:
            status_box.write(f"🔎 Minerando lote {start_index} a {start_index+9}...")
            time.sleep(0.3)
            
            res = service.cse().list(
                q=query,
                cx=cse_id,
                start=start_index,
                num=10,
                filter='0' # Importante: Traz tudo sem filtrar duplicados
            ).execute()
            
            if 'items' in res:
                for item in res['items']:
                    results.append({
                        'Título': item.get('title'),
                        'Link de Origem': item.get('link'),
                        'Trecho': item.get('snippet'),
                        'Status': 'Pendente',
                        'Verificado': False
                    })
            else:
                break
                
        except Exception as e:
            # Ignora erros de fim de paginação
            break
        
        if len(results) >= num_results:
            break
    
    status_box.update(label=f"✅ Sucesso! {len(results)} referências encontradas.", state="complete", expanded=False)
    return pd.DataFrame(results)

def check_status_code(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        return str(response.status_code)
    except:
        return "Erro"

# --- Interface e Controles ---

col1, col2 = st.columns([3, 1])
with col1:
    target_site = st.text_input("Domínio do Cliente:", placeholder="ex: zildasimao.com.br")

with col2:
    search_mode = st.radio(
        "Modo de Busca:",
        ("Igual ao Navegador", "Técnico (link:)"),
        help="Use 'Igual ao Navegador' para encontrar Linktree, Jusbrasil e menções."
    )

qtd_busca = st.slider("Quantidade de Resultados:", 10, 100, 50, 10)
btn_search = st.button("🚀 BUSCAR AGORA", type="primary", use_container_width=True)

# --- Lógica Principal ---

if btn_search and credentials_ok:
    if not target_site:
        st.warning("Digite o domínio.")
    else:
        # Limpeza
        clean_site = target_site.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        
        # DECISÃO DO MODO DE BUSCA
        if search_mode == "Igual ao Navegador":
            # Estratégia: Busca o texto exato do domínio. 
            # Isso pega Linktree, Instagram, Jusbrasil igual ao seu print.
            query = f'"{clean_site}" -site:{clean_site}'
            st.info(f"Modo Inteligente: Buscando ocorrências de '{clean_site}' fora do site oficial.")
        else:
            # Estratégia: Operador link: estrito
            query = f'link:{clean_site} -site:{clean_site}'
            st.info(f"Modo Técnico: Buscando apenas backlinks indexados estritamente.")
            
        df = google_search(query, api_key, cse_id, num_results=qtd_busca)
        
        if not df.empty:
            st.session_state['df_results'] = df
            st.rerun()
        else:
            st.error("Nenhum resultado encontrado. Tente mudar o 'Modo de Busca'.")

# --- Exibição ---

if 'df_results' in st.session_state:
    df = st.session_state['df_results']
    
    st.divider()
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Verificado": st.column_config.CheckboxColumn("Sel.", default=True, width="small"),
            "Link de Origem": st.column_config.LinkColumn("Página Encontrada", width="large"),
            "Título": st.column_config.TextColumn("Título da Página", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        disabled=["Título", "Link de Origem", "Trecho", "Status"],
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    if st.button("⚡ Verificar Status (Ping)"):
        bar = st.progress(0)
        to_check = edited_df[edited_df['Verificado']].index
        total = len(to_check)
        
        for i, idx in enumerate(to_check):
            url = edited_df.at[idx, 'Link de Origem']
            code = check_status_code(url)
            
            if code == '200': d = "🟢 200"
            elif code == '404': d = "🔴 404"
            else: d = f"🟠 {code}"
            
            st.session_state['df_results'].at[idx, 'Status'] = d
            bar.progress((i + 1) / total)
            
        st.rerun()
