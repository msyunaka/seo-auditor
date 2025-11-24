import streamlit as st
from googleapiclient.discovery import build
import requests
import pandas as pd
import time

# --- Configuração da Página ---
st.set_page_config(page_title="SEO Link Auditor", layout="wide", page_icon="🔗")

st.title("🔗 Agência SEO - Auditor de Backlinks (Cumulativo)")
st.markdown("Busca todos os links de uma vez e apresenta em uma lista única para verificação.")

# --- Credenciais ---
if 'GOOGLE_API_KEY' in st.secrets and 'SEARCH_ENGINE_ID' in st.secrets:
    api_key = st.secrets['GOOGLE_API_KEY']
    cse_id = st.secrets['SEARCH_ENGINE_ID']
    credentials_ok = True
else:
    st.warning("⚠️ Credenciais não configuradas nos Secrets.")
    with st.sidebar:
        api_key = st.text_input("Google API Key", type="password")
        cse_id = st.text_input("Search Engine ID (CX)")
    credentials_ok = bool(api_key and cse_id)

# --- Funções ---

def google_search(query, api_key, cse_id, num_results):
    """
    Busca acumulativa. O usuário vê o progresso, mas a lista final é única.
    """
    results = []
    service = build("customsearch", "v1", developerKey=api_key)
    
    # Cria um container visual para mostrar o progresso
    status_container = st.status("Iniciando varredura no Google...", expanded=True)
    
    # Loop de 10 em 10 (Limitação do Google)
    for start_index in range(1, num_results + 1, 10):
        try:
            # Atualiza o status visual
            status_container.write(f"🔍 Buscando lote {start_index} a {start_index+9}...")
            
            time.sleep(0.3) # Respeito à API
            
            res = service.cse().list(
                q=query,
                cx=cse_id,
                start=start_index,
                num=10,
                filter='0' # Traz tudo, sem esconder duplicados
            ).execute()
            
            if 'items' in res:
                new_items = len(res['items'])
                status_container.write(f"✅ Encontrados +{new_items} links neste lote.")
                
                for item in res['items']:
                    results.append({
                        'Título': item.get('title'),
                        'Link de Origem': item.get('link'),
                        'Trecho': item.get('snippet'),
                        'Status': 'Pendente',
                        'Verificado': False
                    })
            else:
                status_container.warning("Google não retornou mais resultados neste ponto.")
                break
                
        except Exception as e:
            status_container.error(f"Parada técnica: {e}")
            break
        
        # Se já atingiu a meta, para
        if len(results) >= num_results:
            break
    
    # Finaliza o status visual
    status_container.update(label=f"Varredura concluída! Total carregado: {len(results)} links.", state="complete", expanded=False)
    
    return pd.DataFrame(results)

def check_status_code(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return str(response.status_code)
    except:
        return "Erro"

# --- Interface ---

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    target_site = st.text_input("Site do Cliente:", placeholder="ex: zildasimao.com.br")
with col2:
    # Slider para você decidir quantos quer buscar de uma vez
    qtd_busca = st.slider("Meta de Links:", min_value=10, max_value=100, value=50, step=10)
with col3:
    st.write("")
    st.write("")
    btn_search = st.button("🚀 INICIAR BUSCA", type="primary", use_container_width=True)

if btn_search and credentials_ok:
    if not target_site:
        st.warning("Digite o site.")
    else:
        clean_site = target_site.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        
        # Query: link:site.com -site:site.com
        query = f'link:{clean_site} -site:{clean_site}'
        
        # Chama a função que mostra o progresso na tela
        df = google_search(query, api_key, cse_id, num_results=qtd_busca)
        
        if not df.empty:
            st.session_state['df_results'] = df
            st.rerun()
        else:
            st.error("Nenhum resultado encontrado. Tente buscar pelo Nome da Marca em vez do link:URL.")

# --- Tabela Única (Cumulativa) ---

if 'df_results' in st.session_state:
    df = st.session_state['df_results']
    
    st.divider()
    st.subheader(f"📋 Lista Completa ({len(df)} resultados)")
    
    # Mostra TODOS os resultados em uma única tabela com rolagem
    edited_df = st.data_editor(
        df,
        column_config={
            "Verificado": st.column_config.CheckboxColumn("Sel.", default=True, width="small"),
            "Link de Origem": st.column_config.LinkColumn("URL Onde está o Backlink", width="large"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
        },
        disabled=["Título", "Link de Origem", "Trecho", "Status"],
        use_container_width=True,
        hide_index=True,
        height=500 # Altura fixa com barra de rolagem para caber muitos links
    )
    
    col_a, col_b = st.columns([1, 4])
    if col_a.button("⚡ Checar Status (Selecionados)"):
        bar = st.progress(0)
        to_check = edited_df[edited_df['Verificado']].index
        
        for i, idx in enumerate(to_check):
            url = edited_df.at[idx, 'Link de Origem']
            code = check_status_code(url)
            
            if code == '200': display = "🟢 200 OK"
            elif code == '404': display = "🔴 404 Off"
            else: display = f"🟠 {code}"
            
            st.session_state['df_results'].at[idx, 'Status'] = display
            bar.progress((i + 1) / len(to_check))
            
        st.rerun()
